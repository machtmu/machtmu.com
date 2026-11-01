#!/usr/bin/env python3
"""Render checked-in former-member icon links from reviewed public destinations.

SVG artwork is copied unchanged from MARS founder links (Font Awesome Free
7.3.1), with its license notice retained. No MARS checkout or private evidence
is required for CI. --print emits a document for a reviewed source patch.
"""
import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/team-profile-links.json'
TEAM = ROOT / 'docs/team.md'
SVG_MARKUP = {
    'website': "<svg aria-hidden=\"true\" focusable=\"false\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 512 512\"><!--! Font Awesome Free 7.3.1 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2026 Fonticons, Inc.--><path fill=\"currentColor\" d=\"M351.9 280H161c2.9 64.5 17.2 123.9 37.5 167.4 11.4 24.5 23.7 41.8 35.1 52.4 11.2 10.5 18.9 12.2 22.9 12.2s11.7-1.7 22.9-12.2c11.4-10.6 23.7-28 35.1-52.4 20.3-43.5 34.6-102.9 37.5-167.4zm-191-48h190.9c-2.8-64.5-17.1-123.9-37.4-167.4-11.4-24.4-23.7-41.8-35.1-52.4C268.1 1.7 260.4 0 256.4 0s-11.7 1.7-22.9 12.2c-11.4 10.6-23.7 28-35.1 52.4-20.3 43.5-34.6 102.9-37.5 167.4m-48 0c3.5-85.6 25.6-165.1 57.9-217.3C78.7 47.3 10.9 131.2 1.5 232zM1.5 280c9.4 100.8 77.2 184.7 169.3 217.3-32.3-52.2-54.4-131.7-57.9-217.3zm398.4 0c-3.5 85.6-25.6 165.1-57.9 217.3 92.1-32.7 159.9-116.5 169.3-217.3zm111.4-48C501.9 131.2 434.1 47.3 342 14.7c32.3 52.2 54.4 131.7 57.9 217.3z\"/></svg>",
    'linkedin': "<svg aria-hidden=\"true\" focusable=\"false\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 448 512\"><!--! Font Awesome Free 7.3.1 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free (Icons: CC BY 4.0, Fonts: SIL OFL 1.1, Code: MIT License) Copyright 2026 Fonticons, Inc.--><path fill=\"currentColor\" d=\"M416 32H31.9C14.3 32 0 46.5 0 64.3v383.4C0 465.5 14.3 480 31.9 480H416c17.6 0 32-14.5 32-32.3V64.3c0-17.8-14.4-32.3-32-32.3M135.4 416H69V202.2h66.5V416zM102.2 96a38.5 38.5 0 1 1 0 77 38.5 38.5 0 1 1 0-77m282.1 320h-66.4V312c0-24.8-.5-56.7-34.5-56.7-34.6 0-39.9 27-39.9 54.9V416h-66.4V202.2h63.7v29.2h.9c8.9-16.8 30.6-34.5 62.9-34.5 67.2 0 79.7 44.3 79.7 101.9z\"/></svg>",
}
CARD_PATTERN = re.compile(
    r'<(?P<tag>a|div) class="former-member-card"(?: href="(?P<href>[^"]+)")?>'
    r'(?P<body>.*?)</(?P=tag)>', re.DOTALL)


def span_content_range(source, class_name):
    """Find a known source wrapper without truncating nested role/link spans."""
    matches = list(re.finditer(r'<span class="' + re.escape(class_name) + r'"[^>]*>', source))
    assert len(matches) == 1, f'Expected one {class_name} wrapper'
    start, depth = matches[0].end(), 1
    for tag in re.finditer(r'</?span\b[^>]*>', source[start:]):
        depth += -1 if tag[0].startswith('</') else 1
        if depth == 0:
            return start, start + tag.start()
    raise AssertionError(f'Unclosed {class_name} wrapper')


def load_links(path=DATA):
    data = json.loads(path.read_text())
    assert data['schema_version'] == 1 and len(data['people']) == 30
    seen = set()
    for person in data['people']:
        assert set(person) == {'name', 'linkedin', 'website'}
        assert person['name'] not in seen
        seen.add(person['name'])
        for kind in ('linkedin', 'website'):
            value = person[kind]
            if value is None:
                continue
            url = urlsplit(value)
            assert url.scheme == 'https' and url.hostname and not url.username and not url.password
            assert not url.query and not url.fragment
            if kind == 'linkedin':
                assert url.hostname in {'www.linkedin.com', 'ca.linkedin.com', 'linkedin.com'}
                assert url.path.startswith('/in/') and len(url.path) > 4
        if person['name'] in {'Dmitriy Leminov', 'Yiwei Luo'}:
            assert person['linkedin'] is None, 'Do not invent unverified profile URLs'
    return {p['name']: p for p in data['people']}


def links_markup(person):
    name = person['name']
    links = []
    for kind, title in (('website', 'website'), ('linkedin', 'LinkedIn')):
        if person[kind]:
            label = html.escape(f"{name}'s {title}", quote=True)
            links.append(
                f'<a class="former-member-link former-member-link--{kind}" '
                f'href="{html.escape(person[kind], quote=True)}" target="_blank" '
                f'rel="noopener noreferrer" aria-label="{label}" title="{label}">'
                + SVG_MARKUP[kind] + '</a>')
    if not links:
        return ''
    return ('<span class="former-member-links" role="group" aria-label="'
            + html.escape(f"{name}'s links", quote=True) + '">' + ''.join(links) + '</span>')


def render_document(document, links):
    seen = set()

    def replace(match):
        body = match['body']
        name = html.unescape(re.search(r'<strong>(.*?)</strong>', body)[1])
        assert name in links and name not in seen
        seen.add(name)
        person = links[name]
        if match['tag'] == 'a':
            assert html.unescape(match['href']) == person['linkedin'], 'Preserve verified profile URLs'
        body = re.sub(r'<span class="former-member-links"[^>]*>.*?</span>', '', body, flags=re.DOTALL)
        _, end = span_content_range(body, 'former-member-portrait')
        end += len('</span>')
        body = body[:end] + links_markup(person) + body[end:]
        return '<div class="former-member-card">' + body + '</div>'

    rendered = CARD_PATTERN.sub(replace, document)
    assert seen == links.keys(), 'Only the existing30 former profiles may receive icons'
    return rendered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--print', action='store_true', dest='print_document')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    document = TEAM.read_text()
    rendered = render_document(document, load_links())
    if args.print_document:
        print(rendered, end='')
    else:
        assert rendered == document, 'Icon links differ; apply a reviewed source patch'
        print('Former-member icons match reviewed destinations; current leads untouched.')


if __name__ == '__main__':
    main()
