package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/itchyny/json2yaml"
	"github.com/tidwall/sjson"
)

func writeOutputs(result PipelineResult, doWrite bool) error {
	if !doWrite {
		return nil
	}

	if err := ensureDir("build/canonical"); err != nil {
		return err
	}
	if err := ensureDir("build/reports"); err != nil {
		return err
	}
	if err := ensureDir("build/rejects"); err != nil {
		return err
	}

	lessons := append([]Lesson(nil), result.Lessons...)
	vocab := append([]Vocabulary(nil), result.Vocabulary...)
	sortLessons(lessons)
	sortVocabulary(vocab)

	if err := writeJSON("build/canonical/lessons.mmspanish.json", lessons); err != nil {
		return err
	}
	if err := writeJSON("build/canonical/vocabulary.mmspanish.json", vocab); err != nil {
		return err
	}

	auditContent := generateAudit(result)
	if err := os.WriteFile("build/reports/audit.md", []byte(auditContent), 0o644); err != nil {
		return err
	}

	if err := writeRejects(result.Rejects); err != nil {
		return err
	}

	return nil
}

func ensureDir(path string) error {
	return os.MkdirAll(path, 0o755)
}

func writeJSON(path string, v any) error {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal %s: %w", path, err)
	}
	return os.WriteFile(path, data, 0o644)
}

func writeRejects(rejects []rejectRecord) error {
	for _, reject := range rejects {
		name := reject.SuggestedName
		if name == "" {
			name = slugify(filepath.Base(reject.Path)) + ".txt"
		}
		path := filepath.Join("build", "rejects", name)
		payload := map[string]any{
			"source_path": reject.Path,
			"reason":      reject.Reason,
			"content":     reject.Content,
		}
		data, err := json.Marshal(payload)
		if err != nil {
			return err
		}
		data, err = sjson.SetBytes(data, "meta.generated_at", time.Now().Format(time.RFC3339))
		if err != nil {
			return err
		}
		yaml, err := json2yaml.JSON2YAML(data)
		if err != nil {
			return err
		}
		if err := os.WriteFile(path, yaml, 0o644); err != nil {
			return err
		}
	}
	return nil
}

func formatSummaryLines(result PipelineResult) []string {
	lines := []string{
		fmt.Sprintf("🔍  Scanned %d files", result.Metrics.FilesScanned),
		fmt.Sprintf("⚔️  Resolved %d conflicts", result.Metrics.ConflictsResolved),
		fmt.Sprintf("📘  %d vocab | %d lessons", result.Metrics.VocabularyCount, result.Metrics.LessonCount),
		fmt.Sprintf("✅  %d duplicates merged", result.Metrics.DuplicatesMerged),
		fmt.Sprintf("⚠️  %d with UNSET level", result.Metrics.UnsetLevel),
		fmt.Sprintf("🚫  %d rejects", len(result.Rejects)),
	}
	if result.Strict && (result.Metrics.UnsetLevel > 0 || len(result.Rejects) > 0) {
		lines = append(lines, "❌  strict mode failed")
	}
	if result.Wrote {
		lines = append(lines, "✨ Done! Canonical JSONs written to build/canonical/")
	} else {
		lines = append(lines, "✨ Done! Validation completed (no files written)")
	}
	return lines
}

func stringifySummary(result PipelineResult) string {
	return strings.Join(formatSummaryLines(result), "\n")
}
