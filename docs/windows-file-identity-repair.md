# Windows file identity repair

The first real Windows run, 34574814861, built all three native extensions but
failed 12 filesystem tests (547 passed). Run 34575675337's ASCII and Unicode
probe confirmed initially equal path/fstat signatures, successful exact-byte
validation and digest, followed by `File changed during read` after the move
into staging. No payload was silently discarded.

The CPython 3.12.10 implementation explains that transition:

- [win32_xstat](https://github.com/python/cpython/blob/v3.12.10/Modules/posixmodule.c#L2008)
  copies birthtime into path stat's deprecated `st_ctime`.
- [fstat](https://github.com/python/cpython/blob/v3.12.10/Python/fileutils.c#L1147)
  obtains `FILE_BASIC_INFO` and uses `ChangeTime` for `st_ctime` without that copy.
  The two timestamps often match on creation, but a rename changes ChangeTime.

Capture and subsequent named-file checks now use `file_signature`, which opens
the file and takes its full fstat signature. Reads still compare their held
handle before/after with a fresh observation of the named file. Size,
nanosecond mtime, change time, device and inode are all retained. Path/ancestor
link and reparse checks, full byte comparisons, exclusive Windows deletion,
no-replace operations and write-ahead recovery receipts remain in effect.
Older preview identities that do not match are refused; receipt restore takes
fresh identities and still verifies stored hashes before modifying any path.

Local RED: `core/tests/file_identity_test.py` produced 2 failures / 1 pass
before the repair. It reproduces the path-creation-time versus handle-change-time
boundary using real temporary-file reads, quarantine and restore, substituting
only the observed path stat timestamps. Its other regression verifies that a
change-time-only difference refuses cleanup. A real rename/digest test also
runs on every platform, including Windows.

Local GREEN: `python -m pytest core/tests hscommon/tests -q` — 566 passed,
1 skipped (this macOS Python lacks native xattr APIs). This is local evidence;
the Windows runner must run the same tests and the enhanced staging probe
before the Windows repair can be considered qualified.
