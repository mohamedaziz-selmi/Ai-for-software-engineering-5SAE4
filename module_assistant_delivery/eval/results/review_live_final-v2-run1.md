# Live review check: final-v2-run1

Deliverable `demo/deliverables/M2_v2_fixed`, scored against `eval/datasets/review_demo_v2_gold.json`. Real run through the HTTP API; review served by `None` model `None`. Verdicts are after code-side evidence verification.

- Verdict accuracy: **0/13**
- Planted defects detected with verified evidence (blocker/major): **0/0**
- Findings kept: 0; dropped unverified: {}
- Wall time: 15.2 s for 13 requirements; model `None`

| Requirement | Gold | Model said | Final verdict | OK | Note |
|---|---|---|---|---|---|
| NN-1 | conforms | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| NN-2 | cannot_determine | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| NN-3 | cannot_determine | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| NN-4 | conforms/partial/cannot_determine | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| NN-5 | cannot_determine | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| REQ-001 | conforms/partial | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| REQ-002 | cannot_determine | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| REQ-003 | conforms/partial | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| REQ-004 | conforms/partial | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| REQ-005 | cannot_determine | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| REQ-006 | conforms | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| REQ-007 | cannot_determine | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |
| REQ-008 | cannot_determine | None | review_failed | no | [{"served_by": "hosted", "model": "openai/gpt-oss-120b", "error": "rate_limited"}] |

## Findings

