"""Curated public role dates must be explicit, reproducible and policy-safe."""
import copy
import html
import re
import unittest

from build_team_role_timelines import TEAM, date_text, load_data, render_document, role_lines, role_text, validate
from check_team_history import ROLES


class TeamRoleTimelineTests(unittest.TestCase):
    def setUp(self):
        self.data = load_data()

    def test_complete_canonical_history_export_remains_reproducible(self):
        source = render_document(TEAM.read_text(), self.data)
        self.assertEqual(render_document(source, self.data), source)
        cards = re.findall(r'<div class="former-member-card">.*?</div>', source)
        expected_names = set(ROLES) | {'Antonella Ruta', 'David Machuca', 'Dmitriy Leminov', 'Farhan Raza'}
        names = []
        for card in cards:
            name = html.unescape(re.search(r'<strong>(.*?)</strong>', card)[1])
            names.append(name)
            lines = [html.unescape(re.sub(r'<[^>]+>', '', s))
                     for s in re.findall(r'<small(?: [^>]*)?>(.*?)</small>', card)]
            if any(p['name'] == name for p in self.data['people']):
                self.assertEqual(lines, role_lines(name, ROLES.get(name), self.data))
        self.assertEqual(len(names), 31)
        self.assertEqual(set(names), expected_names)

    def test_current_portrait_overlays_are_unchanged(self):
        overlays = re.findall(r'<span class="team-portrait-caption"><strong>(.*?)</strong><em>(.*?)</em></span>',
                              TEAM.read_text())
        self.assertEqual([(html.unescape(name), html.unescape(role)) for name, role in overlays], [
            ('Julia Puszynska', 'Team Captain'), ('Tobechukwu Okoh', 'Propulsion Lead'),
            ('Samuel Li', 'Operations Director'), ('Jonathan Al-Hinn', 'Safety Officer'),
            ('Kasper Pajak', 'Electrical Lead'), ('Madison Warren', 'Media & Logistics Lead')])
        self.assertNotIn('team-portrait-history', TEAM.read_text())

    def test_maheer_explicit_role_chronology_is_not_inferred_from_the_poster(self):
        person = next(p for p in self.data['people'] if p['name'] == 'Maheer K.')
        self.assertEqual([(r['label'], r['start']['value'], r['end']['value']) for r in person['roles']], [
            ('Telemetry & Control Hardware', '2019-09', '2020-01'),
            ('Avionics Team Lead', '2020-01', '2021-07')])
        for role in person['roles']:
            for endpoint in ('start', 'end'):
                self.assertEqual(role[endpoint]['precision'], 'month')
                self.assertEqual(role[endpoint]['basis'], 'explicit_role_' + endpoint)
                self.assertEqual(role[endpoint]['source_ids'], ['maheer-k-linkedin-rpg-experience'])
        source = self.data['sources']['maheer-k-linkedin-rpg-experience']
        self.assertEqual(source['url'], 'https://ca.linkedin.com/in/7mkazi7')
        self.assertEqual(source['checked_on'], '2026-11-02')

    def test_current_history_cannot_be_rendered(self):
        bad = copy.deepcopy(self.data)
        bad['people'].append({'name': 'Julia Puszynska', 'placement': 'current_history',
                             'roles': [{'label': 'Team Captain'}]})
        with self.assertRaises(AssertionError):
            validate(bad)

    def test_known_role_identities_are_retained(self):
        for person in self.data['people']:
            labels = {role['label'] for role in person['roles']}
            fallback = ROLES.get(person['name'])
            if person['name'] == 'Zak Harrison':
                self.assertTrue('Co-founder · Captain' in labels or {'Co-founder', 'Captain'} <= labels)
            elif fallback:
                self.assertIn(fallback, labels)

    def test_explicit_role_boundaries_only(self):
        for basis in ('held_as_of', 'project_range', 'inferred_membership'):
            bad = copy.deepcopy(self.data)
            bad['people'][0]['roles'][0]['start']['basis'] = basis
            with self.assertRaises(AssertionError):
                validate(bad)

    def test_every_boundary_requires_source(self):
        bad = copy.deepcopy(self.data)
        bad['people'][0]['roles'][0]['end']['source_ids'] = []
        with self.assertRaises(AssertionError):
            validate(bad)

    def test_private_announcement_content_not_curated(self):
        bad = copy.deepcopy(self.data)
        next(iter(bad['sources'].values()))['url'] = 'https://discord.com/channels/private/message'
        with self.assertRaises(AssertionError):
            validate(bad)
        bad = copy.deepcopy(self.data)
        next(iter(bad['sources'].values()))['quote'] = 'Private announcement'
        with self.assertRaises(AssertionError):
            validate(bad)

    def test_precision_and_ongoing_are_explicit(self):
        self.assertEqual(date_text({'value': '2025', 'precision': 'year'}), '2025')
        self.assertEqual(date_text({'value': '2025-07', 'precision': 'month'}), '2025')
        bad = copy.deepcopy(self.data)
        bad['people'][0]['roles'][0]['end'] = {'state': 'present', 'basis': 'held_as_of',
                                             'source_ids': ['zeul-linkedin-mach-experience']}
        with self.assertRaises(AssertionError):
            validate(bad)

    def test_year_only_display_preserves_canonical_months(self):
        role = {'label': 'Lead', 'start': {'value': '2025-03', 'precision': 'month'},
                'end': {'value': '2025-11', 'precision': 'month'}}
        self.assertEqual(role_text(role), 'Lead · 2025')
        role['end']['value'] = '2026-01'
        self.assertEqual(role_text(role), 'Lead · 2025–2026')
        self.assertEqual(role['start']['value'], '2025-03')
        self.assertEqual(role['start']['precision'], 'month')
        del role['end']
        self.assertEqual(role_text(role), 'Lead · started 2025')

    def test_unconfirmed_present_is_not_public_ongoing(self):
        bad = copy.deepcopy(self.data)
        bad['people'][0]['roles'][0]['end'] = {
            'state': 'present', 'basis': 'explicit_ongoing_role',
            'source_ids': ['zeul-linkedin-mach-experience']}
        with self.assertRaises(AssertionError):
            validate(bad)

    def test_user_corrected_endpoints_and_unknown_ends(self):
        people = {p['name']: p for p in self.data['people']}
        for name, label, end in [('Ben Kubica', 'Co-captain', '2025-03'),
                                 ('Audrey Abergel-Preston', 'Chief Engineer', '2026-08'),
                                 ('Zeul Mordasiewicz', 'Captain', '2026-01')]:
            role = next(r for r in people[name]['roles'] if r['label'] == label)
            self.assertEqual(role['end']['value'], end)
            self.assertEqual(role['end']['precision'], 'month')
            self.assertTrue(any(self.data['sources'][s]['kind'] == 'user_confirmation'
                                for s in role['end']['source_ids']))
        for name, label in [('Orion Moore', 'Combustion Dynamics CAD Designer'),
                             ('Milad Hemmat', 'Electrical Team')]:
            role = next(r for r in people[name]['roles'] if r['label'] == label)
            self.assertNotIn('end', role)
            self.assertIn(' · started ', role_text(role))

    def test_user_suppressions_cannot_be_restored(self):
        for name, label in [('Dmitriy Leminov', 'Chief Safety Officer'),
                            ('Audrey Abergel-Preston', 'Chief Safety Officer')]:
            bad = copy.deepcopy(self.data)
            bad['people'].append({'name': name, 'roles': [{'label': label}]})
            with self.assertRaises(AssertionError):
                validate(bad)

    def test_dated_roles_are_chronological(self):
        bad = copy.deepcopy(self.data)
        role = copy.deepcopy(bad['people'][0]['roles'][0])
        role['start']['value'] = '2021-01'
        role['end']['value'] = '2021-08'
        bad['people'][0]['roles'].append(role)
        with self.assertRaises(AssertionError):
            validate(bad)


if __name__ == '__main__':
    unittest.main()
