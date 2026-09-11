import unittest
from pathlib import Path
from unittest.mock import patch
from app.settings import settings
from tools.environment import (
    EnvironmentDetectionError,
    get_runtime_environment,
    resolve_working_directory,
)


class EnvironmentTests(unittest.TestCase):
    def tearDown(self) -> None:
        get_runtime_environment.cache_clear()

    @patch("tools.environment.shutil.which", return_value="C:/Windows/powershell.exe")
    @patch("tools.environment.platform.system", return_value="Windows")
    def test_windows_uses_built_in_powershell(self, _system, _which) -> None:
        environment = get_runtime_environment()
        self.assertEqual(environment.family, "windows")
        self.assertTrue(environment.shell.endswith("powershell.exe"))
        self.assertIn(
            "$ErrorActionPreference = 'Stop'",
            environment.invocation("Write-Error 'x'")[-1],
        )

    @patch("tools.environment.shutil.which", return_value="/bin/bash")
    @patch(
        "tools.environment.platform.freedesktop_os_release",
        return_value={"ID": "linuxmint", "ID_LIKE": "ubuntu debian"},
    )
    @patch("tools.environment.platform.system", return_value="Linux")
    def test_debian_based_distribution_is_supported(
        self, _system, _release, _which
    ) -> None:
        environment = get_runtime_environment()
        self.assertEqual(environment.family, "debian")

    @patch(
        "tools.environment.platform.freedesktop_os_release",
        return_value={"ID": "fedora", "ID_LIKE": "rhel"},
    )
    @patch("tools.environment.platform.system", return_value="Linux")
    def test_non_debian_linux_stops(self, _system, _release) -> None:
        with self.assertRaises(EnvironmentDetectionError):
            get_runtime_environment()

    def test_relative_cwd_always_starts_from_project_root(self) -> None:
        original_root = settings.project_root
        settings.project_root = Path("C:/project")
        try:
            self.assertEqual(resolve_working_directory("src"), Path("C:/project/src"))
        finally:
            settings.project_root = original_root
