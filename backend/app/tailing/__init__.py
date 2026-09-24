"""File tail ingestion front door.

Watches a fixed list of log files and feeds new lines through the existing
ingest_event() pipeline. No pipeline logic is duplicated here — see
app/services/ingest_service.py for the invariant.
"""
from app.tailing.file_tailer import FileTailer  # noqa: F401

__all__ = ["FileTailer"]