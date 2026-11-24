import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const readData = async (name) => JSON.parse(await readFile(new URL(`../data/${name}.json`, import.meta.url), 'utf8'));
const [venues, papers] = await Promise.all([readData('venues'), readData('papers')]);
const noteKeys = ['motivation', 'problem', 'analysis', 'method', 'experiments', 'contribution'];
const presentationFormats = ['oral', 'spotlight', 'poster'];
const formats = [...presentationFormats, 'journal', 'unknown'];
const text = (value) => typeof value === 'string' && value.trim().length > 0;
const https = (value) => text(value) && URL.canParse(value) && new URL(value).protocol === 'https:';
const slug = (value) => text(value) && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
const unique = (items) => new Set(items).size === items.length;

assert(Array.isArray(venues) && venues.length > 0, 'Expected a nonempty venue catalog');
assert(unique(venues.map(({ id }) => id)), 'Duplicate venue ID');
for (const venue of venues) {
  assert(slug(venue.id), `Invalid venue ID: ${venue.id}`);
  assert([venue.name, venue.label, venue.domain].every(text), `Missing catalog metadata: ${venue.id}`);
  assert(['conference', 'journal'].includes(venue.kind), `Invalid venue type: ${venue.id}`);
  assert(https(venue.url), `Invalid bibliographic link: ${venue.id}`);
}

const catalog = new Map(venues.map((venue) => [venue.id, venue]));
assert(Array.isArray(papers) && papers.length > 0, 'Expected a nonempty paper index');
assert(unique(papers.map(({ id }) => id)), 'Duplicate paper ID');
assert(unique(papers.map(({ title }) => title.normalize('NFKC').trim().toLowerCase())), 'Duplicate paper title');

for (const paper of papers) {
  const venue = catalog.get(paper.venue);
  assert(slug(paper.id), `Invalid paper ID: ${paper.id}`);
  assert(venue && paper.year === 2026, `Paper must be from a listed CCF A venue and published in 2026: ${paper.id}`);
  assert(text(paper.title) && text(paper.abstractZh), `Missing title or abstract: ${paper.id}`);
  assert(Array.isArray(paper.authors) && paper.authors.length > 0 && paper.authors.every(text), `Missing authors: ${paper.id}`);
  assert(Array.isArray(paper.keywords) && paper.keywords.every(text), `Invalid keywords: ${paper.id}`);
  assert(formats.includes(paper.format), `Unknown format: ${paper.id}`);
  assert((venue.kind === 'journal') === (paper.format === 'journal'), `Journal/format mismatch: ${paper.id}`);
  assert(https(paper.source), `Missing paper source: ${paper.id}`);
  assert(!presentationFormats.includes(paper.format) || https(paper.formatSource), `Missing presentation evidence: ${paper.id}`);
  assert(!paper.award || (text(paper.award.label) && https(paper.award.source)), `Invalid paper award: ${paper.id}`);
  assert(Array.isArray(paper.links) && paper.links.every(({ label, url }) => text(label) && https(url)), `Invalid paper links: ${paper.id}`);
  assert(noteKeys.every((key) => text(paper.notes?.[key])), `Missing structured notes: ${paper.id}`);
  assert(Array.isArray(paper.topics) && paper.topics.length > 0, `Missing topic path: ${paper.id}`);
  for (const path of paper.topics) {
    assert(Array.isArray(path) && path.length >= 2 && path.every((part) => text(part) && !part.includes('/')), `Invalid topic path: ${paper.id}`);
  }
  assert(unique(paper.topics.map((path) => path.join('/'))), `Duplicate topic path: ${paper.id}`);
}

console.log(`Validated ${papers.length} papers across ${new Set(papers.map(({ venue }) => venue)).size} sources and ${venues.length} CCF A venues.`);
