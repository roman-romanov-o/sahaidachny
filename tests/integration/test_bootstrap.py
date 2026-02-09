"""Integration tests for the bootstrap script using testcontainers.

Tests that saha.sh works in a clean environment without Python pre-installed.
"""

import tarfile
from io import BytesIO
from pathlib import Path

import pytest
from testcontainers.core.container import DockerContainer

PROJECT_ROOT = Path(__file__).parent.parent.parent


def create_project_tarball() -> bytes:
    """Create a tarball of the project for copying into container."""
    buffer = BytesIO()

    include_patterns = [
        "saha.sh",
        "pyproject.toml",
        ".python-version",
        "README.md",
        "saha/",
        "task_tracker/",
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

    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for pattern in include_patterns:
            path = PROJECT_ROOT / pattern
            if path.exists():
                arcname = f"sahaidachny/{pattern}"
                tar.add(path, arcname=arcname, filter=_tar_filter(exclude_patterns))

    buffer.seek(0)
    return buffer.read()


def _tar_filter(exclude_patterns: list[str]):
    """Create a tar filter that excludes certain patterns."""

    def filter_func(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        for pattern in exclude_patterns:
            if pattern in tarinfo.name:
                return None
        return tarinfo

    return filter_func


def run_in_container(container: DockerContainer, cmd: str) -> tuple[int, str]:
    """Run a command in container with proper environment."""
    # Wrap command to set HOME and PATH
    full_cmd = f"bash -c 'export HOME=/root && export PATH=$HOME/.local/bin:$PATH && {cmd}'"
    exit_code, output = container.exec(full_cmd)
    output_str = output.decode() if isinstance(output, bytes) else output
    return exit_code, output_str


class TestBootstrapScript:
    """Test the saha.sh bootstrap script in clean containers."""

    @pytest.fixture
    def debian_container(self):
        """Create a Debian container without Python."""
        container = DockerContainer("debian:bookworm-slim").with_command("sleep infinity")
        container.start()

        # Install curl (needed for uv installation)
        exit_code, output = container.exec("apt-get update -qq")
        assert exit_code == 0, f"apt-get update failed: {output}"

        exit_code, output = container.exec("apt-get install -y -qq curl ca-certificates")
        assert exit_code == 0, f"curl install failed: {output}"

        yield container
        container.stop()

    @pytest.fixture
    def ubuntu_container(self):
        """Create an Ubuntu container without Python."""
        container = DockerContainer("ubuntu:24.04").with_command("sleep infinity")
        container.start()

        exit_code, _ = container.exec("apt-get update -qq")
        assert exit_code == 0

        exit_code, _ = container.exec("apt-get install -y -qq curl ca-certificates")
        assert exit_code == 0

        yield container
        container.stop()

    def copy_project_to_container(self, container: DockerContainer) -> None:
        """Copy the project files into the container."""
        tarball = create_project_tarball()
        docker_client = container.get_docker_client()
        docker_client.client.api.put_archive(
            container.get_wrapped_container().id,
            "/root",
            tarball,
        )

    def test_bootstrap_installs_uv_on_debian(self, debian_container):
        """Test that saha.sh installs uv when not present."""
        self.copy_project_to_container(debian_container)

        # Verify Python is NOT installed
        exit_code, _ = debian_container.exec("which python3")
        assert exit_code != 0, "Python should not be pre-installed"

        # Verify uv is NOT installed
        exit_code, _ = debian_container.exec("which uv")
        assert exit_code != 0, "uv should not be pre-installed"

        # Run saha.sh --help (should bootstrap everything)
        exit_code, output = run_in_container(
            debian_container,
            "cd /root/sahaidachny && ./saha.sh --help",
        )

        assert exit_code == 0, f"saha.sh failed: {output}"
        assert "Agentic loop orchestrator" in output
        assert "run" in output
        assert "status" in output

    def test_bootstrap_installs_uv_on_ubuntu(self, ubuntu_container):
        """Test that saha.sh installs uv when not present on Ubuntu."""
        self.copy_project_to_container(ubuntu_container)

        exit_code, output = run_in_container(
            ubuntu_container,
            "cd /root/sahaidachny && ./saha.sh --help",
        )

        assert exit_code == 0, f"saha.sh failed: {output}"
        assert "Agentic loop orchestrator" in output

    def test_tools_command_works(self, debian_container):
        """Test that 'saha.sh tools' works after bootstrap."""
        self.copy_project_to_container(debian_container)

        # First run to bootstrap
        exit_code, _ = run_in_container(
            debian_container,
            "cd /root/sahaidachny && ./saha.sh version",
        )
        assert exit_code == 0

        # Now run tools command
        exit_code, output = run_in_container(
            debian_container,
            "cd /root/sahaidachny && ./saha.sh tools",
        )

        assert exit_code == 0, f"tools command failed: {output}"
        assert "ruff" in output
        assert "pytest" in output

    def test_version_command_works(self, debian_container):
        """Test that 'saha.sh version' returns correct version."""
        self.copy_project_to_container(debian_container)

        exit_code, output = run_in_container(
            debian_container,
            "cd /root/sahaidachny && ./saha.sh version",
        )

        assert exit_code == 0, f"version command failed: {output}"
        assert "saha version" in output.lower()

    def test_subsequent_runs_are_fast(self, debian_container):
        """Test that after initial setup, subsequent runs don't reinstall."""
        self.copy_project_to_container(debian_container)

        # First run - bootstraps everything
        exit_code, output1 = run_in_container(
            debian_container,
            "cd /root/sahaidachny && ./saha.sh version",
        )
        assert exit_code == 0

        # Second run - should skip installation
        exit_code, output2 = run_in_container(
            debian_container,
            "cd /root/sahaidachny && ./saha.sh version",
        )
        assert exit_code == 0

        # Second run should NOT have installation messages
        assert "Installing uv" not in output2
        assert "Setting up Python" not in output2
        assert "saha version" in output2.lower()
