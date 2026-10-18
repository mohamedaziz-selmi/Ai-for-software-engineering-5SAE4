# Cerebro RAG Knowledge Base - full set (30 PDFs, 3 categories, synthetic)

All people, companies, jobs, proposals, reviews and numbers are **synthetic**. Created 2026-10-14. In production keep live prices, deadlines, availability and ratings in the relational database.

| Category | PDFs | Count |
|---|---|---|
| A. Client requirements | CR-01 to CR-08 | 8 |
| B. Freelancer proposals | FP-01 to FP-08 | 8 |
| C. Evaluation knowledge base | EK-01 to EK-14 | 14 |

## PDFs
- `client_requirements/CR-01_Project_Briefs_JOB-001_to_JOB-005.pdf` (5 source documents)
- `client_requirements/CR-02_Project_Briefs_JOB-006_to_JOB-010.pdf` (5 source documents)
- `client_requirements/CR-03_Requirements_Specs_and_Acceptance_Criteria.pdf` (10 source documents)
- `client_requirements/CR-04_Requirements_Specification_Writing_Guide.pdf` (1 source document)
- `client_requirements/CR-05_Acceptance_Criteria_Catalogue.pdf` (1 source document)
- `client_requirements/CR-06_Clarification_QA_JOB-001_to_JOB-005.pdf` (1 source document)
- `client_requirements/CR-07_Clarification_QA_JOB-006_to_JOB-010.pdf` (1 source document)
- `client_requirements/CR-08_Client_Evaluation_Priorities_and_Weights.pdf` (1 source document)
- `freelancer_proposals/FP-01_Freelancer_Proposals_JOB-001_to_JOB-003.pdf` (11 source documents)
- `freelancer_proposals/FP-02_Freelancer_Proposals_JOB-004_to_JOB-007.pdf` (11 source documents)
- `freelancer_proposals/FP-03_Proposals_JOB-008_to_JOB-010_and_Portfolios.pdf` (9 source documents)
- `freelancer_proposals/FP-04_Estimation_Examples_JOB-001_to_JOB-005.pdf` (1 source document)
- `freelancer_proposals/FP-05_Estimation_Examples_JOB-006_to_JOB-010.pdf` (1 source document)
- `freelancer_proposals/FP-06_Milestone_Plan_and_Payment_Schedule_Examples.pdf` (1 source document)
- `freelancer_proposals/FP-07_Technical_Approach_and_Reference_Architectures.pdf` (1 source document)
- `freelancer_proposals/FP-08_Freelancer_Availability_and_Workload_Plans.pdf` (1 source document)
- `evaluation_knowledge_base/EK-01_Scoring_Criteria_and_Skill_Matching.pdf` (3 source documents)
- `evaluation_knowledge_base/EK-02_Budget_and_Time_Estimation.pdf` (8 source documents)
- `evaluation_knowledge_base/EK-03_Risk_Analysis_Reviews_and_Proposal_Quality.pdf` (5 source documents)
- `evaluation_knowledge_base/EK-04_Technical_Competency_and_Quality_Standards.pdf` (9 source documents)
- `evaluation_knowledge_base/EK-05_Scoring_Rubric_Reference_Card.pdf` (1 source document)
- `evaluation_knowledge_base/EK-06_Worked_Scoring_Examples_Library.pdf` (1 source document)
- `evaluation_knowledge_base/EK-07_Explanation_Templates_and_Citation_Style.pdf` (1 source document)
- `evaluation_knowledge_base/EK-08_Skill_Taxonomy_and_Synonyms.pdf` (1 source document)
- `evaluation_knowledge_base/EK-09_Budget_Estimation_Reference_Ranges.pdf` (1 source document)
- `evaluation_knowledge_base/EK-10_Time_Estimation_and_Capacity_Planning.pdf` (1 source document)
- `evaluation_knowledge_base/EK-11_Risk_Register_and_Proposal_Flags.pdf` (1 source document)
- `evaluation_knowledge_base/EK-12_Fairness_Bias_and_Audit_Guidelines.pdf` (1 source document)
- `evaluation_knowledge_base/EK-13_RAG_Retrieval_and_Citation_Guide.pdf` (1 source document)
- `evaluation_knowledge_base/EK-14_Glossary_FAQ_and_Edge_Cases.pdf` (1 source document)

## Other files
- `manifest.csv` (per PDF), `manifest_entities.csv` (each JOB / PRP / FRE / PRJ / source ID -> PDF).
- `synthetic_dataset.csv` (30 proposals with expected scores, status, completeness, flags) and `synthetic_dataset/` (normalized tables, `expected_rankings.csv`, `retrieval_test_questions.csv`).
- `scoring_engine.py` (deterministic scoring) and `VALIDATION_REPORT.md`.

## Ingestion tips
Split on headings that start with a source ID (for example `PRP-007:` or `EVA-002 -`). Store `document_id`, `pdf_id`, `category`, `job_id`, `proposal_id`, `freelancer_id`, `skills` as metadata. Filter by entity before semantic search, use hybrid retrieval and measure Recall@K, MRR and nDCG@K with `retrieval_test_questions.csv`. Never let the LLM calculate scores.
