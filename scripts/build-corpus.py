"""Merge verified 2026 publication metadata into the site's compact index."""

import argparse
import gzip
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from topics import classify

ROOT = Path(__file__).resolve().parent.parent
YEAR = 2026
NON_RESEARCH = re.compile(
    r'^(?:editorial(?: (?:note|introduction|foreword|board))?[.:]?$|'
    r'(?:invited |keynote )?(?:welcome message|preface|foreword|copyright page|table of contents|'
    r'author index|organizing committee|program committee|message from|call for papers|'
    r'introduction to the (?:issue|proceedings)|front matter|acknowledgm?ents)(?:[.: ]|$)|'
    r'(?:corrigendum|errat(?:um|a)|retraction|withdrawn|in memoriam|obituary)(?:[.: ]|$))', re.I,
)
NON_MAIN = re.compile(
    r'\b(?:companions?|workshops?|findings|short papers?|tutorials?|doctoral consortium|student abstracts?|'
    r'extended abstracts?|session abstracts?|system demonstrations?|posters?|demos?|new ideas and emerging results|'
    r'software engineering in society|industry track|journal[- ]first|technical briefs?|late.breaking work|'
    r'challenge|demonstration track|vision track|education track|student research (?:workshop|competition))\b'
    r'|\b(?:NIER@|ICSE-NIER|ICSE-SEIS|CHI EA|CVPRW|ICCVW)\b', re.I,
)
PACMPL_NUMBER = {'PLDI': 'pldi', 'POPL': 'popl', 'OOPSLA1': 'oopsla', 'OOPSLA2': 'oopsla'}
ACL_ARTICLE = re.compile(r'2026\.acl-long\.\d+')
LATEX_STYLE = re.compile(r'\\(?:boldsymbol|mathbf|text\w*|underline)\b')
LATEX_COMMAND = re.compile(r'\\([A-Za-z]+)')
LATEX_ACCENT = re.compile(r'''\\(["'])(?:\{([A-Za-z])\}|([A-Za-z]))''')
ACCENTS = {'"': '\u0308', "'": '\u0301'}
LATEX_SYMBOLS = {
    'alpha': 'α', 'ell': 'ℓ', 'epsilon': 'ε', 'varepsilon': 'ε', 'mu': 'μ', 'phi': 'φ', 'pi': 'π',
    'psi': 'ψ', 'Psi': 'Ψ', 'partial': '∂', 'infty': '∞', 'nabla': '∇',
}
AAAI_ARCHIVE = 'https://aaai.org/proceeding/aaai-40-2026/'
AAAI_TOPICS = {
    **dict.fromkeys(range(1, 3), 'AI 应用'), 3: '认知建模', **dict.fromkeys(range(4, 17), '计算机视觉'),
    **dict.fromkeys(range(18, 20), '数据挖掘与知识管理'), 20: '博弈论与经济学', 21: '人机协同', 22: '智能机器人',
    23: '知识表示与推理', **dict.fromkeys(range(24, 35), '机器学习方法'), 35: '多智能体系统',
    **dict.fromkeys(range(36, 42), '自然语言处理'), 42: 'AI 伦理', 44: 'AI 对齐', 45: 'AI 社会影响',
}
AWARD_SOURCES = {
    'aaai': 'https://aaai.org/about-aaai/aaai-awards/aaai-conference-paper-awards-and-recognition/',
    'icml': 'https://blog.icml.cc/2026/07/05/announcing-the-icml-2026-awards/',
    'cvpr': 'https://cvpr.thecvf.com/Conferences/2026/News/Best_Papers',
    'osdi': 'https://www.usenix.org/conferences/best-papers',
}
AWARDS = {
    'aaai': {
        'Outstanding Paper': [
            'Model Change for Description Logic Concepts', 'Causal Structure Learning for Dynamical Systems with Theoretical Score Analysis',
            'ReconVLA: Reconstructive Vision-Language-Action Model as Effective Robot Perceiver',
            'High-Pass Matters: Theoretical Insights and Sheaflet-Based Design for Hypergraph Neural Networks',
            'LLM2CLIP: Powerful Language Model Unlocks Richer Cross-Modality Representation',
        ],
    },
    'icml': {'Honorable Mention': [
        'The Obfuscation Atlas: Mapping Where Honesty Emerges in RLVR with Deception Probes',
        'Motion Attribution for Video Generation', 'How much can language models memorize?',
        'A Random Matrix Perspective on the Consistency of Diffusion Models', 'To Grok Grokking: Provable Grokking in Ridge Regression',
    ]},
    'cvpr': {'Best Student Paper': ['Native and Compact Structured Latents for 3D Generation']},
    'osdi': {'Jay Lepreau Best Paper': ['Teaching the Old Dog New Tricks: Building Efficient Data Pipelines for Large-Scale LLM Pre-Training']},
}


def read(path):
    return json.loads(path.read_bytes())


def normalized(value):
    return ''.join(ch for ch in unicodedata.normalize('NFKD', unescape(value)).casefold() if ch.isalnum())


def https(url):
    return isinstance(url, str) and url.startswith('https://')


def publication_ids(row):
    for url in (row.get('source'), row.get('review'), *row.get('editions', ())):
        if not https(url):
            continue
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        if parsed.hostname == 'doi.org':
            if path.startswith('10.18653/v1/') and ACL_ARTICLE.fullmatch(path.rsplit('/', 1)[-1]):
                yield 'acl', path.rsplit('/', 1)[-1]
            else:
                yield 'doi', path.casefold()
        elif parsed.hostname == 'aclanthology.org' and ACL_ARTICLE.fullmatch(path):
            yield 'acl', path
        elif parsed.hostname == 'openaccess.thecvf.com' and path.startswith('content/CVPR2026/html/'):
            yield 'cvf', path
        elif parsed.hostname == 'openreview.net' and path == 'forum':
            for forum_id in parse_qs(parsed.query).get('id', []):
                yield 'openreview', forum_id


def author_key(author):
    words = author.split()
    if len(words) > 2:
        words = [words[0], *(word for word in words[1:-1] if len(word.rstrip('.')) > 1), words[-1]]
    return normalized(' '.join(words))


def latex_accents(title):
    return LATEX_ACCENT.sub(lambda m: unicodedata.normalize('NFC', (m[2] or m[3]) + ACCENTS[m[1]]), title)


def iclr_title_key(title):
    stripped = LATEX_STYLE.sub('', latex_accents(title))
    return normalized(LATEX_COMMAND.sub(lambda m: LATEX_SYMBOLS.get(m[1], m.group()), stripped))


def matching_iclr_key(row, candidates, papers):
    title = row['title']
    if not LATEX_COMMAND.search(title) and not LATEX_ACCENT.search(title) and '$' not in title:
        return None
    authors = {author_key(name) for name in row['authors']}
    comparable = iclr_title_key(title)
    matches = []
    for key in candidates:
        existing = papers[key]
        existing_authors = {author_key(name) for name in existing['authors']}
        overlap = len(authors & existing_authors) / max(len(authors), len(existing_authors))
        score = SequenceMatcher(None, comparable, iclr_title_key(existing['title']), autojunk=False).ratio()
        if overlap >= 0.85 and score >= 0.92:
            matches.append(key)
    return matches[0] if len(matches) == 1 else None


def db_stream(venue):
    return urlparse(venue['url']).path.strip('/').removesuffix('/index.html').removeprefix('db/')


def pages_length(value):
    match = re.fullmatch(r'(?:\d+:)?(\d+)\s*[-–]\s*(?:\d+:)?(\d+)', value or '')
    return int(match[2]) - int(match[1]) + 1 if match else None


def classify_stream(row, stream, direct):
    if stream == 'journals/pacmpl':
        return PACMPL_NUMBER.get(row.get('number')), 'unknown', 'PACMPL'
    if stream == 'journals/pacmse' and row.get('number') == 'FSE':
        return 'fse', 'unknown', 'PACMSE · FSE'
    if stream == 'journals/pacmse' and row.get('number') == 'ISSTA':
        return 'issta', 'unknown', 'PACMSE · ISSTA'
    if stream == 'journals/pacmhci':
        if row.get('number') in {'2', '6'}:
            return 'cscw', 'unknown', 'PACMHCI · CSCW'
        return None, None, None
    if stream == 'journals/imwut':
        return 'ubicomp', 'unknown', 'PACM IMWUT'
    if stream == 'journals/pacmmod':
        if row.get('number') in {'1', '3'}:
            return 'sigmod', 'unknown', 'PACMMOD · SIGMOD'
        return None, None, None
    if stream == 'journals/pvldb':
        return 'vldb', 'unknown', 'PVLDB'
    if stream in {'conf/atc', 'conf/sigopsatc'}:
        return 'acm-sigops-atc', 'unknown', 'DBLP'
    venue = direct.get(stream)
    if not venue:
        return None, None, None
    return venue['id'], 'journal' if venue['kind'] == 'journal' else 'unknown', 'DBLP'


def conference_eligible(raw, paper_venue, stream, parents):
    book = raw.get('booktitle') or ''
    parent = parents.get(raw.get('crossref'), '')
    if (parent and NON_MAIN.search(parent)) or NON_MAIN.search(book):
        return False
    if stream == 'conf/acl':
        return raw.get('crossref') == 'conf/acl/2026-1'
    if stream == 'conf/aaai':
        issue = re.search(r'aaai\.v40i(\d+)\.', ' '.join(raw['ee']), re.I)
        length = pages_length(raw.get('pages'))
        return issue is not None and int(issue[1]) <= 46 and (length is None or length >= 5)
    if paper_venue in {'ppopp', 'sigcomm', 'sigir', 'vldb'}:
        length = pages_length(raw.get('pages'))
        if length is not None and length <= (5 if paper_venue == 'sigir' else 4):
            return False
    return True


def dblp_rows(data, venues):
    streams = {db_stream(venue): venue for venue in venues.values()}
    parents = {p['key']: p['title'] for p in data if p['type'] == 'proceedings'}
    for raw in data:
        if raw['type'] not in {'article', 'inproceedings'} or raw.get('year') != str(YEAR):
            continue
        title = raw.get('title', '').strip()
        if not title or not raw['authors'] or NON_RESEARCH.search(title):
            continue
        if re.search(r'\b(?:informal|withdrawn|retracted)\b', raw.get('publtype', ''), re.I):
            continue
        stream = raw['key'].rpartition('/')[0]
        venue, format_name, publisher = classify_stream(raw, stream, streams)
        if not venue or (format_name != 'journal' and not conference_eligible(raw, venue, stream, parents)):
            continue
        if venue == 'vldb' and re.match(r'^(?:Demonstration of|A Demonstration of|Demo:)', title, re.I):
            continue
        if format_name == 'journal' and raw['type'] != 'article':
            continue
        out = {
            'venue': venue, 'title': unescape(title.removesuffix('.')), 'authors': raw['authors'], 'format': format_name,
            'source': next((url for url in raw['ee'] if https(url)), f"https://dblp.org/rec/{raw['key']}.html"),
            'dblp': raw['key'], 'publicationSource': publisher, 'editions': raw['ee'],
        }
        if venue == 'tog' and raw.get('volume') == '45' and raw.get('number') == '4':
            out['alsoVenues'] = ['siggraph']
        if venue == 'aaai':
            issue = re.search(r'aaai\.v40i(\d+)\.', ' '.join(raw['ee']), re.I)
            topic = AAAI_TOPICS.get(int(issue[1])) if issue else None
            if topic:
                out.update(officialTopic=topic, programSource=AAAI_ARCHIVE)
        if raw.get('pages'):
            out['pages'] = raw['pages']
        yield out


def index_rows(venues, base, official, additional, seeds):
    papers = {}
    by_identifier = {}
    by_title = {}
    iclr_dblp = defaultdict(list)
    origins = Counter()
    for row in [*base, *additional, *official]:
        title = row.get('title', '').strip()
        venue = row.get('venue')
        if not title or venue not in venues or NON_RESEARCH.search(title):
            continue
        title_key = (venue, normalized(title))
        source = row.get('source', '')
        identifiers = list(publication_ids(row))
        key = next((by_identifier[i] for i in identifiers if i in by_identifier), by_title.get(title_key))
        if key is None and venue == 'iclr' and row.get('publicationSource') == 'ICLR' and row.get('authors'):
            key = matching_iclr_key(row, iclr_dblp[author_key(row['authors'][0])], papers)
        if key is None:
            if not row.get('authors') or not https(source) or not row.get('publicationSource'):
                continue
            key = title_key
            papers[key] = {}
            if venue == 'iclr' and row.get('dblp'):
                iclr_dblp[author_key(row['authors'][0])].append(key)
        by_title[title_key] = key
        for identifier in identifiers:
            by_identifier[identifier] = key
        paper = papers[key]
        for field, value in row.items():
            if field == 'title':
                value = latex_accents(value)
                if paper.get('title') and (LATEX_COMMAND.search(value) or '$' in value):
                    continue
            if field != 'editions' and value and (field != 'format' or value != 'unknown' or not paper.get('format')):
                paper[field] = value
        if key[0] != venue:
            paper['venue'] = key[0]
            paper['alsoVenues'] = list(dict.fromkeys([*paper.get('alsoVenues', []), venue]))
        if row.get('publicationSource'):
            origins[row['publicationSource']] += 1

    award_lookup = {(venue, normalized(title)): (name, AWARD_SOURCES[venue])
                    for venue, groups in AWARDS.items() for name, titles in groups.items() for title in titles}
    curated_keys = {(paper['venue'], normalized(paper['title'])) for paper in seeds}
    rows = []
    for (venue, title_key), paper in papers.items():
        active_title = (venue, normalized(paper['title']))
        if (venue, title_key) in curated_keys or active_title in curated_keys:
            continue
        paper['award'] = paper.get('award') or award_lookup.get(active_title) or award_lookup.get((venue, title_key))
        paper['format'] = paper.get('format', 'journal' if venues[venue]['kind'] == 'journal' else 'unknown')
        paper['topics'], paper['topicMethod'] = classify(paper, venues[venue])
        paper['id'] = f"{venue}-{hashlib.blake2b(title_key.encode(), digest_size=10).hexdigest()}"
        rows.append(paper)
    rows.sort(key=lambda p: (p['venue'], normalized(p['title'])))
    return rows, origins


def intern(value, values, index):
    if value not in index:
        index[value] = len(values)
        values.append(value)
    return index[value]


def serialize(rows, venues, seeds, date, extra_sources):
    authors, authors_index = [], {}
    topics, topics_index = [], {}
    formats = ['unknown', 'poster', 'spotlight', 'oral', 'journal']
    methods = ['unclassified', 'title', 'program']
    items = []
    counts = Counter()
    for paper in [*seeds, *rows]:
        counts.update([paper['venue'], *paper.get('alsoVenues', [])])

    for p in rows:
        details = {key: p[key] for key in ['alsoVenues', 'formatSource', 'programSource', 'publicationSource', 'dblp', 'review', 'pages', 'award', 'officialTopic'] if p.get(key)}
        if details.get('formatSource') == p['source']:
            details.pop('formatSource')
        if details.get('programSource') in {p['source'], details.get('formatSource')}:
            details.pop('programSource', None)
        topic_ids = [intern(tuple(path), topics, topics_index) for path in p['topics']]
        author_ids = [intern(name, authors, authors_index) for name in p['authors']]
        items.append([p['id'], p['venue'], p['title'], author_ids, formats.index(p['format']), topic_ids,
                      p['source'], methods.index(p['topicMethod']), details])

    summary = {
        'year': YEAR, 'updated': date, 'total': len(seeds) + len(rows), 'notes': len(seeds),
        'coveredVenues': sum(bool(counts[v]) for v in venues),
        'formats': dict(Counter(p['format'] for p in [*seeds, *rows])),
        'topicMethods': dict(Counter(p['topicMethod'] for p in rows)),
        'providers': dict(Counter(p['publicationSource'] for p in rows)),
        'venueCounts': {venue: counts[venue] for venue in venues},
        'sourceNotes': {
            'neurips': {'message': '2026 年会议安排在 12 月。正式论文集发布后纳入。', 'link': 'https://neurips.cc/Conferences/2026'},
            'iccv': {'message': 'ICCV 在奇数年举行，本年度无正式论文集。', 'link': 'https://iccv.thecvf.com/'},
            **extra_sources,
        },
    }
    return {'schema': 1, 'authors': authors, 'topics': topics, 'rows': items}, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dblp', type=Path)
    parser.add_argument('official', type=Path)
    parser.add_argument('--additional', type=Path)
    parser.add_argument('--date', required=True)
    args = parser.parse_args()
    out = ROOT / 'data'
    venues = {v['id']: v for v in read(out / 'venues.json')}
    seeds = read(out / 'papers.json')
    supplement = read(args.additional) if args.additional else {'rows': [], 'sourceNotes': {}}
    rows, origins = index_rows(venues, list(dblp_rows(read(args.dblp), venues)), read(args.official), supplement['rows'], seeds)
    corpus, coverage = serialize(rows, venues, seeds, args.date, supplement.get('sourceNotes', {}))
    encoded = json.dumps(corpus, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    (out / 'corpus.json.gz').write_bytes(gzip.compress(encoded, compresslevel=6, mtime=0))
    (out / 'coverage.json').write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{coverage['total']:,} papers in {coverage['coveredVenues']}/{len(venues)} venues. {len(encoded):,} JSON bytes.")
    print('Accepted input rows by provider:', dict(origins))
    print('Display formats:', coverage['formats'])
    print('Missing venues:', [v for v, n in coverage['venueCounts'].items() if n == 0])


if __name__ == '__main__':
    main()
