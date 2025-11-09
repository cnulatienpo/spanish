# verify_vocab.py

## Installation

The tool requires Python 3.11 or newer. Optional dependencies are not needed. To install the minimal runtime environment, ensure the repository requirements are available or run:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # optional if your environment already satisfies dependencies
```

## Usage

```bash
python verify_vocab.py --in vocab.json [--require-alpha] [--out-report report.json] [--out-summary summary.txt] [--fail-on WARN|ERROR]
```

### Exit codes

* `0` – all checks pass beneath the failure threshold
* `1` – failed checks at or above `--fail-on`
* `2` – input file unreadable or invalid JSON

### Example

```bash
python verify_vocab.py --in sample_vocab.json --require-alpha --out-report report.json --out-summary summary.txt
```

Sample summary output snippet:

```
Validation summary for sample_vocab.json
================================================================================
Total entries: 4
Errors: 2
Warnings: 3
...
```

## SAMPLE data

The following JSON fragment can be used for quick testing:

```
[
  {
    "word": "tiempo",
    "pos": "noun",
    "gender": "masculine",
    "english": "time",
    "origin": "From Latin 'tempus'.",
    "story": "Used for both time and weather.",
    "example": "No tengo tiempo para eso.",
    "level": "A1"
  },
  {
    "word": "andar",
    "pos": "verb",
    "gender": "masculine",
    "english": "to walk",
    "origin": "From Latin 'ambulare'.",
    "story": "Common verb for walking.",
    "example": "Ella anda todos los días.",
    "level": "B1"
  },
  {
    "word": "brújula",
    "pos": "noun",
    "gender": "feminine",
    "english": "compass",
    "origin": "From Italian 'bussola'.",
    "story": "Instrument for navigation.",
    "example": "La brújula apunta al norte."
  },
  {
    "word": "andar",
    "pos": "verb",
    "gender": "n/a",
    "english": "to walk",
    "origin": "From Latin 'ambulare'.",
    "story": "Frequent verb in everyday speech.",
    "example": "Andar es bueno para la salud.",
    "level": "A2"
  }
]
```

This block includes a clean entry, one with a missing level value, one with mismatched gender for a verb, and a duplicate with conflicting level to exercise the verifier.
