"""Collect public 2026 proceedings metadata and conference presentation evidence."""

import argparse
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin

import fitz
import requests
from bs4 import BeautifulSoup

CVF = 'https://openaccess.thecvf.com'
CVPR_PROGRAM = 'https://media.eventhosts.cc/Conferences/CVPR2026/CVPR_main_conf_2026_15.pdf'
ICSE = 'https://conf.researchr.org/track/icse-2026/icse-2026-research-track'
URLS = {
    'pmlr': 'https://proceedings.mlr.press/v306/',
    'icml': 'https://icml.cc/static/virtual/data/icml-2026-orals-posters.json',
    'iclr': 'https://iclr.cc/static/virtual/data/iclr-2026-orals-posters.json',
    'cvpr': f'{CVF}/CVPR2026?day=all', 'cvpr-program': CVPR_PROGRAM,
    'acl': 'https://aclanthology.org/events/acl-2026/',
    'jmlr': 'https://jmlr.org/papers/v27/', 'icse': ICSE,
}


def normalized(value):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', value).casefold() if ch.isalnum())


def html(data):
    return BeautifulSoup(data, 'html.parser')


def load(cache, key, refresh):
    path = cache / key
    if path.exists() and not refresh:
        return path.read_bytes()
    response = requests.get(URLS[key], timeout=(12, 55))
    response.raise_for_status()
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes(response.content)
    temporary.replace(path)
    return response.content


def event_program(data, venue):
    origin = f'https://{venue}.cc'
    rows = {}
    format_priority = {'poster': 1, 'spotlight': 2, 'oral': 3}
    accepted = {'Accept (regular)', 'Accept (spotlight)'} if venue == 'icml' else {'Accept (Poster)', 'Accept (Oral)'}
    for event in json.loads(data)['results']:
        decision = event.get('decision')
        if decision not in accepted or event.get('eventtype') not in {'Oral', 'Poster'}:
            continue
        title = event['name']
        key = normalized(title)
        if not key or not event.get('virtualsite_url'):
            continue
        format_name = ('oral' if event['eventtype'] == 'Oral' or decision == 'Accept (Oral)' else
                       'spotlight' if decision == 'Accept (spotlight)' else 'poster')
        real_oral = event['eventtype'] == 'Oral'
        rank = format_priority[format_name] * 2 + real_oral
        url = urljoin(origin, event['virtualsite_url'])
        incoming = {
            'venue': venue, 'title': title, 'authors': [a['fullname'] for a in event['authors'] if a.get('fullname')],
            'source': url, 'format': format_name, 'formatSource': url if format_name != 'spotlight' else 'https://icml.cc/virtual/2026/events/2026SpotlightPosters',
            'officialTopic': event.get('topic') or '', 'eventRank': rank, 'programSource': url,
        }
        review = event.get('paper_url', '') or ''
        if 'openreview.net/forum?' in review and '2026-Oral--' not in review:
            incoming['review'] = review
        if key not in rows or rank > rows[key]['eventRank']:
            existing = rows.get(key, {})
            for field in ('officialTopic', 'review'):
                if not incoming.get(field) and existing.get(field):
                    incoming[field] = existing[field]
            rows[key] = incoming
        else:
            for field in ('officialTopic', 'review'):
                if not rows[key].get(field) and incoming.get(field):
                    rows[key][field] = incoming[field]
    return rows


def read_icml(proceedings, program):
    event_rows = event_program(program, 'icml')
    for paper in html(proceedings).select('.paper'):
        title_node, authors_node = paper.select_one('.title'), paper.select_one('.authors')
        source = paper.find('a', string='abs')
        if not (title_node and authors_node and source and source.get('href')):
            continue
        title = title_node.get_text(' ', strip=True)
        if re.match(r'^position\s*:', title, re.I):
            continue
        row = dict(event_rows.get(normalized(title), {}))
        authors = [name.strip() for name in authors_node.get_text().split(',\u00a0') if name.strip()]
        if len(authors) == 1 and ', ' in authors[0]:
            authors = [name.strip() for name in authors[0].split(', ') if name.strip()]
        row.update(venue='icml', title=title, authors=authors, source=source['href'], publicationSource='PMLR')
        if review := paper.find('a', string='OpenReview'):
            row['review'] = review['href']
        yield row


def read_iclr(data):
    for row in event_program(data, 'iclr').values():
        if row.get('review') and row.get('authors'):
            yield {**row, 'publicationSource': 'ICLR'}


def cvpr_oral_sessions(data):
    sections = []
    with fitz.open(stream=data, filetype='pdf') as program:
        for page in program:
            text = page.get_text()
            markers = list(re.finditer(r'Oral Session\s+\d+[A-Z]:\s*([^\n\r]+)', text, re.I))
            for index, match in enumerate(markers):
                after = text[match.end():markers[index + 1].start() if index + 1 < len(markers) else len(text)]
                after = re.split(r'(?:Poster Session\s+\d|Coffee Break|Exhibit Hall|PROGRAM GUIDE\s+MAIN CONFERENCE)', after, maxsplit=1, flags=re.I)[0]
                if len(after) > 100:
                    topic = re.sub(r'[\u200b\u200e]+', '', match.group(1)).strip(' \t,')
                    sections.append((normalized(after), f'CVPR 口头报告专题 -> {topic}', f'{CVPR_PROGRAM}#page={page.number + 1}'))
    return sections


def read_cvpr(data, pdf):
    sections = cvpr_oral_sessions(pdf)
    for entry in html(data).select('dt.ptitle > a[href]'):
        authors = entry.parent.find_next_sibling('dd').select('input[name="query_author"]')
        title = entry.get_text(' ', strip=True)
        row = {'venue': 'cvpr', 'title': title, 'authors': [x['value'] for x in authors if x.get('value')],
               'source': urljoin(CVF, entry['href']), 'publicationSource': 'CVF Open Access'}
        key = normalized(title)
        if len(key) >= 15:
            evidence = next(((topic, url) for body, topic, url in sections if key in body), None)
            if evidence:
                topic, url = evidence
                row.update(format='oral', formatSource=url, officialTopic=topic, programSource=url)
        yield row


def read_acl(data):
    for anchor in html(data).find_all('a', href=re.compile(r'^/2026\.acl-long\.[1-9]\d*/$')):
        block = anchor.find_parent('span', class_='d-block')
        if not block:
            continue
        authors = [a.get_text(' ', strip=True) for a in block.select('a[href^="/people/"]')]
        if authors:
            yield {'venue': 'acl', 'title': anchor.get_text(' ', strip=True), 'authors': authors,
                   'source': urljoin('https://aclanthology.org', anchor['href']), 'publicationSource': 'ACL Anthology'}


def read_jmlr(data):
    for item in html(data).find_all('a', href=re.compile(r'^/papers/v27/\d{2}-\d{4}\.html$')):
        block = item.find_parent('dl')
        if not block or not block.dt or not block.dd or not block.dd.i:
            continue
        title = block.dt.get_text(' ', strip=True)
        authors = [name.strip() for name in block.dd.i.get_text(' ', strip=True).split(',') if name.strip()]
        yield {'venue': 'jmlr', 'title': title, 'authors': authors, 'format': 'journal',
               'source': urljoin('https://jmlr.org', item['href']), 'publicationSource': 'JMLR'}


def read_icse(data):
    soup = html(data)
    for a in soup.select('td > strong > a[data-event-modal]'):
        item = a.find_parent('td')
        td_track = item.select_one('.prog-track')
        if not td_track or td_track.get_text(' ', strip=True) != 'Research Track':
            continue
        title = ''.join(a.find_all(string=True, recursive=False)).strip()
        if not title:
            continue
        authors = [x.get_text(' ', strip=True) for x in item.select('.performers > a')]
        link = item.select_one('a[href*="/details/icse-2026/icse-2026-research-track/"]')
        url = link['href'] if link else ICSE
        label = item.parent.select_one('td.text-right')
        presentation = 'oral' if label and 'talk' in label.get_text(' ', strip=True).lower() else None
        row = {'venue': 'icse', 'title': title, 'authors': authors, 'programSource': url}
        if presentation:
            row.update(format=presentation, formatSource=url)
        if a.select_one('[data-facet-badge="Distinguished Paper Award"]'):
            row['award'] = ('Distinguished Paper', 'https://conf.researchr.org/info/icse-2026/awards')
        yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path)
    parser.add_argument('result', type=Path)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as executor:
        pending = {key: executor.submit(load, args.cache, key, args.refresh) for key in URLS}
        inputs = {key: future.result() for key, future in pending.items()}
    groups = [read_icml(inputs['pmlr'], inputs['icml']), read_iclr(inputs['iclr']),
              read_cvpr(inputs['cvpr'], inputs['cvpr-program']), read_acl(inputs['acl']),
              read_jmlr(inputs['jmlr']), read_icse(inputs['icse'])]
    result = []
    for group in groups:
        rows = [row for row in group if row.get('title') and (row.get('authors') or row['venue'] == 'icse')]
        if not rows:
            raise ValueError('An official collection did not return any records')
        print(rows[0]['venue'], len(rows), flush=True)
        result.extend(rows)
    args.result.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
