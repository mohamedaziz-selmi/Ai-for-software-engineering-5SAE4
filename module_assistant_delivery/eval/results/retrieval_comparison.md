# Retrieval comparison (dev set)

24 answerable questions (EN + FR) over `PRJ-DEMO-001_cahier_des_charges.md`; gold = the section that answers the question.
Small single-document set: differences of one or two questions are not significant.

| Model | Chunks | hit@1 | hit@3 | hit@5 | MRR | load s | index s | query ms (CPU) |
|---|---|---|---|---|---|---|---|---|
| `intfloat/multilingual-e5-base` | 13 | 0.75 | 1.00 | 1.00 | 0.868 | 60.8 | 10.6 | 170 |
