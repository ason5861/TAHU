"""Synthetic npm layouts: never run shims, npm, or a model in default tests."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tahu.agent import AgentError, CodexAgent, resolve_codex_executable


class CliDiscoveryTests(unittest.TestCase):
    def fixture(self, root, arch="x64", optional=None):
        shim = root / "codex.cmd"
        shim.write_text("@echo SHIM_MUST_NEVER_EXECUTE")
        package = root / "node_modules" / "@openai" / "codex"
        package.mkdir(parents=True)
        info = {"name": "@openai/codex", "version": "test"}
        (package / "package.json").write_text(json.dumps(info))
        target = package
        if optional:
            modules = package / "node_modules" if optional == "nested" else root / "node_modules"
            target = modules / "@openai" / ("codex-win32-" + arch)
            target.mkdir(parents=True)
            info["optionalDependencies"] = {"@openai/codex-win32-" + arch: "npm:@openai/codex@test-win32-" + arch}
            (package / "package.json").write_text(json.dumps(info))
            (target / "package.json").write_text(json.dumps({"name": "@openai/codex", "version": "test-win32-" + arch}))
        triple = ("x86_64" if arch == "x64" else "aarch64") + "-pc-windows-msvc"
        binary = target / "vendor" / triple / ("bin" if optional else "codex") / "codex.exe"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"synthetic-not-an-executable")
        return shim, package, binary

    def resolve(self, shim, machine="AMD64", system="win32"):
        with patch("tahu.agent.shutil.which", return_value=str(shim)), patch("tahu.agent.sys.platform", system), patch("tahu.agent.platform.machine", return_value=machine):
            return resolve_codex_executable()

    def test_native_path_preserved(self):
        with patch("tahu.agent.shutil.which", return_value=str(Path("codex.exe").absolute())):
            self.assertEqual(resolve_codex_executable(), str(Path("codex.exe").absolute()))

    def test_windows_layouts_and_architectures(self):
        for optional in (None, "nested", "hoisted"):
            for arch, machine in (("x64", "AMD64"), ("arm64", "ARM64")):
                with self.subTest(optional=optional, arch=arch), tempfile.TemporaryDirectory() as directory:
                    shim, _, binary = self.fixture(Path(directory), arch, optional)
                    self.assertEqual(self.resolve(shim, machine), str(binary.resolve()))

    def test_initializer_runs_only_native_version_before_environment_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            shim, _, binary = self.fixture(Path(directory))
            with patch("tahu.agent.shutil.which", return_value=str(shim)), patch("tahu.agent.sys.platform", "win32"), patch("tahu.agent.platform.machine", return_value="AMD64"), patch("tahu.agent.subprocess.run", return_value=SimpleNamespace(stdout="test-cli\n")) as run, patch("tahu.agent.proposal_environment") as env:
                agent = CodexAgent("test")
                self.assertEqual(run.call_args.args[0], [str(binary.resolve()), "--version"])
                self.assertEqual(agent.executable, str(binary.resolve()))
                self.assertNotIn("shell", run.call_args.kwargs)
                env.assert_not_called()

    def test_missing_or_wrong_package_fails_closed(self):
        for damage in ("missing_binary", "wrong_identity", "malformed_metadata", "oversized_metadata"):
            with self.subTest(damage=damage), tempfile.TemporaryDirectory() as directory:
                shim, package, binary = self.fixture(Path(directory))
                if damage == "missing_binary":
                    binary.unlink()
                else:
                    (package / "package.json").write_text({"wrong_identity": '{"name":"other"}', "malformed_metadata": "[", "oversized_metadata": "x" * 65537}[damage])
                with self.assertRaisesRegex(AgentError, "^native_codex_executable_required$"):
                    self.resolve(shim)

    def test_optional_version_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            shim, _, binary = self.fixture(Path(directory), optional="hoisted")
            (binary.parents[3] / "package.json").write_text('{"name":"@openai/codex-win32-x64","version":"other"}')
            with self.assertRaises(AgentError):
                self.resolve(shim)

    def test_no_batch_or_unknown_platform_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            shim, _, _ = self.fixture(Path(directory))
            for file, machine, system in ((shim.with_suffix(".bat"), "AMD64", "win32"), (shim, "unknown", "win32"), (shim, "AMD64", "linux"), (shim.with_name("other.cmd"), "AMD64", "win32")):
                with self.subTest(file=file, machine=machine, system=system), self.assertRaises(AgentError):
                    self.resolve(file, machine, system)
        with patch("tahu.agent.shutil.which", return_value=None), self.assertRaises(AgentError):
            resolve_codex_executable()

    def test_binary_symlink_outside_package_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            shim, _, binary = self.fixture(Path(directory))
            outside = Path(directory) / "outside.exe"
            outside.write_bytes(b"synthetic")
            binary.unlink()
            try:
                binary.symlink_to(outside)
            except OSError:
                self.skipTest("host does not permit file symlinks")
            with self.assertRaises(AgentError):
                self.resolve(shim)
