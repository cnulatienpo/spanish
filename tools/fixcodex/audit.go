package main

import (
	"bytes"
	"fmt"
	"strings"
	"time"
)

type Metrics struct {
	FilesScanned       int
	ConflictsResolved  int
	VocabularyCount    int
	LessonCount        int
	DuplicatesMerged   int
	UnsetLevel         int
	Rejects            int
	InvalidStrictError bool
}

type PipelineResult struct {
	Lessons    []Lesson
	Vocabulary []Vocabulary
	Rejects    []rejectRecord
	Metrics    Metrics
	Started    time.Time
	Duration   time.Duration
	Strict     bool
	Wrote      bool
}

func generateAudit(result PipelineResult) string {
	buf := &bytes.Buffer{}
	fmt.Fprintf(buf, "# FixCodex Audit\n\n")
	fmt.Fprintf(buf, "- Run started: %s\n", result.Started.Format(time.RFC3339))
	fmt.Fprintf(buf, "- Duration: %s\n", result.Duration.String())
	fmt.Fprintf(buf, "- Files scanned: %d\n", result.Metrics.FilesScanned)
	fmt.Fprintf(buf, "- Conflicts resolved: %d\n", result.Metrics.ConflictsResolved)
	fmt.Fprintf(buf, "- Vocabulary entries: %d\n", result.Metrics.VocabularyCount)
	fmt.Fprintf(buf, "- Lessons: %d\n", result.Metrics.LessonCount)
	fmt.Fprintf(buf, "- Duplicates merged: %d\n", result.Metrics.DuplicatesMerged)
	fmt.Fprintf(buf, "- Entries with UNSET level: %d\n", result.Metrics.UnsetLevel)
	fmt.Fprintf(buf, "- Reject files: %d\n", len(result.Rejects))
	if result.Metrics.InvalidStrictError {
		fmt.Fprintf(buf, "- Strict mode failures detected\n")
	}
	if len(result.Rejects) > 0 {
		fmt.Fprintf(buf, "\n## Rejects\n\n")
		for _, reject := range result.Rejects {
			fmt.Fprintf(buf, "- `%s`: %s\n", reject.Path, summarizeReason(reject.Reason))
		}
	}
	return buf.String()
}

func summarizeReason(reason string) string {
	reason = strings.TrimSpace(reason)
	if len(reason) > 120 {
		return reason[:117] + "..."
	}
	return reason
}
