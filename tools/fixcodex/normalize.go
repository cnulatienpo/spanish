package main

import (
	"sort"
	"strings"

	"golang.org/x/exp/slices"
)

var cefrOrder = map[string]int{
	"A1":    0,
	"A2":    1,
	"B1":    2,
	"B2":    3,
	"C1":    4,
	"C2":    5,
	"UNSET": 6,
}

func sortLessons(lessons []Lesson) {
	slices.SortFunc(lessons, func(a, b Lesson) int {
		if diff := compareLevel(a.Level, b.Level); diff != 0 {
			return diff
		}
		if a.Unit != b.Unit {
			return a.Unit - b.Unit
		}
		if a.LessonNumber != b.LessonNumber {
			return a.LessonNumber - b.LessonNumber
		}
		return strings.Compare(a.ID, b.ID)
	})
}

func sortVocabulary(entries []Vocabulary) {
	sort.SliceStable(entries, func(i, j int) bool {
		a, b := entries[i], entries[j]
		if diff := compareLevel(a.Level, b.Level); diff != 0 {
			return diff < 0
		}
		if a.Spanish != b.Spanish {
			return strings.ToLower(a.Spanish) < strings.ToLower(b.Spanish)
		}
		if a.Pos != b.Pos {
			return strings.ToLower(a.Pos) < strings.ToLower(b.Pos)
		}
		return a.ID < b.ID
	})
}

func compareLevel(a, b string) int {
	ai, aok := cefrOrder[strings.ToUpper(a)]
	bi, bok := cefrOrder[strings.ToUpper(b)]
	if !aok {
		ai = cefrOrder["UNSET"]
	}
	if !bok {
		bi = cefrOrder["UNSET"]
	}
	if ai == bi {
		return 0
	}
	if ai < bi {
		return -1
	}
	return 1
}
