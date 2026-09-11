# Scan evidence review fix

The independent review of b5655d6 found that a refused second scan could relabel a running filename scan as Contents. Four behavioral tests failed before the fix: rejected-request result retention, accepted-worker evidence, and cancellation/error retention. Six existing application cleanup tests remained passing.

The worker now produces a pending tuple containing its actual scan type, groups and discarded count. Successful completion publishes that tuple and refreshes the table on the UI thread. Requests rejected as busy never clear or relabel existing results. Cancelled/failed scans preserve the previous result/evidence pair. File classes and the hardlink option are captured with the accepted scanner options.

Final verification (macOS arm64, existing Python 3.12.7 environment): 563 core/hscommon tests passed, one existing native-metadata skip. Six offscreen Qt tests passed. Black, flake8 and diff checks passed. Five new cases cover refused existing results, both directions of refused scan-mode changes, cancellation and error. One old test expected eager result clearing and was updated to the deliberate preserve-until-success behavior.

Real Windows qualification run 34574814861 built native extensions, then exposed 12 filesystem failures (547 tests passed), before this fix. Those Windows failures remain separate and are not cleared by this local scan-evidence fix. Qt5.15.2 maintenance and package/license gates remain open.
