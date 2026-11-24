"""Extract the 2026 CCF A records from the CC0 DBLP XML dump."""

import argparse
import gzip
import json
import re
import xml.etree.ElementTree as ET
from html.entities import name2codepoint
from pathlib import Path
from urllib.parse import urlparse

YEAR = b'<year>2026</year>'
KEY = b' key="'
TITLE_ENTITIES = re.compile(r'&([A-Za-z][A-Za-z0-9]*);')
ROOT = Path(__file__).resolve().parent.parent
EXTRA_STREAMS = {
    'conf/sigopsatc', 'conf/atc', 'journals/pacmpl', 'journals/pacmse',
    'journals/pacmhci', 'journals/imwut', 'journals/pacmmod', 'journals/pvldb',
}


def records(path, streams):
    """Only XML-decode candidate records. Retain the unfinished record per chunk."""
    entities = dict(name2codepoint)
    dtd = path.with_name('dblp.dtd')
    if dtd.is_file():
        definitions = re.findall(r'<!ENTITY\s+(\w+)\s+"&#(\d+);"', dtd.read_text(encoding='latin-1'))
        entities.update((name, int(code)) for name, code in definitions)

    def numeric_entity(match):
        name = match.group(1)
        if name in {'amp', 'lt', 'gt', 'quot', 'apos'}:
            return match.group()
        return f'&#{entities[name]};' if name in entities else f'&amp;{name};'

    carry = b''
    with gzip.open(path, 'rb') as dump:
        while True:
            part = dump.read(8 * 1024 * 1024)
            buffer = carry + part
            if part:
                key_location = buffer.rfind(KEY)
                if key_location < 0:
                    carry = buffer
                    continue
                split = buffer.rfind(b'<', 0, key_location)
                complete, carry = buffer[:split], buffer[split:]
            else:
                complete = buffer

            cursor = 0
            while (marker := complete.find(YEAR, cursor)) != -1:
                cursor = marker + len(YEAR)
                key_start = complete.rfind(KEY, 0, marker)
                if key_start == -1:
                    continue
                key_start += len(KEY)
                key_end = complete.find(b'"', key_start)
                key = complete[key_start:key_end].decode('ascii', errors='ignore')
                stream = key.rpartition('/')[0]
                if stream not in streams:
                    continue
                start = complete.rfind(b'<', 0, key_start - len(KEY))
                kind = complete[start + 1:complete.find(b' ', start)]
                if kind not in {b'article', b'inproceedings', b'proceedings'}:
                    continue
                closing = b'</' + kind + b'>'
                end = complete.find(closing, start)
                if end < marker:
                    continue
                record = complete[start:end + len(closing)].decode('latin-1')
                yield ET.fromstring(TITLE_ENTITIES.sub(numeric_entity, record))

            if not part:
                break


def content(element):
    return ''.join(element.itertext()).strip()


def to_dict(element):
    result = {'type': element.tag, 'key': element.get('key')}
    for k in ('publtype', 'mdate'):
        if element.get(k):
            result[k] = element.get(k)
    for k in ('title', 'booktitle', 'journal', 'url', 'year', 'volume', 'number', 'crossref', 'pages', 'month'):
        node = element.find(k)
        if node is not None:
            result[k] = content(node)
    result['authors'] = [re.sub(r' \d{4}$', '', content(x)) for x in element.findall('author')]
    result['ee'] = [content(x) for x in element.findall('ee')]
    result['notes'] = [{'type': x.get('type'), 'label': content(x)} for x in element.findall('note')]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump', type=Path)
    parser.add_argument('result', type=Path)
    args = parser.parse_args()
    venues = json.loads((ROOT / 'data' / 'venues.json').read_bytes())
    streams = {urlparse(v['url']).path.strip('/').removesuffix('/index.html').removeprefix('db/') for v in venues}
    results = [to_dict(element) for element in records(args.dump, streams | EXTRA_STREAMS)]
    args.result.write_text(json.dumps(results, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'Extracted {len(results):,} 2026 DBLP proceedings and papers.')


if __name__ == '__main__':
    main()
