# ADR 0001: Inference Runtime Strategy for MVP

- Status: Accepted
- Date: 2026-02-10

## Context

The project documentation set stated an offline-first and privacy-by-design target, while the running app path was effectively hardwired to Modal inference. This created a mismatch between documented intent and executable behavior.

At the same time, MVP delivery needs a practical default that keeps developer velocity and demo reliability high.

## Decision

For MVP, runtime backend selection is explicit and configurable via `INFERENCE_BACKEND`.

Supported values:

- `auto` (default): try `modal` first, then fallback to `transformers`
- `modal`: use only Modal backend
- `transformers`: use only local Transformers backend

Prescription and lab extraction both use the same fallback strategy.

FastAPI is deferred and is not part of the current MVP runtime path.

## Consequences

Positive:

- Runtime behavior now matches documented implementation.
- A single backend outage does not immediately break extraction flows.
- Teams can choose deployment mode per environment without code changes.

Tradeoffs:

- `auto` can still fail if both configured backends are unavailable.
- Local fallback requires environment prerequisites (`HF_TOKEN`, compatible hardware).

## Notes for future work

- Evaluate whether `transformers` should become default-first for strict offline deployments.
- If FastAPI is introduced later, add a new ADR defining service boundaries and ownership.
