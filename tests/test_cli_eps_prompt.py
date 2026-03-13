from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auditoria_pdf.cli import AuditCliApplication, EpsMethodPrompter, RootDirectoryPrompter


class _CaptureSingleExecutor:
    def __init__(self) -> None:
        self.args = None
        self.pdf_paths = None

    def execute(self, args, pdf_paths) -> int:
        self.args = args
        self.pdf_paths = pdf_paths
        return 0


class _FailBatchExecutor:
    def execute(self, args, root_dir) -> int:
        raise AssertionError("No debe ejecutar modo masivo en este test.")


class _FailRootPrompter:
    def prompt(self) -> Path:
        raise AssertionError("No debe pedir root-dir en este test.")


class _EpsPrompterStub:
    def __init__(self, selected_eps: str) -> None:
        self._selected_eps = selected_eps
        self.calls = 0
        self._normalizer = EpsMethodPrompter()

    def prompt(self) -> str:
        self.calls += 1
        return self._selected_eps

    def normalize(self, value: str) -> str:
        return self._normalizer.normalize(value)


class AuditCliEpsPromptTest(unittest.TestCase):
    def test_run_prompts_eps_when_not_provided(self) -> None:
        single = _CaptureSingleExecutor()
        eps_prompter = _EpsPrompterStub("nueva_eps")

        app = AuditCliApplication(
            eps_method_prompter=eps_prompter,
            root_directory_prompter=_FailRootPrompter(),
            single_executor=single,
            batch_executor=_FailBatchExecutor(),
        )

        exit_code = app.run(["--fev", "C:\\temp\\FEV_demo.pdf"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(eps_prompter.calls, 1)
        self.assertEqual(single.args.eps, "nueva_eps")
        self.assertEqual(len(single.pdf_paths), 1)

    def test_run_does_not_prompt_eps_when_numeric_argument_is_provided(self) -> None:
        single = _CaptureSingleExecutor()
        eps_prompter = _EpsPrompterStub("nueva_eps")

        app = AuditCliApplication(
            eps_method_prompter=eps_prompter,
            root_directory_prompter=_FailRootPrompter(),
            single_executor=single,
            batch_executor=_FailBatchExecutor(),
        )

        exit_code = app.run(["--eps", "1", "--fev", "C:\\temp\\FEV_demo.pdf"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(eps_prompter.calls, 0)
        self.assertEqual(single.args.eps, "coosalud")

    def test_run_maps_numeric_argument_to_sanitas(self) -> None:
        single = _CaptureSingleExecutor()
        eps_prompter = _EpsPrompterStub("nueva_eps")

        app = AuditCliApplication(
            eps_method_prompter=eps_prompter,
            root_directory_prompter=_FailRootPrompter(),
            single_executor=single,
            batch_executor=_FailBatchExecutor(),
        )

        exit_code = app.run(["--eps", "3", "--fev", "C:\\temp\\FEV_demo.pdf"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(eps_prompter.calls, 0)
        self.assertEqual(single.args.eps, "sanitas")


class EpsMethodPrompterTest(unittest.TestCase):
    @patch("builtins.input", side_effect=["2"])
    def test_prompt_accepts_numeric_option(self, mocked_input) -> None:
        selected = EpsMethodPrompter().prompt()
        self.assertEqual(selected, "nueva_eps")
        self.assertEqual(mocked_input.call_count, 1)

    @patch("builtins.input", side_effect=["3"])
    def test_prompt_accepts_numeric_option_for_sanitas(self, mocked_input) -> None:
        selected = EpsMethodPrompter().prompt()
        self.assertEqual(selected, "sanitas")
        self.assertEqual(mocked_input.call_count, 1)

    @patch("builtins.input", side_effect=["invalid", "1"])
    def test_prompt_retries_until_valid_numeric_value(self, mocked_input) -> None:
        selected = EpsMethodPrompter().prompt()
        self.assertEqual(selected, "coosalud")
        self.assertEqual(mocked_input.call_count, 2)

    def test_normalize_accepts_legacy_name_alias(self) -> None:
        selected = EpsMethodPrompter().normalize("NUEVA EPS")
        self.assertEqual(selected, "nueva_eps")


class RootDirectoryPrompterTest(unittest.TestCase):
    @patch("builtins.input", side_effect=["", "C:\\no_existe\\x"])
    def test_prompt_retries_when_input_is_empty(self, mocked_input) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mocked_input.side_effect = ["", temp_dir]
            selected = RootDirectoryPrompter().prompt()
            self.assertEqual(selected, Path(temp_dir))
            self.assertEqual(mocked_input.call_count, 2)

    def test_prompt_removes_invisible_characters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dirty = f"\u200b{temp_dir}\u200f"
            with patch("builtins.input", side_effect=[dirty]) as mocked_input:
                selected = RootDirectoryPrompter().prompt()
                self.assertEqual(selected, Path(temp_dir))
                self.assertEqual(mocked_input.call_count, 1)


if __name__ == "__main__":
    unittest.main()
