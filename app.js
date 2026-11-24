const svgPaths = {
  book: '<path d="M12 7C9 4 6 4 3 4v14c4 0 7 1 9 3 2-2 5-3 9-3V4c-3 0-6 0-9 3Zm0 0v14"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  bookmark: '<path d="M6 4h12v17l-6-4-6 4z"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  'chevron-right': '<path d="m9 6 6 6-6 6"/>',
  sliders: '<path d="M4 7h16M4 17h16M9 4v6m6 4v6"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
  sort: '<path d="M4 6h16M4 12h11M4 18h6"/>',
  award: '<circle cx="12" cy="9" r="5"/><path d="m8 13-2 8 6-3 6 3-2-8"/>',
  external: '<path d="M13 4h7v7m0-7-9 9m7 0v7H4V6h7"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r=".8"/>',
  question: '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4m0 3h.01"/>',
  analysis: '<path d="M4 19h16M6 15l4-4 3 2 5-7m-4 0h4v4"/>',
  method: '<path d="M8 3v6l-4 8a2 2 0 0 0 2 3h12a2 2 0 0 0 2-3l-4-8V3M7 3h10M7 14h10"/>',
  bars: '<path d="M4 20h16M7 16v-5m5 5V5m5 11V8"/>',
  star: '<path d="m12 3 2.6 5.3 5.9.9-4.2 4.1 1 5.8-5.3-2.7-5.3 2.7 1-5.8L3.5 9.2l5.9-.9L12 3Z"/>',
};

function icon(name) {
  return `<svg aria-hidden="true" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">${svgPaths[name]}</svg>`;
}

const formats = new Map([
  ['oral', 'Oral'], ['spotlight', 'Spotlight'], ['poster', 'Poster'], ['journal', '期刊'], ['unknown', '未标注'],
]);
const noteFields = [
  ['motivation', '研究动机', 'target'], ['problem', '解决问题', 'question'], ['analysis', '现象分析', 'analysis'],
  ['method', '主要方法', 'method'], ['experiments', '数据与实验', 'bars'], ['contribution', '主要贡献', 'star'],
];
const defaults = { q: '', venue: '', topic: '', format: '', award: false, notes: false, saved: false, sort: 'relevance', page: 1 };
const pageSize = 10;
const storageKey = 'paper-index-2026-bookmarks';
const topicExpansion = new Map();
const topicTrees = new Map();
const papersByVenue = new Map();
const collator = new Intl.Collator(['en', 'zh-CN'], { sensitivity: 'base', numeric: true });
const number = new Intl.NumberFormat('zh-CN');
const pinnedVenues = ['icml', 'iclr', 'cvpr', 'aaai', 'acl', 'sigkdd', 'icse', 'osdi', 'jmlr'];
const byId = (id) => document.getElementById(id);
const searchInput = byId('search-input');
const catalogInput = byId('catalog-input');
const catalogDialog = byId('catalog-dialog');
const paperList = byId('paper-list');
const sortOrder = byId('sort-order');

let papers = [];
let venues = new Map();
let countsByVenue = new Map();
let coverage = null;
let state = { ...defaults };
let ready = false;
let bookmarks = readBookmarks();

function readBookmarks() {
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) || '[]');
    return new Set(Array.isArray(stored) ? stored.filter((item) => typeof item === 'string') : []);
  } catch {
    return new Set();
  }
}

function normalize(value) {
  return value.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

function external(url, label) {
  return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)} ${icon('external')}</a>`;
}

function readState() {
  const query = new URLSearchParams(location.search);
  const sort = query.get('sort');
  return {
    q: query.get('q') || '',
    venue: venues.has(query.get('venue')) ? query.get('venue') : '',
    topic: query.get('topic') || '',
    format: formats.has(query.get('format')) ? query.get('format') : '',
    award: query.get('award') === '1',
    notes: query.get('notes') === '1',
    saved: query.get('saved') === '1',
    sort: [...sortOrder.options].some((option) => option.value === sort) ? sort : defaults.sort,
    page: Math.max(1, Number.parseInt(query.get('page'), 10) || 1),
  };
}

function writeState(mode) {
  const url = new URL(location.href);
  for (const [key, value] of Object.entries(state)) {
    if (value === defaults[key]) url.searchParams.delete(key);
    else url.searchParams.set(key, value === true ? '1' : String(value));
  }
  if (url.href !== location.href) history[mode]({}, '', url);
}

function setState(changes, mode = 'pushState') {
  state = { ...state, page: 1, ...changes };
  render();
  writeState(mode);
}

function chooseVenue(venue) {
  if (!ready) return;
  setState({ venue, topic: '' });
}

function topicMatches(paper, topic) {
  return !topic || paper.topicKeys.some((key) => key === topic || key.startsWith(`${topic}/`));
}

function score(paper, tokens, phrase) {
  if (tokens.length === 0) return 0;
  if (!paper.titleText) {
    const venue = venues.get(paper.venue);
    paper.titleText = normalize(paper.title);
    paper.authorText = normalize(paper.authors.join(' '));
    paper.topicText = normalize([...paper.topics.flat(), ...(paper.keywords || []), paper.officialTopic].join(' '));
    paper.otherText = normalize([
      venue.label, venue.name, venue.domain, ...paper.alsoVenues.map((id) => venues.get(id).label),
      paper.year, formats.get(paper.format), paper.award?.label, paper.abstractZh,
      ...Object.values(paper.notes || {}),
    ].join(' '));
  }
  let total = paper.titleText.includes(phrase) ? 14 : 0;
  for (const token of tokens) {
    if (paper.titleText.includes(token)) total += 8;
    else if (paper.authorText.includes(token) || paper.topicText.includes(token)) total += 5;
    else if (paper.otherText.includes(token)) total += 1;
    else return -1;
  }
  return total;
}

function getResults() {
  const phrase = normalize(state.q);
  const tokens = [...new Set(phrase.split(' ').filter(Boolean))];
  const scope = state.venue ? papersByVenue.get(state.venue) || [] : papers;
  const base = scope.filter((paper) => topicMatches(paper, state.topic) &&
    (!state.saved || bookmarks.has(paper.id)) && (!state.award || paper.award) && (!state.notes || paper.notes),
  ).map((paper) => ({ paper, score: score(paper, tokens, phrase) })).filter((entry) => entry.score >= 0);
  const counts = new Map();
  for (const { paper } of base) counts.set(paper.format, (counts.get(paper.format) || 0) + 1);
  const matched = base.filter(({ paper }) => !state.format || paper.format === state.format);
  const key = { title: (paper) => paper.title, author: (paper) => paper.authors[0], venue: (paper) => venues.get(paper.venue).label }[state.sort];
  if (key) matched.sort((a, b) => collator.compare(key(a.paper), key(b.paper)) || collator.compare(a.paper.title, b.paper.title));
  else if (tokens.length) matched.sort((a, b) => b.score - a.score);
  return { matched, counts, total: base.length };
}

function renderVenueList() {
  const indexed = pinnedVenues.filter((id) => countsByVenue.has(id));
  if (state.venue && !indexed.includes(state.venue)) indexed.push(state.venue);
  const choices = [['', '全部来源', papers.length], ...indexed.map((id) => [id, venues.get(id).label, countsByVenue.get(id) || 0])];
  byId('venue-list').innerHTML = choices.map(([id, label, count]) => `
    <button class="side-choice" type="button" data-venue="${escapeHtml(id)}" data-focus="venue-${escapeHtml(id)}" aria-pressed="${id === state.venue}">
      <span>${escapeHtml(label)}</span><span class="count">${number.format(count)}</span>
    </button>`).join('');
}

function getTopicTree() {
  if (topicTrees.has(state.venue)) return topicTrees.get(state.venue);
  const tree = new Map();
  const scope = state.venue ? papersByVenue.get(state.venue) || [] : papers;
  for (const paper of scope) {
    for (const path of paper.topics) {
      let current = tree;
      for (const [index, segment] of path.entries()) {
        const key = path.slice(0, index + 1).join('/');
        if (!current.has(segment)) current.set(segment, { key, papers: new Set(), children: new Map() });
        const node = current.get(segment);
        node.papers.add(paper.id);
        current = node.children;
      }
    }
  }
  topicTrees.set(state.venue, tree);
  return tree;
}

function renderTree(tree) {
  return [...tree].sort(([, a], [, b]) => b.papers.size - a.papers.size).map(([name, node]) => {
    const key = escapeHtml(node.key);
    const expanded = topicExpansion.get(node.key) ?? (state.topic.startsWith(`${node.key}/`) || Boolean(state.venue && !node.key.includes('/')));
    const childrenId = `topic-children-${encodeURIComponent(node.key)}`;
    const branch = node.children.size > 0;
    return `<div><div class="topic-row${branch ? '' : ' topic-leaf'}">
      ${branch ? `<button type="button" class="topic-expand" data-fold="${key}" data-focus="fold-${key}" aria-label="${escapeHtml(name)}子主题" aria-expanded="${expanded}" aria-controls="${childrenId}">${icon('chevron')}</button>` : ''}
      <button type="button" class="topic-toggle" data-topic="${key}" data-focus="topic-${key}" aria-pressed="${node.key === state.topic}"><span class="topic-name">${escapeHtml(name)}</span><span class="count">${number.format(node.papers.size)}</span></button>
    </div>${branch ? `<div class="topic-children" id="${childrenId}"${expanded ? '' : ' hidden'}>${renderTree(node.children)}</div>` : ''}</div>`;
  }).join('');
}

function renderFilters(results) {
  const choices = [['', '全部', results.total], ...[...formats].map(([key, value]) => [key, value, results.counts.get(key) || 0])];
  byId('format-list').innerHTML = choices.map(([key, label, count]) => `
    <button type="button" class="format-button" data-format="${key}" data-focus="format-${key}" aria-pressed="${key === state.format}">${label} <span class="count">${number.format(count)}</span></button>`).join('');
  byId('award-filter').setAttribute('aria-pressed', state.award);
  byId('notes-filter').setAttribute('aria-pressed', state.notes);
  byId('saved-nav').setAttribute('aria-pressed', state.saved);
  const savedCount = byId('saved-count');
  savedCount.textContent = bookmarks.size;
  savedCount.hidden = bookmarks.size === 0;
  const filters = [
    ['q', state.q], ['venue', venues.get(state.venue)?.label], ['topic', state.topic.replaceAll('/', ' › ')],
    ['format', formats.get(state.format)], ['award', state.award && '获奖论文'], ['notes', state.notes && '有中文笔记'],
  ].filter(([, label]) => label);
  const active = byId('active-filters');
  active.hidden = filters.length === 0;
  active.innerHTML = filters.map(([key, label]) => `
    <button type="button" class="active-chip" data-remove="${key}" aria-label="移除筛选 ${escapeHtml(label)}">${escapeHtml(label)} ${icon('close')}</button>`).join('') +
    '<button type="button" class="clear-filters" data-reset>清除筛选</button>';
}

function paperCard(paper) {
  const id = escapeHtml(paper.id);
  const venue = venues.get(paper.venue);
  const saved = bookmarks.has(paper.id);
  const details = paper.topics.map((path) => `<span class="topic-path">${path.map((name, index) =>
    `<button type="button" data-paper-topic="${escapeHtml(path.slice(0, index + 1).join('/'))}" data-paper-venue="${escapeHtml(paper.venue)}">${escapeHtml(name)}</button>`,
  ).join(icon('chevron-right'))}</span>`).join('');
  const notes = paper.notes && noteFields.map(([key, label, symbol]) =>
    `<dt>${icon(symbol)}${label}</dt><dd>${escapeHtml(paper.notes[key])}</dd>`,
  ).join('');
  const links = [...paper.links];
  if (paper.formatSource && !links.some(({ url }) => url === paper.formatSource)) links.push({ label: '展示来源', url: paper.formatSource });
  if (paper.award && !links.some(({ url }) => url === paper.award.source)) links.push({ label: '获奖公告', url: paper.award.source });
  if (paper.programSource && !links.some(({ url }) => url === paper.programSource)) links.push({ label: '议程', url: paper.programSource });
  if (paper.dblp) links.push({ label: 'DBLP', url: `https://dblp.org/rec/${paper.dblp}.html` });
  if (!notes) links.unshift({ label: paper.source.startsWith('https://dblp.org/') ? '出版书目' : '原文与摘要', url: paper.source });
  const topicOrigin = { program: '官方主题或议程', title: '按标题归类', unclassified: '主题待细分' }[paper.topicMethod];
  const provenance = topicOrigin && `<div class="paper-provenance"><strong>${escapeHtml(paper.publicationSource)}</strong><span>${topicOrigin}</span>${paper.pages ? `<span>页码 ${escapeHtml(paper.pages)}</span>` : ''}</div>`;
  return `<article class="paper-card" id="paper-${id}" aria-labelledby="title-${id}">
    <div class="card-head">
      <div>
        <div class="card-meta"><span class="paper-related-venues"><button type="button" class="paper-venue" data-venue="${escapeHtml(paper.venue)}" data-focus="paper-venue-${id}">${escapeHtml(venue.label)}</button>
          ${paper.alsoVenues.map((alias) => `<button type="button" class="paper-venue" data-venue="${escapeHtml(alias)}">${escapeHtml(venues.get(alias).label)}</button>`).join('')}</span>
          <span class="paper-year">${paper.year}</span><span class="paper-badge ${paper.format}">${formats.get(paper.format)}</span>
          ${paper.award ? `<span class="paper-badge award">${escapeHtml(paper.award.label)}</span>` : ''}
        </div>
        <h3 id="title-${id}" class="paper-title">${external(paper.source, paper.title)}</h3>
      </div>
      <button type="button" class="icon-button" data-bookmark="${id}" data-focus="bookmark-${id}" aria-label="收藏 ${escapeHtml(paper.title)}" aria-pressed="${saved}">${icon('bookmark')}</button>
    </div>
    <p class="paper-authors">${paper.authors.map(escapeHtml).join(' · ')}</p>
    <div class="topic-paths" aria-label="论文主题">${details}</div>
    ${notes ? `<dl class="paper-notes">${notes}</dl>` : ''}
    <div class="paper-bottom${notes ? '' : ' bibliography'}">
      ${notes ? `<details class="abstract"><summary>查看摘要</summary><p class="abstract-body">${escapeHtml(paper.abstractZh)}</p>
        <span class="abstract-source">${external(paper.source, '查看完整原文摘要')}</span>
      </details>` : provenance || ''}
      <div class="paper-links">${links.map(({ url, label }) => external(url, label)).join('')}</div>
    </div>
  </article>`;
}

function renderResults(results) {
  const { matched } = results;
  const pages = Math.max(1, Math.ceil(matched.length / pageSize));
  state.page = Math.min(pages, state.page);
  const start = (state.page - 1) * pageSize;
  const end = Math.min(start + pageSize, matched.length);
  const title = state.saved ? '我的收藏' : venues.get(state.venue)?.label || '全部论文';
  byId('results-title').textContent = title;
  byId('results-count').textContent = `${number.format(matched.length)} 篇论文${pages > 1 ? ` · 显示第 ${number.format(start + 1)}–${number.format(end)} 篇` : ''}`;
  if (matched.length) {
    const openCards = new Set([...paperList.querySelectorAll('.abstract[open]')].map((element) => element.closest('article').id));
    paperList.innerHTML = matched.slice(start, end).map(({ paper }) => paperCard(paper)).join('');
    for (const card of paperList.children) if (openCards.has(card.id)) card.querySelector('.abstract').open = true;
  } else {
    const emptyVenue = state.venue && !countsByVenue.has(state.venue);
    const emptySaved = state.saved && bookmarks.size === 0;
    const message = emptyVenue ? '此来源尚未收录 2026 年论文' : emptySaved ? '还没有收藏论文' : '没有符合条件的论文';
    const sourceNote = emptyVenue && coverage?.sourceNotes?.[state.venue];
    const description = emptyVenue ? sourceNote?.message || '当前快照中暂未核实到正式出版记录。' : emptySaved ? '在论文卡片上点击收藏，即可在这里查看。' : '试试其他关键词，或清除部分筛选条件。';
    paperList.innerHTML = `<div class="empty-state"><h3>${message}</h3><p>${escapeHtml(description)}</p>
      ${sourceNote?.link ? external(sourceNote.link, '查看官方来源') : emptyVenue ? external(venues.get(state.venue).url, '查看 DBLP 书目') : ''}
      ${emptySaved ? '<button type="button" class="clear-filters" data-leave-saved>浏览全部论文</button>' : ''}
      ${!emptySaved && !emptyVenue ? '<button type="button" class="clear-filters" data-reset>清除筛选</button>' : ''}</div>`;
  }
  const pagination = byId('pagination');
  pagination.hidden = pages <= 1;
  pagination.innerHTML = pages <= 1 ? '' : `
    <button type="button" class="page-button" data-page="${state.page - 1}" ${state.page === 1 ? 'disabled' : ''}>上一页</button>
    <span>第 ${state.page} / ${pages} 页</span>
    <button type="button" class="page-button" data-page="${state.page + 1}" ${state.page === pages ? 'disabled' : ''}>下一页</button>`;
}

function render() {
  const focusKey = document.activeElement?.dataset.focus;
  searchInput.value = state.q;
  sortOrder.value = state.sort;
  renderVenueList();
  const tree = getTopicTree();
  byId('topic-list').innerHTML = tree.size ? renderTree(tree) : '<p class="sidebar-note">暂无主题</p>';
  const results = getResults();
  renderFilters(results);
  renderResults(results);
  if (focusKey) document.querySelector(`[data-focus="${CSS.escape(focusKey)}"]`)?.focus({ preventScroll: true });
}

function renderCatalog() {
  const query = normalize(catalogInput.value);
  const groups = new Map();
  for (const venue of venues.values()) {
    if (query && !normalize(`${venue.label} ${venue.name} ${venue.domain}`).includes(query)) continue;
    if (!groups.has(venue.domain)) groups.set(venue.domain, []);
    groups.get(venue.domain).push(venue);
  }
  byId('catalog-list').innerHTML = [...groups].map(([domain, group]) => `
    <details class="catalog-group"${query || group.some(({ id }) => id === state.venue) ? ' open' : ''}>
      <summary>${escapeHtml(domain)} <span class="count">${group.length}</span></summary>
      ${group.map(({ id, label, name, kind }) => `<button class="catalog-venue" type="button" data-catalog-venue="${escapeHtml(id)}">
        <strong>${escapeHtml(label)}</strong><span>${escapeHtml(name)} · ${kind === 'journal' ? '期刊' : '会议'}</span><span class="count">${number.format(countsByVenue.get(id) || 0)} 篇</span>
      </button>`).join('')}
    </details>`).join('') || '<p class="sidebar-note">没有匹配的会议或期刊。</p>';
}

function focusResults() {
  const title = byId('results-title');
  title.focus({ preventScroll: true });
  title.scrollIntoView({ block: 'start' });
}

document.addEventListener('click', (event) => {
  const button = event.target.closest('button');
  if (!ready || !button) return;
  const data = button.dataset;
  if ('openCatalog' in data) {
    catalogInput.value = '';
    renderCatalog();
    catalogDialog.showModal();
    catalogInput.focus();
  } else if ('catalogVenue' in data) {
    catalogDialog.close();
    setState({ ...defaults, sort: state.sort, venue: data.catalogVenue });
    focusResults();
  } else if ('venue' in data) {
    chooseVenue(data.venue);
  } else if ('fold' in data) {
    const expanded = button.getAttribute('aria-expanded') !== 'true';
    topicExpansion.set(data.fold, expanded);
    button.setAttribute('aria-expanded', expanded);
    byId(button.getAttribute('aria-controls')).hidden = !expanded;
  } else if ('topic' in data) {
    setState({ topic: state.topic === data.topic ? '' : data.topic });
  } else if ('paperTopic' in data) {
    setState({ topic: data.paperTopic, venue: data.paperVenue });
    focusResults();
  } else if ('format' in data) {
    setState({ format: data.format });
  } else if (button.id === 'award-filter') {
    setState({ award: !state.award });
  } else if (button.id === 'notes-filter') {
    setState({ notes: !state.notes });
  } else if (button.id === 'saved-nav') {
    setState({ ...defaults, sort: state.sort, saved: !state.saved });
    focusResults();
  } else if ('bookmark' in data) {
    if (bookmarks.has(data.bookmark)) bookmarks.delete(data.bookmark);
    else bookmarks.add(data.bookmark);
    try { localStorage.setItem(storageKey, JSON.stringify([...bookmarks])); } catch { /* Retain bookmarks for this visit. */ }
    if (state.saved) {
      render();
      writeState('replaceState');
      if (!document.activeElement?.dataset.focus) byId('results-title').focus({ preventScroll: true });
    } else {
      button.setAttribute('aria-pressed', bookmarks.has(data.bookmark));
      renderFilters(getResults());
    }
  } else if ('remove' in data) {
    const changes = { [data.remove]: defaults[data.remove] };
    if (data.remove === 'venue') changes.topic = '';
    setState(changes);
    focusResults();
  } else if ('reset' in data || 'leaveSaved' in data) {
    setState({ ...defaults, saved: 'reset' in data && state.saved, sort: state.sort });
    focusResults();
  } else if ('page' in data) {
    setState({ page: Number(data.page) });
    focusResults();
  } else if (button.id === 'mobile-filters') {
    const opened = button.getAttribute('aria-expanded') === 'true';
    button.setAttribute('aria-expanded', !opened);
    byId('sidebar').dataset.open = String(!opened);
  }
});

function updateSearch(event) {
  if (!event.isComposing && searchInput.value !== state.q) setState({ q: searchInput.value }, 'replaceState');
}

searchInput.addEventListener('input', updateSearch);
searchInput.addEventListener('compositionend', updateSearch);
catalogInput.addEventListener('input', renderCatalog);
sortOrder.addEventListener('change', () => setState({ sort: sortOrder.value }));
window.addEventListener('popstate', () => {
  if (!ready) return;
  state = readState();
  render();
});
window.addEventListener('storage', (event) => {
  if (ready && (event.key === storageKey || event.key === null)) {
    bookmarks = readBookmarks();
    render();
  }
});
document.addEventListener('keydown', (event) => {
  const editing = event.target.closest?.('input, textarea, select, [contenteditable]');
  if (ready && event.key === '/' && !editing && !catalogDialog.open && !event.ctrlKey && !event.metaKey && !event.altKey) {
    event.preventDefault();
    searchInput.focus();
  }
});

function dataUrl(filename) {
  const module = new URL(import.meta.url);
  const url = new URL(`data/${filename}`, module);
  const version = module.searchParams.get('v');
  if (version) url.searchParams.set('v', version);
  return url;
}

async function fetchData(filename) {
  const response = await fetch(dataUrl(`${filename}.json`));
  if (!response.ok) throw new Error(`${filename} returned ${response.status}`);
  return response.json();
}

async function fetchCorpus() {
  const response = await fetch(dataUrl('corpus.json.gz'));
  if (!response.ok) throw new Error(`Corpus returned ${response.status}`);
  const payload = await response.arrayBuffer();
  const magic = new Uint8Array(payload, 0, Math.min(payload.byteLength, 2));
  if (magic[0] === 0x1f && magic[1] === 0x8b) {
    const decoded = new Blob([payload]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Response(decoded).json();
  }
  return JSON.parse(new TextDecoder().decode(payload));
}

function expandCorpus(corpus) {
  if (corpus.schema !== 1) throw new Error('Unsupported paper index schema');
  const codes = ['unknown', 'poster', 'spotlight', 'oral', 'journal'];
  const methods = ['unclassified', 'title', 'program'];
  return corpus.rows.map(([id, venue, title, authors, format, topics, source, method, details]) => {
    const { award, review, ...rest } = details;
    return {
      ...rest, id, venue, title, source, year: 2026, format: codes[format], topicMethod: methods[method],
      authors: authors.map((index) => corpus.authors[index]), topics: topics.map((index) => corpus.topics[index]),
      award: award && { label: award[0], source: award[1] }, links: review ? [{ label: 'OpenReview', url: review }] : [],
    };
  });
}

async function start() {
  for (const node of document.querySelectorAll('[data-icon]')) node.innerHTML = icon(node.dataset.icon);
  try {
    const [catalog, records, corpus, summary] = await Promise.all([
      fetchData('venues'), fetchData('papers'), fetchCorpus(), fetchData('coverage'),
    ]);
    coverage = summary;
    venues = new Map(catalog.map((venue) => [venue.id, venue]));
    papers = [...records, ...expandCorpus(corpus)].map((paper) => ({
      ...paper, alsoVenues: paper.alsoVenues || [], topicKeys: paper.topics.map((path) => path.join('/')),
    }));
    if (papers.length !== coverage.total) throw new Error('Paper index does not match coverage metadata');
    for (const paper of papers) {
      for (const id of [paper.venue, ...paper.alsoVenues]) {
        if (!papersByVenue.has(id)) papersByVenue.set(id, []);
        papersByVenue.get(id).push(paper);
      }
    }
    countsByVenue = new Map([...papersByVenue].map(([id, records]) => [id, records.length]));
    if (bookmarks.size) {
      const available = new Set(papers.map((paper) => paper.id));
      bookmarks = new Set([...bookmarks].filter((id) => available.has(id)));
    }
    state = readState();
    render();
    ready = true;
    for (const control of [searchInput, sortOrder, byId('award-filter'), byId('notes-filter')]) control.disabled = false;
    byId('catalog-count').textContent = `第七版 · ${venues.size} 个会议与期刊 · ${number.format(coverage.coveredVenues)} 个已有论文`;
    byId('coverage-line').textContent = `${number.format(coverage.total)} 篇论文 · ${coverage.coveredVenues} 个会议与期刊 · 更新于 ${coverage.updated}`;
  } catch (error) {
    console.error(error);
    byId('results-count').textContent = '论文索引加载失败';
    paperList.innerHTML = '<div class="empty-state"><h3>暂时无法加载论文</h3><p>请通过 GitHub Pages 或本地 HTTP 服务访问。</p></div>';
  } finally {
    byId('workspace').setAttribute('aria-busy', 'false');
  }
}

start();
