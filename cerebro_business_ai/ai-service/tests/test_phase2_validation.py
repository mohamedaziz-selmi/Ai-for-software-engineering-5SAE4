import json
from pathlib import Path

from data.validate_phase2 import validate_jsonl


def test_smoke_schema_validation(tmp_path: Path):
    path = tmp_path / "sample.jsonl"
    path.write_text(json.dumps({"title": "Example", "description": "text"}) + "\n", encoding="utf-8")
    result = validate_jsonl(path, ["title", "description"])
    assert result["valid"] is True
    assert result["duplicate_rows"] == 0


def test_smoke_schema_detects_missing_column(tmp_path: Path):
    path = tmp_path / "sample.jsonl"
    path.write_text(json.dumps({"title": "Example"}) + "\n", encoding="utf-8")
    result = validate_jsonl(path, ["title", "description"])
    assert result["valid"] is False
    assert result["missing_expected_columns"] == ["description"]
