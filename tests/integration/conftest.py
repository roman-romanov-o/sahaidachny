"""Shared fixtures for integration tests."""

import tarfile
from io import BytesIO
from pathlib import Path

import pytest
from testcontainers.core.container import DockerContainer

PROJECT_ROOT = Path(__file__).parent.parent.parent


def create_project_tarball(extra_files: dict[str, str] | None = None) -> bytes:
    """Create a tarball of the project for copying into container.

    Args:
        extra_files: Additional files to include {arcname: content}
    """
    buffer = BytesIO()

    include_patterns = [
        "saha.sh",
        "pyproject.toml",
        ".python-version",
        "README.md",
        "saha/",
        "task_tracker/",
        "claude_plugin/",
    ]

    exclude_patterns = [
        "__pycache__",
        ".venv",
        ".git",
        "*.pyc",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    ]

    def tar_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        for pattern in exclude_patterns:
            if pattern in tarinfo.name:
                return None
        return tarinfo

    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for pattern in include_patterns:
            path = PROJECT_ROOT / pattern
            if path.exists():
                arcname = f"sahaidachny/{pattern}"
                tar.add(path, arcname=arcname, filter=tar_filter)

        # Add extra files
        if extra_files:
            for arcname, content in extra_files.items():
                data = content.encode("utf-8")
                info = tarfile.TarInfo(name=f"sahaidachny/{arcname}")
                info.size = len(data)
                tar.addfile(info, BytesIO(data))

    buffer.seek(0)
    return buffer.read()


def run_in_container(container: DockerContainer, cmd: str) -> tuple[int, str]:
    """Run a command in container with proper environment."""
    full_cmd = f"export HOME=/root && export PATH=$HOME/.local/bin:$PATH && {cmd}"
    exit_code, output = container.exec(["bash", "-c", full_cmd])
    output_str = output.decode() if isinstance(output, bytes) else output
    return exit_code, output_str


def run_python_in_container(container: DockerContainer, code: str) -> tuple[int, str]:
    """Run Python code in container by writing to a temp file first.

    This avoids shell quoting issues with complex Python code.
    """
    cmd = f"""cd /root/sahaidachny && cat > /tmp/test_script.py << "ENDPYTHON"
{code}
ENDPYTHON
.venv/bin/python /tmp/test_script.py"""

    return run_in_container(container, cmd)


def copy_to_container(
    container: DockerContainer,
    tarball: bytes,
    dest: str = "/root",
) -> None:
    """Copy tarball contents to container."""
    docker_client = container.get_docker_client()
    docker_client.client.api.put_archive(
        container.get_wrapped_container().id,
        dest,
        tarball,
    )


@pytest.fixture(scope="module")
def debian_container():
    """Create a Debian container with curl installed.

    Module-scoped for efficiency - reused across tests in same module.
    """
    container = DockerContainer("debian:bookworm-slim").with_command("sleep infinity")
    container.start()

    # Install curl
    exit_code, _ = container.exec("apt-get update -qq")
    assert exit_code == 0

    exit_code, _ = container.exec("apt-get install -y -qq curl ca-certificates")
    assert exit_code == 0

    yield container
    container.stop()


@pytest.fixture(scope="module")
def bootstrapped_container(debian_container):
    """A Debian container with saha already bootstrapped.

    Module-scoped - bootstrap once, reuse for multiple tests.
    """
    tarball = create_project_tarball()
    copy_to_container(debian_container, tarball)

    # Bootstrap
    exit_code, output = run_in_container(
        debian_container,
        "cd /root/sahaidachny && ./saha.sh version",
    )
    assert exit_code == 0, f"Bootstrap failed: {output}"

    return debian_container


@pytest.fixture
def sample_python_project() -> dict[str, str]:
    """Sample Python project files for testing tools."""
    return {
        "sample_project/__init__.py": "",
        "sample_project/main.py": '''"""Sample module with intentional issues."""

def calculate_sum(a, b):
    """Add two numbers."""
    result = a + b
    return result


def complex_function(x, y, z):
    """A more complex function."""
    if x > 0:
        if y > 0:
            if z > 0:
                return x + y + z
            else:
                return x + y - z
        else:
            if z > 0:
                return x - y + z
            else:
                return x - y - z
    else:
        return 0


def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"
''',
        "sample_project/with_errors.py": '''"""Module with linting errors."""

import os
import sys  # unused import

def bad_function( x,y ):
    """Bad formatting."""
    unused_var = 42
    return x+y
''',
        "tests/__init__.py": "",
        "tests/test_main.py": '''"""Tests for main module."""

from sample_project.main import calculate_sum, greet


def test_calculate_sum():
    """Test addition."""
    assert calculate_sum(2, 3) == 5
    assert calculate_sum(-1, 1) == 0


def test_greet():
    """Test greeting."""
    assert greet("World") == "Hello, World!"


def test_failing():
    """This test fails intentionally."""
    assert 1 == 2, "Intentional failure"
''',
    }


@pytest.fixture
def clean_python_project() -> dict[str, str]:
    """Clean Python project that passes all checks."""
    return {
        "clean_project/__init__.py": "",
        "clean_project/main.py": '''"""Clean module."""


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b
''',
        "tests/__init__.py": "",
        "tests/test_main.py": '''"""Tests for main module."""

from clean_project.main import add, multiply


def test_add():
    """Test addition."""
    assert add(2, 3) == 5


def test_multiply():
    """Test multiplication."""
    assert multiply(2, 3) == 6
''',
    }
