# Changelog

All notable changes to this project are documented in this file.

## [v0.1.0] - 2026-03-23

### Added
- FastAPI service for AWS Connect and DynamoDB integration using IAM auth.
- Queue and contact retrieval APIs with pagination/filter support.
- Sync API to persist Connect queue/contact snapshots into DynamoDB.
- Demo lifecycle APIs:
  - `POST /demo/seed`
  - `DELETE /demo/cleanup`
- DynamoDB query APIs for saved queue/contact data.
- Project documentation:
  - `README.md`
  - `requirement.prd`
  - `to-do.md`
  - `testing.md`
- Automated API tests with `pytest`.

### Changed
- Migrated startup initialization to FastAPI lifespan handlers.
- Improved demo queue behavior to idempotent creation.

### Notes
- Contact detail sync currently relies on stored demo contact markers.
