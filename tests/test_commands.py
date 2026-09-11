import unittest
from pathlib import Path
from tools.environment import RuntimeEnvironment
from tools.commands import FilesystemRequest, build_filesystem_command


class CommandBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = Path("C:/project/file.txt")

    def _environment(self, family: str) -> RuntimeEnvironment:
        shell = {
            "windows": "powershell.exe",
            "debian": "/bin/bash",
            "macos": "/bin/zsh",
        }[family]
        return RuntimeEnvironment("test", family, None, shell)

    def test_windows_write_uses_stdin_and_full_replacement(self) -> None:
        request = FilesystemRequest(action="write", path=self.path, content="hello")
        spec = build_filesystem_command(self._environment("windows"), request)
        self.assertEqual(spec.stdin, "hello")
        self.assertIn("WriteAllText", spec.command)

    def test_debian_binary_write_uses_base64_decode(self) -> None:
        request = FilesystemRequest(
            action="write",
            path=Path("/project/file.bin"),
            content="AAE=",
            content_format="base64",
        )
        spec = build_filesystem_command(self._environment("debian"), request)
        self.assertEqual(spec.stdin, "AAE=")
        self.assertIn("base64 --decode", spec.command)

    def test_macos_binary_write_uses_native_decode_flag(self) -> None:
        request = FilesystemRequest(
            action="write",
            path=Path("/project/file.bin"),
            content="AAE=",
            content_format="base64",
        )
        spec = build_filesystem_command(self._environment("macos"), request)
        self.assertIn("base64 -D", spec.command)

    def test_transfer_supports_copy_and_move(self) -> None:
        for family in ("windows", "debian", "macos"):
            with self.subTest(family=family):
                copy = build_filesystem_command(
                    self._environment(family),
                    FilesystemRequest(
                        action="transfer",
                        path=self.path,
                        destination=Path("C:/project/copy.txt"),
                        transfer_mode="copy",
                    ),
                )
                move = build_filesystem_command(
                    self._environment(family),
                    FilesystemRequest(
                        action="transfer",
                        path=self.path,
                        destination=Path("C:/project/moved.txt"),
                        transfer_mode="move",
                    ),
                )
                self.assertNotEqual(copy.command, move.command)

    def test_search_supports_combined_name_and_content(self) -> None:
        request = FilesystemRequest(
            action="search",
            path=Path("/project"),
            query="agent",
            search_target="both",
            recursive=True,
        )
        for family in ("windows", "debian", "macos"):
            with self.subTest(family=family):
                command = build_filesystem_command(
                    self._environment(family), request
                ).command
                self.assertIn("name matches", command)
                self.assertIn("content matches", command)
