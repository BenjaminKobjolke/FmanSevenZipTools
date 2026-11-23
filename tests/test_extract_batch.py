import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "sevenziptools" / "extract_batch.py"
SPEC = importlib.util.spec_from_file_location("extract_batch", MODULE_PATH)
extract_batch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(extract_batch)


class DestinationNameTests(unittest.TestCase):
    def test_uses_name_without_last_supported_extension(self):
        supported_extensions = [".zip", ".7z"]

        self.assertEqual(
            "a", extract_batch.destination_name("a.zip", supported_extensions)
        )
        self.assertEqual(
            "a.tar", extract_batch.destination_name("a.tar.7z", supported_extensions)
        )

    def test_returns_none_without_a_supported_extension(self):
        supported_extensions = [".zip", ".7z"]

        self.assertIsNone(
            extract_batch.destination_name("a.txt", supported_extensions)
        )
        self.assertIsNone(
            extract_batch.destination_name("README", supported_extensions)
        )


class FormatExtractSummaryTests(unittest.TestCase):
    def test_returns_empty_when_there_are_no_failures_or_skips(self):
        self.assertEqual("", extract_batch.format_extract_summary([], []))

    def test_formats_failures(self):
        failures = [extract_batch.ExtractFailure("bad.zip", "Wrong password")]

        self.assertEqual(
            "Failed to extract 1 archive(s):\nbad.zip: Wrong password",
            extract_batch.format_extract_summary(failures, []),
        )

    def test_formats_skipped_files(self):
        self.assertEqual(
            "Skipped (not an archive):\nnotes.txt\nphotos",
            extract_batch.format_extract_summary([], ["notes.txt", "photos"]),
        )

    def test_lists_failures_before_skipped_files(self):
        failures = [extract_batch.ExtractFailure("bad.zip", "Corrupt archive")]

        self.assertEqual(
            "Failed to extract 1 archive(s):\nbad.zip: Corrupt archive\n\n"
            "Skipped (not an archive):\nnotes.txt",
            extract_batch.format_extract_summary(failures, ["notes.txt"]),
        )


if __name__ == "__main__":
    unittest.main()
