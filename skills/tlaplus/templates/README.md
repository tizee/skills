# <Feature> TLA+ spec

## Question

One sentence. Name the bug class, not the feature.

## Scope and assumptions

- Nodes, items, and constants used by the model.
- Failure model: crash, timeout, duplicate delivery, reorder, partition, clock skew.
- What is deliberately not modeled, and why.

## Model

| Action | Code | Notes |
| --- | --- | --- |
| `Init` | | |
| `Claim` | `src/...` | |
| `Complete` | `src/...` | |

## Properties

- `TypeOK`: every variable stays in its intended domain.
- Safety: nothing bad happens. Name the invariant.
- Liveness: something good eventually happens. Name the fairness assumption.

## Run

```bash
# With a local tla2tools.jar
java -cp tla2tools.jar tlc2.TLC -config <Feature>.cfg <Feature>.tla

# Or with the agent's TLA+ skill runner
bash <skill-dir>/scripts/tlc <Feature>.tla
```

## Results

- Pass or counterexample.
- States generated, distinct states, search depth.
- The shortest trace, if a property failed.

## Findings

- Root cause in code, not only in the model.
- Regression test added.
- Design or constraint changed.

## Limits

- Bounded constants or bounded search depth.
- Assumptions that the code does not enforce.
- Follow-up models that are still needed.
