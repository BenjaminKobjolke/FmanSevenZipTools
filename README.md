# SevenZipTools

A fork of https://github.com/kairanaquazi/SevenZipTools2

A plugin for [fman](https://fman.io) that replicates a few of 7-zip's context menu functions.

## Testing

This plugin has only been tested on Windows 10 64-bit.

## Commands added:

### Extract here

“Extract here” and “Extract to opposite” extract every selected archive. If no files are
selected, they extract the archive under the cursor. When a destination folder already exists,
choose a new name, skip that archive, or cancel the whole batch. Extraction continues after an
archive fails, then one summary lists failures and selected files or folders that were skipped
because they are not archives.
