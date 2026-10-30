from fman import submit_task, show_alert, show_prompt, DirectoryPaneCommand, \
                  ABORT, CANCEL, NO, YES
from fman.fs import exists, is_dir, mkdir, move_to_trash, resolve
from fman.url import as_human_readable, join, splitscheme

from .configuration import _CHECK_EXTENSION, _COMPARE_HASH, _COMPRESS_ARGS, \
                            _HASH, _SUPPORTED_EXTENSIONS

from os.path import basename

from .archive_tasks import (
    ExtractArchive,
    _7zipTaskWithProgress,
    _get_hash,
    _get_opposite_pane,
)

def _extract_archive(url, source_pane, destination_pane):
    # Keep the original default name available while handling destination prompts.
    originalName = None

    if url is None:
        workingFile = source_pane.get_file_under_cursor()
        if workingFile:
            url = workingFile

    fileName = basename(url)

    if _CHECK_EXTENSION:
        try:
            extension = fileName[fileName.rindex('.') :]
        except ValueError:
            show_alert("Failed to determine extension, aborting!")
            return

        if extension not in _SUPPORTED_EXTENSIONS:
            show_alert("Unsupported extension, aborting!")
            return

        newDirName = fileName[0 : fileName.rindex('.')]
    else:
        try:
            newDirName = fileName[0 : fileName.rindex('.')]
        except ValueError:
            message = "Archive has no extension.\n"
            message += "Click 'YES' to enter a name "
            message += "for the destination directory.\n"
            message += "Click 'NO' to use the archive name.\n"
            message += "Click 'ABORT' to abort extraction."
            choice = show_alert(
                message,
                buttons=YES | NO | ABORT,
                default_button=ABORT,
            )

            if choice == YES:
                newDirName, ok = show_prompt(
                    "Destination directory:", default=fileName
                )
                if not (newDirName and ok):
                    return
            elif choice == NO:
                newDirName = fileName
            else:
                return

    destination_url = destination_pane.get_path()
    destination_scheme, _ = splitscheme(resolve(destination_url))
    if destination_scheme != 'file://':
        show_alert("Can't extract to %s, aborting!" % destination_scheme)
        return

    new_dir_url = join(destination_url, newDirName)
    while exists(new_dir_url):
        if not originalName:
            originalName = newDirName
        message = newDirName + " already exists!\nEnter a different name?"
        choice = show_alert(
            message,
            buttons=YES | ABORT,
            default_button=ABORT,
        )
        if choice == YES:
            newDirName, ok = show_prompt(
                "Destination directory:", default=newDirName
            )
            if not (newDirName and ok):
                continue
            new_dir_url = join(destination_url, newDirName)

    try:
        mkdir(new_dir_url)
    except (FileNotFoundError, NotImplementedError):
        message = "Failed to create directory '"
        message += newDirName + "', aborting!"
        show_alert(message)
        return

    archive = as_human_readable(url)
    destination_dir = as_human_readable(new_dir_url)
    submit_task(ExtractArchive(archive, destination_dir))


class ExtractToOpposite(DirectoryPaneCommand):
    def __call__(self, url=None):
        destination_pane = _get_opposite_pane(self.pane)
        _extract_archive(url, self.pane, destination_pane)


class ExtractHere(DirectoryPaneCommand):
    def __call__(self, url=None):
        _extract_archive(url, self.pane, self.pane)
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
