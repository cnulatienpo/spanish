package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/fatih/color"
	"github.com/spf13/cobra"
)

type RunnerConfig struct {
	Check  bool
	Write  bool
	Strict bool
}

func main() {
	var cfg RunnerConfig

	root := &cobra.Command{
		Use:   "fixcodex",
		Short: "Reconstruct canonical MixMethod Spanish datasets",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx := context.Background()
			result, err := runPipeline(ctx, cfg)
			printSummary(result, err)
			return err
		},
	}

	root.Flags().BoolVar(&cfg.Check, "check", false, "validate only without writing")
	root.Flags().BoolVar(&cfg.Write, "write", false, "write canonical outputs")
	root.Flags().BoolVar(&cfg.Strict, "strict", false, "fail on rejects or UNSET levels")

	if err := root.Execute(); err != nil {
		os.Exit(1)
	}
}

func runPipeline(_ context.Context, cfg RunnerConfig) (PipelineResult, error) {
	start := time.Now()
	metrics := Metrics{}

	if cfg.Check && cfg.Write {
		return PipelineResult{}, fmt.Errorf("--check and --write cannot be combined")
	}

	rawRecords, rejects, err := collectRawRecords("content", &metrics)
	if err != nil {
		return PipelineResult{}, err
	}

	lessons, vocabulary, normalizationRejects := normalizeAndValidate(rawRecords, &metrics, cfg.Strict)
	rejects = append(rejects, normalizationRejects...)

	metrics.Rejects = len(rejects)

	result := PipelineResult{
		Lessons:    lessons,
		Vocabulary: vocabulary,
		Rejects:    rejects,
		Metrics:    metrics,
		Started:    start,
		Duration:   time.Since(start),
		Strict:     cfg.Strict,
		Wrote:      cfg.Write && !cfg.Check,
	}

	if cfg.Strict && (metrics.UnsetLevel > 0 || len(rejects) > 0) {
		metrics.InvalidStrictError = true
		result.Metrics = metrics
		if cfg.Write && !cfg.Check {
			_ = writeOutputs(result, true)
			result.Wrote = true
		}
		return result, errors.New("strict mode: unresolved entries present")
	}

	if err := writeOutputs(result, cfg.Write && !cfg.Check); err != nil {
		return result, err
	}
	if cfg.Write && !cfg.Check {
		result.Wrote = true
	}

	return result, nil
}

func printSummary(result PipelineResult, runErr error) {
	lines := formatSummaryLines(result)
	for _, line := range lines {
		switch {
		case strings.HasPrefix(line, "❌"):
			color.New(color.FgHiRed).Println(line)
		case strings.HasPrefix(line, "⚠️"):
			color.New(color.FgYellow).Println(line)
		case strings.HasPrefix(line, "✅"):
			color.New(color.FgGreen).Println(line)
		case strings.HasPrefix(line, "🚫"):
			color.New(color.FgRed).Println(line)
		case strings.HasPrefix(line, "✨"):
			color.New(color.FgHiCyan).Println(line)
		default:
			color.New(color.FgWhite).Println(line)
		}
	}
	if runErr != nil {
		color.New(color.FgHiRed).Printf("error: %v\n", runErr)
	}
}
