"""Fetch additional 2026 proceedings from publisher-deposited Crossref metadata."""

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path

import requests

REGISTRY = 'https://api.crossref.org/works'
IEEE_CSDL = 'https://www.computer.org/csdl/api/v1/graphql'
IEEE_PROCEEDINGS = {'sc': ('2lkuyoe0xtm', 'https://www.computer.org/csdl/proceedings/sc/2026/2lkuyoe0xtm')}
IEEE_QUERY = '''
query ($proceedingId: String!, $limit: Int, $skip: Int) {
  proceeding(proceedingId: $proceedingId) { title year }
  articlesByProceedingWithPagination(proceedingId: $proceedingId, limit: $limit, skip: $skip) {
    totalResults
    articleResults { title pubDate year doi pages sectionTitle authors { fullName } }
  }
}
'''
CONFERENCES = {
    'icse': ('10.1145/3744916', 'Proceedings of the 2026 IEEE/ACM 48th International Conference on Software Engineering', 7),
    'ase': ('10.1145/3832783', 'Proceedings of the 41st IEEE/ACM International Conference on Automated Software Engineering', 7),
    'ccs': ('10.1145/3830454', 'Proceedings of the 2026 ACM SIGSAC Conference on Computer and Communications Security', 7),
    'mobicom': ('10.1145/3795866', 'Proceedings of the 32nd Annual International Conference on Mobile Computing and Networking', 7),
    'acm-mm': ('10.1145/3767308', 'Proceedings of the 34th ACM International Conference on Multimedia', 7),
    'acm-sigops-atc': ('10.1145/3828523', 'Proceedings of the 2026 ACM SIGOPS Annual Technical Conference', 6),
}
SCHEDULE = {
    'focs': {'message': '官方会议列出了录用论文。本快照尚未匹配正式出版书目。', 'link': 'https://focs.computer.org/2026/accepted-papers/'},
    'rtss': {'message': '2026 年会议安排在 12 月。本快照尚未核实正式出版书目。', 'link': 'https://2026.rtss.org/'},
    'micro': {'message': '可查阅 2026 年大会研究论文议程。本快照尚未匹配正式出版书目。', 'link': 'https://microarch.org/micro59/program/'},
    'ieee-vis': {'message': '可查阅 2026 年大会论文。本快照尚未分辨正式论文与期刊报告、短文。', 'link': 'https://ieeevis.org/year/2026/program/content/'},
    'sc': {'message': '可查阅 IEEE Computer Society 已发布的 2026 年正式论文集。', 'link': IEEE_PROCEEDINGS['sc'][1]},
}


def request(endpoint, params=None):
    for attempt in range(6):
        response = requests.get(endpoint, params=params, timeout=(12, 32), headers={'User-Agent': 'PaperIndex2026/1.0 (bibliographic metadata)'})
        if response.status_code not in {429, 500, 502, 503, 504}:
            response.raise_for_status()
            return response.json()['message']
        time.sleep(1 + attempt * 1.5)
    response.raise_for_status()


def cache_result(cache, name, build, refresh):
    path = cache / f'publisher-{name}.json'
    if not refresh and path.exists():
        return json.loads(path.read_bytes())
    results = build()
    path.write_text(json.dumps(results, ensure_ascii=False), encoding='utf-8')
    return results


def conference_records(doi, container, date):
    prefix, _ = doi.split('/', 1)
    items = []
    needs_more = len(container) > 0
    offset = 0
    empty_pages = 0
    while needs_more and offset < 3000 and empty_pages < 1:
        page = request(REGISTRY, {
            'filter': f'prefix:{prefix},type:proceedings-article,from-pub-date:2026-01-01,until-pub-date:{date}',
            'query.container-title': container, 'select': 'DOI,title,author,published,page,container-title',
            'rows': 1000, 'offset': offset,
        })
        selected = [record for record in page['items'] if record.get('DOI', '').casefold().startswith(doi.casefold() + '.')]
        items.extend(selected)
        empty_pages += not selected
        needs_more = len(page['items']) == 1000
        offset += 1000
    return items


def issta_records(date):
    sample = request(f'{REGISTRY}/10.1145/3832115')
    issn, = sample['ISSN'][:1]
    candidates = request(f'https://api.crossref.org/journals/{issn}/works', {
        'filter': f'from-pub-date:2026-08-01,until-pub-date:{date}',
        'select': 'DOI,title,author,published,page,volume,issue,container-title', 'rows': 1000,
    })['items']
    return [record for record in candidates if record.get('volume') == '3' and record.get('issue', '').upper() == 'ISSTA']


def ieee_records(proceeding_id):
    results = []
    for offset in range(0, 1500, 100):
        response = requests.post(IEEE_CSDL, json={'query': IEEE_QUERY, 'variables': {
            'proceedingId': proceeding_id, 'limit': 100, 'skip': offset,
        }}, timeout=(12, 24))
        response.raise_for_status()
        data = response.json().get('data') or {}
        publication = data.get('proceeding') or {}
        if publication.get('year') != '2026':
            raise ValueError('IEEE publication year could not be verified')
        content = data['articlesByProceedingWithPagination']
        results.extend(content['articleResults'])
        if len(results) >= content['totalResults']:
            break
    return results


def ieee_row(record, venue, date):
    title = unescape(re.sub(r'<[^>]+>', '', record.get('title') or '')).strip()
    authors = [a['fullName'] for a in record.get('authors', []) if a.get('fullName')]
    pub_date = record.get('pubDate') or ''
    topic = (record.get('sectionTitle') or '').strip()
    if not title or not authors or not record.get('doi') or not pub_date.startswith('2026-') or pub_date > date:
        return
    pages = record.get('pages') or ''
    span = re.fullmatch(r'(\d+)\s*[-–]\s*(\d+)', pages)
    if span and int(span[2]) - int(span[1]) + 1 < 6:
        return
    if re.search(r'\b(?:posters?|workshops?|doctoral|student competition|tutorial|abstracts?)\b', topic, re.I):
        return
    row = {'venue': venue, 'title': title, 'authors': authors, 'source': f"https://doi.org/{record['doi']}",
           'publicationSource': 'IEEE Computer Society', 'pages': pages}
    if topic:
        row.update(officialTopic=topic, programSource=IEEE_PROCEEDINGS[venue][1])
    return row


def record_to_paper(record, venue, minimum_pages):
    title = (record.get('title') or [''])[0].strip()
    pages = record.get('page', '')
    span = re.fullmatch(r'(\d+)\s*[-–]\s*(\d+)', pages)
    if not title or not record.get('author') or not record.get('DOI'):
        return
    if span and int(span[2]) - int(span[1]) + 1 < minimum_pages:
        return
    if re.search(r'\b(?:tool demonstration|tutorial|workshop|grand challenge|challenge proposal|doctoral consortium|student research competition)\b', title, re.I):
        return
    authors = [f"{author.get('given', '')} {author.get('family', author.get('name', ''))}".strip() for author in record['author']]
    if not any(authors):
        return
    return {'venue': venue, 'title': title, 'authors': [name for name in authors if name],
            'source': f"https://doi.org/{record['DOI']}", 'publicationSource': 'PACMSE · ISSTA' if venue == 'issta' else 'Crossref / 出版商', 'pages': pages}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache', type=Path)
    parser.add_argument('result', type=Path)
    parser.add_argument('--date', required=True)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    args.cache.mkdir(exist_ok=True, parents=True)

    def collect(name, doi, title, minimum):
        try:
            fetch = (lambda: issta_records(args.date)) if name == 'issta' else (lambda: conference_records(doi, title, args.date))
            all_records = cache_result(args.cache, name, fetch, args.refresh)
            rows = [paper for item in all_records if (paper := record_to_paper(item, name, minimum))]
            print(name, len(rows), 'of', len(all_records), flush=True)
            return rows
        except (requests.RequestException, KeyError, ValueError) as error:
            print(f'{name}: {type(error).__name__} ({error})', flush=True)
            return []

    def collect_ieee(name, proceeding_id):
        try:
            records = cache_result(args.cache, f'ieee-{name}', lambda: ieee_records(proceeding_id), args.refresh)
            rows = [paper for item in records if (paper := ieee_row(item, name, args.date))]
            print(name, len(rows), 'of', len(records), flush=True)
            return rows
        except (requests.RequestException, KeyError, ValueError) as error:
            print(f'{name}: {type(error).__name__} ({error})', flush=True)
            return []

    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = [pool.submit(collect, name, *settings) for name, settings in CONFERENCES.items()]
        tasks.append(pool.submit(collect, 'issta', '', '', 7))
        tasks.extend(pool.submit(collect_ieee, name, source[0]) for name, source in IEEE_PROCEEDINGS.items())
        rows = [row for task in tasks for row in task.result()]
    args.result.write_text(json.dumps({'rows': rows, 'sourceNotes': SCHEDULE}, ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
