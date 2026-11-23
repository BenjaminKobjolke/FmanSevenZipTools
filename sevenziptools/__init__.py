from fman import submit_task, show_alert, show_prompt, DirectoryPaneCommand, \
                  ABORT, CANCEL, NO, YES
from fman.fs import exists, is_dir, mkdir, move_to_trash, resolve
from fman.url import as_human_readable, join, splitscheme

from .configuration import _CHECK_EXTENSION, _COMPARE_HASH, _COMPRESS_ARGS, \
                            _HASH, _SUPPORTED_EXTENSIONS

from os.path import basename
from .extract_batch import ExtractFailure, ExtractJob, destination_name

from .archive_tasks import (
    ExtractArchives,
    _7zipTaskWithProgress,
    _get_hash,
    _get_opposite_pane,
)

_DESTINATION_DIRECTORY_PROMPT = "Destination directory:"

def _extract_archives(url, source_pane, destination_pane):
    if url:
        urls = [url]
    else:
        urls = source_pane.get_selected_files()
        if not urls:
            cursor_file = source_pane.get_file_under_cursor()
            urls = [cursor_file] if cursor_file else []
    if not urls:
        return

    destination_url = destination_pane.get_path()
    destination_scheme, _ = splitscheme(resolve(destination_url))
    if destination_scheme != 'file://':
        show_alert("Can't extract to %s, aborting!" % destination_scheme)
        return

    skipped = []
    failures = []
    planned = []
    claimed_names = set()

    for archive_url in urls:
        file_name = basename(archive_url)
        if is_dir(archive_url):
            skipped.append(file_name)
            continue

        if _CHECK_EXTENSION:
            new_dir_name = destination_name(file_name, _SUPPORTED_EXTENSIONS)
            if new_dir_name is None:
                skipped.append(file_name)
                continue
        else:
            extension = file_name.rfind('.')
            if extension >= 0:
                new_dir_name = file_name[:extension]
            else:
                message = "Archive has no extension.\n"
                message += "Click 'YES' to enter a name "
                message += "for the destination directory.\n"
                message += "Click 'NO' to use the archive name.\n"
                message += "Click 'ABORT' to skip this archive."
                choice = show_alert(
                    message,
                    buttons=YES | NO | ABORT,
                    default_button=ABORT,
                )

                if choice == YES:
                    new_dir_name, ok = show_prompt(
                        _DESTINATION_DIRECTORY_PROMPT, default=file_name
                    )
                    if not (new_dir_name and ok):
                        continue
                elif choice == NO:
                    new_dir_name = file_name
                else:
                    continue

        skip_archive = False
        while True:
            new_dir_url = join(destination_url, new_dir_name)
            if not exists(new_dir_url) and new_dir_name not in claimed_names:
                break

            message = new_dir_name + " already exists!\n"
            message += "Click 'YES' to enter a different name.\n"
            message += "Click 'NO' to skip this archive.\n"
            message += "Click 'ABORT' to cancel all."
            choice = show_alert(
                message,
                buttons=YES | NO | ABORT,
                default_button=ABORT,
            )
            if choice == YES:
                entered_name, ok = show_prompt(
                    _DESTINATION_DIRECTORY_PROMPT, default=new_dir_name
                )
                if not (entered_name and ok):
                    continue
                new_dir_name = entered_name
            elif choice == NO:
                skip_archive = True
                break
            else:
                return

        if skip_archive:
            continue
        claimed_names.add(new_dir_name)
        planned.append((archive_url, file_name, new_dir_name))

    jobs = []
    for archive_url, file_name, new_dir_name in planned:
        new_dir_url = join(destination_url, new_dir_name)
        try:
            mkdir(new_dir_url)
        except (FileNotFoundError, NotImplementedError):
            failures.append(
                ExtractFailure(
                    file_name,
                    "Failed to create directory '" + new_dir_name + "'.",
                )
            )
            continue
        jobs.append(
            ExtractJob(
                as_human_readable(archive_url),
                as_human_readable(new_dir_url),
            )
        )

    submit_task(ExtractArchives(jobs, skipped, failures))


class ExtractToOpposite(DirectoryPaneCommand):
    def __call__(self, url=None):
        destination_pane = _get_opposite_pane(self.pane)
        _extract_archives(url, self.pane, destination_pane)


class ExtractHere(DirectoryPaneCommand):
    def __call__(self, url=None):
        _extract_archives(url, self.pane, self.pane)
class CreateArchive(_7zipTaskWithProgress):
    def __init__(self, zip_path, src_path):
        super().__init__('Compressing ' + basename(src_path), size=100)
        self._zip_path = zip_path
        self._cwd = src_path
    def __call__(self):
        args = _COMPRESS_ARGS + [self._zip_path, '.']
        self.run_7zip_with_progress(args, cwd=self._cwd)

class CompressToOpposite(DirectoryPaneCommand):
    def __call__(self, url=None):

        sourceDirUrl = self.pane.get_path()
        archiveName = basename(sourceDirUrl) + '.7z'

        oppositePane = _get_opposite_pane(self.pane)
        oppositePaneUrl = oppositePane.get_path()

        archiveUrl = join(oppositePaneUrl, archiveName)

        sourceDir = as_human_readable(sourceDirUrl)
        archive = as_human_readable(archiveUrl)

        if exists(archiveUrl):

            if is_dir(archiveUrl):
                message = archiveName + " exists and is a directory, aborting!"
                show_alert(message)
                return

            choice = show_alert("Archive exists!\nReplace?",
                                buttons = YES | CANCEL,
                                default_button = CANCEL)
            if choice == YES:
                try:
                    move_to_trash(archiveUrl)
                except NotImplementedError:
                    show_alert("Failed to delete archive, aborting!")
                    return

            elif choice == CANCEL:
                return

        submit_task(CreateArchive(archive, sourceDir))
        oppositePane.reload()

        return

class GetHash(DirectoryPaneCommand):
    def __call__(self, url=None):

        if url is None:
            workingFile = self.pane.get_file_under_cursor()
            if workingFile:
                url = workingFile

        hash = _get_hash(url, hash_type=_HASH)

        if hash:
            show_alert(hash)

        return

class CompareFiles(DirectoryPaneCommand):
    def __call__(self, url=None):

        if url is None:
            workingFile = self.pane.get_file_under_cursor()
            if workingFile:
                url = workingFile

        oppositePane = _get_opposite_pane(self.pane)
        oppositePaneUrl = oppositePane.get_file_under_cursor()

        # Considering names isn't practical when comparing directories because
        #  it results in a mismatch if only the names of the directories
        #  being compared differ.
#        if is_dir(url) and is_dir(oppositePaneUrl):
#            considerNames=True
#        else:
#            considerNames=False
        considerNames=False

        thisHash = _get_hash(url, hash_type=_COMPARE_HASH,
                             consider_names=considerNames)
        thatHash = _get_hash(oppositePaneUrl, hash_type=_COMPARE_HASH,
                             consider_names=considerNames)

        if thisHash == thatHash:
            show_alert("Files match.")
        else:
            show_alert("Files differ.")

        return
