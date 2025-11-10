#!/usr/bin/env node

import { promises as fs } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import process from 'process';
import { createHash } from 'crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');

const options = {
  check: process.argv.includes('--check')
};

const allowedLevels = new Set(['A1', 'A2', 'B1', 'B2', 'C1', 'C2']);
const cefrOrder = { A1: 1, A2: 2, B1: 3, B2: 4, C1: 5, C2: 6, UNSET: 7 };
const allowedPos = new Set(['noun', 'verb', 'adj', 'adv', 'prep', 'det', 'pron', 'conj', 'expr']);
const allowedGenders = new Set(['masculine', 'feminine']);

const buildDirs = {
  canonical: path.join(repoRoot, 'build', 'canonical'),
  reports: path.join(repoRoot, 'build', 'reports'),
  rejects: path.join(repoRoot, 'build', 'rejects')
};

const schemaPaths = {
  lesson: path.join(repoRoot, 'tools', 'schemas', 'lesson.schema.json'),
  vocab: path.join(repoRoot, 'tools', 'schemas', 'vocab.schema.json')
};

function slugify(value) {
  return value
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 50) || 'slug';
}

async function pathExists(target) {
  try {
    await fs.access(target);
    return true;
  } catch (error) {
    return false;
  }
}

async function listFilesRecursive(dir) {
  const results = [];
  async function walk(current) {
    let entries;
    try {
      entries = await fs.readdir(current, { withFileTypes: true });
    } catch (error) {
      return;
    }
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (entry.isFile()) {
        results.push(fullPath);
      }
    }
  }
  await walk(dir);
  return results;
}

function mergeTextVariants(a, b) {
  if (!a) return b || '';
  if (!b) return a || '';
  if (a.trim() === b.trim()) return a;
  return `${a}\n\n— MERGED VARIANT —\n\n${b}`;
}

function normalizeWhitespaceForCompare(value) {
  return value.replace(/\s+/g, ' ').trim();
}

function uniqueArray(values) {
  return Array.from(new Set(values.filter((v) => v !== undefined && v !== null)));
}

function sortKeys(value) {
  if (Array.isArray(value)) {
    return value.map((item) => sortKeys(item));
  }
  if (value && typeof value === 'object') {
    const sorted = {};
    for (const key of Object.keys(value).sort()) {
      sorted[key] = sortKeys(value[key]);
    }
    return sorted;
  }
  return value;
}

function deepEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

async function loadSchema(schemaPath) {
  const raw = await fs.readFile(schemaPath, 'utf8');
  return JSON.parse(raw);
}

function computeVocabId(key) {
  const hash = createHash('sha1').update(key).digest('hex');
  const num = parseInt(hash.slice(0, 8), 16) % 100000;
  return `mmspanish__vocab_${String(num).padStart(5, '0')}`;
}

function computeLessonId(lesson) {
  if (lesson.id && /^mmspanish__grammar_[a-z0-9_\-]+$/.test(lesson.id)) {
    return lesson.id;
  }
  const numberPart = lesson.lesson_number ?? 0;
  const slugBase = slugify(lesson.nickname || lesson.title || 'lesson');
  const numeric = String(numberPart).padStart(3, '0');
  return `mmspanish__grammar_${numeric}_${slugBase}`;
}

function normalizeLevel(level, context, audit) {
  if (!level || typeof level !== 'string') {
    audit.unresolvedLevels.add(context);
    return 'UNSET';
  }
  const upper = level.toUpperCase();
  if (allowedLevels.has(upper)) {
    return upper;
  }
  audit.unresolvedLevels.add(`${context} (input=${level})`);
  return 'UNSET';
}

function normalizePos(pos) {
  if (!pos || typeof pos !== 'string') return null;
  const lower = pos.toLowerCase();
  const map = {
    adjective: 'adj',
    adjetivo: 'adj',
    adverb: 'adv',
    adverbio: 'adv',
    verbo: 'verb',
    sustantivo: 'noun',
    nombre: 'noun',
    pronoun: 'pron',
    pronombre: 'pron',
    conjunction: 'conj',
    conjunct: 'conj',
    expression: 'expr',
    phrase: 'expr',
    determiner: 'det',
    article: 'det',
    preposition: 'prep'
  };
  const normalized = map[lower] || lower;
  if (allowedPos.has(normalized)) return normalized;
  return null;
}

function normalizeGender(gender) {
  if (!gender || typeof gender !== 'string') return null;
  const lower = gender.toLowerCase();
  if (lower.startsWith('m')) return 'masculine';
  if (lower.startsWith('f')) return 'feminine';
  return null;
}

function chooseScalar(existing, incoming, existingMeta, incomingMeta, field, noteCollector) {
  if (existing === undefined || existing === null || existing === '') {
    return incoming;
  }
  if (incoming === undefined || incoming === null || incoming === '') {
    return existing;
  }
  if (existing === incoming) {
    return existing;
  }
  const existingTime = existingMeta?.newestMtime ?? 0;
  const incomingTime = incomingMeta?.newestMtime ?? 0;
  if (incomingTime !== existingTime) {
    const chosen = incomingTime > existingTime ? incoming : existing;
    const alt = incomingTime > existingTime ? existing : incoming;
    if (noteCollector) noteCollector(field, alt);
    return chosen;
  }
  const existingLen = String(existing).length;
  const incomingLen = String(incoming).length;
  const chosen = incomingLen > existingLen ? incoming : existing;
  const alt = incomingLen > existingLen ? existing : incoming;
  if (noteCollector) noteCollector(field, alt);
  return chosen;
}

function unionArrays(existing, incoming) {
  const set = new Map();
  for (const value of existing || []) {
    const key = typeof value === 'string' ? normalizeWhitespaceForCompare(value) : JSON.stringify(sortKeys(value));
    set.set(key, value);
  }
  for (const value of incoming || []) {
    const key = typeof value === 'string' ? normalizeWhitespaceForCompare(value) : JSON.stringify(sortKeys(value));
    if (!set.has(key)) {
      set.set(key, value);
    }
  }
  return Array.from(set.values());
}

function deepMerge(existing, incoming, existingMeta, incomingMeta, noteCollector) {
  if (existing === undefined) return incoming;
  if (incoming === undefined) return existing;
  if (Array.isArray(existing) && Array.isArray(incoming)) {
    return unionArrays(existing, incoming);
  }
  if (typeof existing === 'object' && typeof incoming === 'object' && existing && incoming) {
    const result = { ...existing };
    for (const key of Object.keys(incoming)) {
      result[key] = deepMerge(existing[key], incoming[key], existingMeta, incomingMeta, noteCollector);
    }
    return result;
  }
  return chooseScalar(existing, incoming, existingMeta, incomingMeta, 'scalar', noteCollector);
}

function appendAltVariantNotes(entry, field, value) {
  if (value === undefined || value === null || value === '') return;
  if (entry.type === 'lesson') {
    if (!entry.data.notes) {
      entry.data.notes = '';
    }
    const prefix = entry.data.notes ? '\n\n' : '';
    entry.data.notes += `${prefix}alt_variant:${field} => ${value}`;
  } else if (entry.type === 'vocab') {
    if (!Array.isArray(entry.data.tags)) {
      entry.data.tags = [];
    }
    const tagValue = `alt_variant:${field}=>${String(value)}`;
    if (!entry.data.tags.includes(tagValue)) {
      entry.data.tags.push(tagValue);
    }
  }
}

function generateConflictVariants(text) {
  const normalized = text.replace(/\r\n/g, '\n');
  const conflictRegex = /<<<<<<<[^\n]*\n([\s\S]*?)\n=======\n([\s\S]*?)\n>>>>>>>[^\n]*\n?/g;
  let lastIndex = 0;
  const segments = [];
  let match;
  while ((match = conflictRegex.exec(normalized)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'literal', value: normalized.slice(lastIndex, match.index) });
    }
    segments.push({ type: 'choice', options: [match[1], match[2]] });
    lastIndex = conflictRegex.lastIndex;
  }
  if (lastIndex === 0) {
    return [normalized];
  }
  if (lastIndex < normalized.length) {
    segments.push({ type: 'literal', value: normalized.slice(lastIndex) });
  }
  let variants = [''];
  for (const segment of segments) {
    if (segment.type === 'literal') {
      variants = variants.map((base) => base + segment.value);
    } else if (segment.type === 'choice') {
      const next = [];
      for (const base of variants) {
        for (const option of segment.options) {
          next.push(base + option);
        }
      }
      variants = next;
    }
  }
  const deduped = Array.from(new Set(variants.map((v) => v.trim())));
  return deduped.length ? deduped : [normalized];
}

function sanitizeJsonText(text) {
  let cleaned = text.replace(/\r\n/g, '\n');
  cleaned = cleaned.replace(/\/\/.*$/gm, '');
  cleaned = cleaned.replace(/\/\*[\s\S]*?\*\//g, '');
  cleaned = cleaned.replace(/,(\s*[}\]])/g, '$1');
  return cleaned;
}

function convertSingleQuotes(text) {
  return text.replace(/'([^'\\]*(?:\\.[^'\\]*)*)'/g, (match, inner) => {
    const escaped = inner.replace(/"/g, '\\"');
    return `"${escaped}"`;
  });
}

function parseJsonLoose(text) {
  const cleaned = sanitizeJsonText(text);
  try {
    return JSON.parse(cleaned);
  } catch (error) {
    try {
      const converted = convertSingleQuotes(cleaned);
      return JSON.parse(converted);
    } catch (innerError) {
      throw innerError;
    }
  }
}

function attemptJsonParse(text) {
  try {
    return { ok: true, value: parseJsonLoose(text) };
  } catch (error) {
    return { ok: false, error };
  }
}

function extractJsonCandidates(text) {
  const results = [];
  const normalized = text;
  const stack = [];
  let currentStart = null;
  let inString = false;
  let stringChar = '';
  let escape = false;
  for (let i = 0; i < normalized.length; i += 1) {
    const char = normalized[i];
    if (inString) {
      if (escape) {
        escape = false;
      } else if (char === '\\') {
        escape = true;
      } else if (char === stringChar) {
        inString = false;
        stringChar = '';
      }
      continue;
    }
    if (char === '"' || char === '\'' || char === '`') {
      inString = true;
      stringChar = char;
      continue;
    }
    if (char === '{' || char === '[') {
      stack.push({ char, index: i });
      if (stack.length === 1) {
        currentStart = i;
      }
      continue;
    }
    if (char === '}' || char === ']') {
      if (stack.length) {
        stack.pop();
        if (!stack.length && currentStart !== null) {
          results.push(normalized.slice(currentStart, i + 1));
          currentStart = null;
        }
      }
    }
  }
  return results;
}

function tryParseVariant(text) {
  const trimmed = text.trim();
  const entries = [];
  const rejects = [];
  if (!trimmed) {
    return { entries, rejects };
  }
  const parsed = attemptJsonParse(trimmed);
  if (parsed.ok) {
    const value = parsed.value;
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item && typeof item === 'object') {
          entries.push(structuredClone(item));
        }
      }
    } else if (value && typeof value === 'object') {
      entries.push(structuredClone(value));
    } else {
      rejects.push({ reason: 'Parsed value is not object/array', fragment: trimmed });
    }
    return { entries, rejects };
  }
  // Try JSON Lines
  const lines = trimmed.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  let parsedAny = false;
  if (lines.length > 1) {
    for (const line of lines) {
      const attempt = attemptJsonParse(line);
      if (attempt.ok) {
        parsedAny = true;
        entries.push(structuredClone(attempt.value));
      }
    }
  }
  if (parsedAny) {
    return { entries, rejects };
  }
  // Extract candidate JSON blocks
  const candidates = extractJsonCandidates(trimmed);
  for (const candidate of candidates) {
    const attempt = attemptJsonParse(candidate);
    if (attempt.ok) {
      entries.push(structuredClone(attempt.value));
      parsedAny = true;
    }
  }
  if (!parsedAny) {
    rejects.push({ reason: parsed.error ? parsed.error.message : 'Unable to parse', fragment: trimmed });
  }
  return { entries, rejects };
}

function preprocessEntry(raw) {
  if (!raw || typeof raw !== 'object') return raw;
  const entry = structuredClone(raw);
  if (entry.palabra && !entry.spanish) {
    entry.spanish = entry.palabra;
  }
  if (entry.word && !entry.spanish) {
    entry.spanish = entry.word;
  }
  if (entry.english && !entry.english_gloss) {
    entry.english_gloss = entry.english;
  }
  if (entry.gloss && !entry.english_gloss) {
    entry.english_gloss = entry.gloss;
  }
  if (entry.gloss_en && !entry.english_gloss) {
    entry.english_gloss = entry.gloss_en;
  }
  if (entry.definition_full && !entry.definition) {
    entry.definition = entry.definition_full;
  }
  if (entry.def && !entry.definition) {
    entry.definition = entry.def;
  }
  if (entry.description && !entry.definition) {
    entry.definition = entry.description;
  }
  if (entry.etymology && !entry.origin) {
    entry.origin = entry.etymology;
  }
  if (entry.mnemonic && !entry.story) {
    entry.story = entry.mnemonic;
  }
  if (entry.story && Array.isArray(entry.story)) {
    entry.story = entry.story.join('\n');
  }
  if (entry.examples_es && entry.examples_en) {
    const esArray = Array.isArray(entry.examples_es) ? entry.examples_es : [entry.examples_es];
    const enArray = Array.isArray(entry.examples_en) ? entry.examples_en : [entry.examples_en];
    entry.examples = esArray.map((es, idx) => ({ es, en: enArray[idx] || '' }));
  }
  if (entry.examples && typeof entry.examples === 'object' && !Array.isArray(entry.examples)) {
    const maybePairs = [];
    for (const [es, en] of Object.entries(entry.examples)) {
      maybePairs.push({ es, en });
    }
    entry.examples = maybePairs;
  }
  if (entry.example_es && entry.example_en) {
    entry.examples = [{ es: entry.example_es, en: entry.example_en }];
  }
  if (entry.examples && Array.isArray(entry.examples)) {
    entry.examples = entry.examples.map((example) => {
      if (typeof example === 'string') {
        return { es: example, en: '' };
      }
      const es = example.es ?? example.spanish ?? example.es_example ?? '';
      const en = example.en ?? example.english ?? example.en_example ?? '';
      return { es, en };
    }).filter((example) => example.es || example.en);
  }
  if (entry.part_of_speech && !entry.pos) {
    entry.pos = entry.part_of_speech;
  }
  if (entry.pos_tag && !entry.pos) {
    entry.pos = entry.pos_tag;
  }
  if (entry.gender === undefined && entry.genero !== undefined) {
    entry.gender = entry.genero;
  }
  if (entry.title_short && !entry.nickname) {
    entry.nickname = entry.title_short;
  }
  if (entry.alias && !entry.nickname) {
    entry.nickname = entry.alias;
  }
  if (entry.short_name && !entry.nickname) {
    entry.nickname = entry.short_name;
  }
  if (entry.lesson_title && !entry.title) {
    entry.title = entry.lesson_title;
  }
  if (entry.name && !entry.title && entry.steps) {
    entry.title = entry.name;
  }
  if (entry.slug && !entry.nickname) {
    entry.nickname = entry.slug;
  }
  if (entry.lessonNum && !entry.lesson_number) {
    entry.lesson_number = entry.lessonNum;
  }
  if (entry.lesson && typeof entry.lesson === 'object') {
    if (!entry.title && entry.lesson.title) entry.title = entry.lesson.title;
    if (!entry.nickname && entry.lesson.nickname) entry.nickname = entry.lesson.nickname;
    if (!entry.steps && entry.lesson.steps) entry.steps = entry.lesson.steps;
  }
  if (entry.tags && typeof entry.tags === 'string') {
    entry.tags = entry.tags.split(/[,;]+/).map((tag) => tag.trim()).filter(Boolean);
  }
  return entry;
}

function classifyEntry(entry) {
  if (!entry || typeof entry !== 'object') return 'unknown';
  const hasLessonHints = entry.title || entry.nickname || Array.isArray(entry.steps) || entry.unit !== undefined || entry.lesson_number !== undefined;
  const hasVocabHints = entry.spanish || entry.english_gloss || entry.definition || entry.pos;
  if (hasLessonHints && Array.isArray(entry.steps)) return 'lesson';
  if (hasLessonHints && !hasVocabHints) return 'lesson';
  if (hasVocabHints && !hasLessonHints) return 'vocab';
  if (hasVocabHints) return 'vocab';
  return 'unknown';
}

function normalizeLesson(raw, meta, audit) {
  const entry = structuredClone(raw);
  entry.title = entry.title ? String(entry.title).trim() : '';
  entry.nickname = entry.nickname ? String(entry.nickname).trim() : '';
  if (!entry.nickname && entry.title) {
    entry.nickname = slugify(entry.title).slice(0, 20);
  }
  const levelContext = `${meta.source}`;
  entry.level = normalizeLevel(entry.level, levelContext, audit);
  entry.unit = Number.isFinite(Number(entry.unit)) ? Number(entry.unit) : 0;
  entry.lesson_number = Number.isFinite(Number(entry.lesson_number)) ? Number(entry.lesson_number) : 0;
  if (!Array.isArray(entry.tags)) entry.tags = [];
  entry.tags = uniqueArray(entry.tags.map((tag) => String(tag)));
  if (!Array.isArray(entry.steps)) entry.steps = [];
  entry.steps = entry.steps.map((step, index) => {
    if (!step || typeof step !== 'object') {
      return { phase: 'unspecified', line: String(step ?? '') };
    }
    const normalizedStep = { ...step };
    if (!normalizedStep.phase) {
      normalizedStep.phase = normalizedStep.type || normalizedStep.name || `phase_${index + 1}`;
    }
    if (normalizedStep.text && !normalizedStep.line) {
      normalizedStep.line = normalizedStep.text;
    }
    if (Array.isArray(normalizedStep.items)) {
      normalizedStep.items = uniqueArray(normalizedStep.items.map((item) => String(item)));
    }
    if (normalizedStep.items && !Array.isArray(normalizedStep.items)) {
      normalizedStep.items = [String(normalizedStep.items)];
    }
    if (normalizedStep.origin && Array.isArray(normalizedStep.origin)) {
      normalizedStep.origin = normalizedStep.origin.join('\n');
    }
    if (normalizedStep.story && Array.isArray(normalizedStep.story)) {
      normalizedStep.story = normalizedStep.story.join('\n');
    }
    if (normalizedStep.lines && !normalizedStep.line) {
      normalizedStep.line = Array.isArray(normalizedStep.lines) ? normalizedStep.lines.join('\n') : String(normalizedStep.lines);
    }
    return normalizedStep;
  });
  entry.notes = entry.notes ? String(entry.notes) : '';
  const sourceFiles = new Set();
  for (const src of entry.source_files || []) {
    sourceFiles.add(src);
  }
  sourceFiles.add(meta.source);
  entry.source_files = Array.from(sourceFiles);
  entry.id = computeLessonId(entry);
  return entry;
}

function normalizeExamples(examples) {
  if (!Array.isArray(examples)) return [];
  const seen = new Map();
  const normalized = [];
  for (const example of examples) {
    if (!example) continue;
    const es = example.es ?? example.spanish ?? '';
    const en = example.en ?? example.english ?? '';
    const key = `${normalizeWhitespaceForCompare(es)}|${normalizeWhitespaceForCompare(en)}`;
    if (!seen.has(key)) {
      normalized.push({ es: es || '', en: en || '' });
      seen.set(key, true);
    }
  }
  return normalized;
}

function normalizeVocab(raw, meta, audit) {
  const entry = structuredClone(raw);
  entry.spanish = entry.spanish ? String(entry.spanish).trim() : '';
  entry.pos = normalizePos(entry.pos);
  if (!entry.pos && entry.spanish) {
    entry.pos = 'expr';
  }
  entry.gender = entry.pos === 'noun' ? normalizeGender(entry.gender) : null;
  entry.english_gloss = entry.english_gloss ? String(entry.english_gloss).trim() : '';
  if (Array.isArray(entry.english_gloss)) {
    entry.english_gloss = entry.english_gloss.join('; ');
  }
  entry.definition = Array.isArray(entry.definition) ? entry.definition.join('\n\n') : (entry.definition ? String(entry.definition) : '');
  entry.origin = Array.isArray(entry.origin) ? entry.origin.join('\n\n') : (entry.origin ? String(entry.origin) : '');
  entry.story = Array.isArray(entry.story) ? entry.story.join('\n\n') : (entry.story ? String(entry.story) : '');
  entry.examples = normalizeExamples(entry.examples);
  const levelContext = `${meta.source}`;
  entry.level = normalizeLevel(entry.level, levelContext, audit);
  if (!Array.isArray(entry.tags)) {
    entry.tags = [];
  }
  entry.tags = uniqueArray(entry.tags.map((tag) => String(tag)));
  const sourceFiles = new Set();
  for (const src of entry.source_files || []) {
    sourceFiles.add(src);
  }
  sourceFiles.add(meta.source);
  entry.source_files = Array.from(sourceFiles);
  const key = `${entry.spanish.toLowerCase()}|${entry.pos || 'unknown'}|${entry.gender || 'null'}`;
  entry.id = computeVocabId(key);
  return entry;
}

function ensureDefinitionMerge(target, incoming, field) {
  if (!incoming) return target || '';
  if (!target) return incoming;
  if (normalizeWhitespaceForCompare(target) === normalizeWhitespaceForCompare(incoming)) {
    return target;
  }
  return mergeTextVariants(target, incoming);
}

function mergeLesson(existing, incoming, audit) {
  const noteCollector = (field, altValue) => appendAltVariantNotes(existing, field, altValue);
  const existingMeta = existing.meta;
  const incomingMeta = incoming.meta;
  const merged = existing.data;
  const inc = incoming.data;
  merged.title = chooseScalar(merged.title, inc.title, existingMeta, incomingMeta, 'title', noteCollector);
  merged.nickname = chooseScalar(merged.nickname, inc.nickname, existingMeta, incomingMeta, 'nickname', noteCollector);
  merged.level = chooseScalar(merged.level, inc.level, existingMeta, incomingMeta, 'level', noteCollector);
  merged.unit = chooseScalar(merged.unit, inc.unit, existingMeta, incomingMeta, 'unit', noteCollector);
  merged.lesson_number = chooseScalar(merged.lesson_number, inc.lesson_number, existingMeta, incomingMeta, 'lesson_number', noteCollector);
  merged.tags = unionArrays(merged.tags, inc.tags);
  merged.steps = mergeSteps(merged.steps, inc.steps);
  merged.notes = mergeTextVariants(merged.notes, inc.notes);
  merged.source_files = Array.from(new Set([...merged.source_files, ...inc.source_files]));
  existing.meta.sourceFiles = new Set([...existing.meta.sourceFiles, ...incoming.meta.sourceFiles]);
  existing.meta.newestMtime = Math.max(existing.meta.newestMtime, incoming.meta.newestMtime);
  existing.meta.sources.push(...incoming.meta.sources);
}

function mergeSteps(existingSteps, incomingSteps) {
  if (!Array.isArray(existingSteps) || existingSteps.length === 0) {
    return Array.isArray(incomingSteps) ? incomingSteps.slice() : [];
  }
  if (!Array.isArray(incomingSteps) || incomingSteps.length === 0) {
    return existingSteps.slice();
  }
  const merged = existingSteps.slice();
  for (const step of incomingSteps) {
    const matchIndex = merged.findIndex((candidate) => candidate.phase === step.phase);
    if (matchIndex === -1) {
      merged.push(step);
    } else {
      const existing = merged[matchIndex];
      const combined = { ...existing };
      if (step.line) {
        combined.line = mergeTextVariants(existing.line || '', step.line);
      }
      if (step.origin) {
        combined.origin = mergeTextVariants(existing.origin || '', step.origin);
      }
      if (step.story) {
        combined.story = mergeTextVariants(existing.story || '', step.story);
      }
      combined.items = unionArrays(existing.items, step.items);
      merged[matchIndex] = combined;
    }
  }
  return merged;
}

function mergeVocab(existing, incoming) {
  const noteCollector = (field, altValue) => appendAltVariantNotes(existing, field, altValue);
  const existingMeta = existing.meta;
  const incomingMeta = incoming.meta;
  const merged = existing.data;
  const inc = incoming.data;
  merged.spanish = chooseScalar(merged.spanish, inc.spanish, existingMeta, incomingMeta, 'spanish', noteCollector);
  merged.pos = chooseScalar(merged.pos, inc.pos, existingMeta, incomingMeta, 'pos', noteCollector);
  merged.gender = chooseScalar(merged.gender, inc.gender, existingMeta, incomingMeta, 'gender', noteCollector);
  merged.english_gloss = chooseScalar(merged.english_gloss, inc.english_gloss, existingMeta, incomingMeta, 'english_gloss', noteCollector);
  merged.definition = ensureDefinitionMerge(merged.definition, inc.definition, 'definition');
  merged.origin = ensureDefinitionMerge(merged.origin, inc.origin, 'origin');
  merged.story = ensureDefinitionMerge(merged.story, inc.story, 'story');
  merged.examples = unionArrays(merged.examples, inc.examples);
  merged.level = chooseScalar(merged.level, inc.level, existingMeta, incomingMeta, 'level', noteCollector);
  merged.tags = unionArrays(merged.tags, inc.tags);
  merged.source_files = Array.from(new Set([...merged.source_files, ...inc.source_files]));
  existing.meta.sourceFiles = new Set([...existing.meta.sourceFiles, ...incoming.meta.sourceFiles]);
  existing.meta.newestMtime = Math.max(existing.meta.newestMtime, incoming.meta.newestMtime);
  existing.meta.sources.push(...incoming.meta.sources);
}

function createEntryRecord(data, type, meta) {
  return {
    data,
    type,
    meta: {
      newestMtime: meta.mtimeMs,
      sourceFiles: new Set([meta.source]),
      sources: [meta]
    }
  };
}

function dedupeAndMerge(entries, type, audit) {
  const map = new Map();
  const duplicateClusters = [];
  for (const entry of entries) {
    const data = entry.data;
    let key;
    if (type === 'lesson') {
      if (data.title) {
        if (data.unit || data.lesson_number) {
          key = `${data.title}|${data.unit}|${data.lesson_number}`;
        }
        if (!key) {
          key = `${data.title}|${data.nickname}`;
        }
      } else {
        key = data.id;
      }
    } else {
      key = `${data.spanish.toLowerCase()}|${data.pos || 'unknown'}|${data.gender || 'null'}`;
    }
    if (!map.has(key)) {
      map.set(key, entry);
    } else {
      const existing = map.get(key);
      if (type === 'lesson') {
        mergeLesson(existing, entry, audit);
      } else {
        mergeVocab(existing, entry, audit);
      }
      duplicateClusters.push({ key, sources: [...existing.meta.sourceFiles].concat([...entry.meta.sourceFiles]) });
    }
  }
  return { merged: Array.from(map.values()), duplicateClusters };
}

function filterValidRecords(records, type, rejects) {
  const valid = [];
  for (const record of records) {
    const data = record.data;
    const sources = Array.from(record.meta.sourceFiles).join(', ');
    if (type === 'lesson') {
      const missing = [];
      if (!data.title) missing.push('title');
      if (!data.nickname) missing.push('nickname');
      if (!Array.isArray(data.steps) || data.steps.length === 0) missing.push('steps');
      if (missing.length) {
        rejects.push({
          reason: `Lesson missing ${missing.join(', ')}`,
          fragment: JSON.stringify(data, null, 2),
          file: sources
        });
        continue;
      }
    } else if (type === 'vocab') {
      const missing = [];
      if (!data.spanish) missing.push('spanish');
      if (!data.pos) missing.push('pos');
      if (!data.english_gloss) missing.push('english_gloss');
      if (!data.definition) missing.push('definition');
      if (missing.length) {
        rejects.push({
          reason: `Vocabulary missing ${missing.join(', ')}`,
          fragment: JSON.stringify(data, null, 2),
          file: sources
        });
        continue;
      }
    }
    valid.push(record);
  }
  return valid;
}

async function ensureDirectories() {
  await fs.mkdir(buildDirs.canonical, { recursive: true });
  await fs.mkdir(buildDirs.reports, { recursive: true });
  await fs.mkdir(buildDirs.rejects, { recursive: true });
}

async function collectContentFiles() {
  const contentDir = path.join(repoRoot, 'content');
  if (!(await pathExists(contentDir))) {
    return [];
  }
  const files = await listFilesRecursive(contentDir);
  return files;
}

async function readFileWithStat(filePath) {
  const [content, stats] = await Promise.all([
    fs.readFile(filePath, 'utf8'),
    fs.stat(filePath)
  ]);
  return { content, stats };
}

async function processFile(filePath, audit) {
  const relative = path.relative(repoRoot, filePath);
  const { content, stats } = await readFileWithStat(filePath);
  const mtimeMs = stats.mtimeMs || stats.mtime?.getTime() || 0;
  const variants = generateConflictVariants(content);
  const lessons = [];
  const vocabulary = [];
  const rejects = [];
  for (const variant of variants) {
    const { entries, rejects: variantRejects } = tryParseVariant(variant);
    for (const reject of variantRejects) {
      rejects.push({ ...reject, file: relative });
    }
    for (const rawEntry of entries) {
      const preprocessed = preprocessEntry(rawEntry);
      const classification = classifyEntry(preprocessed);
      if (classification === 'lesson') {
        const normalized = normalizeLesson(preprocessed, { source: relative, mtimeMs }, audit);
        lessons.push(createEntryRecord(normalized, 'lesson', { source: relative, mtimeMs }));
      } else if (classification === 'vocab') {
        const normalized = normalizeVocab(preprocessed, { source: relative, mtimeMs }, audit);
        vocabulary.push(createEntryRecord(normalized, 'vocab', { source: relative, mtimeMs }));
      } else {
        rejects.push({ reason: 'Unable to classify entry', fragment: JSON.stringify(preprocessed, null, 2), file: relative });
      }
    }
  }
  audit.filesScanned += 1;
  audit.entriesScanned += lessons.length + vocabulary.length;
  return { lessons, vocabulary, rejects };
}

function finalizeEntries(entryRecords) {
  return entryRecords.map((record) => {
    const data = record.data;
    data.source_files = Array.from(record.meta.sourceFiles).sort();
    return sortKeys(data);
  });
}

async function scanForConflictMarkers() {
  const offenders = [];
  const dirs = [path.join(repoRoot, 'content'), path.join(repoRoot, 'build')];
  for (const dir of dirs) {
    if (!(await pathExists(dir))) continue;
    const files = await listFilesRecursive(dir);
    for (const file of files) {
      const text = await fs.readFile(file, 'utf8');
      if (text.includes('<<<<<<<') || text.includes('=======') || text.includes('>>>>>>>')) {
        offenders.push(path.relative(repoRoot, file));
      }
    }
  }
  return offenders;
}

async function buildOnce(audit) {
  const files = await collectContentFiles();
  const lessons = [];
  const vocabulary = [];
  const rejects = [];
  for (const file of files) {
    const result = await processFile(file, audit);
    lessons.push(...result.lessons);
    vocabulary.push(...result.vocabulary);
    rejects.push(...result.rejects);
  }
  const lessonMerge = dedupeAndMerge(lessons, 'lesson', audit);
  const vocabMerge = dedupeAndMerge(vocabulary, 'vocab', audit);
  audit.lessonDuplicateClusters.push(...lessonMerge.duplicateClusters);
  audit.vocabDuplicateClusters.push(...vocabMerge.duplicateClusters);
  const validLessonRecords = filterValidRecords(lessonMerge.merged, 'lesson', rejects);
  const validVocabRecords = filterValidRecords(vocabMerge.merged, 'vocab', rejects);
  const finalLessons = finalizeEntries(validLessonRecords);
  const finalVocab = finalizeEntries(validVocabRecords);
  return { lessons: finalLessons, vocabulary: finalVocab, rejects };
}

function computeHash(value) {
  return createHash('sha256').update(value).digest('hex');
}

function stringifyPretty(value) {
  return JSON.stringify(value, null, 2) + '\n';
}

function typeMatches(expected, value) {
  switch (expected) {
    case 'string':
      return typeof value === 'string';
    case 'integer':
      return Number.isInteger(value);
    case 'number':
      return typeof value === 'number';
    case 'object':
      return value !== null && typeof value === 'object' && !Array.isArray(value);
    case 'array':
      return Array.isArray(value);
    case 'boolean':
      return typeof value === 'boolean';
    case 'null':
      return value === null;
    default:
      return false;
  }
}

function validateWithSchema(schema, value, path = '') {
  const errors = [];
  const types = Array.isArray(schema.type) ? schema.type : schema.type ? [schema.type] : [];
  if (types.length && !types.some((t) => typeMatches(t, value))) {
    errors.push(`${path}: expected type ${types.join(' or ')}`);
    return errors;
  }
  if (schema.enum && !schema.enum.includes(value)) {
    errors.push(`${path}: value ${JSON.stringify(value)} not in enum`);
  }
  if (schema.pattern && typeof value === 'string') {
    const regex = new RegExp(schema.pattern);
    if (!regex.test(value)) {
      errors.push(`${path}: value ${value} does not match pattern ${schema.pattern}`);
    }
  }
  if (schema.minLength !== undefined && typeof value === 'string') {
    if (value.length < schema.minLength) {
      errors.push(`${path}: string shorter than ${schema.minLength}`);
    }
  }
  if (schema.minimum !== undefined && typeof value === 'number') {
    if (value < schema.minimum) {
      errors.push(`${path}: number less than ${schema.minimum}`);
    }
  }
  if (types.includes('object')) {
    if (schema.required) {
      for (const requiredKey of schema.required) {
        if (!(requiredKey in value)) {
          errors.push(`${path}.${requiredKey}: missing required property`);
        }
      }
    }
    if (schema.properties) {
      for (const [key, propertySchema] of Object.entries(schema.properties)) {
        if (value[key] !== undefined) {
          errors.push(...validateWithSchema(propertySchema, value[key], `${path}.${key}`));
        }
      }
    }
    if (schema.additionalProperties === false && schema.properties) {
      for (const key of Object.keys(value)) {
        if (!(key in schema.properties)) {
          errors.push(`${path}.${key}: additional property not allowed`);
        }
      }
    }
  }
  if (types.includes('array') && Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) {
      errors.push(`${path}: array shorter than ${schema.minItems}`);
    }
    if (schema.uniqueItems) {
      const seen = new Set(value.map((item) => JSON.stringify(item)));
      if (seen.size !== value.length) {
        errors.push(`${path}: array items not unique`);
      }
    }
    if (schema.items) {
      for (let i = 0; i < value.length; i += 1) {
        errors.push(...validateWithSchema(schema.items, value[i], `${path}[${i}]`));
      }
    }
  }
  return errors;
}

function buildAuditMarkdown(audit, lessons, vocabulary, rejects) {
  const lines = [];
  lines.push('# Canonical rebuild audit');
  lines.push('');
  lines.push(`Files scanned: ${audit.filesScanned}`);
  lines.push(`Entries parsed: ${audit.entriesScanned}`);
  lines.push(`Lessons emitted: ${lessons.length}`);
  lines.push(`Vocabulary emitted: ${vocabulary.length}`);
  lines.push(`Reject fragments: ${rejects.length}`);
  lines.push('');
  if (audit.unresolvedLevels.size) {
    lines.push('## Entries with unresolved levels');
    for (const item of audit.unresolvedLevels) {
      lines.push(`- ${item}`);
    }
    lines.push('');
  }
  if (audit.lessonDuplicateClusters.length) {
    lines.push('## Lesson duplicate clusters');
    for (const cluster of audit.lessonDuplicateClusters) {
      lines.push(`- ${cluster.key} ← ${Array.from(new Set(cluster.sources)).join(', ')}`);
    }
    lines.push('');
  }
  if (audit.vocabDuplicateClusters.length) {
    lines.push('## Vocabulary duplicate clusters');
    for (const cluster of audit.vocabDuplicateClusters) {
      lines.push(`- ${cluster.key} ← ${Array.from(new Set(cluster.sources)).join(', ')}`);
    }
    lines.push('');
  }
  if (rejects.length) {
    lines.push('## Rejects');
    for (const reject of rejects) {
      lines.push(`- ${reject.file}: ${reject.reason}`);
    }
    lines.push('');
  }
  return lines.join('\n');
}

async function writeRejects(rejects) {
  const outputs = [];
  for (let index = 0; index < rejects.length; index += 1) {
    const reject = rejects[index];
    const fileName = `${index + 1}-${slugify(reject.file || 'fragment')}.txt`;
    const filePath = path.join(buildDirs.rejects, fileName);
    const content = [`# Reject from ${reject.file || 'unknown'}`, `Reason: ${reject.reason}`, '', reject.fragment || ''].join('\n');
    await fs.writeFile(filePath, content, 'utf8');
    outputs.push(filePath);
  }
  return outputs;
}

async function validateOutput(lessons, vocabulary) {
  const [lessonSchema, vocabSchema] = await Promise.all([
    loadSchema(schemaPaths.lesson),
    loadSchema(schemaPaths.vocab)
  ]);
  const lessonErrors = [];
  for (const lesson of lessons) {
    const errors = validateWithSchema(lessonSchema, lesson, 'lesson');
    if (errors.length) {
      lessonErrors.push({ id: lesson.id, errors });
    }
  }
  const vocabErrors = [];
  for (const vocab of vocabulary) {
    const errors = validateWithSchema(vocabSchema, vocab, 'vocab');
    if (errors.length) {
      vocabErrors.push({ id: vocab.id, errors });
    }
  }
  return { lessonErrors, vocabErrors };
}

function sortLessons(lessons) {
  return lessons.slice().sort((a, b) => {
    const levelCmp = (cefrOrder[a.level] || 7) - (cefrOrder[b.level] || 7);
    if (levelCmp !== 0) return levelCmp;
    const unitCmp = (a.unit || 0) - (b.unit || 0);
    if (unitCmp !== 0) return unitCmp;
    const lessonCmp = (a.lesson_number || 0) - (b.lesson_number || 0);
    if (lessonCmp !== 0) return lessonCmp;
    return a.id.localeCompare(b.id);
  });
}

function sortVocabulary(vocabulary) {
  return vocabulary.slice().sort((a, b) => {
    const levelCmp = (cefrOrder[a.level] || 7) - (cefrOrder[b.level] || 7);
    if (levelCmp !== 0) return levelCmp;
    return a.id.localeCompare(b.id);
  });
}

async function main() {
  const audit = {
    filesScanned: 0,
    entriesScanned: 0,
    unresolvedLevels: new Set(),
    lessonDuplicateClusters: [],
    vocabDuplicateClusters: []
  };
  const firstRun = await buildOnce(audit);
  const firstLessonsSorted = sortLessons(firstRun.lessons);
  const firstVocabSorted = sortVocabulary(firstRun.vocabulary);
  const firstLessonsJson = stringifyPretty(firstLessonsSorted.map(sortKeys));
  const firstVocabJson = stringifyPretty(firstVocabSorted.map(sortKeys));
  const firstHash = computeHash(firstLessonsJson + firstVocabJson);
  const secondRun = await buildOnce({
    filesScanned: 0,
    entriesScanned: 0,
    unresolvedLevels: new Set(),
    lessonDuplicateClusters: [],
    vocabDuplicateClusters: []
  });
  const secondLessonsSorted = sortLessons(secondRun.lessons);
  const secondVocabSorted = sortVocabulary(secondRun.vocabulary);
  const secondLessonsJson = stringifyPretty(secondLessonsSorted.map(sortKeys));
  const secondVocabJson = stringifyPretty(secondVocabSorted.map(sortKeys));
  const secondHash = computeHash(secondLessonsJson + secondVocabJson);
  if (firstHash !== secondHash) {
    console.error('Idempotency check failed: consecutive rebuilds differ.');
    process.exitCode = 1;
    return;
  }
  const validation = await validateOutput(firstLessonsSorted, firstVocabSorted);
  if (validation.lessonErrors.length || validation.vocabErrors.length) {
    console.error('Schema validation failed.');
    if (validation.lessonErrors.length) {
      console.error('Lesson validation errors:', JSON.stringify(validation.lessonErrors, null, 2));
    }
    if (validation.vocabErrors.length) {
      console.error('Vocab validation errors:', JSON.stringify(validation.vocabErrors, null, 2));
    }
    process.exitCode = 1;
    return;
  }
  await ensureDirectories();
  if (options.check) {
    const lessonsPath = path.join(buildDirs.canonical, 'lessons.mmspanish.json');
    const vocabPath = path.join(buildDirs.canonical, 'vocabulary.mmspanish.json');
    let changesNeeded = false;
    try {
      const existingLessons = await fs.readFile(lessonsPath, 'utf8');
      if (!deepEqual(JSON.parse(existingLessons), JSON.parse(firstLessonsJson))) {
        changesNeeded = true;
      }
    } catch (error) {
      changesNeeded = true;
    }
    try {
      const existingVocab = await fs.readFile(vocabPath, 'utf8');
      if (!deepEqual(JSON.parse(existingVocab), JSON.parse(firstVocabJson))) {
        changesNeeded = true;
      }
    } catch (error) {
      changesNeeded = true;
    }
    if (changesNeeded) {
      console.error('Canonical files are outdated. Run npm run rebuild.');
      process.exitCode = 1;
      return;
    }
  } else {
    await fs.writeFile(path.join(buildDirs.canonical, 'lessons.mmspanish.json'), firstLessonsJson, 'utf8');
    await fs.writeFile(path.join(buildDirs.canonical, 'vocabulary.mmspanish.json'), firstVocabJson, 'utf8');
    const auditMarkdown = buildAuditMarkdown(audit, firstLessonsSorted, firstVocabSorted, firstRun.rejects);
    await fs.writeFile(path.join(buildDirs.reports, 'audit.md'), auditMarkdown + '\n', 'utf8');
    await writeRejects(firstRun.rejects);
    console.log(auditMarkdown);
  }
  const conflicts = await scanForConflictMarkers();
  if (conflicts.length) {
    console.error('Conflict markers remain in files:', conflicts);
    process.exitCode = 1;
    return;
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
