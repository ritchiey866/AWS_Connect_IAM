# Implementation Plan and Prioritized Backlog

## Planning Summary
Current implementation is functionally complete for demo and baseline usage. This backlog prioritizes production readiness using P0/P1/P2 tiers with effort estimates.

## Priority Definition
- **P0**: Must-have for safe production rollout
- **P1**: Should-have for reliability and maintainability
- **P2**: Nice-to-have optimizations and scale improvements

## Estimation Scale
- **S**: 0.5 day
- **M**: 1 day
- **L**: 2 days
- **XL**: 3+ days

## Sprint 1 (P0) - Production Safety Baseline
Target: 4-6 days

- [ ] **P0-T01 | M | API input validation hardening**  
  Add strict validation for ISO date parameters and explicit error messages for invalid format/range.

- [ ] **P0-T02 | M | Unified error response contract**  
  Standardize all HTTP error payloads (code/message/context/request_id).

- [ ] **P0-T03 | M | Global exception middleware**  
  Handle uncaught exceptions safely; avoid leaking internals in API responses.

- [ ] **P0-T04 | S | Startup config validation**  
  Validate required env vars at startup based on enabled endpoints (seed/sync/cleanup).

- [ ] **P0-T05 | M | Demo endpoint safety guard**  
  Restrict `/demo/seed` and `/demo/cleanup` behind environment flag (e.g., `ENABLE_DEMO_OPERATIONS=true`).

- [ ] **P0-T06 | M | Cleanup resilience**  
  Add retry/backoff for queue deletion and preserve partial-success reporting.

- [ ] **P0-T07 | M | Critical path tests expansion**  
  Add tests for invalid date ranges, partial cleanup failures, and sync partial-contact failures.

- [ ] **P0-T08 | M | CI baseline pipeline**  
  Add CI workflow for `compileall`, lint, and `pytest`.

## Sprint 2 (P1) - Reliability and Operability
Target: 5-7 days

- [ ] **P1-T01 | M | Structured logging + correlation IDs**  
  Add request-scoped IDs and consistent JSON logs.

- [ ] **P1-T02 | M | Dependency health endpoint**  
  Add detailed health checks for Connect and DynamoDB connectivity.

- [ ] **P1-T03 | M | Endpoint metadata in responses**  
  Include processing duration and request ID in selected endpoints.

- [ ] **P1-T04 | L | DynamoDB repository abstraction**  
  Move raw table operations into repository layer for cleaner testing and evolution.

- [ ] **P1-T05 | M | Demo marker TTL strategy**  
  Add optional TTL support for `DEMO_CONTACT` markers in non-prod.

- [ ] **P1-T06 | M | Security docs hardening**  
  Update IAM policy examples to resource-scoped ARNs and least privilege guidance.

- [ ] **P1-T07 | M | Pre-commit quality gates**  
  Add format/lint/test pre-commit hooks.

## Sprint 3 (P2) - Scale and Developer Experience
Target: 1-2 sprints

- [ ] **P2-T01 | M | Additional API filters/sorting**  
  Add queue status filter, contact initiation method filter, and response sorting controls.

- [ ] **P2-T02 | L | Token-based pagination improvements**  
  Replace/augment offset pagination where AWS APIs can use continuation tokens.

- [ ] **P2-T03 | XL | Integration test stage**  
  Add `moto`/sandbox integration tests and CI stage gating.

- [ ] **P2-T04 | M | Contract test suite**  
  Add schema contract tests for all API endpoints.

- [ ] **P2-T05 | M | Containerization and runbook**  
  Add Dockerfile, deployment examples, and operational troubleshooting docs.

- [ ] **P2-T06 | L | Optional query optimization (GSI)**  
  Evaluate and add GSIs for future query patterns (e.g., by sync timestamp).

## Dependency Notes
- `P0-T02` should be completed before `P1-T03`.
- `P0-T08` should include tests from `P0-T07`.
- `P1-T04` may require minor refactoring of existing service methods.
- `P2-T06` should be decided after observing real query patterns in logs/metrics.

## Suggested Execution Order (Top 10)
1. P0-T01  
2. P0-T04  
3. P0-T02  
4. P0-T03  
5. P0-T05  
6. P0-T06  
7. P0-T07  
8. P0-T08  
9. P1-T01  
10. P1-T02

## Delivery Checkpoints
- **Checkpoint A (end Sprint 1)**: safe production baseline with CI and robust errors.
- **Checkpoint B (end Sprint 2)**: improved observability and maintainability.
- **Checkpoint C (end Sprint 3)**: scale-ready testing and deployment ergonomics.
