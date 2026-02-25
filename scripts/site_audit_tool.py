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

    seo_keys = ['title:', 'description:', 'keywords:', 'logo:']
    seo_missing = [k.rstrip(':') for k in seo_keys if k not in config_text]

    has_seo_tag = '{% seo %}' in default_layout
    has_viewport = 'name="viewport"' in default_layout
    has_skip_link = 'skip-link' in default_layout

    malformed_links: list[dict] = []
    placeholder_hits: list[dict] = []
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
            if not malformed_links and not placeholder_hits and (not http_check or not http_failures)
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
                    'aspect': 'HTTP Reachability Sample',
                    'result': 'Skipped'
                    if not http_check
                    else ('Healthy' if not http_failures else f'Issues Found ({len(http_failures)})'),
                    'details': 'Enable with --http-check to sample external URLs.'
                    if not http_check
                    else f'Checked {http_sample_size} external URL(s) with timeout={http_timeout}s.',
                },
            ],
            'broken_links': malformed_links + placeholder_hits,
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
            'score': 8.5 if not formspree_blog_preconnect else 7.2,
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
