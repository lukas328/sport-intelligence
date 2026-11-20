"""The end of a video job is handled per job kind (services/video_callbacks.py); the full paths
run in test_job_paths.py and test_matches.py."""

from __future__ import annotations

from handball_api.services import video_callbacks as cb


def test_every_video_job_kind_has_its_handlers() -> None:
    # the kinds the API starts on a video (ingest, import, analysis, sync)
    assert set(cb.ON_SUCCEEDED) == {"import", "ingest", "analysis", "sync"}
    # a failed analysis or sync leaves the file playable; any other failed job fails the file
    assert cb.ON_FAILED == {"analysis": cb._analysis_failed, "sync": cb._sync_failed}
    assert cb.ON_FAILED.get("ingest", cb._file_failed) is cb._file_failed
    assert cb.ON_FAILED.get("import", cb._file_failed) is cb._file_failed
