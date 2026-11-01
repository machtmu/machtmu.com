#!/usr/bin/env python3
"""Render/check curated former-role lines without private research dependencies.

Edit the public fact file only after source review. --check verifies checked-in
HTML is reproducible; --print shows the document for a reviewed source patch.
Report dates, project dates and unknown endpoints are never tenure boundaries.
"""
import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from build_team_profile_links import CARD_PATTERN, span_content_range

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/team-role-timelines.json'
TEAM = ROOT / 'docs/team.md'
CURRENT_PORTRAITS = {
    'Julia Puszynska': 'julia', 'Tobechukwu Okoh': 'toby', 'Samuel Li': 'samuel',
    'Jonathan Al-Hinn': 'jonathan', 'Kasper Pajak': 'kasper', 'Madison Warren': 'madison',
}


def validate(data):
    assert data['schema_version'] == 1
    sources = data['sources']
    for source in sources.values():
        assert set(source) <= {'kind', 'url', 'checked_on'}, 'No private source content in curated data'
        assert source['kind'] in {'linkedin_experience', 'linkedin_volunteering',
                                  'explicit_announcement', 'user_confirmation'}
        if source.get('url'):
            url = urlsplit(source['url'])
            assert url.scheme == 'https' and url.hostname
            assert not url.username and not url.password and not url.query
            assert 'discord' not in url.hostname, 'Private announcements use opaque IDs only'
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', source['checked_on'])
    seen = set()
    for person in data['people']:
        name = person['name']
        assert name not in seen
        seen.add(name)
        assert person.get('placement', 'former') == 'former'
        assert name not in CURRENT_PORTRAITS, 'Current leads do not display historical role blocks'
        assert person['roles'] and name != 'Dmitriy Leminov'
        starts = []
        for role in person['roles']:
            label = role['label']
            assert label and not label.startswith('Former ') and 'Transfer' not in label
            assert label != 'Founder'
            if name == 'Audrey Abergel-Preston':
                assert label == 'Chief Engineer'
            if name == 'Balin Moher':
                assert label in {'Co-founder', 'Co-founder & Director'}
            start, end = role.get('start'), role.get('end')
            assert not end or start, 'End-only dates must not imply an invented start'
            for which, boundary in (('start', start), ('end', end)):
                if not boundary:
                    continue
                assert set(boundary) <= {'value', 'precision', 'basis', 'source_ids', 'state'}
                assert boundary['source_ids'] and set(boundary['source_ids']) <= sources.keys()
                if boundary.get('state') == 'present':
                    assert which == 'end' and boundary['basis'] == 'explicit_ongoing_role'
                    assert 'value' not in boundary
                    assert any(sources[s]['kind'] == 'user_confirmation' for s in boundary['source_ids']), \
                        'Unconfirmed LinkedIn Present is not a public ongoing-role claim'
                    continue
                assert boundary['basis'] == f'explicit_role_{which}'
                value, precision = boundary['value'], boundary['precision']
                assert precision in {'year', 'month'}
                pattern = r'\d{4}' if precision == 'year' else r'\d{4}-(0[1-9]|1[0-2])'
                assert re.fullmatch(pattern, value)
                assert 1900 <= int(value[:4]) <= 2100
            if start:
                starts.append(start['value'])
                if end and end.get('state') != 'present':
                    assert start['value'][:4] <= end['value'][:4]
                    if start['precision'] == end['precision']:
                        assert start['value'] <= end['value']
        assert starts == sorted(starts), 'Dated roles must be oldest first'
    return data


def load_data(path=DATA):
    return validate(json.loads(path.read_text()))


def date_text(boundary):
    if boundary.get('state') == 'present':
        return 'Present'
    # Display preference only: retain exact source month precision in curated data.
    return boundary['value'][:4]


def role_text(role):
    label = role['label']
    if not role.get('start'):
        return label
    start = date_text(role['start'])
    if not role.get('end'):
        # An explicit role start is not proof that the role remains ongoing.
        return f'{label} · started {start}'
    end = date_text(role['end'])
    return f'{label} · {start}' if start == end else f'{label} · {start}–{end}'


def role_lines(name, fallback, data=None):
    data = load_data() if data is None else data
    person = next((p for p in data['people'] if p['name'] == name), None)
    if person:
        return [role_text(role) for role in person['roles']]
    return [fallback] if fallback else []


def role_markup(role):
    text = role_text(role)
    if not role.get('start'):
        content = html.escape(text)
    else:
        label = role['label']
        content = ('<span class="former-member-role-label">' + html.escape(label) + '</span>'
                   '<span class="former-member-role-dates">' + html.escape(text[len(label):]) + '</span>')
    return '<small class="former-member-role">' + content + '</small>'


def render_document(document, data):
    validate(data)
    people = {person['name']: person for person in data['people']}
    seen = set()

    def replace_card(match):
        body = match['body']
        name = html.unescape(re.search(r'<strong>(.*?)</strong>', body)[1])
        if name not in people:
            return match[0]
        assert name not in seen
        seen.add(name)
        person = people[name]
        lines = ''.join(role_markup(role) for role in person['roles'])
        start, end = span_content_range(body, 'former-member-details')
        body = body[:start] + lines + body[end:]
        relative_start = match.start('body') - match.start()
        relative_end = match.end('body') - match.start()
        return match[0][:relative_start] + body + match[0][relative_end:]

    rendered = CARD_PATTERN.sub(replace_card, document)
    assert seen == people.keys(), 'Every curated former person must appear exactly once'
    return rendered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--print', action='store_true', dest='print_document')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    document = TEAM.read_text()
    rendered = render_document(document, load_data())
    if args.print_document:
        print(rendered, end='')
    else:
        # The visible UI now uses concise summaries, not every canonical period.
        # --print still exports the complete reproducible history for review.
        from build_team_member_summaries import load_summaries, render_document as render_summaries
        assert render_summaries(document, load_summaries()) == document
        print('Canonical timelines retain explicit provenance; visible summaries match approved facts.')


if __name__ == '__main__':
    main()
