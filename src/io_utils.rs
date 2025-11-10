use std::fs::{self, File};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::SystemTime;

use ahash::AHasher;
use anyhow::{Context, Result};
use rayon::prelude::*;
use serde::Serialize;
use std::hash::Hasher;
use walkdir::WalkDir;

#[derive(Debug, Clone)]
pub struct FileRecord {
    pub path: PathBuf,
    pub content: String,
    pub mtime: SystemTime,
}

pub fn scan_content(root: &Path) -> Result<Vec<FileRecord>> {
    let mut paths = Vec::new();
    for entry in WalkDir::new(root)
        .follow_links(true)
        .into_iter()
        .filter_map(|e| e.ok())
    {
        let path = entry.path();
        if path.is_file() {
            paths.push(path.to_path_buf());
        }
    }

    let records: Result<Vec<FileRecord>> = paths
        .par_iter()
        .map(|path| {
            let metadata =
                fs::metadata(path).with_context(|| format!("metadata for {}", path.display()))?;
            let mtime = metadata.modified().unwrap_or(SystemTime::UNIX_EPOCH);
            let content =
                fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
            Ok(FileRecord {
                path: path.clone(),
                content,
                mtime,
            })
        })
        .collect();

    records
}

pub fn ensure_build_dirs() -> Result<()> {
    fs::create_dir_all(Path::new("build/canonical"))?;
    fs::create_dir_all(Path::new("build/reports"))?;
    fs::create_dir_all(Path::new("build/rejects"))?;
    Ok(())
}

pub fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<String> {
    let json = serde_json::to_string_pretty(value)?;
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut file = File::create(path)?;
    file.write_all(json.as_bytes())?;
    file.flush()?;
    Ok(json)
}

#[derive(Debug, Clone)]
pub struct RejectRecord {
    pub source: PathBuf,
    pub content: String,
}

pub fn write_rejects(records: &[RejectRecord]) -> Result<()> {
    if records.is_empty() {
        return Ok(());
    }
    for (idx, record) in records.iter().enumerate() {
        let path = Path::new("build/rejects").join(format!("reject_{:04}.txt", idx));
        let mut file = File::create(path)?;
        writeln!(
            file,
            "# Source: {}\n{}",
            record.source.display(),
            record.content
        )?;
    }
    Ok(())
}

pub fn write_audit(path: &Path, body: &str) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(path, body)?;
    Ok(())
}

pub fn compute_hash(strings: &[(&str, String)]) -> u64 {
    let mut hasher = AHasher::default();
    for (label, value) in strings {
        hasher.write(label.as_bytes());
        hasher.write(value.as_bytes());
    }
    hasher.finish()
}
