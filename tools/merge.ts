// deno-lint-ignore-file no-explicit-any
import { mergeNotesToString, MergeNotes, LessonStep, VocabularyExample } from "./models.ts";
import { unionStringArrays } from "./io.ts";
import {
  NormalizedLesson,
  NormalizedVocabulary,
  SourceMeta,
} from "./normalize.ts";

interface NotePayload extends MergeNotes {
  text?: string[];
}

function cloneNotes(note: string | undefined): NotePayload {
  if (!note) return {};
  try {
    const parsed = JSON.parse(note) as NotePayload;
    if (typeof parsed === "object" && parsed) {
      const copy: NotePayload = {};
      if (Array.isArray(parsed.alt_variant)) {
        copy.alt_variant = [...parsed.alt_variant];
      }
      if (Array.isArray(parsed.text)) {
        copy.text = [...parsed.text];
      } else if (typeof parsed.text === "string") {
        copy.text = [parsed.text];
      }
      return copy;
    }
  } catch {
    // ignore
  }
  return { text: [note] };
}

function appendNoteText(target: NotePayload, note: string | undefined) {
  if (!note) return;
  if (!target.text) target.text = [];
  if (!target.text.includes(note)) {
    target.text.push(note);
  }
}

function addAltVariant(
  target: NotePayload,
  field: string,
  value: unknown,
  sources: string[],
) {
  if (!target.alt_variant) {
    target.alt_variant = [];
  }
  target.alt_variant.push({ field, value, sources });
}

function finalizeNotes(payload: NotePayload | undefined): string | undefined {
  if (!payload) return undefined;
  if (!payload.alt_variant && (!payload.text || payload.text.length === 0)) {
    return undefined;
  }
  const sortable: Record<string, unknown> = {};
  if (payload.alt_variant) sortable.alt_variant = payload.alt_variant;
  if (payload.text) {
    sortable.text = payload.text.length === 1 ? payload.text[0] : payload.text;
  }
  return mergeNotesToString(sortable as MergeNotes);
}

function mergeSourceMeta(base: SourceMeta[], next: SourceMeta[]): SourceMeta[] {
  const combined = [...base];
  for (const source of next) {
    if (!combined.some((existing) => existing.path === source.path && existing.mtimeMs === source.mtimeMs)) {
      combined.push(source);
    }
  }
  return combined;
}

function maxMtime(meta: SourceMeta[]): number {
  return meta.reduce((max, source) => Math.max(max, source.mtimeMs), 0);
}

function pathsFromMeta(meta: SourceMeta[]): string[] {
  const seen = new Set<string>();
  const paths: string[] = [];
  for (const source of meta) {
    if (!seen.has(source.path)) {
      seen.add(source.path);
      paths.push(source.path);
    }
  }
  return paths;
}

function chooseScalar(
  a: string,
  metaA: SourceMeta[],
  b: string,
  metaB: SourceMeta[],
): "a" | "b" {
  const mtimeA = maxMtime(metaA);
  const mtimeB = maxMtime(metaB);
  if (mtimeA !== mtimeB) {
    return mtimeA > mtimeB ? "a" : "b";
  }
  const lenA = a.length;
  const lenB = b.length;
  if (lenA !== lenB) {
    return lenA >= lenB ? "a" : "b";
  }
  return "a";
}

function mergeDefinitionField(a: string, b: string): string {
  if (a.trim() === b.trim()) {
    return a;
  }
  const separator = "\n\n— MERGED VARIANT —\n\n";
  if (a.includes(separator) && a.includes(b)) {
    return a;
  }
  if (b.includes(separator) && b.includes(a)) {
    return b;
  }
  return `${a}${separator}${b}`;
}

function mergeStringArrays(base: string[], next: string[]): string[] {
  return unionStringArrays(base, next);
}

function mergeExampleArrays(
  base: VocabularyExample[],
  next: VocabularyExample[],
): VocabularyExample[] {
  const existing = [...base];
  for (const example of next) {
    const normalizedEs = normalizeExample(example.es);
    const normalizedEn = normalizeExample(example.en);
    if (existing.some((ex) => normalizeExample(ex.es) === normalizedEs && normalizeExample(ex.en) === normalizedEn)) {
      continue;
    }
    existing.push(example);
  }
  return existing;
}

function normalizeExample(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLowerCase();
}

export interface MergeSummary {
  mergedLessons: NormalizedLesson[];
  mergedVocabulary: NormalizedVocabulary[];
  duplicateClusters: number;
}

export function mergeNormalized(
  lessons: NormalizedLesson[],
  vocabulary: NormalizedVocabulary[],
): MergeSummary {
  const lessonMerged = mergeLessons(lessons);
  const vocabMerged = mergeVocabulary(vocabulary);
  return {
    mergedLessons: lessonMerged.records,
    mergedVocabulary: vocabMerged.records,
    duplicateClusters: lessonMerged.duplicates + vocabMerged.duplicates,
  };
}

function mergeLessons(records: NormalizedLesson[]): { records: NormalizedLesson[]; duplicates: number } {
  const grouped = new Map<string, NormalizedLesson[]>();
  for (const record of records) {
    const key = lessonKey(record.data);
    const group = grouped.get(key) ?? [];
    group.push(record);
    grouped.set(key, group);
  }
  const merged: NormalizedLesson[] = [];
  let duplicates = 0;
  for (const group of grouped.values()) {
    if (group.length === 1) {
      merged.push(group[0]);
      continue;
    }
    duplicates += 1;
    const combined = mergeLessonGroup(group);
    merged.push(combined);
  }
  return { records: merged, duplicates };
}

function lessonKey(lesson: NormalizedLesson["data"]): string {
  const unit = lesson.unit ?? 9999;
  const lessonNumber = lesson.lesson_number ?? 9999;
  if (lesson.title && Number.isFinite(unit) && Number.isFinite(lessonNumber)) {
    return `${lesson.title}|${unit}|${lessonNumber}`;
  }
  return `${lesson.title}|${lesson.nickname}`;
}

function mergeLessonGroup(group: NormalizedLesson[]): NormalizedLesson {
  const [first, ...rest] = group;
  const mergedData = structuredClone(first.data);
  let metaSources = [...first.meta.sources];
  let notesPayload = cloneNotes(first.data.notes);

  for (const item of rest) {
    const previousMeta = metaSources;
    metaSources = mergeSourceMeta(metaSources, item.meta.sources);
    mergedData.source_files = unionStringArrays(mergedData.source_files, item.data.source_files);
    mergedData.tags = mergeStringArrays(mergedData.tags, item.data.tags);
    mergedData.steps = mergeLessonSteps(mergedData.steps, item.data.steps);

    if (item.data.notes) {
      appendNoteText(notesPayload, item.data.notes);
    }

    const scalarFields: Array<keyof NormalizedLesson["data"]> = [
      "title",
      "nickname",
    ];
    for (const field of scalarFields) {
      const current = mergedData[field];
      const incoming = item.data[field];
      if (typeof current === "string" && typeof incoming === "string" && current !== incoming) {
        const winner = chooseScalar(current, previousMeta, incoming, item.meta.sources);
        if (winner === "b") {
          addAltVariant(notesPayload, field, current, pathsFromMeta(previousMeta));
          (mergedData as any)[field] = incoming;
        } else {
          addAltVariant(notesPayload, field, incoming, item.data.source_files);
        }
      }
    }

    mergedData.level = resolveLevel(
      mergedData.level,
      pathsFromMeta(previousMeta),
      item.data.level,
      item.data.source_files,
      notesPayload,
      previousMeta,
      item.meta.sources,
    );
    mergedData.unit = Math.min(mergedData.unit ?? 9999, item.data.unit ?? 9999);
    mergedData.lesson_number = Math.min(mergedData.lesson_number ?? 9999, item.data.lesson_number ?? 9999);
  }

  mergedData.notes = finalizeNotes(notesPayload);

  return { data: mergedData, meta: { sources: metaSources } };
}

function mergeLessonSteps(base: LessonStep[], next: LessonStep[]): LessonStep[] {
  const existing = [...base];
  for (const step of next) {
    const key = JSON.stringify(sortObject(step));
    if (existing.some((current) => JSON.stringify(sortObject(current)) === key)) {
      continue;
    }
    existing.push(step);
  }
  return existing;
}

function sortObject(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sortObject(item));
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    entries.sort(([a], [b]) => a.localeCompare(b));
    const sorted: Record<string, unknown> = {};
    for (const [key, val] of entries) {
      sorted[key] = sortObject(val);
    }
    return sorted;
  }
  return value;
}

function resolveLevel(
  currentLevel: string,
  currentSources: string[],
  incomingLevel: string,
  incomingSources: string[],
  notes: NotePayload,
  metaCurrent: SourceMeta[],
  metaIncoming: SourceMeta[],
): string {
  if (currentLevel === incomingLevel) return currentLevel;
  if (incomingLevel === "UNSET") {
    addAltVariant(notes, "level", incomingLevel, incomingSources);
    return currentLevel;
  }
  if (currentLevel === "UNSET") {
    addAltVariant(notes, "level", currentLevel, currentSources);
    return incomingLevel;
  }
  const winner = chooseScalar(currentLevel, metaCurrent, incomingLevel, metaIncoming);
  if (winner === "b") {
    addAltVariant(notes, "level", currentLevel, currentSources);
    return incomingLevel;
  }
  addAltVariant(notes, "level", incomingLevel, incomingSources);
  return currentLevel;
}

function mergeVocabulary(records: NormalizedVocabulary[]): { records: NormalizedVocabulary[]; duplicates: number } {
  const grouped = new Map<string, NormalizedVocabulary[]>();
  for (const record of records) {
    const key = vocabKey(record.data);
    const bucket = grouped.get(key) ?? [];
    bucket.push(record);
    grouped.set(key, bucket);
  }
  const merged: NormalizedVocabulary[] = [];
  let duplicates = 0;
  for (const group of grouped.values()) {
    if (group.length === 1) {
      merged.push(group[0]);
      continue;
    }
    duplicates += 1;
    merged.push(mergeVocabularyGroup(group));
  }
  return { records: merged, duplicates };
}

function vocabKey(vocab: NormalizedVocabulary["data"]): string {
  return `${vocab.spanish.toLowerCase()}|${vocab.pos}|${vocab.gender ?? "null"}`;
}

function mergeVocabularyGroup(group: NormalizedVocabulary[]): NormalizedVocabulary {
  const [first, ...rest] = group;
  const mergedData = structuredClone(first.data);
  let metaSources = [...first.meta.sources];
  let notesPayload = cloneNotes(first.data.notes);

  for (const item of rest) {
    const previousMeta = metaSources;
    metaSources = mergeSourceMeta(metaSources, item.meta.sources);
    mergedData.source_files = unionStringArrays(mergedData.source_files, item.data.source_files);
    mergedData.tags = mergeStringArrays(mergedData.tags, item.data.tags);
    mergedData.examples = mergeExampleArrays(mergedData.examples, item.data.examples);

    if (item.data.notes) {
      appendNoteText(notesPayload, item.data.notes);
    }

    const scalarFields: Array<keyof NormalizedVocabulary["data"]> = [
      "spanish",
      "english_gloss",
      "definition",
      "origin",
      "story",
    ];

    for (const field of scalarFields) {
      const currentValue = mergedData[field];
      const incomingValue = item.data[field];
      if (typeof currentValue === "string" && typeof incomingValue === "string" && currentValue !== incomingValue) {
        if (field === "definition" || field === "origin" || field === "story") {
          mergedData[field] = mergeDefinitionField(currentValue, incomingValue) as any;
          continue;
        }
        const winner = chooseScalar(currentValue, previousMeta, incomingValue, item.meta.sources);
        if (winner === "b") {
          addAltVariant(notesPayload, field, currentValue, pathsFromMeta(previousMeta));
          (mergedData as any)[field] = incomingValue;
        } else {
          addAltVariant(notesPayload, field, incomingValue, item.data.source_files);
        }
      } else if (currentValue === null && typeof incomingValue === "string") {
        (mergedData as any)[field] = incomingValue;
      } else if (typeof currentValue === "string" && incomingValue === null) {
        // keep current, track alt variant
        addAltVariant(notesPayload, field, incomingValue, item.data.source_files);
      }
    }

    if (mergedData.gender === null && item.data.gender) {
      mergedData.gender = item.data.gender;
    }

    mergedData.level = resolveLevel(
      mergedData.level,
      pathsFromMeta(previousMeta),
      item.data.level,
      item.data.source_files,
      notesPayload,
      previousMeta,
      item.meta.sources,
    );
  }

  mergedData.notes = finalizeNotes(notesPayload);

  return { data: mergedData, meta: { sources: metaSources } };
}
