use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet};

use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use serde_with::{serde_as, DefaultOnNull, OneOrMany};

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[serde(rename_all = "UPPERCASE")]
pub enum Level {
    A1,
    A2,
    B1,
    B2,
    C1,
    C2,
    UNSET,
}

impl Level {
    pub fn order(&self) -> usize {
        match self {
            Level::A1 => 1,
            Level::A2 => 2,
            Level::B1 => 3,
            Level::B2 => 4,
            Level::C1 => 5,
            Level::C2 => 6,
            Level::UNSET => 7,
        }
    }

    pub fn parse<S: AsRef<str>>(input: S) -> Option<Self> {
        match input.as_ref().trim().to_uppercase().as_str() {
            "A1" => Some(Level::A1),
            "A2" => Some(Level::A2),
            "B1" => Some(Level::B1),
            "B2" => Some(Level::B2),
            "C1" => Some(Level::C1),
            "C2" => Some(Level::C2),
            "UNSET" => Some(Level::UNSET),
            _ => None,
        }
    }
}

#[serde_as]
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct LessonStepExamples {
    #[serde_as(as = "OneOrMany<String>")]
    pub items: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "phase", rename_all = "snake_case")]
pub enum LessonStep {
    EnglishAnchor {
        line: String,
    },
    SystemLogic {
        line: String,
    },
    MeaningDepth {
        origin: Option<String>,
        story: Option<String>,
    },
    SpanishEntry {
        line: String,
    },
    Examples(LessonStepExamples),
}

impl LessonStep {
    pub fn validate(&self) -> Result<()> {
        match self {
            LessonStep::EnglishAnchor { line }
            | LessonStep::SystemLogic { line }
            | LessonStep::SpanishEntry { line } => {
                if line.trim().is_empty() {
                    Err(anyhow!("Lesson step line must be non-empty"))
                } else {
                    Ok(())
                }
            }
            LessonStep::MeaningDepth { .. } => Ok(()),
            LessonStep::Examples(examples) => {
                if examples.items.is_empty() {
                    Err(anyhow!("Examples must contain at least one item"))
                } else {
                    Ok(())
                }
            }
        }
    }
}

#[serde_as]
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ExamplesArray {
    #[serde_as(as = "OneOrMany<ExamplePair>")]
    pub examples: Vec<ExamplePair>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ExamplePair {
    pub es: String,
    pub en: String,
}

impl ExamplePair {
    pub fn normalize_key(&self) -> (String, String) {
        (
            self.es
                .split_whitespace()
                .collect::<Vec<_>>()
                .join(" ")
                .to_lowercase(),
            self.en
                .split_whitespace()
                .collect::<Vec<_>>()
                .join(" ")
                .to_lowercase(),
        )
    }
}

#[serde_as]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Lesson {
    pub id: String,
    pub title: String,
    pub nickname: String,
    pub level: Level,
    pub unit: u32,
    pub lesson_number: u32,
    #[serde_as(as = "DefaultOnNull<Vec<String>>")]
    pub tags: Vec<String>,
    pub steps: Vec<LessonStep>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub notes: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub source_files: Vec<String>,
}

impl Lesson {
    pub fn validate(&self) -> Result<()> {
        if self.id.trim().is_empty() {
            return Err(anyhow!("Lesson id is required"));
        }
        if self.title.trim().is_empty() {
            return Err(anyhow!("Lesson title is required"));
        }
        if self.nickname.trim().is_empty() {
            return Err(anyhow!("Lesson nickname is required"));
        }
        if self.steps.is_empty() {
            return Err(anyhow!("Lesson must contain steps"));
        }
        for step in &self.steps {
            step.validate()?;
        }
        Ok(())
    }

    pub fn sort_key(&self) -> (usize, u32, u32, String) {
        (
            self.level.order(),
            self.unit,
            self.lesson_number,
            self.id.clone(),
        )
    }
}

#[serde_as]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Vocabulary {
    pub id: String,
    pub spanish: String,
    pub pos: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub gender: Option<String>,
    pub english_gloss: String,
    pub definition: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub origin: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub story: Option<String>,
    pub examples: Vec<ExamplePair>,
    pub level: Level,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tags: Vec<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub source_files: Vec<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub notes: Option<String>,
}

impl Vocabulary {
    pub fn validate(&self) -> Result<()> {
        if self.id.trim().is_empty() {
            return Err(anyhow!("Vocabulary id is required"));
        }
        if self.spanish.trim().is_empty() {
            return Err(anyhow!("spanish is required"));
        }
        if self.pos.trim().is_empty() {
            return Err(anyhow!("pos is required"));
        }
        if self.english_gloss.trim().is_empty() {
            return Err(anyhow!("english_gloss is required"));
        }
        if self.definition.trim().is_empty() {
            return Err(anyhow!("definition is required"));
        }
        if self.examples.is_empty() {
            return Err(anyhow!("examples are required"));
        }
        Ok(())
    }

    pub fn sort_key(&self) -> (usize, String) {
        (self.level.order(), self.id.clone())
    }

    pub fn dedup_key(&self) -> (String, String, String) {
        let gender = self.gender.clone().unwrap_or_else(|| "null".to_string());
        (
            self.spanish.to_lowercase(),
            self.pos.to_lowercase(),
            gender.to_lowercase(),
        )
    }
}

#[derive(Default, Debug, Clone)]
pub struct AuditLog {
    pub total_files: usize,
    pub conflict_blocks: usize,
    pub vocab_count: usize,
    pub lesson_count: usize,
    pub duplicate_clusters: usize,
    pub level_unset: Vec<String>,
    pub rejects: usize,
    pub schema_failures: Vec<String>,
    pub conflict_files: BTreeSet<String>,
    pub duplicate_groups: BTreeMap<String, Vec<String>>,
}

impl AuditLog {
    pub fn record_unset(&mut self, id: &str) {
        self.level_unset.push(id.to_string());
    }
}
