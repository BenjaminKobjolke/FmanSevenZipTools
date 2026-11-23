"""Pure values and formatting for extracting several archives at once."""

from dataclasses import dataclass
from os.path import splitext


FAILED_TO_EXTRACT_HEADER = "Failed to extract {count} archive(s):"
SKIPPED_FILES_HEADER = "Skipped (not an archive):"


@dataclass(frozen=True)
class ExtractJob:
    archive_path: str
    dest_path: str


@dataclass(frozen=True)
class ExtractFailure:
    archive_name: str
    reason: str


def destination_name(file_name: str, supported_extensions: list[str]) -> str | None:
    """Return the basename before its supported final extension."""
    name, extension = splitext(file_name)
    if not extension or extension not in supported_extensions:
        return None
    return name


def format_extract_summary(
    failures: list[ExtractFailure], skipped: list[str]
) -> str:
    """Format one end-of-batch message, with archive failures before skipped items."""
    sections = []
    if failures:
        lines = [FAILED_TO_EXTRACT_HEADER.format(count=len(failures))]
        lines.extend(
            f"{failure.archive_name}: {failure.reason}" for failure in failures
        )
        sections.append("\n".join(lines))
    if skipped:
        sections.append("\n".join([SKIPPED_FILES_HEADER, *skipped]))
    return "\n\n".join(sections)
