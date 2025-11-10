# Mix Method Spanish — Vocabulary Curation Style Guide

## 1. Purpose & Scope
- Defines the shared tone, intent, and structure for every curated vocabulary entry used in Mix Method Spanish across all CEFR levels (A1–C2).
- Applies to the four editable fields for each entry: `english`, `origin`, `story`, and `example`.
- Guarantees that curators deliver neutral, accurate, and learner-appropriate copy that aligns with the game experience and downstream tooling.

## 2. Global Voice & Formatting Rules
- Keep the tone **neutral, factual, and learner-friendly**; prioritize clarity over flair.
- Do not editorialize, moralize, joke, or speculate.
- Write in **modern, natural Spanish or English** depending on the field; avoid machine-translation phrasing.
- Avoid addressing the reader directly ("you") or using imperatives unless explicitly allowed at lower levels (A1–A2 examples only).
- Do not include links, citations, slang, politics, religion, unverifiable claims, or disputed etymologies without qualifiers.
- When etymology is uncertain use: `Possibly from…` or `Origin unclear; related to…`.
- Use UTF-8 curly quotation marks when quotes are needed. Avoid straight quotes, emojis, or decorative marks.
- Sentence casing: every sentence starts with an uppercase letter and ends with a period.
- Insert exactly **one blank line between sections** in an entry draft to aid readability.
- Keep content within the length targets (see §2.1); stay concise while preserving nuance.

### 2.1 Length Targets by Level
| Field | A1–A2 | B1–B2 | C1–C2 |
|-------|-------|-------|-------|
| `origin` | 20–60 chars | 40–100 chars | 60–140 chars |
| `story` | 60–120 chars | 100–200 chars | 150–280 chars |
| `example` | ≤80 chars | ≤140 chars | ≤200 chars |

If a field falls outside its range, tighten phrasing rather than padding with filler.

## 3. Field-Specific Guidance

### 3.1 `english`
- Provide a clear, concise gloss. Separate multiple senses with semicolons ordered by frequency.
- Avoid redundant clarifiers (e.g., do not repeat "to" within a verb list).
- For expressions or phrasal verbs, keep words in teaching order and prefer standard American English wording.
- Refrain from parenthetical overload; use commas sparingly.

**Good**: `poder — to be able to; can`

**Needs Revision**: `poder — (to) be able; maybe can?`

### 3.2 `origin`
- Deliver a factual etymology, including the donor language when known.
- Identify the borrowing path if the word travelled through intermediary languages.
- Use italics for foreign lemmas: *vivere*.
- When origin is uncertain, label it without speculation.

**Good**: `From Latin *vivere* (to live).`

**Bad**: `Latin word for life idk maybe.`

### 3.3 `story`
- Offer 1–3 sentences explaining the word’s function, connotation, or common contexts.
- Focus on why the learner encounters this word or how it behaves; avoid restating the definition.
- Keep the voice level-appropriate (see §4) and avoid trivia unrelated to usage.

**Good**: `Highlights actions taken with confidence and consistency.`

**Bad**: `Fun fact: the Romans used it in poems!`

### 3.4 `example`
- Craft a realistic sentence in Spanish that matches the target CEFR level’s grammar and vocabulary.
- Avoid proper nouns beyond neutral names (Ana, Luis, María) and skip pop-culture references.
- Use natural punctuation and keep within length bounds.
- Prefer declaratives; questions or exclamations only when pedagogically justified.

**Example progression by level**:
| Level | Example |
|-------|---------|
| A1 | Tengo una casa. |
| A2 | Necesito tiempo para estudiar. |
| B1 | Ese cambio afecta el resultado. |
| B2 | Lo explicó claramente, sin exagerar. |
| C1 | Conviene analizar el problema con rigor. |
| C2 | Este concepto afina la lectura crítica del texto. |

## 4. Tone & Structure by CEFR Level
| Level | Tone & Focus | Story Notes | Example Constraints |
|-------|--------------|-------------|---------------------|
| **A1** | Warm, concrete, immediate. Stick to present-tense, everyday contexts. | Emphasize tangible uses (objects, family, routine). | Simple declaratives with common nouns and verbs. |
| **A2** | Helpful, conversational. Include basic time connectors (ayer, mañana, porque). | Mention routines, intentions, or needs. | Short compound sentences allowed; maintain high-frequency vocab. |
| **B1** | Balanced, informative. Introduce moderate abstraction or cause/effect. | Highlight contrasts or typical scenarios. | One subordinate clause permitted; keep clauses short. |
| **B2** | Confident, precise. Use transitions such as *sin embargo*, *además*. | Discuss nuance, register differences, or collocations. | Manage two clauses comfortably; avoid idiomatic overload. |
| **C1** | Formal, academic, or literary. | Explain function, nuance, or constraints in formal registers. | Complex syntax (nominalizations, passive voice) acceptable. |
| **C2** | Elegant, controlled, expert-level. | Allow metalinguistic commentary on usage. | Advanced structures welcome, but stay lucid and purposeful. |

## 5. Prohibited Content & Red Flags
- Slang, profanity, dialect prejudice, or culturally biased jokes.
- Political, religious, or speculative commentary.
- Unverifiable claims about word origins or history.
- Copying dictionary entries verbatim or using AI-generated boilerplate.
- Any sentence beginning with lowercase or lacking terminal punctuation.
- Overlong `origin` paragraphs or stories that drift beyond the defined length.

## 6. Good vs. Bad Entry Comparison

| Field | Good Entry | Why It Works | Bad Entry | Issue |
|-------|------------|--------------|-----------|-------|
| `origin` | `From Arabic *az-zayt* (“olive juice”).` | Precise source, italicized lemma, natural punctuation. | `Arabic? maybe related to oil i think` | Speculative, informal, missing capitalization. |
| `story` | `Appears in recipes to distinguish olive oil from other fats.` | Connects to real usage, neutral tone. | `People love this fancy oil in Spain lol.` | Informal, slangy, imprecise. |
| `example` | `Añade una cucharada de aceite al final.` | Level-appropriate, clear action. | `¡Añade aceite ya mismo porque te lo digo!` | Imperative without need, overly forceful tone. |

## 7. Sample Complete Entry (C1)
```json
{
  "word": "coherencia",
  "pos": "noun",
  "gender": "feminine",
  "english": "coherence; logical consistency",
  "origin": "From Latin cohaerentia (connection, unity).",
  "story": "Used in academic writing to describe logical structure and internal unity of a text or argument.",
  "example": "El ensayo destaca por su coherencia interna y claridad."
}
```

## 8. Workflow Expectations
- The guide anchors automated suggestions generated by `tools/curate.py`; review auto-filled text against every rule above.
- Run validators after applying edits to confirm schema compliance and length limits.
- Share this document with any collaborator who edits the curated fields; adherence is mandatory.

