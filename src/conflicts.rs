use std::collections::{BTreeSet, HashSet};

use anyhow::{anyhow, Result};
use regex::Regex;
use serde_json::{Map, Value};

#[derive(Debug, Default, Clone)]
pub struct ConflictResolution {
    pub content: String,
    pub rejects: Vec<String>,
    pub conflicts: usize,
    pub had_conflicts: bool,
}

fn tolerant_parse(input: &str) -> Option<Value> {
    match serde_json::from_str::<Value>(input) {
        Ok(v) => Some(v),
        Err(_) => json5::from_str::<Value>(input).ok(),
    }
}

fn normalize_notes(existing: Option<&Value>) -> String {
    existing
        .and_then(|v| v.as_str().map(|s| s.trim()))
        .filter(|s| !s.is_empty())
        .map(|s| format!("{}\n\n", s))
        .unwrap_or_default()
}

fn merge_arrays(a: &[Value], b: &[Value]) -> Vec<Value> {
    let mut seen: BTreeSet<String> = BTreeSet::new();
    let mut merged: Vec<Value> = Vec::new();

    for value in a.iter().chain(b.iter()) {
        let key = match value {
            Value::String(s) => s.clone(),
            _ => serde_json::to_string(value).unwrap_or_default(),
        };
        if seen.insert(key) {
            merged.push(value.clone());
        }
    }
    merged
}

fn merge_with_notes(a: &Value, b: &Value, path: &str) -> (Value, Vec<String>) {
    match (a, b) {
        (Value::Object(map_a), Value::Object(map_b)) => {
            let mut result = Map::new();
            let mut notes: Vec<String> = Vec::new();
            let mut keys: HashSet<String> = HashSet::new();
            for key in map_a.keys() {
                keys.insert(key.clone());
            }
            for key in map_b.keys() {
                keys.insert(key.clone());
            }
            let mut keys_vec: Vec<String> = keys.into_iter().collect();
            keys_vec.sort();
            for key in keys_vec {
                let next_path = if path.is_empty() {
                    key.clone()
                } else {
                    format!("{}.{}", path, key)
                };
                match (map_a.get(&key), map_b.get(&key)) {
                    (Some(va), Some(vb)) => {
                        let (merged, mut child_notes) = merge_with_notes(va, vb, &next_path);
                        if !child_notes.is_empty() {
                            notes.append(&mut child_notes);
                        }
                        result.insert(key.clone(), merged);
                    }
                    (Some(va), None) => {
                        result.insert(key.clone(), va.clone());
                    }
                    (None, Some(vb)) => {
                        result.insert(key.clone(), vb.clone());
                    }
                    (None, None) => {}
                }
            }

            if !notes.is_empty() {
                let mut combined = normalize_notes(result.get("notes"));
                combined.push_str("ALT VARIANTS:\n");
                for note in &notes {
                    combined.push_str(note);
                    combined.push('\n');
                }
                result.insert(
                    "notes".to_string(),
                    Value::String(combined.trim().to_string()),
                );
            }
            (Value::Object(result), Vec::new())
        }
        (Value::Array(arr_a), Value::Array(arr_b)) => {
            (Value::Array(merge_arrays(arr_a, arr_b)), Vec::new())
        }
        (Value::String(sa), Value::String(sb)) => {
            if sa == sb {
                (Value::String(sa.clone()), Vec::new())
            } else {
                let field = path.split('.').last().unwrap_or("");
                if matches!(field, "definition" | "origin" | "story") {
                    let merged = format!("{}\n\n— MERGED VARIANT —\n\n{}", sa, sb);
                    (Value::String(merged), Vec::new())
                } else {
                    let (chosen, alt) = if sb.len() >= sa.len() {
                        (sb.clone(), sa.clone())
                    } else {
                        (sa.clone(), sb.clone())
                    };
                    (Value::String(chosen), vec![format!("{} => {}", path, alt)])
                }
            }
        }
        (Value::Number(_), Value::Number(_))
        | (Value::Bool(_), Value::Bool(_))
        | (Value::Null, Value::Null) => (b.clone(), Vec::new()),
        (Value::Null, _) => (b.clone(), Vec::new()),
        (_, Value::Null) => (a.clone(), Vec::new()),
        _ => (b.clone(), vec![format!("{} => {}", path, a)]),
    }
}

pub fn resolve_conflicts(content: &str) -> Result<ConflictResolution> {
    let re = Regex::new(r"(?s)<<<<<<<[^\n]*\n(.*?)\n=======\n(.*?)\n>>>>>>>[^\n]*\n?")
        .map_err(|_| anyhow!("invalid regex"))?;
    let mut cursor = 0;
    let mut output = String::with_capacity(content.len());
    let mut rejects = Vec::new();
    let mut conflicts = 0usize;

    for cap in re.captures_iter(content) {
        let m = cap.get(0).unwrap();
        let before = &content[cursor..m.start()];
        output.push_str(before);
        cursor = m.end();
        let variant_a = cap.get(1).map(|m| m.as_str()).unwrap_or("");
        let variant_b = cap.get(2).map(|m| m.as_str()).unwrap_or("");
        conflicts += 1;

        let parsed_a = tolerant_parse(variant_a.trim());
        let parsed_b = tolerant_parse(variant_b.trim());

        let merged = match (parsed_a, parsed_b) {
            (Some(a), Some(b)) => {
                let (value, notes) = merge_with_notes(&a, &b, "");
                if !notes.is_empty() {
                    rejects.push(notes.join("\n"));
                }
                serde_json::to_string_pretty(&value).unwrap_or_else(|_| variant_b.to_string())
            }
            (Some(a), None) => {
                serde_json::to_string_pretty(&a).unwrap_or_else(|_| variant_a.to_string())
            }
            (None, Some(b)) => {
                serde_json::to_string_pretty(&b).unwrap_or_else(|_| variant_b.to_string())
            }
            (None, None) => {
                rejects.push(variant_a.to_string());
                rejects.push(variant_b.to_string());
                variant_b.to_string()
            }
        };
        output.push_str(&merged);
    }
    output.push_str(&content[cursor..]);

    Ok(ConflictResolution {
        content: output,
        rejects,
        conflicts,
        had_conflicts: conflicts > 0,
    })
}
