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
import struct
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
LIQUID_LINK_TAG_RE = re.compile(r'\{%\s*link\s+([^\s%]+)\s*%\}')
PRECONNECT_HINT_RE = re.compile(r'<link\s+rel="preconnect"\s+href="([^"]+)"')
DNS_PREFETCH_HINT_RE = re.compile(r'<link\s+rel="dns-prefetch"\s+href="([^"]+)"')
APPLE_TOUCH_ICON_RE = re.compile(r'<link\s+rel="apple-touch-icon"[^>]*href="([^"]+)"[^>]*>')
WEB_MANIFEST_RE = re.compile(r'<link\s+rel="manifest"[^>]*href="([^"]+)"[^>]*>')
FORM_POST_ACTION_RE = re.compile(
    r'<form\b[^>]*\bmethod\s*=\s*["\']post["\'][^>]*\baction\s*=\s*["\'](https?://[^"\']+)["\']|'
    r'<form\b[^>]*\baction\s*=\s*["\'](https?://[^"\']+)["\'][^>]*\bmethod\s*=\s*["\']post["\']',
    re.IGNORECASE,
)
FRONT_MATTER_VALUE_RE = re.compile(r'^[ \t]*([A-Za-z0-9_-]+)[ \t]*:[ \t]*(.+)$', re.MULTILINE)
BOOLEAN_LITERALS = {'true', 'false'}


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


def parse_front_matter_values(text: str) -> dict[str, str]:
    if not text.startswith('---'):
        return {}
    parts = text.split('---', 2)
    if len(parts) < 3:
        return {}
    values: dict[str, str] = {}
    for match in FRONT_MATTER_VALUE_RE.finditer(parts[1]):
        values[match.group(1)] = match.group(2).strip().strip('"\'')
    return values


def normalize_hint_href(value: str) -> str:
    return value.strip().rstrip('/').lower()


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


def collect_missing_liquid_link_tag_targets() -> list[dict]:
    missing: list[dict] = []
    targets = ['_layouts', '_includes', 'pages', '_posts', '_blogs', 'index.html', '404.html']

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
            for match in LIQUID_LINK_TAG_RE.finditer(text):
                raw = match.group(1).strip().strip('\'"')
                if not raw or '{{' in raw:
                    continue
                repo_rel = raw.lstrip('/')
                if not (ROOT / repo_rel).exists():
                    missing.append(
                        {
                            'location': str(rel),
                            'issue': 'liquid link tag target not found',
                            'value': raw,
                        }
                    )
    return missing


def collect_posts_missing_image_dimensions() -> list[dict]:
    missing: list[dict] = []
    for collection in ('_posts', '_blogs'):
        folder = ROOT / collection
        if not folder.exists():
            continue
        for post_file in folder.glob('*'):
            if post_file.suffix not in ('.md', '.markdown', '.html'):
                continue
            text = read_text(post_file)
            image = extract_front_matter_value(text, 'image')
            if not image:
                continue
            has_width = extract_front_matter_value(text, 'image_width')
            has_height = extract_front_matter_value(text, 'image_height')
            if has_width and has_height:
                continue
            rel = post_file.relative_to(ROOT)
            missing.append(
                {
                    'location': str(rel),
                    'issue': 'post image dimensions missing',
                    'value': image,
                }
            )
    return missing


def collect_pages_missing_image_dimensions() -> list[dict]:
    missing: list[dict] = []
    folder = ROOT / 'pages'
    if not folder.exists():
        return missing
    for page_file in folder.glob('*'):
        if page_file.suffix not in ('.md', '.markdown', '.html'):
            continue
        text = read_text(page_file)
        image = extract_front_matter_value(text, 'image')
        if not image:
            continue
        has_width = extract_front_matter_value(text, 'image_width')
        has_height = extract_front_matter_value(text, 'image_height')
        if has_width and has_height:
            continue
        rel = page_file.relative_to(ROOT)
        missing.append(
            {
                'location': str(rel),
                'issue': 'page image dimensions missing',
                'value': image,
            }
        )
    return missing


def collect_entries_missing_image_alt() -> list[dict]:
    missing: list[dict] = []
    for collection in ('_posts', '_blogs', 'pages'):
        folder = ROOT / collection
        if not folder.exists():
            continue
        for source_file in folder.glob('*'):
            if source_file.suffix not in ('.md', '.markdown', '.html'):
                continue
            text = read_text(source_file)
            image = extract_front_matter_value(text, 'image')
            if not image:
                continue
            image_alt = extract_front_matter_value(text, 'image_alt')
            if image_alt:
                continue
            rel = source_file.relative_to(ROOT)
            missing.append(
                {
                    'location': str(rel),
                    'issue': 'entry image_alt missing',
                    'value': image,
                }
            )
    return missing


def collect_invalid_boolean_front_matter_flags(keys: list[str]) -> list[dict]:
    invalid: list[dict] = []
    targets = ['_posts', '_blogs', 'pages', 'index.html']

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
            values = parse_front_matter_values(read_text(fp))
            if not values:
                continue
            for key in keys:
                if key not in values:
                    continue
                value = values[key].strip().lower()
                if value in BOOLEAN_LITERALS:
                    continue
                invalid.append(
                    {
                        'location': str(rel),
                        'issue': f'front matter flag `{key}` must be boolean',
                        'value': values[key],
                    }
                )

    return invalid


def extract_yaml_value(text: str, key: str) -> str | None:
    match = re.search(rf'^[ \t]*{re.escape(key)}[ \t]*:[ \t]*(.+)$', text, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"\'')


def resolve_local_image_path(value: str | None) -> Path | None:
    if not value:
        return None
    candidate = value.strip()
    liquid_relative = re.search(r'\{\{\s*[\'"](/[^\'"]+)[\'"]\s*\|\s*relative_url\s*\}\}', candidate)
    if liquid_relative:
        candidate = liquid_relative.group(1)
    if '://' in candidate:
        return None
    if candidate.startswith('/'):
        candidate = candidate[1:]
    path = ROOT / candidate
    return path if path.exists() else None


def get_image_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open('rb') as f:
        sig = f.read(12)
        f.seek(0)
        if sig.startswith(b'\x89PNG\r\n\x1a\n'):
            f.read(8)  # signature
            f.read(8)  # chunk length + chunk type(IHDR)
            width, height = struct.unpack('>II', f.read(8))
            return int(width), int(height)
        if sig.startswith(b'\xff\xd8'):
            f.read(2)
            while True:
                marker_start = f.read(1)
                if not marker_start:
                    return None
                if marker_start != b'\xff':
                    continue
                marker = f.read(1)
                while marker == b'\xff':
                    marker = f.read(1)
                if marker in (b'\xc0', b'\xc1', b'\xc2', b'\xc3', b'\xc5', b'\xc6', b'\xc7', b'\xc9', b'\xca', b'\xcb', b'\xcd', b'\xce', b'\xcf'):
                    f.read(2)  # segment length
                    f.read(1)  # precision
                    height, width = struct.unpack('>HH', f.read(4))
                    return int(width), int(height)
                if marker in (b'\xd8', b'\xd9'):
                    continue
                seg_len_bytes = f.read(2)
                if len(seg_len_bytes) != 2:
                    return None
                seg_len = struct.unpack('>H', seg_len_bytes)[0]
                if seg_len < 2:
                    return None
                f.seek(seg_len - 2, 1)
    return None


def parse_web_manifest(path: Path | None) -> dict | None:
    if not path or not path.exists():
        return None
    try:
        data = json.loads(read_text(path))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def has_manifest_icon(manifest: dict | None, min_size: int) -> bool:
    if not manifest:
        return False
    icons = manifest.get('icons')
    if not isinstance(icons, list):
        return False
    for icon in icons:
        if not isinstance(icon, dict):
            continue
        src = icon.get('src')
        if not isinstance(src, str) or not src.strip():
            continue
        icon_path = resolve_local_image_path(src)
        dims = get_image_dimensions(icon_path) if icon_path else None
        if dims and dims[0] >= min_size and dims[1] >= min_size:
            return True
    return False


def has_manifest_maskable_icon(manifest: dict | None, min_size: int = 192) -> bool:
    if not manifest:
        return False
    icons = manifest.get('icons')
    if not isinstance(icons, list):
        return False
    for icon in icons:
        if not isinstance(icon, dict):
            continue
        purpose = str(icon.get('purpose', '')).lower()
        if 'maskable' not in purpose:
            continue
        src = icon.get('src')
        if not isinstance(src, str) or not src.strip():
            continue
        icon_path = resolve_local_image_path(src)
        dims = get_image_dimensions(icon_path) if icon_path else None
        if dims and dims[0] >= min_size and dims[1] >= min_size:
            return True
    return False


def collect_external_urls() -> list[str]:
    urls: set[str] = set()
    for fp in iter_files():
        text = read_text(fp)
        for url in URL_RE.findall(text):
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                urls.add(url.rstrip('.,;:!?)'))
    return sorted(urls)


def collect_post_only_external_urls() -> set[str]:
    post_only_urls: set[str] = set()
    for fp in iter_files():
        text = read_text(fp)
        for match in FORM_POST_ACTION_RE.finditer(text):
            action_url = match.group(1) or match.group(2)
            if action_url:
                post_only_urls.add(action_url.rstrip('.,;:!?)'))
    return post_only_urls


def collect_preconnect_root_urls() -> set[str]:
    default_layout_path = ROOT / '_layouts/default.html'
    if not default_layout_path.exists():
        return set()
    default_layout = read_text(default_layout_path)
    roots: set[str] = set()
    for href in PRECONNECT_HINT_RE.findall(default_layout):
        parsed = urllib.parse.urlparse(href)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            continue
        roots.add(f'{parsed.scheme}://{parsed.netloc}'.rstrip('/'))
    return roots


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
    post_only_urls = collect_post_only_external_urls()
    preconnect_root_urls = collect_preconnect_root_urls()
    filtered_urls = [
        url for url in urls
        if url.rstrip('/') not in post_only_urls and url.rstrip('/') not in preconnect_root_urls
    ]
    sampled = filtered_urls[: max(sample_size, 0)]
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
    share_layout = read_text(ROOT / '_layouts/share.html')
    homepage = read_text(ROOT / 'index.html')

    seo_keys = ['title:', 'description:', 'keywords:', 'logo:']
    seo_missing = [k.rstrip(':') for k in seo_keys if k not in config_text]
    site_social_image = extract_yaml_value(config_text, 'image')
    site_social_image_alt = extract_yaml_value(config_text, 'image_alt')
    site_social_image_path = resolve_local_image_path(site_social_image)
    site_social_image_dimensions = get_image_dimensions(site_social_image_path) if site_social_image_path else None
    has_large_social_image = bool(
        site_social_image_dimensions
        and site_social_image_dimensions[0] >= 1200
        and site_social_image_dimensions[1] >= 630
    )
    has_social_image_alt = bool(site_social_image_alt and site_social_image_alt.strip())
    share_page_file = ROOT / 'pages/share.html'
    share_page_text = read_text(share_page_file) if share_page_file.exists() else ''
    share_page_social_image = extract_front_matter_value(share_page_text, 'image')
    share_page_social_image_path = resolve_local_image_path(share_page_social_image)
    share_page_social_image_dimensions = (
        get_image_dimensions(share_page_social_image_path) if share_page_social_image_path else None
    )
    has_share_page_large_social_image = bool(
        share_page_social_image_dimensions
        and share_page_social_image_dimensions[0] >= 1200
        and share_page_social_image_dimensions[1] >= 630
    )

    has_seo_tag = '{% seo %}' in default_layout
    has_manual_canonical = '<link rel="canonical"' in default_layout
    has_viewport = 'name="viewport"' in default_layout
    has_skip_link = 'skip-link' in default_layout
    has_default_mobile_web_app_meta = (
        'name="mobile-web-app-capable" content="yes"' in default_layout
        and 'name="apple-mobile-web-app-capable" content="yes"' in default_layout
    )
    has_share_mobile_web_app_meta = (
        'name="mobile-web-app-capable" content="yes"' in share_layout
        and 'name="apple-mobile-web-app-capable" content="yes"' in share_layout
    )
    has_default_mobile_web_app_title = 'name="apple-mobile-web-app-title" content="{{ site.title | escape }}"' in default_layout
    has_share_mobile_web_app_title = 'name="apple-mobile-web-app-title" content="{{ site.title | escape }}"' in share_layout
    has_default_application_name_meta = 'name="application-name" content="{{ site.title | escape }}"' in default_layout
    has_share_application_name_meta = 'name="application-name" content="{{ site.title | escape }}"' in share_layout
    has_default_theme_color_meta = (
        'name="theme-color" content="#2c3e50"' in default_layout
        and 'name="theme-color" media="(prefers-color-scheme: dark)" content="#0b1320"' in default_layout
    )
    has_share_theme_color_meta = (
        'name="theme-color" content="#2c3e50"' in share_layout
        and 'name="theme-color" media="(prefers-color-scheme: dark)" content="#0b1320"' in share_layout
    )
    has_default_main_landmark_aria_label = (
        '<main class="flex-grow-1" id="main-content" role="main" tabindex="-1" aria-label=' in default_layout
    )
    has_share_main_landmark_aria_label = (
        '<main id="main-content" role="main" tabindex="-1" aria-label=' in share_layout
    )
    has_paginated_noindex_policy = (
        "{% assign is_paginated_archive_page = paginator and paginator.page and paginator.page > 1 %}" in default_layout
        and '<meta name="robots" content="noindex,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">' in default_layout
        and '<meta name="googlebot" content="noindex,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">' in default_layout
    )
    has_paginated_hreflang_guard = (
        '{% unless is_paginated_archive_page %}' in default_layout
        and '<link rel="alternate" hreflang="{{ page_lang }}" href="{{ page.url | absolute_url }}">' in default_layout
        and '<link rel="alternate" hreflang="x-default" href="{{ page.url | absolute_url }}">' in default_layout
        and '{% endunless %}' in default_layout
    )
    has_paginated_rel_navigation = (
        '{% if paginator %}' in default_layout
        and '<link rel="prev" href="{{ paginator.previous_page_path | absolute_url }}">' in default_layout
        and '<link rel="next" href="{{ paginator.next_page_path | absolute_url }}">' in default_layout
        and '<link rel="first" href="{{ \'/blog/\' | absolute_url }}">' in default_layout
        and '<link rel="last" href="{{ site.paginate_path | absolute_url | replace: \':num\', paginator.total_pages }}">' in default_layout
    )
    has_canonical_signal_consistency = has_seo_tag and not has_manual_canonical and has_paginated_rel_navigation

    malformed_links: list[dict] = []
    placeholder_hits: list[dict] = []
    missing_internal_links = collect_missing_internal_links()
    missing_liquid_internal_links = collect_missing_liquid_internal_links()
    missing_liquid_link_tag_targets = collect_missing_liquid_link_tag_targets()
    posts_missing_image_dimensions = collect_posts_missing_image_dimensions()
    pages_missing_image_dimensions = collect_pages_missing_image_dimensions()
    entries_missing_image_alt = collect_entries_missing_image_alt()
    invalid_perf_flags = collect_invalid_boolean_front_matter_flags(
        [
            'hero_avatar_preload',
            'preload_social_image',
            'preload_featured_image',
            'prefetch_adjacent_posts',
            'preconnect_disqus',
            'preconnect_analytics',
            'preconnect_fonts',
        ]
    )
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
    has_home_avatar_responsive_sources = 'srcset=' in homepage and 'sizes=' in homepage
    has_theme_js_preload = "rel=\"preload\" href=\"{{ '/assets/js/theme.js' | relative_url }}\" as=\"script\"" in default_layout
    has_bootstrap_css_preload = (
        'rel="preload" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" as="style"' in default_layout
    )
    has_local_css_preload = (
        "rel=\"preload\" href=\"{{ '/assets/css/theme.css' | relative_url }}\" as=\"style\"" in default_layout
        or "rel=\"preload\" href=\"{{ '/assets/css/custom.css' | relative_url }}\" as=\"style\"" in default_layout
    )
    has_guarded_share_social_image_preload = '{% if page.preload_social_image and page.image %}' in share_layout
    social_alt_fallback_expr = '{% assign social_image_alt = page.image_alt | default: site.image_alt | default: page.title | default: site.title %}'
    has_social_alt_fallback_template = (
        social_alt_fallback_expr in default_layout
        and social_alt_fallback_expr in share_layout
        and '<meta property="og:image:alt" content="{{ social_image_alt | escape }}">' in default_layout
        and '<meta name="twitter:image:alt" content="{{ social_image_alt | escape }}">' in default_layout
        and '<meta property="og:image:alt" content="{{ social_image_alt | escape }}">' in share_layout
        and '<meta name="twitter:image:alt" content="{{ social_image_alt | escape }}">' in share_layout
    )
    has_guarded_featured_image_preload = (
        "{% if page.preload_featured_image or page.image_loading == 'eager' or page.image_fetchpriority == 'high' %}" in default_layout
        and "page.layout == 'post' or page.image_loading == 'eager' or page.image_fetchpriority == 'high'" not in default_layout
    )
    has_guarded_adjacent_post_prefetch = "{% if page.layout == 'post' and page.prefetch_adjacent_posts %}" in default_layout
    has_guarded_disqus_preconnect = "{% if site.disqus and page.layout == 'post' and page.preconnect_disqus %}" in default_layout
    has_guarded_analytics_preconnect = (
        '{% if site.google_analytics %}' in default_layout
        and '{% if page.preconnect_analytics %}' in default_layout
        and '{% if site.google_analytics %}' in share_layout
        and '{% if page.preconnect_analytics %}' in share_layout
    )
    has_default_font_preconnect = (
        'rel="preconnect" href="https://fonts.googleapis.com"' in default_layout
        or 'rel="preconnect" href="https://fonts.gstatic.com"' in default_layout
    )
    has_guarded_default_font_preconnect = (
        '{% if page.preconnect_fonts %}' in default_layout
        and 'rel="preconnect" href="https://fonts.googleapis.com"' in default_layout
        and 'rel="preconnect" href="https://fonts.gstatic.com" crossorigin' in default_layout
    )
    has_share_font_preconnect = (
        'rel="preconnect" href="https://fonts.googleapis.com"' in share_layout
        or 'rel="preconnect" href="https://fonts.gstatic.com"' in share_layout
    )
    has_share_font_stylesheet = 'fonts.googleapis.com/css2?family=' in share_layout
    has_share_font_css_preload = 'rel="preload" as="style" href="https://fonts.googleapis.com/css2?' in share_layout
    has_share_local_css_preload = (
        "rel=\"preload\" href=\"{{ '/assets/css/theme.css' | relative_url }}\" as=\"style\"" in share_layout
        or "rel=\"preload\" href=\"{{ '/assets/css/custom.css' | relative_url }}\" as=\"style\"" in share_layout
    )
    preconnect_hints = {
        normalize_hint_href(value)
        for value in PRECONNECT_HINT_RE.findall(default_layout + '\n' + share_layout)
    }
    dns_prefetch_hints = {
        normalize_hint_href(value)
        for value in DNS_PREFETCH_HINT_RE.findall(default_layout + '\n' + share_layout)
    }
    duplicate_resource_hint_hosts = sorted(preconnect_hints.intersection(dns_prefetch_hints))
    apple_touch_icon_href = APPLE_TOUCH_ICON_RE.search(default_layout)
    apple_touch_icon_value = apple_touch_icon_href.group(1) if apple_touch_icon_href else None
    apple_touch_icon_path = resolve_local_image_path(apple_touch_icon_value)
    apple_touch_icon_dimensions = get_image_dimensions(apple_touch_icon_path) if apple_touch_icon_path else None
    has_apple_touch_icon_sizes = bool(
        re.search(r'<link\s+rel="apple-touch-icon"[^>]*sizes="180x180"[^>]*>', default_layout)
    )
    has_mobile_ready_apple_touch_icon = bool(
        has_apple_touch_icon_sizes
        and apple_touch_icon_dimensions
        and apple_touch_icon_dimensions[0] == apple_touch_icon_dimensions[1]
        and apple_touch_icon_dimensions[0] >= 180
    )
    share_apple_touch_icon_href = APPLE_TOUCH_ICON_RE.search(share_layout)
    share_apple_touch_icon_value = share_apple_touch_icon_href.group(1) if share_apple_touch_icon_href else None
    share_apple_touch_icon_path = resolve_local_image_path(share_apple_touch_icon_value)
    share_apple_touch_icon_dimensions = get_image_dimensions(share_apple_touch_icon_path) if share_apple_touch_icon_path else None
    has_share_apple_touch_icon_sizes = bool(
        re.search(r'<link\s+rel="apple-touch-icon"[^>]*sizes="180x180"[^>]*>', share_layout)
    )
    has_share_mobile_ready_apple_touch_icon = bool(
        has_share_apple_touch_icon_sizes
        and share_apple_touch_icon_dimensions
        and share_apple_touch_icon_dimensions[0] == share_apple_touch_icon_dimensions[1]
        and share_apple_touch_icon_dimensions[0] >= 180
    )
    default_manifest_href_match = WEB_MANIFEST_RE.search(default_layout)
    default_manifest_href = default_manifest_href_match.group(1) if default_manifest_href_match else None
    default_manifest_path = resolve_local_image_path(default_manifest_href)
    share_manifest_href_match = WEB_MANIFEST_RE.search(share_layout)
    share_manifest_href = share_manifest_href_match.group(1) if share_manifest_href_match else None
    share_manifest_path = resolve_local_image_path(share_manifest_href)
    has_default_manifest_link = bool(default_manifest_href and default_manifest_path)
    has_share_manifest_link = bool(share_manifest_href and share_manifest_path)
    manifest_paths_match = bool(default_manifest_path and share_manifest_path and default_manifest_path == share_manifest_path)
    web_manifest = parse_web_manifest(default_manifest_path if manifest_paths_match else None)
    has_manifest_baseline = bool(
        web_manifest
        and web_manifest.get('name')
        and web_manifest.get('short_name')
        and web_manifest.get('description')
        and web_manifest.get('lang')
        and web_manifest.get('id')
        and web_manifest.get('start_url')
        and web_manifest.get('display')
    )
    has_manifest_icon_192 = has_manifest_icon(web_manifest, min_size=192)
    has_manifest_icon_512 = has_manifest_icon(web_manifest, min_size=512)
    has_manifest_maskable_icon_192 = has_manifest_maskable_icon(web_manifest, min_size=192)
    has_mobile_ready_web_manifest = bool(
        has_default_manifest_link
        and has_share_manifest_link
        and manifest_paths_match
        and has_manifest_baseline
        and has_manifest_icon_192
        and has_manifest_icon_512
        and has_manifest_maskable_icon_192
    )

    sections = {
        'layout_assessment': {
            'score': 8.9
            if has_viewport
            and has_skip_link
            and has_default_mobile_web_app_meta
            and has_share_mobile_web_app_meta
            and has_default_mobile_web_app_title
            and has_share_mobile_web_app_title
            and has_default_application_name_meta
            and has_share_application_name_meta
            and has_default_theme_color_meta
            and has_share_theme_color_meta
            and has_default_main_landmark_aria_label
            and has_share_main_landmark_aria_label
            else 7.0,
            'max_score': 10.0,
            'findings': [
                {
                    'aspect': 'Mobile Experience',
                    'result': 'Good' if has_viewport else 'Needs improvement',
                    'details': 'Viewport meta and skip-link checked in default layout.'
                    if has_skip_link
                    else 'Viewport exists but skip-link missing from default layout.',
                },
                {
                    'aspect': 'Mobile web app capability hints',
                    'result': 'Improved'
                    if has_default_mobile_web_app_meta and has_share_mobile_web_app_meta
                    else 'Needs tuning',
                    'details': 'Both default and share layouts expose mobile-web-app-capable and apple-mobile-web-app-capable metas for better mobile install/browser treatment.'
                    if has_default_mobile_web_app_meta and has_share_mobile_web_app_meta
                    else 'Add mobile-web-app-capable and apple-mobile-web-app-capable meta tags to both default and share layouts.',
                },
                {
                    'aspect': 'Apple mobile web app title',
                    'result': 'Improved'
                    if has_default_mobile_web_app_title and has_share_mobile_web_app_title
                    else 'Needs tuning',
                    'details': 'Default and share layouts define apple-mobile-web-app-title so iOS home-screen launches use the intended app name.'
                    if has_default_mobile_web_app_title and has_share_mobile_web_app_title
                    else 'Add apple-mobile-web-app-title meta tags to both default and share layouts.',
                },
                {
                    'aspect': 'Application name meta',
                    'result': 'Improved'
                    if has_default_application_name_meta and has_share_application_name_meta
                    else 'Needs tuning',
                    'details': 'Default and share layouts define application-name with site.title for consistent install/browser identity.'
                    if has_default_application_name_meta and has_share_application_name_meta
                    else 'Add application-name meta tags to both default and share layouts using site.title.',
                },
                {
                    'aspect': 'Theme color parity',
                    'result': 'Improved'
                    if has_default_theme_color_meta and has_share_theme_color_meta
                    else 'Needs tuning',
                    'details': 'Default and share layouts both expose matching light/dark theme-color meta tags for consistent mobile browser UI tint.'
                    if has_default_theme_color_meta and has_share_theme_color_meta
                    else 'Keep matching light/dark theme-color meta tags in both default and share layouts.',
                },
                {
                    'aspect': 'Main landmark labeling',
                    'result': 'Improved'
                    if has_default_main_landmark_aria_label and has_share_main_landmark_aria_label
                    else 'Needs tuning',
                    'details': 'Main landmark uses aria-label to avoid broken aria-labelledby references across mixed layouts.'
                    if has_default_main_landmark_aria_label and has_share_main_landmark_aria_label
                    else 'Set a stable aria-label on #main-content in both default and share layouts instead of relying on page-title ids.',
                }
            ],
            'default_mobile_web_app_meta': has_default_mobile_web_app_meta,
            'share_mobile_web_app_meta': has_share_mobile_web_app_meta,
            'default_mobile_web_app_title': has_default_mobile_web_app_title,
            'share_mobile_web_app_title': has_share_mobile_web_app_title,
            'default_application_name_meta': has_default_application_name_meta,
            'share_application_name_meta': has_share_application_name_meta,
            'default_theme_color_meta': has_default_theme_color_meta,
            'share_theme_color_meta': has_share_theme_color_meta,
            'default_main_landmark_labeled': has_default_main_landmark_aria_label,
            'share_main_landmark_labeled': has_share_main_landmark_aria_label,
        },
        'broken_links_check': {
            'score': 9.0
            if not malformed_links
            and not placeholder_hits
            and not missing_internal_links
            and not missing_liquid_internal_links
            and not missing_liquid_link_tag_targets
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
                    if not missing_internal_links
                    and not missing_liquid_internal_links
                    and not missing_liquid_link_tag_targets
                    else (
                        f'Issues found ({len(missing_internal_links) + len(missing_liquid_internal_links) + len(missing_liquid_link_tag_targets)})'
                    ),
                    'details': 'Checks markdown links ](/path/), Liquid href/src {{ "/path/" | relative_url }}, and {% link ... %} targets.',
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
            'broken_links': malformed_links
            + placeholder_hits
            + missing_internal_links
            + missing_liquid_internal_links
            + missing_liquid_link_tag_targets,
            'http_check': http_check_result,
        },
        'seo_evaluation': {
            'score': 9.0
            if has_seo_tag
            and not seo_missing
            and has_large_social_image
            and has_social_image_alt
            and not entries_missing_image_alt
            and has_share_page_large_social_image
            and has_social_alt_fallback_template
            and has_paginated_noindex_policy
            and has_paginated_hreflang_guard
            and has_canonical_signal_consistency
            else 7.0,
            'max_score': 10.0,
            'findings': [
                {
                    'aspect': 'Meta/SEO baseline',
                    'result': 'Good' if has_seo_tag and not seo_missing else 'Needs improvement',
                    'details': 'default.html contains {% seo %}; _config.yml includes core SEO keys.'
                    if not seo_missing
                    else f"Missing keys in _config.yml: {', '.join(seo_missing)}",
                },
                {
                    'aspect': 'Social preview image size',
                    'result': 'Good' if has_large_social_image else 'Needs improvement',
                    'details': f"_config.yml image points to {site_social_image_path.relative_to(ROOT)} ({site_social_image_dimensions[0]}x{site_social_image_dimensions[1]})."
                    if has_large_social_image and site_social_image_path and site_social_image_dimensions
                    else 'Set _config.yml image to a local asset >=1200x630 for better OG/Twitter previews.',
                },
                {
                    'aspect': 'Social preview image alt',
                    'result': 'Good' if has_social_image_alt else 'Needs improvement',
                    'details': f"_config.yml image_alt is set: {site_social_image_alt}"
                    if has_social_image_alt
                    else 'Set _config.yml image_alt so OG/Twitter image metadata has an accessible fallback description.',
                },
                {
                    'aspect': 'Entry social image alt coverage',
                    'result': 'Good' if not entries_missing_image_alt else 'Needs improvement',
                    'details': 'Entries with front matter image include image_alt for social preview and accessibility metadata.'
                    if not entries_missing_image_alt
                    else f"Found {len(entries_missing_image_alt)} entry file(s) with image but missing image_alt.",
                },
                {
                    'aspect': 'Share page social image size',
                    'result': 'Good' if has_share_page_large_social_image else 'Needs improvement',
                    'details': (
                        f"pages/share.html image points to {share_page_social_image_path.relative_to(ROOT)} "
                        f"({share_page_social_image_dimensions[0]}x{share_page_social_image_dimensions[1]})."
                    )
                    if has_share_page_large_social_image and share_page_social_image_path and share_page_social_image_dimensions
                    else 'Set pages/share.html image to a local asset >=1200x630 for stronger social preview quality.',
                },
                {
                    'aspect': 'Social image alt fallback template',
                    'result': 'Good' if has_social_alt_fallback_template else 'Needs improvement',
                    'details': 'default/share layouts both expose social_image_alt fallback chain (page.image_alt -> site.image_alt -> page.title -> site.title) for OG/Twitter alt metadata.'
                    if has_social_alt_fallback_template
                    else 'Keep matching social_image_alt fallback chain and OG/Twitter alt tags in both default and share layouts.',
                },
                {
                    'aspect': 'Paginated archive indexing policy',
                    'result': 'Good' if has_paginated_noindex_policy else 'Needs improvement',
                    'details': 'Paginated archive pages (page > 1) are marked noindex,follow to reduce duplicate listing-page indexing.'
                    if has_paginated_noindex_policy
                    else 'Add paginated page > 1 noindex,follow fallback for robots/googlebot in default layout while preserving page-level overrides.',
                },
                {
                    'aspect': 'Paginated hreflang policy',
                    'result': 'Good' if has_paginated_hreflang_guard else 'Needs improvement',
                    'details': 'Paginated archive pages (page > 1) skip alternate hreflang tags to avoid sending duplicate language signals on noindex listings.'
                    if has_paginated_hreflang_guard
                    else 'Wrap alternate hreflang links in a page > 1 guard so noindex paginated archives do not emit duplicate language alternates.',
                },
                {
                    'aspect': 'Canonical signal consistency',
                    'result': 'Good' if has_canonical_signal_consistency else 'Needs improvement',
                    'details': 'Canonical tag generation stays centralized in jekyll-seo-tag, and paginated archives expose prev/next/first/last rel signals for crawler consistency.'
                    if has_canonical_signal_consistency
                    else 'Keep canonical generation in one place (jekyll-seo-tag) and ensure paginator rel prev/next/first/last links exist in default layout.',
                },
            ],
            'missing_entry_image_alt': entries_missing_image_alt,
            'share_page_social_image_ready': has_share_page_large_social_image,
            'social_alt_fallback_template': has_social_alt_fallback_template,
            'paginated_noindex_policy': has_paginated_noindex_policy,
            'paginated_hreflang_policy': has_paginated_hreflang_guard,
            'canonical_signal_consistency': has_canonical_signal_consistency,
        },
        'content_quality': {
            'score': 9.0
            if not formspree_blog_preconnect
            and has_home_avatar_preload_flag
            and has_home_avatar_priority
            and has_home_avatar_responsive_sources
            and not has_theme_js_preload
            and not has_bootstrap_css_preload
            and not has_local_css_preload
            and not has_share_font_css_preload
            and not has_share_local_css_preload
            and has_guarded_share_social_image_preload
            and has_guarded_featured_image_preload
            and has_guarded_adjacent_post_prefetch
            and has_guarded_disqus_preconnect
            and has_guarded_analytics_preconnect
            and has_guarded_default_font_preconnect
            and not has_share_font_preconnect
            and not has_share_font_stylesheet
            and not duplicate_resource_hint_hosts
            and not invalid_perf_flags
            and not posts_missing_image_dimensions
            and not pages_missing_image_dimensions
            and has_mobile_ready_apple_touch_icon
            and has_share_mobile_ready_apple_touch_icon
            and has_mobile_ready_web_manifest
            else 7.2,
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
                    'aspect': 'Responsive hero image variants',
                    'result': 'Improved' if has_home_avatar_responsive_sources else 'Needs tuning',
                    'details': 'Homepage hero image provides srcset/sizes variants to avoid over-downloading on mobile.'
                    if has_home_avatar_responsive_sources
                    else 'Add srcset/sizes to the homepage hero image so smaller viewports fetch smaller assets.',
                },
                {
                    'aspect': 'Script preload pressure',
                    'result': 'Improved' if not has_theme_js_preload else 'Needs tuning',
                    'details': 'theme.js is deferred without preload to avoid competing with render-critical CSS/image downloads.'
                    if not has_theme_js_preload
                    else 'Remove theme.js preload because deferred script fetch is non-critical during initial render.',
                },
                {
                    'aspect': 'Bootstrap stylesheet preload policy',
                    'result': 'Improved' if not has_bootstrap_css_preload else 'Needs tuning',
                    'details': 'Bootstrap CSS loads via stylesheet link only, avoiding extra preload hint contention on mobile.'
                    if not has_bootstrap_css_preload
                    else 'Remove Bootstrap CSS preload hint and keep the stylesheet link to reduce redundant high-priority fetch pressure.',
                },
                {
                    'aspect': 'Local stylesheet preload policy',
                    'result': 'Improved' if not has_local_css_preload else 'Needs tuning',
                    'details': 'theme.css/custom.css are discovered early via normal stylesheet links, avoiding redundant preload hints.'
                    if not has_local_css_preload
                    else 'Remove local stylesheet preload hints for theme.css/custom.css to reduce duplicate high-priority fetch pressure.',
                },
                {
                    'aspect': 'Share layout stylesheet preload policy',
                    'result': 'Improved' if not has_share_font_css_preload and not has_share_local_css_preload else 'Needs tuning',
                    'details': 'Share layout avoids font/local stylesheet preload hints and relies on deferred stylesheet loading to reduce mobile bandwidth contention.'
                    if not has_share_font_css_preload and not has_share_local_css_preload
                    else 'Remove share layout font/local stylesheet preload hints to avoid redundant high-priority fetch pressure.',
                },
                {
                    'aspect': 'Share page social image preload',
                    'result': 'Improved' if has_guarded_share_social_image_preload else 'Needs tuning',
                    'details': 'Share layout only preloads social image when page.preload_social_image is explicitly enabled, reducing default mobile bandwidth use.'
                    if has_guarded_share_social_image_preload
                    else 'Guard share layout social image preload behind page.preload_social_image to avoid unnecessary image prefetching.',
                },
                {
                    'aspect': 'Featured image preload policy',
                    'result': 'Improved' if has_guarded_featured_image_preload else 'Needs tuning',
                    'details': 'Featured image preload is opt-in via preload_featured_image (or explicit eager/high priority), preventing unconditional preload on all post pages.'
                    if has_guarded_featured_image_preload
                    else 'Avoid auto-preloading featured images on every post page; gate preload behind preload_featured_image or explicit eager/high image priority flags.',
                },
                {
                    'aspect': 'Adjacent post prefetch policy',
                    'result': 'Improved' if has_guarded_adjacent_post_prefetch else 'Needs tuning',
                    'details': 'Adjacent post prefetch is opt-in via page.prefetch_adjacent_posts, avoiding unconditional mobile bandwidth consumption.'
                    if has_guarded_adjacent_post_prefetch
                    else 'Only enable adjacent post prefetch when page.prefetch_adjacent_posts is explicitly set.',
                },
                {
                    'aspect': 'Disqus preconnect policy',
                    'result': 'Improved' if has_guarded_disqus_preconnect else 'Needs tuning',
                    'details': 'Disqus preconnect is opt-in via page.preconnect_disqus so post pages avoid default third-party handshakes on mobile.'
                    if has_guarded_disqus_preconnect
                    else 'Guard Disqus preconnect behind page.preconnect_disqus to reduce default third-party connection cost on post pages.',
                },
                {
                    'aspect': 'Analytics preconnect policy',
                    'result': 'Improved' if has_guarded_analytics_preconnect else 'Needs tuning',
                    'details': 'Google Analytics preconnect is opt-in via page.preconnect_analytics, so default pages avoid extra third-party handshakes on mobile.'
                    if has_guarded_analytics_preconnect
                    else 'Guard GA preconnect behind page.preconnect_analytics in default/share layouts to reduce default third-party connection cost.',
                },
                {
                    'aspect': 'Default font preconnect policy',
                    'result': 'Improved' if has_guarded_default_font_preconnect else 'Needs tuning',
                    'details': 'Google Fonts preconnect in default layout is opt-in via page.preconnect_fonts, reducing unnecessary third-party handshakes by default.'
                    if has_guarded_default_font_preconnect
                    else (
                        'Guard default layout Google Fonts preconnect behind page.preconnect_fonts to avoid default third-party connection cost.'
                        if has_default_font_preconnect
                        else 'Default layout has no Google Fonts preconnect hints; keep this lightweight unless a page needs explicit font preconnect.'
                    ),
                },
                {
                    'aspect': 'Share font preconnect policy',
                    'result': 'Improved' if not has_share_font_preconnect else 'Needs tuning',
                    'details': 'Share layout avoids Google Fonts preconnect hints so third-party handshakes only occur when async stylesheet fetching is actually needed.'
                    if not has_share_font_preconnect
                    else 'Remove share layout Google Fonts preconnect hints to reduce up-front third-party connection cost on mobile.',
                },
                {
                    'aspect': 'Share font stylesheet policy',
                    'result': 'Improved' if not has_share_font_stylesheet else 'Needs tuning',
                    'details': 'Share layout uses local/system typography only, removing Google Fonts stylesheet fetches for faster mobile first paint.'
                    if not has_share_font_stylesheet
                    else 'Remove share layout Google Fonts stylesheet to cut third-party render-blocking dependency on mobile.',
                },
                {
                    'aspect': 'Resource hint deduplication',
                    'result': 'Improved' if not duplicate_resource_hint_hosts else 'Needs tuning',
                    'details': 'Domains with preconnect avoid duplicated dns-prefetch hints to keep head metadata lean and avoid redundant hints.'
                    if not duplicate_resource_hint_hosts
                    else f'Duplicate preconnect+dns-prefetch hints found for: {", ".join(duplicate_resource_hint_hosts)}.',
                },
                {
                    'aspect': 'Front matter performance toggles',
                    'result': 'Improved' if not invalid_perf_flags else 'Needs tuning',
                    'details': 'hero_avatar_preload/preload_social_image/preload_featured_image/prefetch_adjacent_posts/preconnect_disqus/preconnect_analytics/preconnect_fonts use explicit true/false values.'
                    if not invalid_perf_flags
                    else f'Found {len(invalid_perf_flags)} invalid toggle value(s); use true/false booleans in front matter.',
                },
                {
                    'aspect': 'External URL volume',
                    'result': 'Observed',
                    'details': f'Detected {urls_count} http(s) links across scanned files.',
                },
                {
                    'aspect': 'Post featured image dimensions',
                    'result': 'Improved' if not posts_missing_image_dimensions else 'Needs tuning',
                    'details': 'Posts/blog entries with front matter image now include image_width/image_height to reduce layout shift.'
                    if not posts_missing_image_dimensions
                    else f"Found {len(posts_missing_image_dimensions)} post(s) with image but without image_width/image_height.",
                },
                {
                    'aspect': 'Page featured image dimensions',
                    'result': 'Improved' if not pages_missing_image_dimensions else 'Needs tuning',
                    'details': 'Pages with front matter image include image_width/image_height to reduce mobile layout shift.'
                    if not pages_missing_image_dimensions
                    else f"Found {len(pages_missing_image_dimensions)} page(s) with image but without image_width/image_height.",
                },
                {
                    'aspect': 'Apple touch icon readiness',
                    'result': 'Improved' if has_mobile_ready_apple_touch_icon else 'Needs tuning',
                    'details': (
                        f"apple-touch-icon points to {apple_touch_icon_path.relative_to(ROOT)} "
                        f"({apple_touch_icon_dimensions[0]}x{apple_touch_icon_dimensions[1]}) with sizes=180x180 for iOS home-screen installs."
                    )
                    if has_mobile_ready_apple_touch_icon and apple_touch_icon_path and apple_touch_icon_dimensions
                    else 'Use a square local apple-touch-icon (>=180x180) and declare sizes="180x180" for mobile install quality.',
                },
                {
                    'aspect': 'Share page apple touch icon readiness',
                    'result': 'Improved' if has_share_mobile_ready_apple_touch_icon else 'Needs tuning',
                    'details': (
                        f"share layout apple-touch-icon points to {share_apple_touch_icon_path.relative_to(ROOT)} "
                        f"({share_apple_touch_icon_dimensions[0]}x{share_apple_touch_icon_dimensions[1]}) with sizes=180x180 for iOS home-screen installs."
                    )
                    if has_share_mobile_ready_apple_touch_icon and share_apple_touch_icon_path and share_apple_touch_icon_dimensions
                    else 'Use a square local apple-touch-icon (>=180x180) and declare sizes="180x180" in share layout for mobile install quality.',
                },
                {
                    'aspect': 'Web app manifest readiness',
                    'result': 'Improved' if has_mobile_ready_web_manifest else 'Needs tuning',
                    'details': (
                        f"default/share layouts reference {default_manifest_path.relative_to(ROOT)} with name/short_name/description/lang/id/start_url/display, local 192px+512px icons, and a >=192px maskable icon."
                    )
                    if has_mobile_ready_web_manifest and default_manifest_path
                    else 'Add one shared local manifest link in default/share layouts, include description/lang/id metadata, provide local 192px/512px icons, and include a maskable icon for better Android adaptive install visuals.',
                },
            ],
            'missing_post_image_dimensions': posts_missing_image_dimensions,
            'missing_page_image_dimensions': pages_missing_image_dimensions,
            'duplicate_resource_hint_hosts': duplicate_resource_hint_hosts,
            'invalid_front_matter_perf_flags': invalid_perf_flags,
            'analytics_preconnect_policy': has_guarded_analytics_preconnect,
            'default_font_preconnect_policy': has_guarded_default_font_preconnect,
            'share_font_preconnect_policy': not has_share_font_preconnect,
            'share_font_stylesheet_policy': not has_share_font_stylesheet,
            'apple_touch_icon_ready': has_mobile_ready_apple_touch_icon,
            'share_apple_touch_icon_ready': has_share_mobile_ready_apple_touch_icon,
            'web_app_manifest_ready': has_mobile_ready_web_manifest,
            'web_app_manifest_maskable_icon_ready': has_manifest_maskable_icon_192,
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


def collect_strict_failures(report: dict, http_check_enabled: bool) -> list[str]:
    sections = report.get('sections', {})
    default_mobile_web_app_meta = sections.get('layout_assessment', {}).get('default_mobile_web_app_meta', False)
    share_mobile_web_app_meta = sections.get('layout_assessment', {}).get('share_mobile_web_app_meta', False)
    default_mobile_web_app_title = sections.get('layout_assessment', {}).get('default_mobile_web_app_title', False)
    share_mobile_web_app_title = sections.get('layout_assessment', {}).get('share_mobile_web_app_title', False)
    default_application_name_meta = sections.get('layout_assessment', {}).get('default_application_name_meta', False)
    share_application_name_meta = sections.get('layout_assessment', {}).get('share_application_name_meta', False)
    default_theme_color_meta = sections.get('layout_assessment', {}).get('default_theme_color_meta', False)
    share_theme_color_meta = sections.get('layout_assessment', {}).get('share_theme_color_meta', False)
    default_main_landmark_labeled = sections.get('layout_assessment', {}).get('default_main_landmark_labeled', False)
    share_main_landmark_labeled = sections.get('layout_assessment', {}).get('share_main_landmark_labeled', False)
    broken = sections.get('broken_links_check', {}).get('broken_links', [])
    missing_entry_alt = sections.get('seo_evaluation', {}).get('missing_entry_image_alt', [])
    share_page_social_image_ready = sections.get('seo_evaluation', {}).get('share_page_social_image_ready', False)
    social_alt_fallback_template = sections.get('seo_evaluation', {}).get('social_alt_fallback_template', False)
    paginated_noindex_policy = sections.get('seo_evaluation', {}).get('paginated_noindex_policy', False)
    paginated_hreflang_policy = sections.get('seo_evaluation', {}).get('paginated_hreflang_policy', False)
    canonical_signal_consistency = sections.get('seo_evaluation', {}).get('canonical_signal_consistency', False)
    missing_dimensions = sections.get('content_quality', {}).get('missing_post_image_dimensions', [])
    missing_page_dimensions = sections.get('content_quality', {}).get('missing_page_image_dimensions', [])
    invalid_perf_flags = sections.get('content_quality', {}).get('invalid_front_matter_perf_flags', [])
    analytics_preconnect_policy = sections.get('content_quality', {}).get('analytics_preconnect_policy', False)
    default_font_preconnect_policy = sections.get('content_quality', {}).get('default_font_preconnect_policy', False)
    share_font_preconnect_policy = sections.get('content_quality', {}).get('share_font_preconnect_policy', False)
    share_font_stylesheet_policy = sections.get('content_quality', {}).get('share_font_stylesheet_policy', False)
    apple_touch_icon_ready = sections.get('content_quality', {}).get('apple_touch_icon_ready', False)
    share_apple_touch_icon_ready = sections.get('content_quality', {}).get('share_apple_touch_icon_ready', False)
    web_app_manifest_ready = sections.get('content_quality', {}).get('web_app_manifest_ready', False)
    web_app_manifest_maskable_icon_ready = sections.get('content_quality', {}).get('web_app_manifest_maskable_icon_ready', False)
    http_failures = sections.get('broken_links_check', {}).get('http_check', {}).get('failures', [])

    failures: list[str] = []
    if not default_mobile_web_app_meta:
        failures.append('default_mobile_web_app_meta=0')
    if not share_mobile_web_app_meta:
        failures.append('share_mobile_web_app_meta=0')
    if not default_mobile_web_app_title:
        failures.append('default_mobile_web_app_title=0')
    if not share_mobile_web_app_title:
        failures.append('share_mobile_web_app_title=0')
    if not default_application_name_meta:
        failures.append('default_application_name_meta=0')
    if not share_application_name_meta:
        failures.append('share_application_name_meta=0')
    if not default_theme_color_meta:
        failures.append('default_theme_color_meta=0')
    if not share_theme_color_meta:
        failures.append('share_theme_color_meta=0')
    if not default_main_landmark_labeled:
        failures.append('default_main_landmark_labeled=0')
    if not share_main_landmark_labeled:
        failures.append('share_main_landmark_labeled=0')
    if broken:
        failures.append(f'broken_links={len(broken)}')
    if missing_entry_alt:
        failures.append(f'missing_entry_image_alt={len(missing_entry_alt)}')
    if not share_page_social_image_ready:
        failures.append('share_page_social_image_ready=0')
    if not social_alt_fallback_template:
        failures.append('social_alt_fallback_template=0')
    if not paginated_noindex_policy:
        failures.append('paginated_noindex_policy=0')
    if not paginated_hreflang_policy:
        failures.append('paginated_hreflang_policy=0')
    if not canonical_signal_consistency:
        failures.append('canonical_signal_consistency=0')
    if missing_dimensions:
        failures.append(f'missing_post_image_dimensions={len(missing_dimensions)}')
    if missing_page_dimensions:
        failures.append(f'missing_page_image_dimensions={len(missing_page_dimensions)}')
    if invalid_perf_flags:
        failures.append(f'invalid_front_matter_perf_flags={len(invalid_perf_flags)}')
    if not analytics_preconnect_policy:
        failures.append('analytics_preconnect_policy=0')
    if not default_font_preconnect_policy:
        failures.append('default_font_preconnect_policy=0')
    if not share_font_preconnect_policy:
        failures.append('share_font_preconnect_policy=0')
    if not share_font_stylesheet_policy:
        failures.append('share_font_stylesheet_policy=0')
    if not apple_touch_icon_ready:
        failures.append('apple_touch_icon_ready=0')
    if not share_apple_touch_icon_ready:
        failures.append('share_apple_touch_icon_ready=0')
    if not web_app_manifest_ready:
        failures.append('web_app_manifest_ready=0')
    if not web_app_manifest_maskable_icon_ready:
        failures.append('web_app_manifest_maskable_icon_ready=0')
    if http_check_enabled and http_failures:
        failures.append(f'http_failures={len(http_failures)}')
    return failures


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
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Exit with code 2 when broken links or key metadata/performance guardrails regress.',
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

    if args.strict:
        failures = collect_strict_failures(report, http_check_enabled=args.http_check)
        if failures:
            print(f"STRICT_FAIL: {', '.join(failures)}")
            raise SystemExit(2)


if __name__ == '__main__':
    main()
