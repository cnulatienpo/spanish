// deno-lint-ignore-file no-explicit-any
export type CEFRLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2" | "UNSET";

export const CEFR_LEVELS: CEFRLevel[] = [
  "A1",
  "A2",
  "B1",
  "B2",
  "C1",
  "C2",
  "UNSET",
];

export const CEFR_LEVEL_ORDER: Record<CEFRLevel, number> = {
  "A1": 1,
  "A2": 2,
  "B1": 3,
  "B2": 4,
  "C1": 5,
  "C2": 6,
  "UNSET": 7,
};

export type LessonPhase =
  | "english_anchor"
  | "system_logic"
  | "meaning_depth"
  | "spanish_entry"
  | "examples";

export interface LessonStep {
  phase: LessonPhase;
  line?: string;
  origin?: string;
  story?: string;
  items?: string[];
}

export interface Lesson {
  id: string;
  title: string;
  nickname: string;
  level: CEFRLevel;
  unit: number;
  lesson_number: number;
  tags: string[];
  steps: LessonStep[];
  notes?: string;
  source_files: string[];
}

export type PartOfSpeech =
  | "noun"
  | "verb"
  | "adj"
  | "adv"
  | "prep"
  | "det"
  | "pron"
  | "conj"
  | "expr";

export type GrammaticalGender = "masculine" | "feminine" | null;

export interface VocabularyExample {
  es: string;
  en: string;
}

export interface Vocabulary {
  id: string;
  spanish: string;
  pos: PartOfSpeech;
  gender: GrammaticalGender;
  english_gloss: string;
  definition: string;
  origin: string | null;
  story: string | null;
  examples: VocabularyExample[];
  level: CEFRLevel;
  tags: string[];
  source_files: string[];
  notes?: string;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function assertArray(value: unknown, message: string): asserts value is unknown[] {
  if (!Array.isArray(value)) {
    throw new Error(message);
  }
}

function assertString(value: unknown, message: string): asserts value is string {
  if (typeof value !== "string") {
    throw new Error(message);
  }
}

function assertOptionalString(
  value: unknown,
  message: string,
): asserts value is string | undefined {
  if (value === undefined) return;
  if (typeof value !== "string") {
    throw new Error(message);
  }
}

function assertCEFRLevel(value: unknown, message: string): asserts value is CEFRLevel {
  if (typeof value !== "string" || !CEFR_LEVELS.includes(value as CEFRLevel)) {
    throw new Error(message);
  }
}

function assertLessonPhase(value: unknown, message: string): asserts value is LessonPhase {
  if (
    typeof value !== "string" ||
    !["english_anchor", "system_logic", "meaning_depth", "spanish_entry", "examples"]
      .includes(value)
  ) {
    throw new Error(message);
  }
}

function assertPartOfSpeech(value: unknown, message: string): asserts value is PartOfSpeech {
  if (
    typeof value !== "string" ||
    !["noun", "verb", "adj", "adv", "prep", "det", "pron", "conj", "expr"]
      .includes(value)
  ) {
    throw new Error(message);
  }
}

function assertGender(value: unknown, message: string): asserts value is GrammaticalGender {
  if (value === null) return;
  if (value === undefined) {
    throw new Error(message);
  }
  if (value !== "masculine" && value !== "feminine") {
    throw new Error(message);
  }
}

export function assertLesson(value: unknown): asserts value is Lesson {
  if (!isObject(value)) {
    throw new Error("Lesson must be an object");
  }
  const {
    id,
    title,
    nickname,
    level,
    unit,
    lesson_number,
    tags,
    steps,
    notes,
    source_files,
  } = value;

  assertString(id, "Lesson.id must be string");
  assertString(title, "Lesson.title must be string");
  assertString(nickname, "Lesson.nickname must be string");
  assertCEFRLevel(level, "Lesson.level invalid");
  if (typeof unit !== "number") {
    throw new Error("Lesson.unit must be number");
  }
  if (typeof lesson_number !== "number") {
    throw new Error("Lesson.lesson_number must be number");
  }
  assertArray(tags, "Lesson.tags must be array");
  for (const tag of tags) {
    assertString(tag, "Lesson.tag must be string");
  }
  assertArray(steps, "Lesson.steps must be array");
  for (const step of steps) {
    if (!isObject(step)) {
      throw new Error("Lesson.step must be object");
    }
    assertLessonPhase(step.phase, "Lesson.step.phase invalid");
    assertOptionalString(step.line, "Lesson.step.line must be string");
    assertOptionalString(step.origin, "Lesson.step.origin must be string");
    assertOptionalString(step.story, "Lesson.step.story must be string");
    if (step.items !== undefined) {
      assertArray(step.items, "Lesson.step.items must be array");
      for (const item of step.items) {
        assertString(item, "Lesson.step.items[] must be string");
      }
    }
  }
  assertOptionalString(notes, "Lesson.notes must be string");
  assertArray(source_files, "Lesson.source_files must be array");
  for (const path of source_files) {
    assertString(path, "Lesson.source_files[] must be string");
  }
}

export function assertVocabulary(value: unknown): asserts value is Vocabulary {
  if (!isObject(value)) {
    throw new Error("Vocabulary must be an object");
  }
  const {
    id,
    spanish,
    pos,
    gender,
    english_gloss,
    definition,
    origin,
    story,
    examples,
    level,
    tags,
    source_files,
    notes,
  } = value;

  assertString(id, "Vocabulary.id must be string");
  assertString(spanish, "Vocabulary.spanish must be string");
  assertPartOfSpeech(pos, "Vocabulary.pos invalid");
  if (gender !== undefined) {
    if (gender !== null && gender !== "masculine" && gender !== "feminine") {
      throw new Error("Vocabulary.gender invalid");
    }
  }
  assertString(english_gloss, "Vocabulary.english_gloss must be string");
  assertString(definition, "Vocabulary.definition must be string");
  if (origin !== null && origin !== undefined) {
    assertString(origin, "Vocabulary.origin must be string or null");
  }
  if (story !== null && story !== undefined) {
    assertString(story, "Vocabulary.story must be string or null");
  }
  assertArray(examples, "Vocabulary.examples must be array");
  for (const example of examples) {
    if (!isObject(example)) {
      throw new Error("Vocabulary example must be object");
    }
    assertString(example.es, "Vocabulary example.es must be string");
    assertString(example.en, "Vocabulary example.en must be string");
  }
  assertCEFRLevel(level, "Vocabulary.level invalid");
  assertArray(tags, "Vocabulary.tags must be array");
  for (const tag of tags) {
    assertString(tag, "Vocabulary.tags[] must be string");
  }
  assertArray(source_files, "Vocabulary.source_files must be array");
  for (const source of source_files) {
    assertString(source, "Vocabulary.source_files[] must be string");
  }
  if (notes !== undefined) {
    assertString(notes, "Vocabulary.notes must be string");
  }
}

export interface PipelineError {
  file: string;
  reason: string;
  fragment?: string;
}

export type AuditAltVariant = {
  field: string;
  value: unknown;
  sources: string[];
};

export interface MergeNotes {
  alt_variant?: AuditAltVariant[];
  text?: string | string[];
}

export function mergeNotesToString(notes: MergeNotes | undefined): string | undefined {
  if (!notes) return undefined;
  const keys = Object.keys(notes);
  if (keys.length === 0) return undefined;
  return JSON.stringify(notes, Object.keys(notes).sort(), 2);
}
