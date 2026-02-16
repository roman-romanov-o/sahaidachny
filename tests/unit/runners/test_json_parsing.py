"""Unit tests for JSON parsing utility.

Tests: TC-UNIT-020 through TC-UNIT-023
Covers: Markdown code blocks, standalone JSON, non-JSON text, multiple blocks.
"""

import pytest

from saha.runners._utils import try_parse_json


class TestTryParseJson:
    """Tests for JSON extraction from mixed text output."""

    def test_extracts_json_from_markdown(self) -> None:
        """TC-UNIT-020: Extract JSON from markdown code block."""
        output = '''
Some text before

```json
{"status": "success", "files": ["a.py"]}
```

Some text after
'''
        parsed = try_parse_json(output)
        assert parsed is not None
        assert parsed["status"] == "success"
        assert "a.py" in parsed["files"]

    def test_handles_standalone_json(self) -> None:
        """TC-UNIT-021: Parse standalone JSON string."""
        output = '{"key": "value"}'
        parsed = try_parse_json(output)
        assert parsed is not None
        assert parsed["key"] == "value"

    def test_returns_none_for_non_json(self) -> None:
        """TC-UNIT-022: Return None for plain text without JSON."""
        output = "Just plain text with no JSON"
        parsed = try_parse_json(output)
        assert parsed is None

    def test_handles_multiple_json_blocks(self) -> None:
        """TC-UNIT-023: Returns first valid JSON block from multiple."""
        output = '''
```json
{"first": "block"}
```

Some text

```json
{"second": "block"}
```
'''
        parsed = try_parse_json(output)
        assert parsed is not None
        assert parsed["first"] == "block"

    def test_returns_none_for_empty_string(self) -> None:
        """Return None for empty string."""
        assert try_parse_json("") is None
        assert try_parse_json("   ") is None

    def test_handles_nested_json(self) -> None:
        """Parse nested JSON objects correctly."""
        output = '{"outer": {"inner": "value"}, "list": [1, 2, 3]}'
        parsed = try_parse_json(output)
        assert parsed is not None
        assert parsed["outer"]["inner"] == "value"
        assert parsed["list"] == [1, 2, 3]

    def test_handles_json_with_surrounding_text(self) -> None:
        """Extract JSON from text with content before and after."""
        output = """Here is some preamble text
{"status": "done", "count": 42}
And some trailing text"""
        parsed = try_parse_json(output)
        assert parsed is not None
        assert parsed["status"] == "done"

    def test_handles_multiline_json(self) -> None:
        """Parse multiline JSON block outside of code fences."""
        output = """Some text
{
  "status": "success",
  "summary": "Implemented feature",
  "files_changed": ["a.py", "b.py"]
}
More text"""
        parsed = try_parse_json(output)
        assert parsed is not None
        assert parsed["status"] == "success"
        assert len(parsed["files_changed"]) == 2

    @pytest.mark.parametrize(
        ("input_text", "expected_output"),
        [
            pytest.param('{"a": 1}', {"a": 1}, id="simple_json"),
            pytest.param('```json\n{"a": 1}\n```', {"a": 1}, id="code_block"),
            pytest.param("not json", None, id="plain_text"),
            pytest.param("", None, id="empty_string"),
        ],
    )
    def test_parametrized_json_extraction(
        self, input_text: str, expected_output: dict | None
    ) -> None:
        """Parametrized JSON extraction test cases."""
        result = try_parse_json(input_text)
        assert result == expected_output
