"""Run 7-Zip tasks and read archive hashes."""

from os import name as osname
from os.path import basename

import re
import subprocess

from fman import PLATFORM, Task, show_alert
from fman.url import as_human_readable

import core.fs.zip

from .configuration import _USER_7ZIP
from .extract_batch import ExtractFailure, ExtractJob, format_extract_summary
from .seven_zip_errors import describe_7zip_failure

# fman++ renamed this attribute; upstream fman keeps the original name.
_BINARY_ATTR = (
    "SEVEN_ZIP_BINARY"
    if hasattr(core.fs.zip, "SEVEN_ZIP_BINARY")
    else "_7ZIP_BINARY"
)
_FMAN_7ZIP = getattr(core.fs.zip, _BINARY_ATTR)


class _7zipTaskWithProgress(Task):
    def run_7zip_with_progress(self, args, failure_hint: str = "", **kwargs):
        try:
            self._run_7zip(args, **kwargs)
        except core.fs.zip._7zipError as error:
            message = "7-Zip failed:\n" + describe_7zip_failure(
                error.output or "", error.returncode
            )
            if failure_hint:
                message += "\n" + failure_hint
            show_alert(message)

    def _run_7zip(self, args, progress_offset: int = 0, **kwargs):
        if _USER_7ZIP:
            setattr(core.fs.zip, _BINARY_ATTR, _USER_7ZIP)
        try:
            with core.fs.zip._7zip(args, pty=True, **kwargs) as process:
                for line in process.stdout_lines:
                    try:
                        self.check_canceled()
                    except Task.Canceled:
                        process.kill()
                        raise
                    match = re.match(r"\r? *(\d{1,3})% ", line)
                    if match:
                        progress = progress_offset + int(match.group(1))
                        if progress > self.get_progress():
                            self.set_progress(progress)
        finally:
            if _USER_7ZIP:
                setattr(core.fs.zip, _BINARY_ATTR, _FMAN_7ZIP)


class ExtractArchives(_7zipTaskWithProgress):
    def __init__(
        self,
        jobs: list[ExtractJob],
        skipped: list[str],
        failures: list[ExtractFailure],
    ) -> None:
        title = (
            "Extracting " + basename(jobs[0].archive_path)
            if len(jobs) == 1
            else f"Extracting {len(jobs)} archives"
        )
        super().__init__(title, size=100 * max(len(jobs), 1))
        self._jobs = jobs
        self._skipped = skipped
        self._failures = failures

    def __call__(self) -> None:
        for index, job in enumerate(self._jobs):
            archive_name = basename(job.archive_path)
            self.set_text(archive_name)
            args = ["x", job.archive_path, "-o" + job.dest_path]
            try:
                self._run_7zip(args, progress_offset=100 * index)
            except core.fs.zip._7zipError as error:
                reason = describe_7zip_failure(error.output or "", error.returncode)
                reason += (
                    "\nFiles extracted before the error are in "
                    + job.dest_path
                    + "."
                )
                self._failures.append(ExtractFailure(archive_name, reason))
            self.set_progress(100 * (index + 1))

        summary = format_extract_summary(self._failures, self._skipped)
        if summary:
            show_alert(summary)


def _get_hash(url, hash_type="crc32", consider_names=False):
    # Valid values for hash_type: crc32, crc64, sha1, sha256, blake2sp
    startupinfo = None
    if osname == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    # Considering names isn't practical when comparing directories because
    # it results in a mismatch if only the directory names differ.
    reg_hash_search = re.compile(r"for data:", re.U).search
    hash_index = 3
    reg_err_match = re.compile(
        r"^(Error:.+|.+     Data Error?|Sub items Errors:.+)", re.U
    ).match

    seven_zip_binary = _USER_7ZIP if _USER_7ZIP else _FMAN_7ZIP
    working_file = as_human_readable(url)
    command = '"%s" h "-scrc%s" "%s"' % (
        seven_zip_binary,
        hash_type,
        working_file,
    )
    if PLATFORM == "Windows":
        command += " -sccWIN"

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        bufsize=1,
        stdin=subprocess.PIPE,
        startupinfo=startupinfo,
    )
    error_line = ""

    with proc.stdout as out:
        for line in iter(out.readline, b""):
            line = str(line, "utf8")
            if reg_err_match(line):
                error_line = line + "".join(out)
                break
            if reg_hash_search(line):
                data_hash = line.split()[hash_index]

    return_code = proc.wait()
    if return_code or error_line:
        show_alert(
            "%s: Get hash failed:\nReturn value: %s\n%s"
            % (basename(working_file), str(return_code), error_line)
        )
        return None
    return data_hash


def _get_opposite_pane(pane):
    panes = pane.window.get_panes()
    return panes[(panes.index(pane) + 1) % len(panes)]
