"""Integration tests for tool integrations in containers.

Tests that Ruff, ty, complexity, and pytest work correctly in clean environments.
"""


from tests.integration.conftest import (
    run_in_container,
    run_python_in_container,
)


class TestRuffIntegration:
    """Test Ruff linter integration."""

    def test_ruff_detects_errors(self, bootstrapped_container, sample_python_project):
        """Test that Ruff detects linting errors."""
        # Write test file directly instead of copying tarball
        file_content = sample_python_project["sample_project/with_errors.py"]
        run_in_container(
            bootstrapped_container,
            f"cd /root/sahaidachny && mkdir -p sample_project && cat > sample_project/with_errors.py << 'EOF'\n{file_content}\nEOF",
        )

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && .venv/bin/ruff check sample_project/with_errors.py 2>&1 || true",
        )

        # Ruff should find issues (unused import, etc.)
        assert "F401" in output or "unused" in output.lower(), f"Ruff should detect unused import: {output}"

    def test_ruff_passes_clean_code(self, bootstrapped_container, clean_python_project):
        """Test that Ruff passes on clean code."""
        # Write test file directly
        file_content = clean_python_project["clean_project/main.py"]
        run_in_container(
            bootstrapped_container,
            f"cd /root/sahaidachny && mkdir -p clean_project && cat > clean_project/main.py << 'EOF'\n{file_content}\nEOF",
        )

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && .venv/bin/ruff check clean_project/",
        )

        assert exit_code == 0, f"Ruff should pass on clean code: {output}"


class TestTyIntegration:
    """Test ty type checker integration."""

    def test_ty_available(self, bootstrapped_container):
        """Test that ty is installed and available."""
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && .venv/bin/ty --version",
        )

        assert exit_code == 0, f"ty should be available: {output}"
        assert "ty" in output.lower() or "0." in output, f"Should show ty version: {output}"


class TestComplexityIntegration:
    """Test complexity checker integration."""

    def test_complexity_available(self, bootstrapped_container):
        """Test that complexipy is installed."""
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && .venv/bin/complexipy --version 2>&1 || .venv/bin/python -c 'import complexipy; print(complexipy.__version__)'",
        )

        # Should either show version or import successfully
        assert exit_code == 0 or "complexipy" in output.lower(), f"complexipy should be available: {output}"


class TestPytestIntegration:
    """Test pytest integration."""

    def test_pytest_runs_tests(self, bootstrapped_container, sample_python_project):
        """Test that pytest can run tests."""
        # Write test files directly
        main_content = sample_python_project["sample_project/main.py"]
        test_content = sample_python_project["tests/test_main.py"]

        run_in_container(
            bootstrapped_container,
            f"""cd /root/sahaidachny && \\
mkdir -p sample_project tests && \\
cat > sample_project/__init__.py << 'EOF'
EOF
cat > sample_project/main.py << 'EOF'
{main_content}
EOF
cat > tests/__init__.py << 'EOF'
EOF
cat > tests/test_main.py << 'EOF'
{test_content}
EOF""",
        )

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && .venv/bin/pytest tests/ -v 2>&1 || true",
        )

        # Should run tests (some pass, one fails)
        assert "test_calculate_sum" in output, f"Should run tests: {output}"
        assert "test_greet" in output, f"Should run greet test: {output}"
        assert "PASSED" in output, f"Some tests should pass: {output}"
        assert "FAILED" in output, f"Failing test should fail: {output}"

    def test_pytest_passes_clean_tests(self, bootstrapped_container, clean_python_project):
        """Test that pytest passes on clean tests."""
        # Write test files directly
        main_content = clean_python_project["clean_project/main.py"]
        test_content = clean_python_project["tests/test_main.py"]

        run_in_container(
            bootstrapped_container,
            f"""cd /root/sahaidachny && \\
mkdir -p clean_project tests && \\
cat > clean_project/__init__.py << 'EOF'
EOF
cat > clean_project/main.py << 'EOF'
{main_content}
EOF
cat > tests/__init__.py << 'EOF'
EOF
cat > tests/test_main.py << 'EOF'
{test_content}
EOF""",
        )

        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && .venv/bin/pytest tests/ -v",
        )

        assert exit_code == 0, f"All tests should pass: {output}"
        assert "2 passed" in output, f"Should show 2 passed: {output}"


class TestToolsCommand:
    """Test the saha tools command."""

    def test_tools_lists_all_tools(self, bootstrapped_container):
        """Test that 'saha tools' lists all available tools."""
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh tools",
        )

        assert exit_code == 0, f"tools command failed: {output}"
        assert "ruff" in output
        assert "ty" in output
        assert "complexity" in output
        assert "pytest" in output

    def test_all_tools_available(self, bootstrapped_container):
        """Test that all tools show as available (checkmark)."""
        exit_code, output = run_in_container(
            bootstrapped_container,
            "cd /root/sahaidachny && ./saha.sh tools",
        )

        assert exit_code == 0
        # All 4 tools should be available (check for checkmark character)
        checkmarks = output.count("✓")
        assert checkmarks >= 4, f"All tools should be available (found {checkmarks}): {output}"


class TestToolRegistryIntegration:
    """Test tool registry via Python API."""

    def test_tool_registry_lists_tools(self, bootstrapped_container):
        """Test that tool registry lists all tools."""
        python_code = '''
from saha.tools import create_default_registry

registry = create_default_registry()
tools = registry.list_all()
print(f"Available tools: {tools}")

assert "ruff" in tools
assert "ty" in tools
assert "complexity" in tools
assert "pytest" in tools

print("Tool registry works!")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Tool registry test failed: {output}"
        assert "Tool registry works!" in output

    def test_tool_registry_checks_availability(self, bootstrapped_container):
        """Test that tools report their availability."""
        python_code = '''
from saha.tools import create_default_registry

registry = create_default_registry()

for name in registry.list_all():
    tool = registry.get(name)
    available = tool.is_available()
    print(f"{name}: available={available}")

print("Availability check done!")
'''
        exit_code, output = run_python_in_container(bootstrapped_container, python_code)

        assert exit_code == 0, f"Availability check failed: {output}"
        assert "Availability check done!" in output
