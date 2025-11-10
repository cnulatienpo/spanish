// deno-lint-ignore-file no-explicit-any
import { healConflictMarkers } from "./conflicts.ts";
import {
  CEFR_LEVELS,
  CEFR_LEVEL_ORDER,
  CEFRLevel,
  Lesson,
  LessonStep,
  Vocabulary,
  PartOfSpeech,
  GrammaticalGender,
} from "./models.ts";
import { ContentFileInfo, RejectRecord, digestHex } from "./io.ts";

export interface SourceMeta {
  path: string;
  mtimeMs: number;
}

export interface NormalizedRecord<T> {
  data: T;
  meta: { sources: SourceMeta[] };
}

export type NormalizedLesson = NormalizedRecord<Lesson>;
export type NormalizedVocabulary = NormalizedRecord<Vocabulary>;

export interface NormalizeResult {
  lessons: NormalizedLesson[];
  vocabulary: NormalizedVocabulary[];
  rejects: RejectRecord[];
  fragments: number;
  conflicts: number;
}

const POS_VALUES: PartOfSpeech[] = [
  "noun",
  "verb",
  "adj",
  "adv",
  "prep",
  "det",
  "pron",
  "conj",
  "expr",
];

export async function normalizeContentFile(
  file: ContentFileInfo,
  relativePath: string,
): Promise<NormalizeResult> {
  const rejects: RejectRecord[] = [];
  const lessons: NormalizedLesson[] = [];
  const vocabulary: NormalizedVocabulary[] = [];

  const { healedText, conflicts } = healConflictMarkers(file.text);
  const fragments = extractJsonFragments(healedText);

  if (fragments.length === 0 && healedText.trim().length > 0) {
    fragments.push(healedText);
  }

  let parsedFragments = 0;

  for (const fragment of fragments) {
    const trimmed = fragment.trim();
    if (!trimmed) {
      continue;
    }
    const parseResult = tryParseJson(trimmed);
    if (!parseResult.ok) {
      rejects.push({
        file: relativePath,
        reason: `Failed to parse fragment: ${parseResult.error}`,
        content: trimmed.slice(0, 1000),
      });
      continue;
    }
    parsedFragments += 1;

    const values = Array.isArray(parseResult.value)
      ? (parseResult.value as unknown[])
      : [parseResult.value];

    for (const raw of values) {
      if (!raw || typeof raw !== "object") {
        continue;
      }
      const object = raw as Record<string, unknown>;
      const normalizedSource = [{ path: relativePath, mtimeMs: file.mtimeMs }];
      const context = { file: relativePath, source: normalizedSource };

      const asLesson = await normalizeLesson(object, context);
      if (asLesson) {
        lessons.push({ data: asLesson, meta: { sources: normalizedSource } });
      }

      const asVocab = await normalizeVocabulary(object, context);
      if (asVocab) {
        vocabulary.push({ data: asVocab, meta: { sources: normalizedSource } });
      }

      if (!asLesson && !asVocab) {
        rejects.push({
          file: relativePath,
          reason: "Unrecognized object shape",
          content: JSON.stringify(object).slice(0, 1000),
        });
      }
    }
  }

  return {
    lessons,
    vocabulary,
    rejects,
    fragments: parsedFragments,
    conflicts: conflicts.length,
  };
}

function extractJsonFragments(text: string): string[] {
  const fragments: string[] = [];
  const stack: { start: number; type: string }[] = [];
  let inString = false;
  let stringChar = '"';
  let escape = false;
  let segmentStart = -1;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inString) {
      if (escape) {
        escape = false;
        continue;
      }
      if (ch === "\\") {
        escape = true;
        continue;
      }
      if (ch === stringChar) {
        inString = false;
      }
      continue;
    }

    if (ch === '"' || ch === "'") {
      inString = true;
      stringChar = ch;
      continue;
    }

    if (ch === "{" || ch === "[") {
      stack.push({ start: i, type: ch });
      if (stack.length === 1) {
        segmentStart = i;
      }
      continue;
    }

    if (ch === "}" || ch === "]") {
      if (stack.length === 0) {
        continue;
      }
      const last = stack.pop();
      if (!last) continue;
      if ((ch === "}" && last.type !== "{") || (ch === "]" && last.type !== "[")) {
        continue;
      }
      if (stack.length === 0 && segmentStart !== -1) {
        const fragment = text.slice(segmentStart, i + 1);
        fragments.push(fragment);
        segmentStart = -1;
      }
    }
  }

  if (fragments.length === 0) {
    const maybeJsonLines = text.split(/\n+/)
      .map((line) => line.trim())
      .filter((line) => line.startsWith("{") || line.startsWith("["));
    if (maybeJsonLines.length > 1) {
      return maybeJsonLines;
    }
  }

  return fragments;
}

interface ParseSuccess {
  ok: true;
  value: any;
}

interface ParseFailure {
  ok: false;
  error: string;
}

type ParseResult = ParseSuccess | ParseFailure;

function tryParseJson(fragment: string): ParseResult {
  const attempts = [fragment, repairJson(fragment)];
  for (const attempt of attempts) {
    if (!attempt) continue;
    try {
      return { ok: true, value: JSON.parse(attempt) };
    } catch (error) {
      if (attempt === attempts[attempts.length - 1]) {
        return { ok: false, error: (error as Error).message };
      }
    }
  }
  return { ok: false, error: "Unknown parse failure" };
}

function repairJson(input: string): string {
  let text = input.trim();
  if (!text) return text;
  text = text.replace(/([,{\[]\s*)([A-Za-z0-9_]+)\s*:/g, '$1"$2":');
  text = text.replace(/'([^'\\]*(?:\\.[^'\\]*)*)'/g, (_, group) => `"${group.replace(/"/g, '\\"')}"`);
  text = text.replace(/,\s*([}\]])/g, '$1');

  const openCurly = (text.match(/\{/g) || []).length;
  const closeCurly = (text.match(/\}/g) || []).length;
  const openSquare = (text.match(/\[/g) || []).length;
  const closeSquare = (text.match(/\]/g) || []).length;

  if (openCurly > closeCurly) {
    text = text + "}".repeat(openCurly - closeCurly);
  }
  if (openSquare > closeSquare) {
    text = text + "]".repeat(openSquare - closeSquare);
  }

  return text;
}

interface LessonContext {
  file: string;
  source: SourceMeta[];
}

async function normalizeLesson(
  candidate: Record<string, unknown>,
  context: LessonContext,
): Promise<Lesson | undefined> {
  if (!hasLessonShape(candidate)) {
    return undefined;
  }

  const title = pickString(candidate.title) ?? pickString(candidate["lesson_title"]);
  if (!title) {
    return undefined;
  }

  const nicknameRaw = pickString(candidate.nickname) || slugify(title);
  const unitValue = toNumber(candidate.unit, 9999);
  const lessonNumber = toNumber(candidate.lesson_number, 9999);
  const levelRaw = pickString(candidate.level);
  const inferredLevel = inferLevel(levelRaw, context.file);

  const tags = toStringArray(candidate.tags);
  const stepsArray = Array.isArray(candidate.steps)
    ? candidate.steps
    : Array.isArray(candidate["lesson_steps"]) ? candidate["lesson_steps"] : [];

  const normalizedSteps: LessonStep[] = [];
  for (const rawStep of stepsArray as unknown[]) {
    if (!rawStep || typeof rawStep !== "object") continue;
    const stepObj = rawStep as Record<string, unknown>;
    const phase = pickLessonPhase(stepObj.phase) || pickLessonPhase(stepObj.type);
    if (!phase) continue;
    const line = pickString(stepObj.line);
    const origin = pickString(stepObj.origin);
    const story = pickString(stepObj.story);
    const items = toStringArray(stepObj.items);
    normalizedSteps.push({ phase, line, origin, story, items: items.length ? items : undefined });
  }

  if (normalizedSteps.length === 0) {
    return undefined;
  }

  const notes = pickString(candidate.notes);
  const level = inferredLevel;
  const nickname = nicknameRaw || slugify(title);
  const id = generateLessonId(unitValue, title);

  const lesson: Lesson = {
    id,
    title,
    nickname,
    level,
    unit: unitValue,
    lesson_number: lessonNumber,
    tags,
    steps: normalizedSteps,
    notes: notes || undefined,
    source_files: uniqueSources(context.source),
  };

  return lesson;
}

function hasLessonShape(candidate: Record<string, unknown>): boolean {
  return Boolean(
    candidate.title ||
      candidate["lesson_title"] ||
      candidate.steps ||
      candidate["lesson_steps"],
  );
}

interface VocabularyContext {
  file: string;
  source: SourceMeta[];
}

async function normalizeVocabulary(
  candidate: Record<string, unknown>,
  context: VocabularyContext,
): Promise<Vocabulary | undefined> {
  if (!hasVocabShape(candidate)) {
    return undefined;
  }

  const spanishRaw = pickString(candidate.spanish) || pickString(candidate["word"]);
  const englishRaw = pickString(candidate.english_gloss) || pickString(candidate["english"]);
  const definitionRaw = pickString(candidate.definition) || pickString(candidate["meaning"]);

  if (!spanishRaw || !englishRaw || !definitionRaw) {
    return undefined;
  }

  const posRaw = pickString(candidate.pos) || pickString(candidate.part_of_speech) || "expr";
  const pos = normalizePos(posRaw);
  const gender = normalizeGender(candidate.gender, pos);
  const origin = pickNullableString(candidate.origin);
  const story = pickNullableString(candidate.story);
  const examplesRaw = candidate.examples || candidate["example"] || candidate["sentences"];
  const examples = normalizeExamples(examplesRaw);
  const levelRaw = pickString(candidate.level);
  const level = inferLevel(levelRaw, context.file);
  const tags = toStringArray(candidate.tags);

  const id = await generateVocabId(spanishRaw, pos, gender);

  const vocab: Vocabulary = {
    id,
    spanish: spanishRaw.trim(),
    pos,
    gender,
    english_gloss: englishRaw.trim(),
    definition: definitionRaw.trim(),
    origin: origin ?? null,
    story: story ?? null,
    examples,
    level,
    tags,
    source_files: uniqueSources(context.source),
  };

  if (candidate.notes) {
    const note = pickString(candidate.notes);
    if (note) {
      vocab.notes = note;
    }
  }

  return vocab;
}

function hasVocabShape(candidate: Record<string, unknown>): boolean {
  return Boolean(candidate.spanish || candidate["word"]);
}

function pickString(value: unknown): string | undefined {
  if (typeof value === "string" && value.trim().length > 0) {
    return value.trim();
  }
  return undefined;
}

function pickNullableString(value: unknown): string | null | undefined {
  if (value === null) return null;
  return pickString(value);
}

function toNumber(value: unknown, fallback: number): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number.parseInt(value, 10);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function toStringArray(value: unknown): string[] {
  if (!value) return [];
  if (Array.isArray(value)) {
    const result: string[] = [];
    for (const item of value) {
      const str = pickString(item);
      if (str) result.push(str);
    }
    return result;
  }
  const single = pickString(value);
  return single ? [single] : [];
}

function pickLessonPhase(value: unknown): LessonStep["phase"] | undefined {
  if (typeof value !== "string") return undefined;
  const normalized = value.trim().toLowerCase();
  switch (normalized) {
    case "english_anchor":
    case "english":
      return "english_anchor";
    case "system_logic":
    case "logic":
      return "system_logic";
    case "meaning_depth":
    case "meaning":
      return "meaning_depth";
    case "spanish_entry":
    case "spanish":
      return "spanish_entry";
    case "examples":
      return "examples";
    default:
      return undefined;
  }
}

function inferLevel(levelRaw: string | undefined, path: string): CEFRLevel {
  if (levelRaw && CEFR_LEVELS.includes(levelRaw as CEFRLevel)) {
    return levelRaw as CEFRLevel;
  }
  const match = path.match(/(?:^|\W)(A1|A2|B1|B2|C1|C2)(?:\W|$)/i);
  if (match) {
    const level = match[1].toUpperCase() as CEFRLevel;
    if (CEFR_LEVELS.includes(level)) {
      return level;
    }
  }
  return "UNSET";
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 48) || "lesson";
}

function generateLessonId(unit: number, title: string): string {
  const unitSegment = unit.toString().padStart(3, "0");
  const slug = slugify(title);
  return `mmspanish__grammar_${unitSegment}_${slug}`;
}

async function generateVocabId(
  spanish: string,
  pos: PartOfSpeech,
  gender: GrammaticalGender,
): Promise<string> {
  const key = `${spanish.trim().toLowerCase()}|${pos}|${gender ?? "null"}`;
  const hash = await digestHex(key);
  return `mmspanish__vocab_${hash}`;
}

function normalizePos(value: string): PartOfSpeech {
  const normalized = value.trim().toLowerCase();
  if (POS_VALUES.includes(normalized as PartOfSpeech)) {
    return normalized as PartOfSpeech;
  }
  if (["nm", "nf", "noun"].includes(normalized)) return "noun";
  if (["v", "verb"].includes(normalized)) return "verb";
  if (["adj", "adjective"].includes(normalized)) return "adj";
  if (["adv", "adverb"].includes(normalized)) return "adv";
  if (["prep", "preposition"].includes(normalized)) return "prep";
  if (["det", "determiner"].includes(normalized)) return "det";
  if (["pron", "pronoun"].includes(normalized)) return "pron";
  if (["conj", "conjunction"].includes(normalized)) return "conj";
  return "expr";
}

function normalizeGender(value: unknown, pos: PartOfSpeech): GrammaticalGender {
  if (pos !== "noun") return null;
  if (value === null || value === undefined) return null;
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (normalized.startsWith("m")) return "masculine";
    if (normalized.startsWith("f")) return "feminine";
  }
  return null;
}

function normalizeExamples(raw: unknown): Vocabulary["examples"] {
  if (!raw) return [];
  const result: Vocabulary["examples"] = [];
  const addExample = (es: string, en: string) => {
    const cleanEs = es.trim();
    const cleanEn = en.trim();
    if (!cleanEs || !cleanEn) return;
    if (result.some((ex) => normalizeExampleText(ex.es) === normalizeExampleText(cleanEs) &&
      normalizeExampleText(ex.en) === normalizeExampleText(cleanEn))) {
      return;
    }
    result.push({ es: cleanEs, en: cleanEn });
  };

  if (Array.isArray(raw)) {
    for (const item of raw) {
      if (!item) continue;
      if (typeof item === "string") {
        addExample(item, item);
      } else if (typeof item === "object") {
        const obj = item as Record<string, unknown>;
        const es = pickString(obj.es) || pickString(obj["spanish"]);
        const en = pickString(obj.en) || pickString(obj["english"]);
        if (es && en) addExample(es, en);
      }
    }
    return result;
  }

  if (typeof raw === "object") {
    const obj = raw as Record<string, unknown>;
    const es = pickString(obj.es) || pickString(obj["spanish"]);
    const en = pickString(obj.en) || pickString(obj["english"]);
    if (es && en) addExample(es, en);
    return result;
  }

  if (typeof raw === "string") {
    addExample(raw, raw);
    return result;
  }

  return result;
}

function normalizeExampleText(text: string): string {
  return text.replace(/\s+/g, " ").trim().toLowerCase();
}

function uniqueSources(sources: SourceMeta[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const source of sources) {
    if (!seen.has(source.path)) {
      seen.add(source.path);
      result.push(source.path);
    }
  }
  return result;
}

export function cefrSorter<T extends { level: CEFRLevel; unit?: number; lesson_number?: number; id: string }>(a: T, b: T): number {
  const levelA = CEFR_LEVEL_ORDER[a.level] ?? CEFR_LEVEL_ORDER["UNSET"];
  const levelB = CEFR_LEVEL_ORDER[b.level] ?? CEFR_LEVEL_ORDER["UNSET"];
  if (levelA !== levelB) return levelA - levelB;
  const unitA = a.unit ?? 9999;
  const unitB = b.unit ?? 9999;
  if (unitA !== unitB) return unitA - unitB;
  const lessonA = a.lesson_number ?? 9999;
  const lessonB = b.lesson_number ?? 9999;
  if (lessonA !== lessonB) return lessonA - lessonB;
  return a.id.localeCompare(b.id);
}
