import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { gunzipSync } from 'node:zlib';

const readData = async (name) => JSON.parse(await readFile(new URL(`../data/${name}.json`, import.meta.url), 'utf8'));
const [venues, papers, coverage, corpusZip] = await Promise.all([
  readData('venues'), readData('papers'), readData('coverage'), readFile(new URL('../data/corpus.json.gz', import.meta.url)),
]);
const corpus = JSON.parse(gunzipSync(corpusZip));
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

assert(corpus.schema === 1, 'Unexpected database schema');
assert(corpus.authors.every(text), 'An imported author is empty');
for (const path of corpus.topics) {
  assert(path.length >= 2 && path.every((part) => text(part) && !part.includes('/')), 'Invalid imported topic path');
}

const importedFormats = ['unknown', 'poster', 'spotlight', 'oral', 'journal'];
const topicMethods = ['unclassified', 'title', 'program'];
const titleKey = (value) => value.normalize('NFKD').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');
const importedIds = new Set(papers.map(({ id }) => id));
const titles = new Set(papers.map(({ venue, title }) => `${venue}/${titleKey(title)}`));
const doi = new Set();
const distribution = {};
const topicStats = {};
const increment = (counts, key) => { counts[key] = (counts[key] || 0) + 1; };
for (const paper of papers) increment(distribution, paper.format);
const byVenue = Object.fromEntries(venues.map(({ id }) => [id, 0]));
for (const paper of papers) byVenue[paper.venue]++;

for (const row of corpus.rows) {
  assert(Array.isArray(row) && row.length === 9, 'Invalid row shape');
  const [id, venue, title, authorIds, format, topicIds, url, method, details] = row;
  assert(slug(id) && !importedIds.has(id), `Duplicate or invalid imported ID ${id}`);
  importedIds.add(id);
  assert(catalog.has(venue) && text(title) && https(url), `Invalid imported bibliographic fields ${id}`);
  const key = `${venue}/${titleKey(title)}`;
  assert(!titles.has(key), `Duplicate imported title ${id}`);
  titles.add(key);
  assert(authorIds.length > 0 && authorIds.every((index) => Number.isInteger(index) && text(corpus.authors[index])), `Invalid authors ${id}`);
  assert(topicIds.length > 0 && topicIds.every((index) => Number.isInteger(index) && corpus.topics[index]), `Invalid topics ${id}`);
  assert(importedFormats[format] && topicMethods[method], `Invalid labels ${id}`);
  assert((format === 4) === (catalog.get(venue).kind === 'journal'), `Invalid journal classification ${id}`);
  assert(text(details.publicationSource), `Missing source provenance ${id}`);
  assert(!details.formatSource || https(details.formatSource), `Invalid presentation source ${id}`);
  assert(!details.programSource || https(details.programSource), `Invalid program link ${id}`);
  assert(!details.dblp || /^[^\s?#]+$/.test(details.dblp), `Invalid DBLP key ${id}`);
  assert(!details.review || https(details.review), `Invalid external review link ${id}`);
  if (details.award) assert(text(details.award[0]) && https(details.award[1]), `Invalid award source ${id}`);
  const aliases = details.alsoVenues || [];
  assert(unique([venue, ...aliases]), `Duplicate venue association ${id}`);
  for (const alias of aliases) assert(catalog.has(alias), `Unknown secondary venue ${id}`);
  for (const source of [venue, ...aliases]) byVenue[source]++;
  const doiMatch = url.match(/^https:\/\/doi\.org\/(.+)$/i);
  if (doiMatch) {
    const key = doiMatch[1].toLowerCase();
    assert(!doi.has(key), `Duplicate DOI ${key}`);
    doi.add(key);
  }
  increment(distribution, importedFormats[format]);
  increment(topicStats, topicMethods[method]);
}

assert.equal(coverage.total, importedIds.size, 'Wrong collection total');
assert.equal(coverage.year, 2026, 'Wrong collection year');
assert.equal(coverage.notes, papers.length, 'Wrong number of reading notes');
assert.equal(coverage.coveredVenues, Object.values(byVenue).filter(Boolean).length, 'Wrong venue coverage');
assert.deepEqual(coverage.venueCounts, byVenue, 'Venue totals do not match');
assert.deepEqual(coverage.formats, distribution, 'Format totals do not match');
assert.deepEqual(coverage.topicMethods, topicStats, 'Topic counts do not match');
console.log(`Validated ${coverage.total} records, ${coverage.notes} reading notes and ${coverage.coveredVenues}/${venues.length} CCF A venues.`);
