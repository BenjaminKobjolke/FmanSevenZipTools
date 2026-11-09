"""Extract concise failure details from raw 7-Zip output."""

import re


_NAME_VALUE_LINE = re.compile(r"^.+ = .+$")


def describe_7zip_failure(output: str, returncode: int) -> str:
    """Return the error lines from 7-Zip output or its exit code."""
    pieces = [piece.strip() for piece in re.split(r"[\r\n]", output)]
    errors = []
    in_errors_section = False

    for piece in pieces:
        if not piece:
            in_errors_section = False
            continue

        if piece == "ERRORS:":
            in_errors_section = True
            continue

        if in_errors_section and _NAME_VALUE_LINE.match(piece):
            in_errors_section = False

        if piece.startswith("ERROR:") or in_errors_section:
            if piece not in errors:
                errors.append(piece)

    return "\n".join(errors) if errors else f"7-Zip exit code {returncode}"
