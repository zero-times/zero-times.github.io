#!/usr/bin/env python3
"""Generate a lightweight Jekyll site audit report in reports/.

Checks: SEO template coverage, obvious malformed links/placeholders,
mobile/accessibility guardrails, and basic performance hygiene.
"""

from __future__ import annotations

import datetime as dt
import json
import re
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


def build_report() -> dict:
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
            'score': 9.0 if not malformed_links and not placeholder_hits else 6.5,
            'max_score': 10.0,
            'findings': [
                {
                    'aspect': 'URL Pattern Scan',
                    'result': 'Clean'
                    if not malformed_links and not placeholder_hits
                    else f"Issues found ({len(malformed_links) + len(placeholder_hits)})",
                    'details': 'Regex scan for duplicated protocol and placeholder domains/markers.',
                }
            ],
            'broken_links': malformed_links + placeholder_hits,
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
            'Periodically validate high-traffic external links with an HTTP checker in CI.',
        ],
    }


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    out = REPORTS_DIR / f'site_audit_{stamp}.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
