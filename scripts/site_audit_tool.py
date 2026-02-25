#!/usr/bin/env python3
"""Generate a lightweight Jekyll site audit report in reports/.

Checks: SEO template coverage, obvious malformed links/placeholders,
mobile/accessibility guardrails, and basic performance hygiene.
"""

from __future__ import annotations

import datetime as dt
import argparse
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / 'reports'

SCAN_TARGETS = [
    '_posts',
    '_blogs',
    'pages',
    '_layouts',
    '_includes',
    'index.html',
    '_config.yml',
]

URL_RE = re.compile(r'https?://[^\s\)\]>\'"]+')
DUP_PROTOCOL_RE = re.compile(r'https?://[^\s\)\]]*https?://')
PLACEHOLDER_RE = re.compile(r'example\.com|localhost|127\.0\.0\.1|\bTODO\b|\bTBD\b')
INTERNAL_LINK_RE = re.compile(r'\]\((/[^)\s?#][^)\s]*)')
LIQUID_RELATIVE_URL_RE = re.compile(
    r'(?:href|src)\s*=\s*["\']\{\{\s*[\'"](/[^\'"]+)[\'"]\s*\|\s*relative_url\s*\}\}["\']'
)
FRONT_MATTER_VALUE_RE = re.compile(r'^[ \t]*([A-Za-z0-9_-]+)[ \t]*:[ \t]*(.+)$', re.MULTILINE)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return path.read_text(encoding='latin-1', errors='ignore')


def iter_files() -> Iterable[Path]:
    for target in SCAN_TARGETS:
        p = ROOT / target
        if p.is_file():
            yield p
        elif p.is_dir():
            for ext in ('*.md', '*.markdown', '*.html', '*.yml', '*.yaml', '*.scss', '*.css', '*.js'):
                yield from p.rglob(ext)


def extract_front_matter_value(text: str, key: str) -> str | None:
    if not text.startswith('---'):
        return None
    parts = text.split('---', 2)
    if len(parts) < 3:
        return None
    for match in FRONT_MATTER_VALUE_RE.finditer(parts[1]):
        if match.group(1) == key:
            return match.group(2).strip().strip('"\'')
    return None


def normalize_route(path: str) -> str:
    if not path:
        return '/'
    if not path.startswith('/'):
        path = '/' + path
    if path != '/' and path.endswith('/'):
        return path
    if path.endswith('.html'):
        stem = path[:-5]
        return stem + '/' if stem else '/'
    return path + '/'


def collect_known_routes() -> set[str]:
    routes = {'/'}

    for pages_file in (ROOT / 'pages').glob('*'):
        if pages_file.suffix not in ('.md', '.markdown', '.html'):
            continue
        text = read_text(pages_file)
        permalink = extract_front_matter_value(text, 'permalink')
        if permalink:
            routes.add(normalize_route(permalink))
        else:
            routes.add(normalize_route('/' + pages_file.stem + '/'))

    for collection in ('_posts', '_blogs'):
        for post_file in (ROOT / collection).glob('*'):
            if post_file.suffix not in ('.md', '.markdown', '.html'):
                continue
            text = read_text(post_file)
            permalink = extract_front_matter_value(text, 'permalink')
            if permalink:
                routes.add(normalize_route(permalink))
                continue
            slug = post_file.stem
            parts = slug.split('-', 3)
            if len(parts) == 4:
                slug = parts[3]
            routes.add(normalize_route('/' + slug + '/'))

    return routes


def internal_target_exists(raw_path: str, known_routes: set[str]) -> bool:
    link_path = raw_path.split('#', 1)[0].split('?', 1)[0]
    if not link_path or link_path.startswith('/assets/'):
        return True
    if (ROOT / link_path.lstrip('/')).exists():
        return True
    return normalize_route(link_path) in known_routes


def collect_missing_internal_links() -> list[dict]:
    known_routes = collect_known_routes()
    missing: list[dict] = []
    targets = ['_posts', '_blogs', 'pages', 'index.html', '404.html']

    for target in targets:
        p = ROOT / target
        files: list[Path] = []
        if p.is_file():
            files = [p]
        elif p.is_dir():
            for ext in ('*.md', '*.markdown', '*.html'):
                files.extend(p.rglob(ext))
        for fp in files:
            rel = fp.relative_to(ROOT)
            text = read_text(fp)
            for match in INTERNAL_LINK_RE.finditer(text):
                raw = match.group(1)
                if not internal_target_exists(raw, known_routes):
                    missing.append(
                        {
                            'location': str(rel),
                            'issue': 'internal link target not found',
                            'value': raw,
                        }
                    )
    return missing


def collect_missing_liquid_internal_links() -> list[dict]:
    known_routes = collect_known_routes()
    missing: list[dict] = []
    targets = ['_layouts', '_includes', 'pages', 'index.html', '404.html']

    for target in targets:
        p = ROOT / target
        files: list[Path] = []
        if p.is_file():
            files = [p]
        elif p.is_dir():
            for ext in ('*.html', '*.md', '*.markdown'):
                files.extend(p.rglob(ext))
        for fp in files:
            rel = fp.relative_to(ROOT)
            text = read_text(fp)
            for match in LIQUID_RELATIVE_URL_RE.finditer(text):
                raw = match.group(1)
                if not internal_target_exists(raw, known_routes):
                    missing.append(
                        {
                            'location': str(rel),
                            'issue': 'liquid relative_url target not found',
                            'value': raw,
                        }
                    )
    return missing


def collect_external_urls() -> list[str]:
    urls: set[str] = set()
    for fp in iter_files():
        text = read_text(fp)
        for url in URL_RE.findall(text):
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                urls.add(url.rstrip('.,;:!?)'))
    return sorted(urls)


def probe_url(url: str, timeout: float) -> dict:
    headers = {'User-Agent': 'JekyllSiteAudit/1.0 (+https://youllbe.cn)'}
    req = urllib.request.Request(url, headers=headers, method='HEAD')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {'url': url, 'status': int(getattr(resp, 'status', 200)), 'ok': True, 'method': 'HEAD'}
    except Exception:
        # Some endpoints reject HEAD; fall back to GET so the sample can still be validated.
        get_req = urllib.request.Request(url, headers=headers, method='GET')
        try:
            with urllib.request.urlopen(get_req, timeout=timeout) as resp:
                return {'url': url, 'status': int(getattr(resp, 'status', 200)), 'ok': True, 'method': 'GET'}
        except urllib.error.HTTPError as exc:
            return {'url': url, 'status': int(exc.code), 'ok': False, 'method': 'GET', 'error': str(exc)}
        except Exception as exc:  # noqa: BLE001 - keep audit script resilient to network/runtime issues
            return {'url': url, 'status': None, 'ok': False, 'method': 'GET', 'error': str(exc)}


def sample_http_urls(urls: list[str], sample_size: int, timeout: float) -> dict:
    sampled = urls[: max(sample_size, 0)]
    results = [probe_url(url, timeout=timeout) for url in sampled]
    failures = [r for r in results if not r.get('ok')]
    return {
        'enabled': True,
        'sample_size': len(sampled),
        'timeout_seconds': timeout,
        'failures': failures,
        'results': results,
    }


def build_report(http_check: bool = False, http_sample: int = 20, http_timeout: float = 4.0) -> dict:
    timestamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
    config_text = read_text(ROOT / '_config.yml')
    default_layout = read_text(ROOT / '_layouts/default.html')
    homepage = read_text(ROOT / 'index.html')

    seo_keys = ['title:', 'description:', 'keywords:', 'logo:']
    seo_missing = [k.rstrip(':') for k in seo_keys if k not in config_text]

    has_seo_tag = '{% seo %}' in default_layout
    has_viewport = 'name="viewport"' in default_layout
    has_skip_link = 'skip-link' in default_layout

    malformed_links: list[dict] = []
    placeholder_hits: list[dict] = []
    missing_internal_links = collect_missing_internal_links()
    missing_liquid_internal_links = collect_missing_liquid_internal_links()
    urls_count = 0
    external_urls = collect_external_urls()
    http_check_result: dict = {'enabled': False, 'sample_size': 0, 'failures': [], 'results': []}

    for fp in iter_files():
        rel = fp.relative_to(ROOT)
        text = read_text(fp)
        urls_count += len(URL_RE.findall(text))

        for m in DUP_PROTOCOL_RE.finditer(text):
            malformed_links.append(
                {
                    'location': str(rel),
                    'issue': 'duplicated protocol in URL',
                    'value': m.group(0),
                }
            )

        for m in PLACEHOLDER_RE.finditer(text):
            placeholder_hits.append(
                {
                    'location': str(rel),
                    'issue': 'placeholder or local-only marker',
                    'value': m.group(0),
                }
            )

    if http_check:
        http_check_result = sample_http_urls(external_urls, sample_size=http_sample, timeout=http_timeout)

    http_failures = http_check_result.get('failures', [])
    http_sample_size = http_check_result.get('sample_size', 0)

    formspree_blog_preconnect = "page.url contains '/contact/' or page.url contains '/blog/'" in default_layout
    has_home_avatar_preload_flag = 'hero_avatar_preload: true' in homepage
    has_home_avatar_priority = 'fetchpriority="high"' in homepage and 'loading="eager"' in homepage

    sections = {
        'layout_assessment': {
            'score': 8.8 if has_viewport and has_skip_link else 7.0,
            'max_score': 10.0,
            'findings': [
                {
                    'aspect': 'Mobile Experience',
                    'result': 'Good' if has_viewport else 'Needs improvement',
                    'details': 'Viewport meta and skip-link checked in default layout.'
                    if has_skip_link
                    else 'Viewport exists but skip-link missing from default layout.',
                }
            ],
        },
        'broken_links_check': {
            'score': 9.0
            if not malformed_links
            and not placeholder_hits
            and not missing_internal_links
            and not missing_liquid_internal_links
            and (not http_check or not http_failures)
            else 6.5,
            'max_score': 10.0,
            'findings': [
                {
                    'aspect': 'URL Pattern Scan',
                    'result': 'Clean'
                    if not malformed_links and not placeholder_hits
                    else f"Issues found ({len(malformed_links) + len(placeholder_hits)})",
                    'details': 'Regex scan for duplicated protocol and placeholder domains/markers.',
                },
                {
                    'aspect': 'Internal Link Targets',
                    'result': 'Clean'
                    if not missing_internal_links and not missing_liquid_internal_links
                    else f'Issues found ({len(missing_internal_links) + len(missing_liquid_internal_links)})',
                    'details': 'Checks markdown links ](/path/) and Liquid href/src {{ "/path/" | relative_url }} targets.',
                },
                {
                    'aspect': 'HTTP Reachability Sample',
                    'result': 'Skipped'
                    if not http_check
                    else ('Healthy' if not http_failures else f'Issues Found ({len(http_failures)})'),
                    'details': 'Enable with --http-check to sample external URLs.'
                    if not http_check
                    else f'Checked {http_sample_size} external URL(s) with timeout={http_timeout}s.',
                },
            ],
            'broken_links': malformed_links + placeholder_hits + missing_internal_links + missing_liquid_internal_links,
            'http_check': http_check_result,
        },
        'seo_evaluation': {
            'score': 9.0 if has_seo_tag and not seo_missing else 7.0,
            'max_score': 10.0,
            'findings': [
                {
                    'aspect': 'Meta/SEO baseline',
                    'result': 'Good' if has_seo_tag and not seo_missing else 'Needs improvement',
                    'details': 'default.html contains {% seo %}; _config.yml includes core SEO keys.'
                    if not seo_missing
                    else f"Missing keys in _config.yml: {', '.join(seo_missing)}",
                }
            ],
        },
        'content_quality': {
            'score': 8.8 if not formspree_blog_preconnect and has_home_avatar_preload_flag and has_home_avatar_priority else 7.2,
            'max_score': 10.0,
            'findings': [
                {
                    'aspect': 'Performance hygiene',
                    'result': 'Improved' if not formspree_blog_preconnect else 'Needs tuning',
                    'details': 'Formspree preconnect is restricted to contact pages to reduce unnecessary third-party handshakes.'
                    if not formspree_blog_preconnect
                    else 'Formspree preconnect still applies to non-contact pages.',
                },
                {
                    'aspect': 'Homepage hero image priority',
                    'result': 'Improved'
                    if has_home_avatar_preload_flag and has_home_avatar_priority
                    else 'Needs tuning',
                    'details': 'Homepage avatar uses hero preload flag and eager/high fetch priority to reduce above-the-fold delays.'
                    if has_home_avatar_preload_flag and has_home_avatar_priority
                    else 'Set hero_avatar_preload and eager/high fetchpriority for the above-the-fold homepage avatar image.',
                },
                {
                    'aspect': 'External URL volume',
                    'result': 'Observed',
                    'details': f'Detected {urls_count} http(s) links across scanned files.',
                },
            ],
        },
    }

    scores = [sections[k]['score'] for k in sections]
    overall = round(sum(scores) / len(scores), 1)

    return {
        'audit_timestamp': timestamp,
        'website_url': 'https://youllbe.cn',
        'overall_score': overall,
        'max_possible_score': 10.0,
        'sections': sections,
        'summary': {
            'layout': f"Layout: {sections['layout_assessment']['score']}/10",
            'links': f"Links: {sections['broken_links_check']['score']}/10",
            'seo': f"SEO: {sections['seo_evaluation']['score']}/10",
            'content': f"Content/Perf: {sections['content_quality']['score']}/10",
        },
        'recommendations': [
            'Run this audit after each content batch and fix any placeholder/malformed links.',
            'Run with --http-check periodically (or in CI) to validate sampled external URL reachability.',
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate a lightweight Jekyll site audit report.')
    parser.add_argument(
        '--http-check',
        action='store_true',
        help='Sample external URLs and perform lightweight HTTP reachability checks.',
    )
    parser.add_argument(
        '--http-sample',
        type=int,
        default=20,
        help='Maximum number of external URLs to check when --http-check is enabled (default: 20).',
    )
    parser.add_argument(
        '--http-timeout',
        type=float,
        default=4.0,
        help='HTTP timeout in seconds for each URL check (default: 4.0).',
    )
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report(
        http_check=args.http_check,
        http_sample=args.http_sample,
        http_timeout=args.http_timeout,
    )
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    out = REPORTS_DIR / f'site_audit_{stamp}.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
