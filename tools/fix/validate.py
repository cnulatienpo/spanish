from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

try:  # pragma: no cover - optional dependency
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


@dataclass
class ValidationError:
    entry_id: str
    entry_type: str
    message: str


@dataclass
class ValidationResult:
    errors: List[ValidationError]


class _SimpleError:
    def __init__(self, message: str) -> None:
        self.message = message


class _SimpleValidator:
    def __init__(self, schema: Dict[str, Any]) -> None:
        self.schema = schema

    def iter_errors(self, instance: Any):
        errors: List[str] = []
        self._validate(instance, self.schema, path="", errors=errors)
        for message in errors:
            yield _SimpleError(message)

    def _validate(self, instance: Any, schema: Dict[str, Any], path: str, errors: List[str]) -> None:
        if "const" in schema and instance != schema["const"]:
            errors.append(f"{path or '<root>'}: expected constant {schema['const']}")
            return
        if "enum" in schema and instance not in schema["enum"]:
            errors.append(f"{path or '<root>'}: value not in enum {schema['enum']}")
            return

        schema_type = schema.get("type")
        if schema_type:
            allowed = schema_type if isinstance(schema_type, list) else [schema_type]
            if not any(self._check_type(instance, t) for t in allowed):
                errors.append(f"{path or '<root>'}: expected type {allowed}")
                return

        if schema.get("pattern") and isinstance(instance, str):
            if not re.match(schema["pattern"], instance):
                errors.append(f"{path or '<root>'}: pattern mismatch")

        if schema.get("minLength") and isinstance(instance, str):
            if len(instance) < schema["minLength"]:
                errors.append(f"{path or '<root>'}: shorter than minLength")

        if schema.get("minimum") is not None and isinstance(instance, (int, float)):
            if instance < schema["minimum"]:
                errors.append(f"{path or '<root>'}: below minimum {schema['minimum']}")
        if schema.get("maximum") is not None and isinstance(instance, (int, float)):
            if instance > schema["maximum"]:
                errors.append(f"{path or '<root>'}: above maximum {schema['maximum']}")

        if schema.get("type") in ("object", ["object"]):
            if not isinstance(instance, dict):
                errors.append(f"{path or '<root>'}: expected object")
                return
            required = schema.get("required", [])
            for key in required:
                if key not in instance:
                    errors.append(f"{path or '<root>'}: missing required property '{key}'")
            properties = schema.get("properties", {})
            for key, value in instance.items():
                child_path = f"{path}.{key}" if path else key
                if key in properties:
                    self._validate(value, properties[key], child_path, errors)
                else:
                    if schema.get("additionalProperties", True) is False:
                        errors.append(f"{child_path}: additional property not allowed")
            return

        if schema.get("type") in ("array", ["array"]):
            if not isinstance(instance, list):
                errors.append(f"{path or '<root>'}: expected array")
                return
            if schema.get("uniqueItems"):
                seen = set()
                for item in instance:
                    marker = json.dumps(item, sort_keys=True)
                    if marker in seen:
                        errors.append(f"{path or '<root>'}: duplicate array items")
                        break
                    seen.add(marker)
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, value in enumerate(instance):
                    child_path = f"{path}[{index}]"
                    self._validate(value, item_schema, child_path, errors)
            return

    @staticmethod
    def _check_type(value: Any, schema_type: str) -> bool:
        if schema_type == "string":
            return isinstance(value, str)
        if schema_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if schema_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if schema_type == "object":
            return isinstance(value, dict)
        if schema_type == "array":
            return isinstance(value, list)
        if schema_type == "boolean":
            return isinstance(value, bool)
        if schema_type == "null":
            return value is None
        return False


def _build_validator(schema: Dict[str, Any]):
    if jsonschema is not None:  # pragma: no cover
        return jsonschema.Draft7Validator(schema)
    return _SimpleValidator(schema)


def _load_schema(schema_dir: Path, filename: str) -> Dict[str, Any]:
    path = schema_dir / filename
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_entries(vocabulary: List[Dict[str, Any]], lessons: List[Dict[str, Any]], schema_dir: Path, strict: bool = False) -> ValidationResult:
    vocab_schema = _load_schema(schema_dir, "vocabulary.schema.json")
    lesson_schema = _load_schema(schema_dir, "lesson.schema.json")

    vocab_validator = _build_validator(vocab_schema)
    lesson_validator = _build_validator(lesson_schema)

    errors: List[ValidationError] = []

    for entry in vocabulary:
        for error in vocab_validator.iter_errors(entry):
            errors.append(
                ValidationError(
                    entry_id=entry.get("id", "<unknown>"),
                    entry_type="vocabulary",
                    message=error.message,
                )
            )

    for entry in lessons:
        for error in lesson_validator.iter_errors(entry):
            errors.append(
                ValidationError(
                    entry_id=entry.get("id", "<unknown>"),
                    entry_type="lesson",
                    message=error.message,
                )
            )

    if strict and errors:
        raise ValueError("Validation errors encountered")

    return ValidationResult(errors)

