import Ajv, { JSONSchemaType } from "ajv";

export type CEFRLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2" | "UNSET";

export interface LessonStep {
  phase: "english_anchor" | "system_logic" | "meaning_depth" | "spanish_entry" | "examples";
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

export interface VocabularyExample {
  es: string;
  en: string;
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

export interface Vocabulary {
  id: string;
  spanish: string;
  pos: PartOfSpeech;
  gender?: "masculine" | "feminine" | null;
  english_gloss: string;
  definition: string;
  origin?: string;
  story?: string;
  examples: VocabularyExample[];
  level: CEFRLevel;
  tags: string[];
  source_files: string[];
  notes?: string;
}

const ajv = new Ajv({ allErrors: true, allowUnionTypes: true });

const lessonStepSchema: JSONSchemaType<LessonStep> = {
  type: "object",
  properties: {
    phase: {
      type: "string",
      enum: [
        "english_anchor",
        "system_logic",
        "meaning_depth",
        "spanish_entry",
        "examples",
      ],
    },
    line: { type: "string", nullable: true },
    origin: { type: "string", nullable: true },
    story: { type: "string", nullable: true },
    items: {
      type: "array",
      items: { type: "string" },
      nullable: true,
    },
  },
  required: ["phase"],
  additionalProperties: true,
};

export const lessonSchema: JSONSchemaType<Lesson> = {
  type: "object",
  properties: {
    id: { type: "string" },
    title: { type: "string" },
    nickname: { type: "string" },
    level: {
      type: "string",
      enum: ["A1", "A2", "B1", "B2", "C1", "C2", "UNSET"],
    },
    unit: { type: "number" },
    lesson_number: { type: "number" },
    tags: {
      type: "array",
      items: { type: "string" },
    },
    steps: {
      type: "array",
      items: lessonStepSchema,
      minItems: 1,
    },
    notes: { type: "string", nullable: true },
    source_files: {
      type: "array",
      items: { type: "string" },
      minItems: 1,
    },
  },
  required: [
    "id",
    "title",
    "nickname",
    "level",
    "unit",
    "lesson_number",
    "tags",
    "steps",
    "source_files",
  ],
  additionalProperties: true,
};

const vocabularyExampleSchema: JSONSchemaType<VocabularyExample> = {
  type: "object",
  properties: {
    es: { type: "string" },
    en: { type: "string" },
  },
  required: ["es", "en"],
  additionalProperties: false,
};

export const vocabularySchema: JSONSchemaType<Vocabulary> = {
  type: "object",
  properties: {
    id: { type: "string" },
    spanish: { type: "string" },
    pos: {
      type: "string",
      enum: ["noun", "verb", "adj", "adv", "prep", "det", "pron", "conj", "expr"],
    },
    gender: { type: "string", enum: ["masculine", "feminine"], nullable: true },
    english_gloss: { type: "string" },
    definition: { type: "string" },
    origin: { type: "string", nullable: true },
    story: { type: "string", nullable: true },
    examples: {
      type: "array",
      items: vocabularyExampleSchema,
    },
    level: {
      type: "string",
      enum: ["A1", "A2", "B1", "B2", "C1", "C2", "UNSET"],
    },
    tags: {
      type: "array",
      items: { type: "string" },
    },
    source_files: {
      type: "array",
      items: { type: "string" },
      minItems: 1,
    },
    notes: { type: "string", nullable: true },
  },
  required: [
    "id",
    "spanish",
    "pos",
    "english_gloss",
    "definition",
    "examples",
    "level",
    "tags",
    "source_files",
  ],
  additionalProperties: true,
};

export const validateLesson = ajv.compile(lessonSchema);
export const validateVocabulary = ajv.compile(vocabularySchema);
