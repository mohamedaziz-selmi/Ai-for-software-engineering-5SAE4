# Delivery review tuning: accuracy and stability (2026-10-19)

Live runs of the hosted reviewer (`openai/gpt-oss-120b`, Groq free tier) on the two demo deliverables.
*Original* = as stored by the app at the time. *Re-verified* = the same model outputs, with the rejected
quotes checked again by the current evidence verifier (offline, no model call).

| Run | Deliverable | Prompt / change | Original | Re-verified |
|---|---|---|---|---|
| demo-m2-v1-defects | v1 | baseline prompt (2026-10-18) | 13/13 | 13/13 |
| demo-m2-v2-fixed | v2 | baseline prompt (2026-10-18) | 11/13 | 11/13 |
| stab-v1-run1 | v1 | prompt v2 + seed 7 | 11/13 | 12/13 |
| stab-v1-run2 | v1 | prompt v2 + seed 7 | 12/13 | 12/13 |
| stab-v2-run1 | v2 | prompt v2 + seed 7 | 12/13 | 12/13 |
| stab-v2-run2 | v2 | prompt v2 + seed 7 | 11/13 | 11/13 |
| v3-v1-run1 | v1 | prompt v3 (rejected) | 12/13 | 12/13 |
| v3-v1-run2 | v1 | prompt v3 (rejected) | 13/13 | 13/13 |
| v3-v2-run1 | v2 | prompt v3 (rejected) | 10/13 | 11/13 |
| v3-v2-run2 | v2 | prompt v3 (rejected) | 8/13 (3 failed: rate limit) | 9/13 |

## Re-verified verdict per requirement

| Requirement | demo-m2-v1-defects | demo-m2-v2-fixed | stab-v1-run1 | stab-v1-run2 | stab-v2-run1 | stab-v2-run2 | v3-v1-run1 | v3-v1-run2 | v3-v2-run1 | v3-v2-run2 |
|---|---|---|---|---|---|---|---|---|---|---|
| NN-1 | violates | conforms | violates | violates | conforms | conforms | violates | violates | conforms | conforms |
| NN-2 | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine |
| NN-3 | cannot_determine | partial | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine |
| NN-4 | violates | partial | violates | violates | partial | violates | violates | violates | violates | violates |
| NN-5 | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine |
| REQ-001 | conforms | conforms | conforms | conforms | conforms | conforms | conforms | conforms | conforms | conforms |
| REQ-002 | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine |
| REQ-003 | conforms | conforms | conforms | conforms | conforms | conforms | partial | partial | partial | partial |
| REQ-004 | conforms | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | conforms | cannot_determine | conforms |
| REQ-005 | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine |
| REQ-006 | conforms | conforms | conforms | conforms | conforms | conforms | conforms | conforms | conforms | review_failed |
| REQ-007 | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | review_failed |
| REQ-008 | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | cannot_determine | review_failed |
