package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"hash/crc32"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/samber/lo"
	"github.com/segmentio/ksuid"
	"github.com/tidwall/gjson"
	"golang.org/x/exp/maps"
)

type entryKind string

const (
	entryUnknown    entryKind = "unknown"
	entryVocabulary entryKind = "vocabulary"
	entryLesson     entryKind = "lesson"
)

type rawRecord struct {
	Kind      entryKind
	Data      map[string]any
	Source    string
	LevelHint string
}

type rejectRecord struct {
	Path          string
	Reason        string
	Content       string
	SuggestedName string
}

// collectRawRecords scans the repository and resolves conflicts producing raw records.
func collectRawRecords(root string, metrics *Metrics) ([]rawRecord, []rejectRecord, error) {
	entries := make([]rawRecord, 0)
	rejects := make([]rejectRecord, 0)

	info, err := os.Stat(root)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			return entries, rejects, nil
		}
		return nil, nil, fmt.Errorf("stat content directory: %w", err)
	}
	if !info.IsDir() {
		return nil, nil, fmt.Errorf("%s is not a directory", root)
	}

	err = filepath.WalkDir(root, func(path string, d fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if d.IsDir() {
			return nil
		}
		if !strings.HasSuffix(strings.ToLower(d.Name()), ".json") {
			return nil
		}

		metrics.FilesScanned++
		data, err := os.ReadFile(path)
		if err != nil {
			rejects = append(rejects, rejectRecord{Path: path, Reason: "read error", Content: err.Error()})
			metrics.Rejects++
			return nil
		}

		resolved, resolvedCount, blockRejects := resolveConflicts(data, path, d)
		metrics.ConflictsResolved += resolvedCount
		rejects = append(rejects, blockRejects...)
		metrics.Rejects += len(blockRejects)

		records, err := decodeJSONStream(resolved)
		if err != nil {
			rejects = append(rejects, rejectRecord{Path: path, Reason: "json decode", Content: err.Error()})
			metrics.Rejects++
			return nil
		}

		level := inferLevelFromPath(path)
		for _, obj := range records {
			kind := classifyRecord(obj)
			if kind == entryUnknown {
				rejects = append(rejects, rejectRecord{Path: path, Reason: "unclassified record", Content: mustJSON(obj)})
				metrics.Rejects++
				continue
			}
			entries = append(entries, rawRecord{Kind: kind, Data: obj, Source: path, LevelHint: level})
		}

		return nil
	})
	if err != nil {
		return nil, nil, err
	}

	return entries, rejects, nil
}

func mustJSON(v any) string {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Sprintf("<unserializable: %v>", err)
	}
	return string(data)
}

// decodeJSONStream attempts to decode one or more JSON documents from a byte slice.
func decodeJSONStream(data []byte) ([]map[string]any, error) {
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	results := make([]map[string]any, 0)
	for {
		var raw any
		err := dec.Decode(&raw)
		if errors.Is(err, io.EOF) {
			break
		}
		if err != nil {
			return nil, err
		}

		switch val := raw.(type) {
		case map[string]any:
			results = append(results, val)
		case map[string]interface{}:
			converted := make(map[string]any, len(val))
			for k, v := range val {
				converted[k] = v
			}
			results = append(results, converted)
		case []any:
			for _, item := range val {
				if obj, ok := item.(map[string]any); ok {
					results = append(results, obj)
				}
			}
		case []interface{}:
			for _, item := range val {
				if obj, ok := item.(map[string]any); ok {
					results = append(results, obj)
				}
			}
		default:
			jsonText := gjson.Parse(mustJSON(val))
			if obj := jsonText.Value(); obj != nil {
				if m, ok := obj.(map[string]any); ok {
					results = append(results, m)
				}
			}
		}
	}
	return results, nil
}

// resolveConflicts strips merge conflict markers and merges variants when possible.
func resolveConflicts(data []byte, path string, info fs.DirEntry) ([]byte, int, []rejectRecord) {
	text := string(data)
	if !strings.Contains(text, "<<<<<<<") {
		return data, 0, nil
	}

	var builder strings.Builder
	rejects := make([]rejectRecord, 0)
	resolvedCount := 0
	scanner := bufio.NewScanner(strings.NewReader(text))
	scanner.Buffer(make([]byte, 0, len(data)), len(data)+1024)

	var chunk []string
	inConflict := false
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "<<<<<<<") {
			inConflict = true
			chunk = append(chunk[:0], line)
			continue
		}
		if inConflict {
			chunk = append(chunk, line)
			if strings.HasPrefix(line, ">>>>>>>") {
				resolved, ok, reject := mergeConflictChunk(chunk, path, info)
				if ok {
					builder.WriteString(resolved)
					if !strings.HasSuffix(resolved, "\n") {
						builder.WriteString("\n")
					}
					resolvedCount++
				} else {
					rejects = append(rejects, reject)
				}
				inConflict = false
			}
			continue
		}
		builder.WriteString(line)
		builder.WriteString("\n")
	}
	if err := scanner.Err(); err != nil {
		rejects = append(rejects, rejectRecord{Path: path, Reason: "conflict scan", Content: err.Error()})
	}

	return []byte(builder.String()), resolvedCount, rejects
}

func mergeConflictChunk(lines []string, path string, info fs.DirEntry) (string, bool, rejectRecord) {
	var variantA, variantB []string
	section := "A"
	for _, line := range lines {
		switch {
		case strings.HasPrefix(line, "<<<<<<<"):
			section = "A"
		case strings.HasPrefix(line, "======="):
			section = "B"
		case strings.HasPrefix(line, ">>>>>>>"):
		// end marker
		default:
			if section == "A" {
				variantA = append(variantA, line)
			} else {
				variantB = append(variantB, line)
			}
		}
	}
	a := strings.TrimSpace(strings.Join(variantA, "\n"))
	b := strings.TrimSpace(strings.Join(variantB, "\n"))

	merged, ok := mergeFragments(a, b, info)
	if ok {
		return merged, true, rejectRecord{}
	}

	rejectContent := strings.Join(lines, "\n")
	name := fmt.Sprintf("conflict_%08x.txt", crc32.ChecksumIEEE([]byte(rejectContent)))
	return "", false, rejectRecord{
		Path:          path,
		Reason:        "unresolvable conflict",
		Content:       rejectContent,
		SuggestedName: name,
	}
}

func mergeFragments(a, b string, info fs.DirEntry) (string, bool) {
	if a == b {
		return a + "\n", true
	}

	parse := func(fragment string) (any, error) {
		candidate := strings.TrimSpace(fragment)
		candidate = strings.TrimSuffix(candidate, ",")
		if candidate == "" {
			return nil, errors.New("empty fragment")
		}
		var payload any
		err := json.Unmarshal([]byte(candidate), &payload)
		if err != nil {
			return nil, err
		}
		return payload, nil
	}

	dataA, errA := parse(a)
	dataB, errB := parse(b)

	fileInfo, _ := info.Info()
	mtime := time.Time{}
	if fileInfo != nil {
		mtime = fileInfo.ModTime()
	}

	switch {
	case errA == nil && errB == nil:
		switch va := dataA.(type) {
		case map[string]any:
			if vb, ok := dataB.(map[string]any); ok {
				merged := Merge(va, vb, mtime, mtime)
				return marshalFragment(merged)
			}
		case []any:
			if vb, ok := dataB.([]any); ok {
				merged := append([]any{}, va...)
				merged = append(merged, vb...)
				merged = uniqJSONArray(merged)
				return marshalFragment(merged)
			}
		default:
			jsonStrA := mustJSON(dataA)
			jsonStrB := mustJSON(dataB)
			if len(jsonStrB) > len(jsonStrA) {
				return jsonStrB + "\n", true
			}
			return jsonStrA + "\n", true
		}
	case errA == nil:
		return marshalFragment(dataA)
	case errB == nil:
		return marshalFragment(dataB)
	default:
		return "", false
	}
}

func marshalFragment(v any) (string, bool) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return "", false
	}
	return string(data) + "\n", true
}

func classifyRecord(obj map[string]any) entryKind {
	lowerKeys := make(map[string]struct{}, len(obj))
	for k := range obj {
		lowerKeys[strings.ToLower(k)] = struct{}{}
	}
	_, hasSpanish := lowerKeys["spanish"]
	_, hasDef := lowerKeys["definition"]
	_, hasPos := lowerKeys["pos"]
	_, hasTitle := lowerKeys["title"]
	_, hasNickname := lowerKeys["nickname"]
	_, hasSteps := lowerKeys["steps"]

	if hasSpanish && hasDef && hasPos {
		return entryVocabulary
	}
	if hasTitle || hasNickname || hasSteps {
		return entryLesson
	}
	return entryUnknown
}

func inferLevelFromPath(path string) string {
	tokens := strings.Split(strings.ToUpper(path), string(os.PathSeparator))
	levels := []string{"A1", "A2", "B1", "B2", "C1", "C2"}
	for _, token := range tokens {
		for _, lvl := range levels {
			if strings.Contains(token, lvl) {
				return lvl
			}
		}
	}
	return "UNSET"
}

// normalizeAndValidate converts raw records into canonical lessons and vocabulary entries.
func normalizeAndValidate(records []rawRecord, metrics *Metrics, strict bool) ([]Lesson, []Vocabulary, []rejectRecord) {
	lessons := make([]Lesson, 0)
	vocab := make([]Vocabulary, 0)
	rejects := make([]rejectRecord, 0)

	lessonSeen := map[string]Lesson{}
	vocabSeen := map[string]Vocabulary{}

	for _, record := range records {
		switch record.Kind {
		case entryLesson:
			lesson, err := normalizeLessonRecord(record)
			if err != nil {
				rejects = append(rejects, rejectRecord{Path: record.Source, Reason: err.Error(), Content: mustJSON(record.Data), SuggestedName: fmt.Sprintf("invalid_lesson_%s.json", slugify(record.Source))})
				metrics.Rejects++
				continue
			}
			if err := lesson.Validate(strict); err != nil {
				rejects = append(rejects, rejectRecord{Path: record.Source, Reason: err.Error(), Content: mustJSON(record.Data), SuggestedName: fmt.Sprintf("invalid_lesson_%s.json", slugify(lesson.ID))})
				metrics.Rejects++
				continue
			}

			key := fmt.Sprintf("%s|%d|%d", strings.ToLower(lesson.Title), lesson.Unit, lesson.LessonNumber)
			if existing, ok := lessonSeen[key]; ok {
				n := mergeLessons(existing, lesson)
				lessonSeen[key] = n
				metrics.DuplicatesMerged++
				continue
			}

			if lesson.Level == "UNSET" {
				metrics.UnsetLevel++
			}
			lessonSeen[key] = lesson
		case entryVocabulary:
			entry, err := normalizeVocabularyRecord(record)
			if err != nil {
				rejects = append(rejects, rejectRecord{Path: record.Source, Reason: err.Error(), Content: mustJSON(record.Data), SuggestedName: fmt.Sprintf("invalid_vocab_%s.json", slugify(record.Source))})
				metrics.Rejects++
				continue
			}
			if err := entry.Validate(strict); err != nil {
				rejects = append(rejects, rejectRecord{Path: record.Source, Reason: err.Error(), Content: mustJSON(record.Data), SuggestedName: fmt.Sprintf("invalid_vocab_%s.json", slugify(entry.ID))})
				metrics.Rejects++
				continue
			}

			key := fmt.Sprintf("%s|%s|%s", strings.ToLower(entry.Spanish), strings.ToLower(entry.Pos), strings.ToLower(lo.FromPtrOr(entry.Gender, "")))
			if existing, ok := vocabSeen[key]; ok {
				n := mergeVocabulary(existing, entry)
				vocabSeen[key] = n
				metrics.DuplicatesMerged++
				continue
			}

			if entry.Level == "UNSET" {
				metrics.UnsetLevel++
			}
			vocabSeen[key] = entry
		}
	}

	lessons = append(lessons, maps.Values(lessonSeen)...)
	vocab = append(vocab, maps.Values(vocabSeen)...)

	metrics.LessonCount = len(lessons)
	metrics.VocabularyCount = len(vocab)

	return lessons, vocab, rejects
}

func mergeLessons(a, b Lesson) Lesson {
	merged := a
	merged.Tags = uniqStrings(append(a.Tags, b.Tags...))
	merged.Steps = append(append([]LessonStep{}, a.Steps...), b.Steps...)
	merged.SourceFiles = uniqStrings(append(a.SourceFiles, b.SourceFiles...))
	if b.Notes != "" && b.Notes != a.Notes {
		if merged.Notes == "" {
			merged.Notes = b.Notes
		} else {
			merged.Notes = merged.Notes + "\n\n— MERGED VARIANT —\n\n" + b.Notes
		}
	}
	return merged
}

func mergeVocabulary(a, b Vocabulary) Vocabulary {
	merged := a
	merged.Tags = uniqStrings(append(a.Tags, b.Tags...))
	merged.SourceFiles = uniqStrings(append(a.SourceFiles, b.SourceFiles...))
	merged.Examples = append(append([]map[string]string{}, a.Examples...), b.Examples...)
	merged.Examples = uniqExamplePairs(merged.Examples)
	if b.Definition != "" && b.Definition != a.Definition {
		merged.Definition = merged.Definition + "\n\n— MERGED VARIANT —\n\n" + b.Definition
	}
	if b.Origin != "" && b.Origin != a.Origin {
		if merged.Origin == "" {
			merged.Origin = b.Origin
		} else {
			merged.Origin = merged.Origin + "\n\n— MERGED VARIANT —\n\n" + b.Origin
		}
	}
	if b.Story != "" && b.Story != a.Story {
		if merged.Story == "" {
			merged.Story = b.Story
		} else {
			merged.Story = merged.Story + "\n\n— MERGED VARIANT —\n\n" + b.Story
		}
	}
	return merged
}

func uniqStrings(in []string) []string {
	return lo.UniqBy(in, strings.ToLower)
}

func uniqExamplePairs(in []map[string]string) []map[string]string {
	return lo.UniqBy(in, func(item map[string]string) string {
		return strings.ToLower(item["es"]) + "|" + strings.ToLower(item["en"])
	})
}

func normalizeLessonRecord(record rawRecord) (Lesson, error) {
	data := record.Data
	lesson := Lesson{}
	lesson.Level = pickString(data, "level", record.LevelHint)
	if lesson.Level == "" {
		lesson.Level = record.LevelHint
	}
	lesson.Title = pickString(data, "title", "")
	lesson.Nickname = pickString(data, "nickname", "")
	if lesson.Nickname == "" {
		lesson.Nickname = slugify(lesson.Title)
	}
	lesson.Unit = pickInt(data, "unit")
	lesson.LessonNumber = pickInt(data, "lesson_number")
	lesson.Tags = normalizeStringList(data["tags"])
	lesson.SourceFiles = []string{record.Source}

	if rawSteps, ok := data["steps"].([]any); ok {
		for _, step := range rawSteps {
			if m, ok := step.(map[string]any); ok {
				lesson.Steps = append(lesson.Steps, LessonStep{
					Phase:  pickString(m, "phase", ""),
					Line:   pickString(m, "line", ""),
					Origin: pickString(m, "origin", ""),
					Story:  pickString(m, "story", ""),
					Items:  normalizeStringList(m["items"]),
				})
			}
		}
	}

	lesson.Notes = pickString(data, "notes", "")
	lesson.ID = ensureLessonID(data, lesson)
	return lesson, nil
}

func ensureLessonID(data map[string]any, lesson Lesson) string {
	if id := pickString(data, "id", ""); id != "" {
		return id
	}
	unit := lesson.Unit
	slug := slugify(lesson.Title)
	if slug == "" {
		slug = ksuid.New().String()
	}
	return fmt.Sprintf("mmspanish__grammar_%d_%s", unit, slug)
}

func normalizeVocabularyRecord(record rawRecord) (Vocabulary, error) {
	data := record.Data
	entry := Vocabulary{}
	entry.Level = pickString(data, "level", record.LevelHint)
	if entry.Level == "" {
		entry.Level = record.LevelHint
	}
	entry.Spanish = pickString(data, "spanish", "")
	entry.Pos = pickString(data, "pos", "")
	entry.EnglishGloss = pickString(data, "english_gloss", pickString(data, "english", ""))
	entry.Definition = pickString(data, "definition", "")
	entry.Origin = pickString(data, "origin", "")
	entry.Story = pickString(data, "story", "")
	entry.Tags = normalizeStringList(data["tags"])
	entry.SourceFiles = []string{record.Source}

	if gender := pickString(data, "gender", ""); gender != "" {
		entry.Gender = lo.ToPtr(gender)
	}

	entry.Examples = normalizeExamples(data["examples"], data)
	entry.ID = ensureVocabularyID(data, entry)
	return entry, nil
}

func ensureVocabularyID(data map[string]any, entry Vocabulary) string {
	if id := pickString(data, "id", ""); id != "" {
		return id
	}
	slug := slugify(entry.Spanish)
	if slug == "" {
		slug = ksuid.New().String()
	}
	return fmt.Sprintf("mmspanish__vocab_%s", slug)
}

func normalizeExamples(raw any, parent map[string]any) []map[string]string {
	result := make([]map[string]string, 0)
	switch val := raw.(type) {
	case []any:
		for _, item := range val {
			if m, ok := item.(map[string]any); ok {
				es := pickString(m, "es", "")
				en := pickString(m, "en", "")
				if es != "" || en != "" {
					result = append(result, map[string]string{"es": es, "en": en})
				}
			}
		}
	case []interface{}:
		for _, item := range val {
			if m, ok := item.(map[string]any); ok {
				es := pickString(m, "es", "")
				en := pickString(m, "en", "")
				if es != "" || en != "" {
					result = append(result, map[string]string{"es": es, "en": en})
				}
			}
		}
	}

	es := pickString(parent, "example_es", "")
	en := pickString(parent, "example_en", "")
	if es != "" || en != "" {
		result = append(result, map[string]string{"es": es, "en": en})
	}

	if len(result) == 0 {
		fallbackEs := pickString(parent, "spanish", "")
		fallbackEn := pickString(parent, "english_gloss", pickString(parent, "english", ""))
		if fallbackEs != "" || fallbackEn != "" {
			result = append(result, map[string]string{"es": fallbackEs, "en": fallbackEn})
		}
	}

	return uniqExamplePairs(result)
}

func pickString(m map[string]any, key string, fallback string) string {
	if val, ok := m[key]; ok {
		switch v := val.(type) {
		case string:
			return strings.TrimSpace(v)
		case json.Number:
			return v.String()
		case fmt.Stringer:
			return strings.TrimSpace(v.String())
		}
	}
	return fallback
}

func pickInt(m map[string]any, key string) int {
	if val, ok := m[key]; ok {
		switch v := val.(type) {
		case int:
			return v
		case float64:
			return int(v)
		case json.Number:
			i, _ := v.Int64()
			return int(i)
		case string:
			vv := strings.TrimSpace(v)
			if vv == "" {
				return 0
			}
			if parsed, err := strconv.Atoi(vv); err == nil {
				return parsed
			}
		}
	}
	return 0
}

func normalizeStringList(v any) []string {
	result := make([]string, 0)
	switch val := v.(type) {
	case []any:
		for _, item := range val {
			if str, ok := item.(string); ok {
				result = append(result, strings.TrimSpace(str))
			}
		}
	case []string:
		for _, item := range val {
			result = append(result, strings.TrimSpace(item))
		}
	case string:
		for _, piece := range strings.Split(val, ",") {
			result = append(result, strings.TrimSpace(piece))
		}
	}
	return uniqStrings(lo.Filter(result, func(item string, _ int) bool { return item != "" }))
}

func slugify(input string) string {
	lower := strings.ToLower(strings.TrimSpace(input))
	if lower == "" {
		return ""
	}
	replacer := strings.NewReplacer(" ", "-", "_", "-", "--", "-")
	lower = replacer.Replace(lower)
	buf := make([]rune, 0, len(lower))
	for _, r := range lower {
		if (r >= 'a' && r <= 'z') || (r >= '0' && r <= '9') || r == '-' {
			buf = append(buf, r)
		}
	}
	collapsed := strings.Trim(strings.ReplaceAll(string(buf), "--", "-"), "-")
	collapsed = strings.TrimSpace(collapsed)
	collapsed = strings.Trim(collapsed, "-")
	return collapsed
}
