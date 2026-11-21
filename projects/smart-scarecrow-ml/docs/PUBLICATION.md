# Publication and provenance notes

This public case study was prepared for the owner’s engineering-research-portfolio at their explicit request. It contains code, documentation, attribution and curated results. Source audio, model binaries, private capture logs and machine-specific inventories are excluded. The earlier local-only development phase is documented in the technical report.

The 29 pre-existing project files remain unchanged and have a full local backup. Four pre-existing Arduino sketches were copied from the owner's Arduino directory into `firmware/originals/`, with source paths and SHA-256 in its local inventory. No original Arduino file was edited.

Before public publication, choose an appropriate license for owner-controlled code. This task does not assign a license to the user's original work. External libraries retain their own licenses; their source is not vendored here. ESC-50 audio and attribution retain the upstream data licenses. XC1002645 and the self-recorded voice file must not be presumed freely redistributable.

The `.gitignore` excludes audio formats, raw/processed audio folders, captures, `.venv`, backups, build products and local model/run files. Ignore rules do not remove files already tracked in an existing repository and do not prevent `git add -f`; review the staged file list before publishing. Curated experiment summaries and ESC-50-derived figures under `docs/` include source attribution in the dataset card. Full private experiment outputs should remain local.

The source archive excludes audio, model binaries, private capture logs, `.venv`, backups, raw/local experimental images, machine-specific inventories and generated compiler output. It contains code, reproducibility instructions, manifests, public-data attribution and curated results. Source-group IDs and official folds are included so readers can audit the evaluation.
