"""Former-only links preserve reviewed destinations, MARS glyphs and current leads."""
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest

from build_team_profile_links import CARD_PATTERN, ROOT, SVG_MARKUP, TEAM, links_markup, load_links, render_document, span_content_range


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.svgs, self.groups = [], [], []
        self.anchor_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            assert self.anchor_depth == 0, 'Nested anchors are invalid'
            self.anchor_depth += 1
            self.links.append(attrs)
        if tag == 'svg':
            self.svgs.append(attrs)
        if tag == 'span' and attrs.get('role') == 'group':
            self.groups.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'a':
            self.anchor_depth -= 1
            assert self.anchor_depth == 0


class TeamProfileLinkTests(unittest.TestCase):
    def test_public_links_render_reproducibly(self):
        document, people = TEAM.read_text(), load_links()
        self.assertEqual(render_document(document, people), document)
        cards = list(CARD_PATTERN.finditer(document))
        self.assertEqual(len(cards), 30)
        self.assertNotIn('<a class="former-member-card"', document)
        self.assertEqual(sum(bool(p['linkedin']) for p in people.values()), 28)
        self.assertEqual(sum(bool(p['website']) for p in people.values()), 4)
        for card in cards:
            self.assertEqual(card['tag'], 'div')
            self.assertIn('<span class="former-member-portrait">', card['body'])
            self.assertIn('<span class="former-member-name"><strong>', card['body'])
            self.assertNotIn('<div', card['body'])
            photo_start, photo_end = span_content_range(card['body'], 'former-member-portrait')
            self.assertTrue(card['body'][photo_end:].startswith('</span>'))
            footer = card['body'][photo_end + len('</span>'):]
            portrait = card['body'][photo_start:photo_end]
            self.assertNotIn('former-member-links', portrait)
            overlay_start, overlay_end = span_content_range(portrait, 'former-member-overlay')
            overlay = portrait[overlay_start:overlay_end]
            self.assertIn('<span class="former-member-name">', overlay)
            self.assertIn('<span class="former-member-details">', overlay)
            self.assertEqual(overlay.count('<small'), portrait.count('<small'))
            name = html.unescape(re.search(r'<strong>(.*?)</strong>', card['body'])[1])
            expected = [(kind, people[name][kind]) for kind in ('website', 'linkedin') if people[name][kind]]
            self.assertEqual(footer, links_markup(people[name]))
            parser = LinkParser()
            parser.feed(card['body'])
            self.assertEqual(parser.anchor_depth, 0)
            self.assertEqual(len(parser.links), len(expected))
            self.assertEqual(len(parser.svgs), len(expected))
            self.assertEqual(len(parser.groups), bool(expected))
            for link, svg, (kind, url) in zip(parser.links, parser.svgs, expected):
                title = 'website' if kind == 'website' else 'LinkedIn'
                self.assertEqual(link['href'], url)
                self.assertIn(f'former-member-link--{kind}', link['class'].split())
                self.assertEqual(link['aria-label'], f"{name}'s {title}")
                self.assertEqual(link['title'], link['aria-label'])
                self.assertEqual(link['target'], '_blank')
                self.assertTrue({'noopener', 'noreferrer'} <= set(link['rel'].split()))
                self.assertEqual(svg['aria-hidden'], 'true')
                self.assertEqual(svg['focusable'], 'false')

    def test_exact_mars_artwork_and_license_preserved(self):
        expected = {'website': '85f953f27482b3d37a6354a7b09a5cee5ccf1359177287b34963cc3bb5e32fe3',
                    'linkedin': '4fa4f5f4845d3e12ec6c85e20d61903d8f05ff53d8581876e99aeb503746fd26'}
        for kind, digest in expected.items():
            self.assertEqual(hashlib.sha256(SVG_MARKUP[kind].encode()).hexdigest(), digest)
            self.assertIn('Font Awesome Free 7.3.1', SVG_MARKUP[kind])
            self.assertIn('https://fontawesome.com/license/free', SVG_MARKUP[kind])

    def test_missing_profiles_are_not_guessed(self):
        people = load_links()
        for name in ('Dmitriy Leminov', 'Yiwei Luo'):
            self.assertIsNone(people[name]['linkedin'])
            self.assertIsNone(people[name]['website'])

    def test_current_six_and_employers_source_unchanged(self):
        # Authorized history removal/heading semicolon only; portraits/logos unchanged.
        source = TEAM.read_text()
        current = source[source.index('<div class="team-leads team-portraits">'):source.index('<section class="team-employers"')]
        employers = source[source.index('<section class="team-employers"'):source.index('<span id="founders-and-early-members"')]
        self.assertEqual(hashlib.sha256(current.encode()).hexdigest(),
                         '41416db900fedcc379dba5a134d637993d7e3f46ebf622dbd15be4e28433e5b5')
        self.assertEqual(hashlib.sha256(employers.encode()).hexdigest(),
                         '4926ceb9beadab5df941f4b1717788f0435a034d31a6248fe9d3904b6acef1d4')
        landmarks = json.loads((ROOT / 'scripts/team_portrait_landmarks.json').read_text())
        for photo in landmarks['portraits']:
            path = ROOT / 'docs/assets/images/leads' / photo['file']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), photo['sha256'])


if __name__ == '__main__':
    unittest.main()
