from core import engine, fs
from core.cleanup_plan import EvidenceKind
from core.scanner import ScanType
from core.tests.base import TestApp
from hscommon.jobprogress.job import nulljob


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
