"""Compact summaries are a presentation layer, not revised tenure evidence."""
import copy
import hashlib
import html
import re
import unittest

from build_team_member_summaries import TEAM, load_summaries, render_document, summary_text, validate
from build_team_role_timelines import DATA as TIMELINES, load_data
from build_team_profile_links import CARD_PATTERN


class MemberSummaryTests(unittest.TestCase):
    def setUp(self):
        self.data = load_summaries()
        self.people = {p['name']: p for p in self.data['people']}

    def test_source_is_reproducible_with_one_summary_per_person(self):
        source = TEAM.read_text()
        self.assertEqual(render_document(source, self.data), source)
        cards = list(CARD_PATTERN.finditer(source))
        self.assertEqual(len(cards), 30)
        for card in cards:
            name = html.unescape(re.search(r'<strong>(.*?)</strong>', card['body'])[1])
            summaries = re.findall(r'<small class="former-member-summary" data-full-summary="([^"]*)">(.*?)</small>', card['body'])
            self.assertEqual(len(summaries), 1)
            full, compact = map(html.unescape, summaries[0])
            self.assertEqual(full, summary_text(self.people[name]))
            self.assertEqual(compact, summary_text(self.people[name], compact=True))
            self.assertNotIn('former-member-role-label', card['body'])

    def test_full_history_months_and_provenance_are_unchanged(self):
        self.assertEqual(hashlib.sha256(TIMELINES.read_bytes()).hexdigest(),
                         '6b0c3a6ca8e7db300e2663f7f278d53f6a37fa49da3b3f2571ade2a3a03fc5a1')
        self.assertEqual(sum(bool(r.get('start')) for p in load_data()['people'] for r in p['roles']), 42)

    def test_unknown_and_suppressed_roles_are_not_invented(self):
        self.assertEqual(self.people['Orion Moore']['last_year'], 2022)
        self.assertEqual(self.people['Orion Moore']['year_basis'], 'user_confirmation')
        self.assertEqual(summary_text(self.people['Orion Moore']), 'Combustion Dynamics Lead · 2022')
        self.assertEqual(sum(p['last_year'] is None for p in self.people.values()), 0)
        unknown = dict(self.people['Orion Moore'], last_year=None)
        self.assertEqual(summary_text(unknown), 'Combustion Dynamics Lead')
        self.assertEqual(summary_text(self.people['Dmitriy Leminov']), '2025')
        self.assertEqual(summary_text(self.people['Audrey Abergel-Preston']), 'Chief Engineer · 2026')
        self.assertEqual(summary_text(self.people['Ben Kubica']), 'Co-captain · 2025')
        self.assertEqual(summary_text(self.people['Zeul Mordasiewicz']), 'Captain · 2026')
        self.assertEqual(summary_text(self.people['Nikolai Sydorenko']), 'Technical Director · 2025')
        self.assertEqual(summary_text(self.people['Nikolai Sydorenko'], compact=True), 'Tech. Director · 2025')
        self.assertEqual(self.people['Nikolai Sydorenko']['year_basis'], 'user_confirmation')
        self.assertEqual(self.data['sources']['nikolai-user-role-year-confirmation']['kind'], 'user_confirmation')
        history = next(p for p in load_data()['people'] if p['name'] == 'Nikolai Sydorenko')
        self.assertEqual([r['label'] for r in history['roles']],
                         ['Combustion Dynamics Member', 'Combustion Dynamics Lead'])

    def test_highest_role_and_participation_year_are_independent(self):
        expected = {'Balin Moher': ('Co-founder', 2019), 'Zak Harrison': ('Co-founder', 2020),
                    'Matthew Ho': ('Captain', 2021), 'Umar Shabbir': ('Captain', 2023),
                    'William Pirie': ('Captain', 2025), 'Jack Sinclair': ('Safety Officer', 2024),
                    'Milad Hemmat': ('Media Lead', 2026), 'Rochelle Suarez-Tapanes': ('Propulsion Lead', 2024)}
        for name, facts in expected.items():
            self.assertEqual((self.people[name]['highest_role'], self.people[name]['last_year']), facts)
        self.assertEqual(self.people['Adam Oudeh']['last_year'], 2025)
        self.assertTrue(self.data['sources']['pdr2025_authors']['url'].endswith('#page=4'))

    def test_user_display_labels_preserve_years_and_documented_roles(self):
        for name, year, historical in [
                ('Aditya Shinde', 2025, 'Software & Propulsion Engineer'),
                ('Anuja Thurairajah', 2026, 'Director of Media & Logistics'),
                ('Farhan Raza', 2019, 'Senior Mechanical Engineer – Propellant Management'),
                ('Jack Sinclair', 2024, 'Chief Safety Officer')]:
            person = self.people[name]
            self.assertEqual(person['last_year'], year)
            self.assertTrue(any(self.data['sources'].get(s, {}).get('kind') == 'user_confirmation'
                                for s in person['role_source_ids']))
            expected = f'Safety Officer · {year}' if name == 'Jack Sinclair' else str(year)
            self.assertEqual(summary_text(person), expected)
            self.assertEqual(summary_text(person, compact=True), expected)
            history = next(p for p in load_data()['people'] if p['name'] == name)
            self.assertIn(historical, [r['label'] for r in history['roles']])
        self.assertEqual(summary_text(self.people['Anuja Thurairajah']), '2026')

    def test_full_display_words_do_not_rewrite_historical_telemetry_titles(self):
        for name in ('Daniel Ibanescu', 'Kai Stewart', 'Mark Paul', 'Georgia Jovanovic'):
            self.assertIn('Telemetry and Control', summary_text(self.people[name]))
            self.assertIn('T&C Lead', summary_text(self.people[name], compact=True))

    def test_checked_on_or_stale_present_is_not_activity_proof(self):
        bad = copy.deepcopy(self.data)
        bad['people'][0]['last_year'] = 2026
        with self.assertRaises(AssertionError):
            validate(bad)
        bad = copy.deepcopy(self.data)
        orion = next(p for p in bad['people'] if p['name'] == 'Orion Moore')
        orion.update(last_year=2026, year_basis='explicit_role_end',
                     year_source_ids=['orion-moore-linkedin-volunteering'])
        with self.assertRaises(AssertionError):
            validate(bad)

    def test_private_source_content_is_rejected(self):
        for key, value in [('quote', 'Private evidence'), ('url', 'https://discord.com/channels/private')]:
            bad = copy.deepcopy(self.data)
            bad['sources']['discord_media_20251226'][key] = value
            with self.assertRaises(AssertionError):
                validate(bad)


if __name__ == '__main__':
    unittest.main()
