# Windows source archive fixture correction

Native run 34682937401 failed three local archive/export fixture cases before
installed qualification. The production source verifier correctly rejected bytes
that differed from the committed Git blobs. Git for Windows applies the host's
`core.autocrlf`/`core.eol` settings even to `git archive`; the test's local archive
therefore did not model GitHub's repository-byte source archive.

Reproduced independently with a CRLF checkout, an LF Git blob and `core.autocrlf=true`:
local `git archive` contained CRLF while `git show HEAD:foo` contained LF.
Only test archive generation now explicitly disables checkout conversion and
selects LF. Production verification remains byte-exact and unmodified. A new
regression proves converted bytes are rejected and the repository-byte archive
is accepted under the same Windows-style Git setting.

All 17 focused Store export tests pass locally. Actual Windows rerun remains
required; no new installed lifecycle or Store-ready package is claimed here.
