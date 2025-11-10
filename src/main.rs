mod conflicts;
mod io_utils;
mod models;
mod normalize;

use std::collections::{BTreeSet, HashMap};
use std::path::Path;

use anyhow::{bail, Result};
use clap::Parser;

use conflicts::resolve_conflicts;
use io_utils::{
    compute_hash, ensure_build_dirs, scan_content, write_audit, write_json, write_rejects,
    RejectRecord,
};
use models::{AuditLog, Lesson, Level, Vocabulary};
use normalize::parse_and_normalize;

#[derive(Parser, Debug)]
#[command(
    author,
    version,
    about = "Heal merge conflicts and rebuild canonical Spanish datasets"
)]
struct Cli {
    #[arg(long, help = "Scan and validate without writing outputs")]
    check: bool,
    #[arg(long, help = "Fail on schema issues or unknown levels")]
    strict: bool,
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    let mode_write = !cli.check;
    let mut audit = AuditLog::default();

    let records = scan_content(Path::new("content"))?;
    audit.total_files = records.len();

    let mut lessons: Vec<Lesson> = Vec::new();
    let mut vocabulary: Vec<Vocabulary> = Vec::new();
    let mut rejects: Vec<RejectRecord> = Vec::new();

    for record in records {
        let resolution = resolve_conflicts(&record.content)?;
        if resolution.had_conflicts {
            audit
                .conflict_files
                .insert(record.path.to_string_lossy().to_string());
        }
        audit.conflict_blocks += resolution.conflicts;

        if !resolution.rejects.is_empty() {
            for reject in resolution.rejects {
                rejects.push(RejectRecord {
                    source: record.path.clone(),
                    content: reject,
                });
            }
        }

        let normalized = parse_and_normalize(&record.path, &resolution.content);
        for reject in normalized.rejects {
            rejects.push(RejectRecord {
                source: record.path.clone(),
                content: reject,
            });
        }
        for failure in normalized.invalid {
            audit.schema_failures.push(failure);
        }
        lessons.extend(normalized.lessons);
        vocabulary.extend(normalized.vocabulary);
    }

    let deduped_lessons = dedupe_lessons(&mut audit, lessons);
    let deduped_vocab = dedupe_vocab(&mut audit, vocabulary);

    audit.lesson_count = deduped_lessons.len();
    audit.vocab_count = deduped_vocab.len();
    audit.rejects = rejects.len();

    let mut final_lessons: Vec<Lesson> = Vec::new();
    let mut final_vocab: Vec<Vocabulary> = Vec::new();

    for mut lesson in deduped_lessons {
        if lesson.level == Level::UNSET {
            audit.record_unset(&lesson.id);
        }
        if let Err(err) = lesson.validate() {
            audit
                .schema_failures
                .push(format!("{}: {}", lesson.id, err));
            if cli.strict {
                bail!("strict mode: lesson {} invalid", lesson.id);
            }
        }
        lesson.source_files.sort();
        lesson.tags.sort();
        final_lessons.push(lesson);
    }

    for mut vocab in deduped_vocab {
        if vocab.level == Level::UNSET {
            audit.record_unset(&vocab.id);
        }
        if let Err(err) = vocab.validate() {
            audit.schema_failures.push(format!("{}: {}", vocab.id, err));
            if cli.strict {
                bail!("strict mode: vocab {} invalid", vocab.id);
            }
        }
        vocab.source_files.sort();
        vocab.tags.sort();
        final_vocab.push(vocab);
    }

    final_lessons.sort_by(|a, b| a.sort_key().cmp(&b.sort_key()));
    final_vocab.sort_by(|a, b| a.sort_key().cmp(&b.sort_key()));

    let unset_count = audit.level_unset.len();

    if mode_write {
        ensure_build_dirs()?;
        let lessons_path = Path::new("build/canonical/lessons.mmspanish.json");
        let vocab_path = Path::new("build/canonical/vocabulary.mmspanish.json");
        let audit_path = Path::new("build/reports/audit.md");

        let lessons_json = write_json(lessons_path, &final_lessons)?;
        let vocab_json = write_json(vocab_path, &final_vocab)?;

        write_rejects(&rejects)?;
        let audit_body = render_audit(&audit);
        write_audit(audit_path, &audit_body)?;

        let first_hash = compute_hash(&[
            ("lessons", lessons_json.clone()),
            ("vocabulary", vocab_json.clone()),
            ("audit", audit_body.clone()),
        ]);
        let second_hash = compute_hash(&[
            ("lessons", serde_json::to_string_pretty(&final_lessons)?),
            ("vocabulary", serde_json::to_string_pretty(&final_vocab)?),
            ("audit", audit_body.clone()),
        ]);
        if first_hash != second_hash {
            bail!("idempotency check failed");
        }

        print_summary(&audit, unset_count, true);
    } else {
        print_summary(&audit, unset_count, false);
    }

    if cli.strict && (!audit.schema_failures.is_empty() || unset_count > 0) {
        bail!("strict mode: audit failures present");
    }

    Ok(())
}

fn print_summary(audit: &AuditLog, unset_count: usize, wrote: bool) {
    println!("🔍 Scanned {} files", audit.total_files);
    println!("⚔️  Repaired {} conflict blocks", audit.conflict_blocks);
    println!(
        "📚  {} vocab | {} lessons",
        audit.vocab_count, audit.lesson_count
    );
    println!("✅  Merged {} duplicate clusters", audit.duplicate_clusters);
    println!("⚠️  {} items level=UNSET", unset_count);
    println!("🚫  {} rejects written", audit.rejects);
    if wrote {
        println!("✨ Written: build/canonical/*.json");
    }
}

fn render_audit(audit: &AuditLog) -> String {
    let mut body = String::new();
    body.push_str("# Rebuild Audit\n\n");
    body.push_str(&format!("- Total files scanned: {}\n", audit.total_files));
    body.push_str(&format!(
        "- Conflict blocks repaired: {}\n",
        audit.conflict_blocks
    ));
    body.push_str(&format!("- Vocabulary items: {}\n", audit.vocab_count));
    body.push_str(&format!("- Lessons: {}\n", audit.lesson_count));
    body.push_str(&format!(
        "- Duplicate clusters: {}\n",
        audit.duplicate_clusters
    ));
    body.push_str(&format!("- Reject fragments: {}\n", audit.rejects));
    body.push_str(&format!(
        "- Level UNSET count: {}\n",
        audit.level_unset.len()
    ));
    if !audit.level_unset.is_empty() {
        body.push_str("\n## Level UNSET IDs\n");
        for id in &audit.level_unset {
            body.push_str(&format!("- {}\n", id));
        }
    }
    if !audit.conflict_files.is_empty() {
        body.push_str("\n## Files with merge conflicts\n");
        for file in &audit.conflict_files {
            body.push_str(&format!("- {}\n", file));
        }
    }
    if !audit.schema_failures.is_empty() {
        body.push_str("\n## Schema Failures\n");
        for failure in &audit.schema_failures {
            body.push_str(&format!("- {}\n", failure));
        }
    }
    if !audit.duplicate_groups.is_empty() {
        body.push_str("\n## Duplicate Groups\n");
        for (key, ids) in &audit.duplicate_groups {
            body.push_str(&format!("- {}\n", key));
            for id in ids {
                body.push_str(&format!("  - {}\n", id));
            }
        }
    }
    body
}

fn dedupe_vocab(audit: &mut AuditLog, items: Vec<Vocabulary>) -> Vec<Vocabulary> {
    let mut map: HashMap<(String, String, String), Vocabulary> = HashMap::new();
    for item in items {
        let key = item.dedup_key();
        if let Some(existing) = map.get_mut(&key) {
            merge_vocab(existing, item.clone());
            let group_key = format!("vocab:{}:{}:{}", key.0, key.1, key.2);
            let group = audit
                .duplicate_groups
                .entry(group_key)
                .or_insert_with(|| vec![existing.id.clone()]);
            if !group.contains(&item.id) {
                group.push(item.id.clone());
            }
            if group.len() == 2 {
                audit.duplicate_clusters += 1;
            }
        } else {
            map.insert(key, item);
        }
    }
    map.into_values().collect()
}

fn merge_vocab(existing: &mut Vocabulary, incoming: Vocabulary) {
    let Vocabulary {
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
        ..
    } = incoming;

    if existing.spanish.trim().is_empty() {
        existing.spanish = spanish;
    }
    if existing.pos.trim().is_empty() {
        existing.pos = pos;
    }
    if existing.gender.is_none() {
        existing.gender = gender;
    }
    merge_string_field(
        &mut existing.english_gloss,
        &english_gloss,
        "english_gloss",
        &mut existing.notes,
    );
    merge_definition_field(&mut existing.definition, &definition);
    merge_optional_story(&mut existing.origin, origin);
    merge_optional_story(&mut existing.story, story);
    merge_examples(&mut existing.examples, examples);
    merge_tags(&mut existing.tags, tags);
    merge_sources(&mut existing.source_files, source_files);
    existing.notes = merge_notes(existing.notes.take(), notes);
    if existing.level == Level::UNSET && level != Level::UNSET {
        existing.level = level;
    }
}

fn merge_definition_field(existing: &mut String, incoming: &str) {
    if existing.trim().is_empty() {
        *existing = incoming.to_string();
    } else if !incoming.trim().is_empty() && existing != incoming {
        existing.push_str("\n\n— MERGED VARIANT —\n\n");
        existing.push_str(incoming);
    }
}

fn merge_string_field(
    target: &mut String,
    incoming: &str,
    field: &str,
    notes: &mut Option<String>,
) {
    if target.trim().is_empty() {
        *target = incoming.to_string();
        return;
    }
    if incoming.trim().is_empty() {
        return;
    }
    if target != incoming {
        if incoming.len() > target.len() {
            append_note(notes, field, target.clone());
            *target = incoming.to_string();
        } else {
            append_note(notes, field, incoming.to_string());
        }
    }
}

fn append_note(notes: &mut Option<String>, field: &str, alt: String) {
    if alt.trim().is_empty() {
        return;
    }
    let entry = format!("ALT {} => {}", field, alt);
    match notes {
        Some(existing) => {
            existing.push_str("\n");
            existing.push_str(&entry);
        }
        None => {
            *notes = Some(entry);
        }
    }
}

fn merge_examples(target: &mut Vec<models::ExamplePair>, incoming: Vec<models::ExamplePair>) {
    let mut seen: BTreeSet<(String, String)> = target.iter().map(|e| e.normalize_key()).collect();
    for example in incoming {
        let key = example.normalize_key();
        if seen.insert(key) {
            target.push(example);
        }
    }
}

fn merge_optional_story(target: &mut Option<String>, incoming: Option<String>) {
    if let Some(value) = incoming {
        match target {
            Some(existing) => {
                if existing.trim().is_empty() {
                    *existing = value;
                } else if existing.trim() != value.trim() {
                    existing.push_str("\n\n— MERGED VARIANT —\n\n");
                    existing.push_str(&value);
                }
            }
            None => {
                *target = Some(value);
            }
        }
    }
}

fn merge_tags(target: &mut Vec<String>, incoming: Vec<String>) {
    let mut set: BTreeSet<String> = target.iter().cloned().collect();
    for tag in incoming {
        if set.insert(tag.clone()) {
            target.push(tag);
        }
    }
}

fn merge_sources(target: &mut Vec<String>, incoming: Vec<String>) {
    let mut set: BTreeSet<String> = target.iter().cloned().collect();
    for src in incoming {
        if set.insert(src.clone()) {
            target.push(src);
        }
    }
}

fn dedupe_lessons(audit: &mut AuditLog, items: Vec<Lesson>) -> Vec<Lesson> {
    let mut map: HashMap<String, Lesson> = HashMap::new();
    for item in items {
        let key = if item.unit != 9999 || item.lesson_number != 9999 {
            format!("{}|{}|{}", item.title, item.unit, item.lesson_number)
        } else {
            format!("{}|{}", item.title, item.nickname)
        };
        if let Some(existing) = map.get_mut(&key) {
            merge_lessons(existing, item.clone());
            let group_key = format!("lesson:{}", key);
            let group = audit
                .duplicate_groups
                .entry(group_key)
                .or_insert_with(|| vec![existing.id.clone()]);
            if !group.contains(&item.id) {
                group.push(item.id.clone());
            }
            if group.len() == 2 {
                audit.duplicate_clusters += 1;
            }
        } else {
            map.insert(key, item);
        }
    }
    map.into_values().collect()
}

fn merge_lessons(existing: &mut Lesson, incoming: Lesson) {
    let Lesson {
        level,
        unit,
        lesson_number,
        tags,
        source_files,
        notes,
        steps,
        ..
    } = incoming;

    if existing.level == Level::UNSET && level != Level::UNSET {
        existing.level = level;
    }
    if existing.unit == 9999 && unit != 9999 {
        existing.unit = unit;
    }
    if existing.lesson_number == 9999 && lesson_number != 9999 {
        existing.lesson_number = lesson_number;
    }
    merge_tags(&mut existing.tags, tags);
    merge_sources(&mut existing.source_files, source_files);
    existing.notes = merge_notes(existing.notes.take(), notes);
    if steps.len() > existing.steps.len() {
        existing.steps = steps;
    }
}

fn merge_notes(existing: Option<String>, incoming: Option<String>) -> Option<String> {
    match (existing, incoming) {
        (Some(mut a), Some(b)) => {
            if !a.contains(&b) {
                a.push_str("\n");
                a.push_str(&b);
            }
            Some(a)
        }
        (None, Some(b)) => Some(b),
        (Some(a), None) => Some(a),
        (None, None) => None,
    }
}
