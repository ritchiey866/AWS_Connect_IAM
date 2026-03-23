# Testing Strategy

## 1. Objectives
- Verify API correctness for Connect read, sync, demo lifecycle, and DynamoDB query flows.
- Catch regressions quickly with fast local tests.
- Provide confidence for deployment by layering tests from unit to integration.

## 2. Test Scope

### In Scope
- API endpoint responses, status codes, schema shape.
- Service-level filtering/pagination logic.
- Error handling for invalid input and AWS client exceptions.
- Demo seed/cleanup control flow and DynamoDB marker behavior.

### Out of Scope (for now)
- Full end-to-end telecom validation of live outbound contact completion.
- Production load/performance benchmarking.

## 3. Test Pyramid

### A) Unit Tests (Primary, fast)
- Target: pure functions and service logic (date parsing, filtering, payload mapping).
- Mock AWS SDK (`boto3` clients/resources).
- Validate boundary conditions and failure branches.

### B) API Tests (Current baseline)
- Use FastAPI `TestClient`.
- Replace live service object with fake/mocked service.
- Validate endpoint contracts and query parameter behavior.

### C) Integration Tests (Planned)
- Option 1: `moto` for DynamoDB-focused integration.
- Option 2: dedicated AWS sandbox account for Connect + DynamoDB integration tests.
- Run in CI nightly or on demand due to external dependencies.

## 4. Current Coverage Baseline
- Existing tests validate:
  - queue endpoint behavior,
  - contact endpoint filters,
  - demo seed and cleanup flows,
  - DynamoDB data endpoints.
- Baseline command:
  - `python -m pytest -q`

## 5. Recommended Additional Test Cases

## API Behavior
- [ ] `GET /connect/contacts` returns `400` when `from_date > to_date`.
- [ ] `GET /connect/queues` with offset beyond result set returns empty items, correct total.
- [ ] `/sync/connect-data` handles partially unavailable contact IDs gracefully.

## Demo Lifecycle
- [ ] `/demo/seed` is idempotent for queue creation across repeated runs.
- [ ] `/demo/cleanup` reports partial queue deletion failures in `failed_queue_deletes`.
- [ ] `/demo/cleanup` still deletes contact markers when one queue deletion fails.

## DynamoDB Query Endpoints
- [ ] `start_sk` pagination returns expected next page and `next_sk`.
- [ ] Empty partition query returns `count=0` and `items=[]`.

## 6. Test Data Strategy
- Use deterministic fake IDs and timestamps in unit/API tests.
- For integration tests, isolate resources per run (prefix with run ID).
- Clean up all created AWS resources post-test to avoid leakage/cost.

## 7. Environments
- Local developer environment:
  - run compile + lint + pytest.
- CI environment:
  - same baseline checks,
  - optional integration stage gated by credentials.
- AWS sandbox:
  - controlled account with scoped IAM and budget alerts.

## 8. Tooling and Automation
- Test framework: `pytest`
- API harness: FastAPI/Starlette `TestClient`
- Future additions:
  - coverage reporting (`pytest-cov`),
  - integration tagging (`-m integration`),
  - CI matrix for Python versions.

## 9. Entry/Exit Criteria

### Entry Criteria
- Dependencies installed.
- Environment variables documented.
- Test doubles/mocks updated for interface changes.

### Exit Criteria
- All unit/API tests pass.
- No critical linter/type errors.
- Critical paths validated:
  - seed,
  - sync,
  - query,
  - cleanup.

## 10. Commands
```bash
python -m compileall app tests
python -m pytest -q
```
