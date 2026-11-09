import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "sevenziptools"
    / "seven_zip_errors.py"
)
SPEC = importlib.util.spec_from_file_location("seven_zip_errors", MODULE_PATH)
seven_zip_errors = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seven_zip_errors)


class Describe7ZipFailureTests(unittest.TestCase):
    def test_extracts_error_under_errors_section(self):
        output = """7-Zip 26.00
ERRORS:
Unexpected end of archive
Physical Size = 52195795
Characteristics = Local"""

        self.assertEqual(
            "Unexpected end of archive",
            seven_zip_errors.describe_7zip_failure(output, 2),
        )

    def test_extracts_error_line(self):
        output = "ERROR: Wrong password : x.mp4"

        self.assertEqual(
            "ERROR: Wrong password : x.mp4",
            seven_zip_errors.describe_7zip_failure(output, 2),
        )

    def test_ignores_carriage_return_progress_fragments(self):
        output = (
            "Extracting archive: archive.zip\r 14% 4 Open\r"
            "ERRORS:\rUnexpected end of archive\rPhysical Size = 52195795"
        )

        self.assertEqual(
            "Unexpected end of archive",
            seven_zip_errors.describe_7zip_failure(output, 2),
        )

    def test_falls_back_to_exit_code(self):
        self.assertEqual(
            "7-Zip exit code 2",
            seven_zip_errors.describe_7zip_failure("", 2),
        )


if __name__ == "__main__":
    unittest.main()
