#!/usr/bin/env python3
"""Render approved highest-role/last-participation-year summaries only.

Complete role periods remain in team-role-timelines.json. Summary selection is
curated, never inferred from stale Present claims or the current calendar year.
"""
import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from build_team_profile_links import CARD_PATTERN, load_links, span_content_range
from build_team_role_timelines import load_data

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/team-member-summaries.json'
TEAM = ROOT / 'docs/team.md'


def validate(data):
    assert data['schema_version'] == 1
    canonical = load_data()
    extra_sources = data.get('sources', {})
    assert not (extra_sources.keys() & canonical['sources'].keys())
    for source in extra_sources.values():
        assert set(source) <= {'kind', 'url', 'checked_on', 'participation_year'}
        assert source['kind'] in {'official_report', 'explicit_announcement',
                                  'user_confirmation', 'repository_snapshot'}
        if source.get('url'):
            url = urlsplit(source['url'])
            assert url.scheme == 'https' and url.hostname and not url.username and not url.password
            assert 'discord' not in url.hostname and not url.query
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', source['checked_on'])
    sources = {**canonical['sources'], **extra_sources}
    people = data['people']
    assert len(people) == 31
    assert {p['name'] for p in people} == load_links().keys()
    for person in people:
        assert set(person) == {'name', 'highest_role', 'compact_role', 'role_source_ids', 'last_year',
                               'year_source_ids', 'year_basis'}
        role = person['highest_role']
        compact = person['compact_role']
        assert (role is None) == (compact is None)
        assert compact is None or (compact and '\n' not in compact and 'Transfer' not in compact)
        assert role is None or (role and '\n' not in role and 'Transfer' not in role)
        assert role != 'Founder' and not (role or '').startswith('Former ')
        assert set(person['role_source_ids']) <= sources.keys()
        assert not role or person['role_source_ids']
        year = person['last_year']
        if year is None:
            assert person['year_basis'] == 'unknown' and not person['year_source_ids']
        else:
            assert type(year) is int and 1900 <= year <= 2100
            assert person['year_basis'] in {'user_confirmation', 'explicit_role_end',
                                          'last_documented_participation'}
            assert person['year_source_ids'] and set(person['year_source_ids']) <= sources.keys()
            periods = next((p['roles'] for p in canonical['people'] if p['name'] == person['name']), [])
            has_verified_end = any(r.get('end', {}).get('value', '')[:4] == str(year) and
                                   set(r['end']['source_ids']) & set(person['year_source_ids'])
                                   for r in periods)
            if person['year_basis'] == 'explicit_role_end':
                assert has_verified_end, 'An explicit-end summary year requires a verified end source'
            elif person['year_basis'] == 'user_confirmation':
                assert any(sources[s]['kind'] == 'user_confirmation' and
                           (has_verified_end or sources[s].get('participation_year') == year)
                           for s in person['year_source_ids']), \
                    'A confirmed participation year need not invent a role-end boundary'
            else:
                assert any(sources[s].get('participation_year') == year for s in person['year_source_ids']), \
                    'An active-year record is required; checked_on/Present is not participation proof'
        if person['name'] in {'Dmitriy Leminov', 'Aditya Shinde', 'Farhan Raza', 'Anuja Thurairajah'}:
            assert role is None, 'User suppressed this role, not merely its historical date'
            assert any(sources[s]['kind'] == 'user_confirmation' for s in person['role_source_ids'])
        if person['name'] == 'Jack Sinclair':
            assert role == compact == 'Safety Officer'
            assert any(sources[s]['kind'] == 'user_confirmation' for s in person['role_source_ids'])
        if person['name'] == 'Audrey Abergel-Preston':
            assert role == 'Chief Engineer' and year == 2026
        if person['name'] == 'Ben Kubica':
            assert year == 2025
        if person['name'] == 'Zeul Mordasiewicz':
            assert role == 'Captain' and year == 2026
        if person['name'] == 'Nikolai Sydorenko':
            assert role == 'Technical Director' and compact == 'Tech. Director' and year == 2025
            assert person['year_basis'] == 'user_confirmation'
    return data


def load_summaries(path=DATA):
    return validate(json.loads(path.read_text()))


def summary_text(person, compact=False):
    role = person['compact_role' if compact else 'highest_role']
    if role and not compact:
        role = role.replace('Telemetry & Control', 'Telemetry and Control')
    parts = [role,
             str(person['last_year']) if person['last_year'] else None]
    return ' · '.join(part for part in parts if part)


def render_document(document, data):
    validate(data)
    people = {p['name']: p for p in data['people']}
    seen = set()

    def replace(match):
        body = match['body']
        name = html.unescape(re.search(r'<strong>(.*?)</strong>', body)[1])
        assert name in people and name not in seen
        seen.add(name)
        text = summary_text(people[name], compact=True)
        full = html.escape(summary_text(people[name]), quote=True)
        markup = ('<small class="former-member-summary" data-full-summary="' + full + '">'
                  + html.escape(text) + '</small>') if text else ''
        start, end = span_content_range(body, 'former-member-details')
        body = body[:start] + markup + body[end:]
        return '<div class="former-member-card">' + body + '</div>'

    result = CARD_PATTERN.sub(replace, document)
    assert seen == people.keys()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--print', action='store_true', dest='print_document')
    args = parser.parse_args()
    source = TEAM.read_text()
    rendered = render_document(source, load_summaries())
    if args.print_document:
        print(rendered, end='')
    else:
        assert rendered == source, 'Summary source differs; apply a reviewed patch'
        print('Former summaries match approved role/year facts; canonical histories preserved.')


if __name__ == '__main__':
    main()
