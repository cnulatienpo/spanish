package main

import (
	"errors"
	"fmt"
)

// Lesson represents a structured lesson entry in the canonical dataset.
type Lesson struct {
	ID           string       `json:"id"`
	Title        string       `json:"title"`
	Nickname     string       `json:"nickname"`
	Level        string       `json:"level"`
	Unit         int          `json:"unit"`
	LessonNumber int          `json:"lesson_number"`
	Tags         []string     `json:"tags"`
	Steps        []LessonStep `json:"steps"`
	Notes        string       `json:"notes,omitempty"`
	SourceFiles  []string     `json:"source_files"`
}

// LessonStep represents an individual step inside a lesson.
type LessonStep struct {
	Phase  string   `json:"phase"`
	Line   string   `json:"line,omitempty"`
	Origin string   `json:"origin,omitempty"`
	Story  string   `json:"story,omitempty"`
	Items  []string `json:"items,omitempty"`
}

// Vocabulary represents a structured vocabulary entry in the canonical dataset.
type Vocabulary struct {
	ID           string              `json:"id"`
	Spanish      string              `json:"spanish"`
	Pos          string              `json:"pos"`
	Gender       *string             `json:"gender,omitempty"`
	EnglishGloss string              `json:"english_gloss"`
	Definition   string              `json:"definition"`
	Origin       string              `json:"origin,omitempty"`
	Story        string              `json:"story,omitempty"`
	Examples     []map[string]string `json:"examples"`
	Level        string              `json:"level"`
	Tags         []string            `json:"tags"`
	SourceFiles  []string            `json:"source_files"`
}

// Validate ensures the lesson adheres to the schema requirements.
func (l Lesson) Validate(strict bool) error {
	if l.ID == "" {
		return errors.New("lesson id is required")
	}
	if l.Title == "" {
		return errors.New("lesson title is required")
	}
	if l.Nickname == "" {
		return errors.New("lesson nickname is required")
	}
	if l.Level == "" {
		return errors.New("lesson level is required")
	}
	if l.Unit <= 0 {
		return fmt.Errorf("lesson %s missing unit", l.ID)
	}
	if l.LessonNumber <= 0 {
		return fmt.Errorf("lesson %s missing lesson number", l.ID)
	}
	if len(l.Steps) == 0 {
		return fmt.Errorf("lesson %s requires at least one step", l.ID)
	}
	for i, step := range l.Steps {
		if step.Phase == "" {
			return fmt.Errorf("lesson %s step %d missing phase", l.ID, i)
		}
		if strict {
			if step.Line == "" && step.Story == "" && len(step.Items) == 0 {
				return fmt.Errorf("lesson %s step %d has no instructional content", l.ID, i)
			}
		}
	}
	if strict && len(l.Tags) == 0 {
		return fmt.Errorf("lesson %s missing tags", l.ID)
	}
	return nil
}

// Validate ensures the vocabulary entry adheres to schema requirements.
func (v Vocabulary) Validate(strict bool) error {
	if v.ID == "" {
		return errors.New("vocabulary id is required")
	}
	if v.Spanish == "" {
		return fmt.Errorf("vocabulary %s missing spanish field", v.ID)
	}
	if v.Pos == "" {
		return fmt.Errorf("vocabulary %s missing pos", v.ID)
	}
	if v.EnglishGloss == "" {
		return fmt.Errorf("vocabulary %s missing english gloss", v.ID)
	}
	if v.Definition == "" {
		return fmt.Errorf("vocabulary %s missing definition", v.ID)
	}
	if strict {
		if len(v.Examples) == 0 {
			return fmt.Errorf("vocabulary %s missing examples", v.ID)
		}
		for i, ex := range v.Examples {
			if ex["es"] == "" || ex["en"] == "" {
				return fmt.Errorf("vocabulary %s example %d incomplete", v.ID, i)
			}
		}
	}
	return nil
}
