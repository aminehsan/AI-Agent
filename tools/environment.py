from __future__ import annotations
import sys
import shutil
import platform
from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass
from app.settings import settings


class EnvironmentDetectionError(RuntimeError):
    """Raised when the host does not provide a supported default shell."""


def configure_utf8_stdio() -> None:
    """Use UTF-8 for model, user, and command streams when Python permits it."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # Redirected or already-closed streams may not be reconfigurable.
            continue


@dataclass(frozen=True)
class RuntimeEnvironment:
    os_name: str
    family: str
    distribution: str | None
    shell: str

    def invocation(self, command: str) -> list[str]:
        if self.family == "windows":
            script = (
                "$OutputEncoding = [Console]::OutputEncoding = [Console]::InputEncoding = "
                "[System.Text.UTF8Encoding]::new($false); "
                "$ErrorActionPreference = 'Stop'; "
                "$global:LASTEXITCODE = 0; "
                "try { "
                f"& {{ {command} }}; "
                "$agentCommandSucceeded = $?; "
                "$agentCommandExitCode = $global:LASTEXITCODE; "
                "if ($agentCommandExitCode -ne 0) { exit $agentCommandExitCode }; "
                "if (-not $agentCommandSucceeded) { exit 1 }; "
                "exit 0 "
                "} catch { [Console]::Error.WriteLine($_.ToString()); exit 1 }"
            )
            return [
                self.shell,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ]
        if self.family == "debian":
            return [self.shell, "--noprofile", "--norc", "-c", command]
        return [self.shell, "-f", "-c", command]


def _require_shell(command: str, fallback_path: str | None = None) -> str:
    shell = shutil.which(command)
    if shell:
        return str(Path(shell).resolve())
    if fallback_path and Path(fallback_path).is_file():
        return str(Path(fallback_path).resolve())
    raise EnvironmentDetectionError(
        f"Required default shell '{command}' is not installed or is not on PATH."
    )


def _detect_debian_distribution() -> str:
    try:
        release = platform.freedesktop_os_release()
    except OSError as exc:
        raise EnvironmentDetectionError(
            "Linux is supported only when /etc/os-release identifies a Debian-based system."
        ) from exc
    distribution_id = release.get("ID", "").strip().lower()
    related_ids = set(release.get("ID_LIKE", "").lower().split())
    if distribution_id not in {"debian", "ubuntu"} and "debian" not in related_ids:
        raise EnvironmentDetectionError(
            "This Linux distribution is not Debian-based and is not supported."
        )
    return release.get("PRETTY_NAME") or distribution_id


@lru_cache(maxsize=1)
def get_runtime_environment() -> RuntimeEnvironment:
    system = platform.system()
    if system == "Windows":
        return RuntimeEnvironment(
            os_name="Windows",
            family="windows",
            distribution=None,
            shell=_require_shell("powershell.exe"),
        )
    if system == "Darwin":
        return RuntimeEnvironment(
            os_name="macOS",
            family="macos",
            distribution=None,
            shell=_require_shell("zsh", "/bin/zsh"),
        )
    if system == "Linux":
        return RuntimeEnvironment(
            os_name="Linux",
            family="debian",
            distribution=_detect_debian_distribution(),
            shell=_require_shell("bash", "/bin/bash"),
        )
    raise EnvironmentDetectionError(
        f"Unsupported operating system: {system or 'unknown'}"
    )


def resolve_working_directory(cwd: str | None) -> Path:
    if not cwd or not cwd.strip():
        return settings.project_root.resolve()
    path = Path(cwd).expanduser()
    if not path.is_absolute():
        path = settings.project_root / path
    return path.resolve()


def resolve_command_path(path: str, cwd: Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = cwd / candidate
    return candidate.resolve()
