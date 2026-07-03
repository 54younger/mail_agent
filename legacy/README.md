# Legacy — archived Flutter/Dart desktop app

This directory holds the **original Flutter/Dart implementation** of mail_agent
(Riverpod + ObjectBox + `enough_mail`, Windows-first desktop).

It is **archived for reference only** and is no longer built or maintained. The project
has been rearchitected into a web app with front/back separation — **React frontend +
Python (FastAPI) backend** — living in `../frontend/` and `../backend/`.

## Why it was replaced

See the root `PLAN.md`. Summary of the pivot:

- Dropped AI semantic search + AI folder-classification (and the ONNX/embedding/model
  catalog/HNSW machinery behind them).
- Kept AI translation.
- Went all-in on the 求职看板 (job-application board).
- Switched from a single Flutter desktop binary to a distributable, self-hosted
  React + Python web app (each user runs their own backend against a local SQLite
  data folder).

## What still ports (domain knowledge, not code)

- IMAP sync flow + the **163/126 RFC 2971 `ID`-command-before-SELECT** quirk
  (`lib/services/mail_sync_service.dart`).
- The IMAP **error taxonomy** and Chinese user hints (`lib/core/imap_error.dart`).
- Data model shapes: `Account`, `EmailMessage`, `JobApplication` (`JobStatus` enum +
  timeline) (`lib/data/models/`).

The old planning doc is preserved here as `PLAN.md`; the old app README as
`README.flutter.md`; original setup notes as `SETUP.md`.
