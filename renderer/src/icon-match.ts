/**
 * Pick a Lucide icon for a concept label, or null when nothing fits well enough. A wrong icon
 * teaches the wrong thing, so matching is deliberately conservative: a hand-checked vocabulary of
 * explainer concepts first, then an icon named exactly after the label's main noun. Lucide's
 * keyword tags are not used: on real labels they gave "brute force" a book and "smaller pieces"
 * a chess pawn. Vague words such as "trick" or "bit" never match; those keep the neutral glyph.
 */
export type IconNode = [string, Record<string, string>][];

// Hand-checked: each word maps to an icon that shows that concept to a beginner.
const VOCABULARY: Record<string, string> = {
  database: 'database', databases: 'database', storage: 'database', store: 'database', memory: 'database', record: 'database', records: 'database',
  server: 'server', servers: 'server', cloud: 'cloud', disk: 'hard-drive',
  document: 'file-text', documents: 'files', file: 'file-text', files: 'files', pdf: 'file-text', page: 'file-text', pages: 'files',
  chunk: 'file-text', chunks: 'files', passage: 'file-text', passages: 'files', text: 'file-text', source: 'file-text', policy: 'file-text', metadata: 'tags',
  question: 'message-circle-question-mark', questions: 'message-circle-question-mark', query: 'message-circle-question-mark', prompt: 'message-square',
  chat: 'message-square', message: 'message-square', conversation: 'messages-square', answer: 'message-square-text', answers: 'message-square-text',
  response: 'message-square-text', reply: 'message-square-text',
  model: 'brain-circuit', models: 'brain-circuit', llm: 'brain-circuit', ai: 'brain-circuit', brain: 'brain', neuron: 'brain-circuit', network: 'network',
  chatbot: 'bot', assistant: 'bot', agent: 'bot', robot: 'bot', processor: 'cpu', chip: 'cpu', gpu: 'cpu', computer: 'monitor',
  search: 'search', lookup: 'search', retrieval: 'file-search', index: 'list-tree', indexes: 'list-tree', catalog: 'library',
  filter: 'funnel', filtering: 'funnel', filters: 'funnel', ranking: 'list-ordered', results: 'list-checks', result: 'list-checks',
  vector: 'chart-scatter', vectors: 'chart-scatter', embedding: 'chart-scatter', embeddings: 'chart-scatter', space: 'axis-3d', dimensions: 'axis-3d',
  cluster: 'boxes', clusters: 'boxes', group: 'boxes', groups: 'boxes', neighbor: 'locate-fixed', neighbors: 'locate-fixed', neighbours: 'locate-fixed',
  graph: 'waypoints', connections: 'waypoints', link: 'link', links: 'link', pipeline: 'workflow', workflow: 'workflow', process: 'workflow',
  token: 'blocks', tokens: 'blocks', word: 'whole-word', words: 'whole-word', sentence: 'text', number: 'binary', numbers: 'binary', id: 'hash', ids: 'hash',
  code: 'code-xml', program: 'code-xml', function: 'braces', data: 'database', dataset: 'database', training: 'graduation-cap', learning: 'graduation-cap',
  layer: 'layers', layers: 'layers', stack: 'layers', context: 'panel-top', window: 'panel-top', history: 'clock', time: 'clock', speed: 'gauge',
  accuracy: 'target', precision: 'target', goal: 'target', idea: 'lightbulb', insight: 'lightbulb', image: 'image', images: 'images', picture: 'image',
  photo: 'camera', video: 'video', audio: 'volume-2', voice: 'mic', user: 'user', users: 'users', person: 'user', people: 'users', team: 'users', teams: 'users',
  library: 'library', book: 'book-open', books: 'library', shelf: 'library', section: 'layout-list', map: 'map', world: 'globe', web: 'globe', internet: 'globe',
  security: 'shield-check', privacy: 'lock', password: 'key-round', key: 'key-round', error: 'triangle-alert', errors: 'triangle-alert', bias: 'scale',
  cost: 'coins', price: 'coins', money: 'coins', budget: 'wallet', scale: 'trending-up', scaling: 'trending-up', growth: 'trending-up',
  water: 'droplet', rain: 'cloud-rain', sun: 'sun', plant: 'sprout', leaf: 'leaf', seed: 'sprout', tree: 'trees', energy: 'zap', power: 'zap',
  math: 'sigma', formula: 'sigma', probability: 'percent', percentage: 'percent', calculation: 'calculator', loop: 'repeat', cycle: 'refresh-cw',
  comparison: 'arrow-right-left', recommendation: 'thumbs-up', recommendations: 'thumbs-up', duplicate: 'copy', duplicates: 'copy', backbone: 'git-branch',
  recap: 'list-checks', summary: 'list-checks', keyword: 'text-search', keywords: 'text-search', piece: 'puzzle', pieces: 'puzzle', king: 'crown', queen: 'crown',
  noise: 'tv-minimal', static: 'tv-minimal', sound: 'audio-waveform',
};
const VAGUE = new Set(('trick bit bits one ones way ways thing things lot lots kind part parts stuff point points area areas option options need needs side top ' +
  'example examples case cases level levels question idea set type types system systems problem problems step steps').split(' '));
const STOP = new Set('a an the of to in on for with and or by from into your our their its this that these those my his her'.split(' '));

const singular = (w: string) => w.endsWith('ies') ? w.slice(0, -3) + 'y' : w.endsWith('ses') || w.endsWith('xes') ? w.slice(0, -2) : w.endsWith('s') && !w.endsWith('ss') ? w.slice(0, -1) : w;

/** The label's words, last (head) noun first: in "vector database" the database is the thing. */
function headFirst(label: string) {
  const words = label.toLowerCase().replace(/[’']s\b/g, '').split(/[^a-z0-9]+/).filter(w => w && !STOP.has(w));
  return words.reverse();
}

export function iconFor(label: string, nodes: Record<string, IconNode>): string | null {
  const words = headFirst(label);
  if (!words.length) return null;
  for (const word of words) {
    const known = VOCABULARY[word] ?? VOCABULARY[singular(word)];
    if (known && nodes[known]) return known;
  }
  const head = words[0], base = singular(head);
  if (VAGUE.has(head) || VAGUE.has(base) || base.length < 3) return null;
  for (const name of [head, base]) if (nodes[name]) return name;
  return null;
}
