from core import engine, fs
from core.cleanup_plan import EvidenceKind
from core.scanner import ScanType
from core.tests.base import TestApp
from hscommon.jobprogress.job import nulljob
import pytest


def populated_app(tmp_path):
    app = TestApp().app
    app.progress_window.create_job()
    app.appdata = str(tmp_path / "appdata")
    files = []
    for name in ["reference.bin", "duplicate.bin"]:
        path = tmp_path / name
        path.write_bytes(b"same bytes")
        file = fs.File(path)
        file.is_ref = False
        files.append(file)
    groups = engine.get_groups([engine.Match(*files, 100)])
    groups[0].prioritize(lambda file: files.index(file))
    app.results.groups = groups
    app.results.mark(groups[0].dupes[0])
    return app


def test_similarity_results_cannot_start_cleanup(tmp_path):
    app = populated_app(tmp_path)
    app.results_scan_type = ScanType.FUZZYBLOCK
    plan = app.build_cleanup_plan()
    assert all(c.evidence is EvidenceKind.SIMILARITY for c in plan.candidates)
    assert app.execute_cleanup_plan(plan, None) is False
    assert "exact-byte" in app.view.messages[-1]


def test_options_change_cannot_upgrade_similarity_evidence(tmp_path):
    app = populated_app(tmp_path)
    app.results_scan_type = ScanType.FILENAME
    app.options["scan_type"] = ScanType.CONTENTS
    assert app.build_cleanup_plan().candidates[0].evidence is EvidenceKind.SIMILARITY


def test_delete_entrypoint_opens_plan_without_removing_file(tmp_path):
    app = populated_app(tmp_path)
    seen = []
    app.view.show_cleanup_plan = seen.append
    app.results_scan_type = ScanType.CONTENTS
    app.delete_marked()
    assert len(seen) == 1
    assert seen[0].candidates[0].path.exists()


def test_cleanup_job_refreshes_results_and_retains_receipt(tmp_path):
    app = populated_app(tmp_path)
    app.results_scan_type = ScanType.CONTENTS
    plan = app.build_cleanup_plan()

    def run(jobid, function, args=()):
        function(nulljob, *args)
        app._job_completed(jobid)
        return True

    app._start_job = run
    assert app.execute_cleanup_plan(plan, tmp_path / "quarantine")
    assert app.last_cleanup_receipt.items[0].status == "quarantined"
    assert app.results.mark_count == 0
    assert app.last_cleanup_receipt.receipt_path.exists()


def test_cancelled_job_still_reports_durable_receipt(tmp_path):
    app = populated_app(tmp_path)
    app.results_scan_type = ScanType.CONTENTS
    plan = app.build_cleanup_plan()

    def run(jobid, function, args=()):
        app.progress_window.job_cancelled = True
        function(nulljob, *args)
        app._job_completed(jobid)
        return True

    app._start_job = run
    assert app.execute_cleanup_plan(plan, tmp_path / "quarantine")
    assert app.last_cleanup_receipt.items[0].status == "cancelled"
    assert plan.candidates[0].path.exists()
    assert app.results.mark_count == 1


def test_busy_cleanup_cannot_replace_running_jobs_completion(tmp_path):
    import pytest
    from core.app import JobType
    from hscommon.jobprogress.job import JobInProgressError

    app = populated_app(tmp_path)
    window = app.progress_window
    completed = []
    window._finish_func = completed.append
    window.jobid = JobType.SCAN
    window._job_running = True
    with pytest.raises(JobInProgressError):
        window.run(JobType.CLEANUP, "cleanup", lambda job: None, complete_on_cancel=True)
    window._job_running = False
    window.last_progress = None
    window.pulse()
    assert completed == [JobType.SCAN]


def hold_scan(app, monkeypatch, outcome=None):
    groups = app.results.groups
    files = list(groups[0])
    requested = []
    monkeypatch.setattr(app.directories, "has_any_file", lambda: True)
    monkeypatch.setattr(app.directories, "get_files", lambda **kwargs: files)
    monkeypatch.setattr(app.view, "show_results_window", lambda: None, raising=False)

    def scan(scanner, files, ignores, job):
        if outcome is not None:
            raise outcome
        return groups

    monkeypatch.setattr(app.SCANNER_CLASS, "get_dupe_groups", scan)

    def hold_worker(target, args=()):
        requested.append((target, args))
        app.progress_window._job_running = True

    monkeypatch.setattr(app.progress_window, "run_threaded", hold_worker)
    return requested


def test_refused_scan_preserves_existing_results_and_evidence(tmp_path, monkeypatch):
    app = populated_app(tmp_path)
    groups = app.results.groups
    app.results_scan_type = ScanType.FILENAME
    requested = hold_scan(app, monkeypatch)
    app.progress_window._job_running = True
    app.options["scan_type"] = ScanType.CONTENTS
    app.start_scanning()
    assert not requested
    assert "previous action" in app.view.messages[-1].lower()
    assert app.results.groups == groups
    assert app.results_scan_type == ScanType.FILENAME
    assert app.results.mark_count == 1


@pytest.mark.parametrize(
    "accepted,refused,evidence",
    [
        (ScanType.FILENAME, ScanType.CONTENTS, EvidenceKind.SIMILARITY),
        (ScanType.CONTENTS, ScanType.FILENAME, EvidenceKind.EXACT_CONTENT),
    ],
)
def test_refused_second_scan_cannot_relabel_accepted_results(tmp_path, monkeypatch, accepted, refused, evidence):
    app = populated_app(tmp_path)
    requested = hold_scan(app, monkeypatch)
    app.options["scan_type"] = accepted
    app.start_scanning()
    app.options["scan_type"] = refused
    app.start_scanning()
    assert len(requested) == 1
    assert "previous action" in app.view.messages[-1].lower()
    target, args = requested[0]
    app.progress_window._async_run(target, *args)
    app.progress_window.pulse()
    assert app.results_scan_type == accepted
    dupe = app.results.groups[0].dupes[0]
    assert app.build_cleanup_plan(marked=[dupe]).candidates[0].evidence is evidence


@pytest.mark.parametrize("cancelled", [False, True])
def test_unsuccessful_scan_preserves_previous_results(tmp_path, monkeypatch, cancelled):
    from hscommon.jobprogress.job import JobCancelled

    app = populated_app(tmp_path)
    groups = app.results.groups
    app.results_scan_type = ScanType.FILENAME
    outcome = JobCancelled() if cancelled else OSError("scan fixture failure")
    requested = hold_scan(app, monkeypatch, outcome)
    app.options["scan_type"] = ScanType.CONTENTS
    app.start_scanning()
    target, args = requested[0]
    app.progress_window._async_run(target, *args)
    if cancelled:
        app.progress_window.job_cancelled = True
        app.progress_window.pulse()
    else:
        with pytest.raises(OSError, match="scan fixture failure"):
            app.progress_window.pulse()
    assert app.results.groups == groups
    assert app.results_scan_type == ScanType.FILENAME
