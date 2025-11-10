use std::collections::BTreeSet;
use std::path::Path;

use anyhow::{anyhow, Result};
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use once_cell::sync::Lazy;
use regex::Regex;
use serde_json::{Map, Value};
use slug::slugify;

use crate::models::{ExamplePair, Lesson, LessonStep, LessonStepExamples, Level, Vocabulary};

static LEVEL_HINT_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"(?i)(a1|a2|b1|b2|c1|c2)").expect("level regex"));

#[derive(Debug, Default)]
pub struct NormalizedOutput {
    pub lessons: Vec<Lesson>,
    pub vocabulary: Vec<Vocabulary>,
    pub rejects: Vec<String>,
    pub invalid: Vec<String>,
}

pub fn parse_and_normalize(path: &Path, content: &str) -> NormalizedOutput {
    let mut output = NormalizedOutput::default();
    let fragments = collect_fragments(content);
    for fragment in fragments {
        match fragment {
            Ok(value) => match classify_and_build(path, value) {
                Ok(mut classified) => {
                    output.lessons.append(&mut classified.lessons);
                    output.vocabulary.append(&mut classified.vocabulary);
                    output.rejects.append(&mut classified.rejects);
                    output.invalid.append(&mut classified.invalid);
                }
                Err(err) => {
                    output.invalid.push(format!("{}: {}", path.display(), err));
                }
            },
            Err(raw) => {
                output.rejects.push(format!("{}", raw));
            }
        }
    }
    output
}

fn collect_fragments(content: &str) -> Vec<Result<Value, String>> {
    let mut fragments = Vec::new();
    if let Some(value) = try_full_parse(content) {
        fragments.push(Ok(value));
        return fragments;
    }

    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        if let Some(value) = try_full_parse(trimmed) {
            fragments.push(Ok(value));
        } else {
            fragments.push(Err(trimmed.to_string()));
        }
    }

    fragments
}

fn try_full_parse(input: &str) -> Option<Value> {
    if input.trim().is_empty() {
        return None;
    }
    if let Ok(value) = serde_json::from_str::<Value>(input) {
        return Some(value);
    }
    if let Ok(value) = json5::from_str::<Value>(input) {
        return Some(value);
    }
    None
}

#[derive(Debug, Default)]
struct Classified {
    lessons: Vec<Lesson>,
    vocabulary: Vec<Vocabulary>,
    rejects: Vec<String>,
    invalid: Vec<String>,
}

fn classify_and_build(path: &Path, value: Value) -> Result<Classified> {
    let mut classified = Classified::default();
    match value {
        Value::Array(items) => {
            for item in items {
                let nested = classify_and_build(path, item)?;
                merge_classified(&mut classified, nested);
            }
        }
        Value::Object(mut map) => {
            canonicalize_keys(&mut map);
            if looks_like_lesson(&map) && looks_like_vocab(&map) {
                let lesson_map = map.clone();
                let vocab_map = map;
                match build_lesson(path, lesson_map) {
                    Ok(lesson) => classified.lessons.push(lesson),
                    Err(err) => classified
                        .invalid
                        .push(format!("{}: {}", path.display(), err)),
                }
                match build_vocab(path, vocab_map) {
                    Ok(vocab) => classified.vocabulary.push(vocab),
                    Err(err) => classified
                        .invalid
                        .push(format!("{}: {}", path.display(), err)),
                }
            } else if looks_like_lesson(&map) {
                match build_lesson(path, map) {
                    Ok(lesson) => classified.lessons.push(lesson),
                    Err(err) => classified
                        .invalid
                        .push(format!("{}: {}", path.display(), err)),
                }
            } else if looks_like_vocab(&map) {
                match build_vocab(path, map) {
                    Ok(vocab) => classified.vocabulary.push(vocab),
                    Err(err) => classified
                        .invalid
                        .push(format!("{}: {}", path.display(), err)),
                }
            } else {
                classified
                    .rejects
                    .push(serde_json::to_string_pretty(&Value::Object(map))?);
            }
        }
        other => {
            classified
                .rejects
                .push(serde_json::to_string_pretty(&other)?);
        }
    }
    Ok(classified)
}

fn merge_classified(target: &mut Classified, mut other: Classified) {
    target.lessons.append(&mut other.lessons);
    target.vocabulary.append(&mut other.vocabulary);
    target.rejects.append(&mut other.rejects);
    target.invalid.append(&mut other.invalid);
}

fn canonicalize_keys(map: &mut Map<String, Value>) {
    let mut renames: Vec<(String, String)> = Vec::new();
    for key in map.keys() {
        let lower = key.to_lowercase();
        let normalized = match lower.as_str() {
            "nikname" | "nick_name" | "lesson_nickname" => Some("nickname".to_string()),
            "lessonnum" | "lesson_no" | "lessonnumber" => Some("lesson_number".to_string()),
            "unitnum" | "unit_no" | "unitnumber" => Some("unit".to_string()),
            "english" | "englishgloss" | "english_glossary" => Some("english_gloss".to_string()),
            "def" | "definition_en" => Some("definition".to_string()),
            "origin_story" => Some("story".to_string()),
            "pos_tag" => Some("pos".to_string()),
            "tags_csv" => Some("tags".to_string()),
            _ => None,
        };
        if let Some(new_key) = normalized {
            renames.push((key.clone(), new_key));
        }
    }
    for (old, new) in renames {
        if let Some(value) = map.remove(&old) {
            map.insert(new, value);
        }
    }
}

fn looks_like_lesson(map: &Map<String, Value>) -> bool {
    map.get("title").is_some() && (map.get("steps").is_some() || map.get("phases").is_some())
}

fn looks_like_vocab(map: &Map<String, Value>) -> bool {
    map.get("spanish").is_some() && map.get("english_gloss").is_some()
}

fn build_lesson(path: &Path, mut map: Map<String, Value>) -> Result<Lesson> {
    let source = path_to_string(path);
    let title = map
        .remove("title")
        .and_then(|v| v.as_str().map(|s| s.to_string()))
        .ok_or_else(|| anyhow!("lesson title missing"))?;
    let nickname = map
        .remove("nickname")
        .and_then(|v| v.as_str().map(|s| s.to_string()))
        .filter(|s| !s.trim().is_empty())
        .unwrap_or_else(|| slugify(&title));
    let level_value = map.remove("level");
    let level = normalize_level(path, level_value.as_ref());
    let unit = map
        .remove("unit")
        .and_then(|v| v.as_i64())
        .map(|n| n as u32)
        .unwrap_or(9999);
    let lesson_number = map
        .remove("lesson_number")
        .and_then(|v| v.as_i64())
        .map(|n| n as u32)
        .unwrap_or(9999);
    let tags = normalize_tags(map.remove("tags"));
    let steps_value = map
        .remove("steps")
        .or_else(|| map.remove("phases"))
        .ok_or_else(|| anyhow!("lesson steps missing"))?;
    let steps = normalize_steps(steps_value)?;
    let mut notes = map
        .remove("notes")
        .and_then(|v| v.as_str().map(|s| s.to_string()));

    let mut lesson = Lesson {
        id: map
            .remove("id")
            .and_then(|v| v.as_str().map(|s| s.to_string()))
            .unwrap_or_else(|| format!("mmspanish__grammar_{:03}_{}", unit, slugify(&title))),
        title,
        nickname,
        level,
        unit,
        lesson_number,
        tags,
        steps,
        notes: None,
        source_files: vec![source],
    };
    lesson.notes = notes.or_else(|| {
        map.remove("alt_notes")
            .and_then(|v| v.as_str().map(|s| s.to_string()))
    });
    Ok(lesson)
}

fn normalize_steps(value: Value) -> Result<Vec<LessonStep>> {
    match value {
        Value::Array(items) => {
            let mut steps = Vec::new();
            for item in items {
                steps.push(parse_step(item)?);
            }
            Ok(steps)
        }
        other => Err(anyhow!("unexpected steps format: {}", other)),
    }
}

fn parse_step(value: Value) -> Result<LessonStep> {
    match value {
        Value::Object(mut map) => {
            let phase = map
                .remove("phase")
                .and_then(|v| v.as_str().map(|s| s.to_string()))
                .unwrap_or_else(|| "english_anchor".to_string());
            match phase.as_str() {
                "english_anchor" => Ok(LessonStep::EnglishAnchor {
                    line: map
                        .remove("line")
                        .and_then(|v| v.as_str().map(|s| s.to_string()))
                        .ok_or_else(|| anyhow!("english_anchor requires line"))?,
                }),
                "system_logic" => Ok(LessonStep::SystemLogic {
                    line: map
                        .remove("line")
                        .and_then(|v| v.as_str().map(|s| s.to_string()))
                        .ok_or_else(|| anyhow!("system_logic requires line"))?,
                }),
                "meaning_depth" => Ok(LessonStep::MeaningDepth {
                    origin: map
                        .remove("origin")
                        .and_then(|v| v.as_str().map(|s| s.to_string())),
                    story: map
                        .remove("story")
                        .and_then(|v| v.as_str().map(|s| s.to_string())),
                }),
                "spanish_entry" => Ok(LessonStep::SpanishEntry {
                    line: map
                        .remove("line")
                        .and_then(|v| v.as_str().map(|s| s.to_string()))
                        .ok_or_else(|| anyhow!("spanish_entry requires line"))?,
                }),
                "examples" => {
                    let items_value = map.remove("items").unwrap_or(Value::Array(Vec::new()));
                    let items = match items_value {
                        Value::Array(v) => v
                            .into_iter()
                            .filter_map(|item| item.as_str().map(|s| s.to_string()))
                            .collect::<Vec<_>>(),
                        Value::String(s) => vec![s],
                        other => {
                            return Err(anyhow!("examples items invalid: {}", other));
                        }
                    };
                    Ok(LessonStep::Examples(LessonStepExamples { items }))
                }
                _ => Ok(LessonStep::EnglishAnchor {
                    line: map
                        .remove("line")
                        .and_then(|v| v.as_str().map(|s| s.to_string()))
                        .unwrap_or_default(),
                }),
            }
        }
        Value::String(line) => Ok(LessonStep::EnglishAnchor { line }),
        other => Err(anyhow!("unexpected lesson step: {}", other)),
    }
}

fn build_vocab(path: &Path, mut map: Map<String, Value>) -> Result<Vocabulary> {
    let source = path_to_string(path);
    let spanish = map
        .remove("spanish")
        .and_then(|v| v.as_str().map(|s| s.trim().to_string()))
        .ok_or_else(|| anyhow!("spanish missing"))?;
    let pos = map
        .remove("pos")
        .and_then(|v| v.as_str().map(|s| s.trim().to_string()))
        .ok_or_else(|| anyhow!("pos missing"))?;
    let gender = map
        .remove("gender")
        .and_then(|v| v.as_str().and_then(|s| normalize_gender(s)));
    let english_gloss = map
        .remove("english_gloss")
        .and_then(|v| v.as_str().map(|s| s.to_string()))
        .ok_or_else(|| anyhow!("english_gloss missing"))?;
    let definition = map
        .remove("definition")
        .and_then(|v| v.as_str().map(|s| s.to_string()))
        .ok_or_else(|| anyhow!("definition missing"))?;
    let origin = map
        .remove("origin")
        .and_then(|v| v.as_str().map(|s| s.to_string()));
    let story = map
        .remove("story")
        .and_then(|v| v.as_str().map(|s| s.to_string()));
    let examples = normalize_examples(map.remove("examples"))?;
    let level_value = map.remove("level");
    let level = normalize_level(path, level_value.as_ref());
    let tags = normalize_tags(map.remove("tags"));
    let notes = map
        .remove("notes")
        .and_then(|v| v.as_str().map(|s| s.to_string()));

    let key = format!(
        "{}|{}|{}",
        spanish.to_lowercase(),
        pos.to_lowercase(),
        gender.clone().unwrap_or_else(|| "null".to_string())
    );
    let hash = blake3::hash(key.as_bytes());
    let id = map
        .remove("id")
        .and_then(|v| v.as_str().map(|s| s.to_string()))
        .unwrap_or_else(|| {
            format!(
                "mmspanish__vocab_{}",
                URL_SAFE_NO_PAD.encode(hash.as_bytes())
            )
        });

    Ok(Vocabulary {
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
        source_files: vec![source],
        notes,
    })
}

fn normalize_examples(value: Option<Value>) -> Result<Vec<ExamplePair>> {
    match value {
        Some(Value::Array(items)) => {
            let mut seen: BTreeSet<(String, String)> = BTreeSet::new();
            let mut pairs = Vec::new();
            for item in items {
                if let Some(pair) = extract_example(item)? {
                    let key = pair.normalize_key();
                    if seen.insert(key) {
                        pairs.push(pair);
                    }
                }
            }
            if pairs.is_empty() {
                Err(anyhow!("no valid examples"))
            } else {
                Ok(pairs)
            }
        }
        Some(Value::Object(map)) => {
            let mut cleaned = Vec::new();
            let mut seen: BTreeSet<(String, String)> = BTreeSet::new();
            for (k, v) in map {
                if let Some(example) = v.as_str() {
                    let pair = ExamplePair {
                        es: k,
                        en: example.to_string(),
                    };
                    if seen.insert(pair.normalize_key()) {
                        cleaned.push(pair);
                    }
                }
            }
            if cleaned.is_empty() {
                Err(anyhow!("examples object empty"))
            } else {
                Ok(cleaned)
            }
        }
        Some(Value::String(line)) => {
            let parts: Vec<&str> = line.split('|').collect();
            if parts.len() == 2 {
                Ok(vec![ExamplePair {
                    es: parts[0].trim().to_string(),
                    en: parts[1].trim().to_string(),
                }])
            } else {
                Err(anyhow!("examples string invalid"))
            }
        }
        None => Err(anyhow!("examples missing")),
        Some(other) => Err(anyhow!("examples invalid: {}", other)),
    }
}

fn extract_example(value: Value) -> Result<Option<ExamplePair>> {
    match value {
        Value::Object(mut map) => {
            let es = map
                .remove("es")
                .and_then(|v| v.as_str().map(|s| s.to_string()))
                .ok_or_else(|| anyhow!("example es missing"))?;
            let en = map
                .remove("en")
                .and_then(|v| v.as_str().map(|s| s.to_string()))
                .ok_or_else(|| anyhow!("example en missing"))?;
            Ok(Some(ExamplePair { es, en }))
        }
        Value::Array(items) => {
            if items.len() == 2 {
                if let (Some(es), Some(en)) = (items[0].as_str(), items[1].as_str()) {
                    return Ok(Some(ExamplePair {
                        es: es.to_string(),
                        en: en.to_string(),
                    }));
                }
            }
            Ok(None)
        }
        Value::String(line) => {
            let parts: Vec<&str> = line.split('|').collect();
            if parts.len() == 2 {
                Ok(Some(ExamplePair {
                    es: parts[0].trim().to_string(),
                    en: parts[1].trim().to_string(),
                }))
            } else {
                Ok(None)
            }
        }
        _ => Ok(None),
    }
}

fn normalize_gender(input: &str) -> Option<String> {
    let lower = input.to_lowercase();
    match lower.as_str() {
        "m" | "masculine" => Some("masculine".to_string()),
        "f" | "feminine" => Some("feminine".to_string()),
        _ => None,
    }
}

fn normalize_tags(value: Option<Value>) -> Vec<String> {
    match value {
        Some(Value::Array(items)) => items
            .into_iter()
            .filter_map(|item| item.as_str().map(|s| s.to_string()))
            .collect(),
        Some(Value::String(s)) => s
            .split(',')
            .map(|part| part.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect(),
        _ => Vec::new(),
    }
}

fn normalize_level(path: &Path, value: Option<&Value>) -> Level {
    if let Some(level_value) = value {
        if let Some(level_str) = level_value.as_str() {
            if let Some(level) = Level::parse(level_str) {
                return level;
            }
        }
    }
    if let Some(level) = infer_level_from_path(path) {
        return level;
    }
    Level::UNSET
}

fn infer_level_from_path(path: &Path) -> Option<Level> {
    let path_str = path.to_string_lossy().to_string();
    if let Some(caps) = LEVEL_HINT_RE.captures(&path_str) {
        if let Some(m) = caps.get(1) {
            return Level::parse(m.as_str());
        }
    }
    None
}

fn path_to_string(path: &Path) -> String {
    path.strip_prefix(Path::new("./"))
        .unwrap_or(path)
        .to_string_lossy()
        .to_string()
}
