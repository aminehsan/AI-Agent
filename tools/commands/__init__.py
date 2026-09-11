from __future__ import annotations
from .base import CommandSpec, FilesystemRequest
from tools.environment import RuntimeEnvironment


def build_filesystem_command(
    environment: RuntimeEnvironment,
    request: FilesystemRequest,
) -> CommandSpec:
    if environment.family == "windows":
        from .windows import build_command
    elif environment.family == "debian":
        from .debian import build_command
    else:
        from .macos import build_command
    return build_command(request)


__all__ = ["CommandSpec", "FilesystemRequest", "build_filesystem_command"]
