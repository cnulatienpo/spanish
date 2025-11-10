package main

import (
	"encoding/json"
	"strings"
	"time"

	"github.com/samber/lo"
)

// Merge merges two maps using the conflict resolution rules.
func Merge(a, b map[string]any, ma, mb time.Time) map[string]any {
	out := map[string]any{}
	for k, va := range a {
		vb, exists := b[k]
		if !exists {
			out[k] = va
			continue
		}
		out[k] = mergeValue(k, va, vb, ma, mb)
	}
	for k, vb := range b {
		if _, exists := out[k]; !exists {
			out[k] = vb
		}
	}
	return out
}

func mergeValue(key string, va, vb any, ma, mb time.Time) any {
	switch vaT := va.(type) {
	case string:
		vbT, _ := vb.(string)
		return mergeString(key, vaT, vbT, ma, mb)
	case []any:
		vbArr, _ := toAnySlice(vb)
		merged := append([]any{}, vaT...)
		merged = append(merged, vbArr...)
		return uniqJSONArray(merged)
	case map[string]any:
		vbMap, _ := toAnyMap(vb)
		return Merge(vaT, vbMap, ma, mb)
	default:
		// Prefer value from newer file timestamp.
		if mb.After(ma) {
			return vb
		}
		return va
	}
}

func mergeString(key, a, b string, ma, mb time.Time) string {
	if specialJoinKey(key) && a != "" && b != "" && a != b {
		return strings.Join([]string{a, b}, "\n\n— MERGED VARIANT —\n\n")
	}
	if mb.After(ma) {
		return longerString(a, b)
	}
	if ma.After(mb) {
		return longerString(b, a)
	}
	return longerString(a, b)
}

func specialJoinKey(key string) bool {
	switch strings.ToLower(key) {
	case "definition", "origin", "story":
		return true
	default:
		return false
	}
}

func longerString(primary, secondary string) string {
	if len(primary) >= len(secondary) {
		return primary
	}
	return secondary
}

func uniqJSONArray(values []any) []any {
	return lo.UniqBy(values, func(item any) string {
		data, err := json.Marshal(item)
		if err != nil {
			return ""
		}
		return string(data)
	})
}

func toAnySlice(v any) ([]any, bool) {
	switch val := v.(type) {
	case []any:
		return val, true
	case []interface{}:
		res := make([]any, len(val))
		for i, item := range val {
			res[i] = item
		}
		return res, true
	default:
		return nil, false
	}
}

func toAnyMap(v any) (map[string]any, bool) {
	switch val := v.(type) {
	case map[string]any:
		return val, true
	case map[string]interface{}:
		res := make(map[string]any, len(val))
		for k, vv := range val {
			res[k] = vv
		}
		return res, true
	default:
		return nil, false
	}
}
