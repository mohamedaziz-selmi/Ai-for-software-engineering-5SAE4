# Freelancer–Project Matching Audit and Evaluation Report

## Data audit
- Rows: 2484
- Columns: 4
- Duplicate rows: 0
- Missing values: {'ID': 0, 'Resume_str': 0, 'Resume_html': 0, 'Category': 0}
- Empty descriptions: 0
- Text length summary: {'min': 21, 'max': 38842, 'mean': 6295.3087761674715}
- Categories: {'INFORMATION-TECHNOLOGY': 120, 'BUSINESS-DEVELOPMENT': 120, 'ADVOCATE': 118, 'CHEF': 118, 'FINANCE': 118, 'ENGINEERING': 118, 'ACCOUNTANT': 118, 'FITNESS': 117, 'AVIATION': 117, 'SALES': 116, 'HEALTHCARE': 115, 'CONSULTANT': 115, 'BANKING': 115, 'CONSTRUCTION': 112, 'PUBLIC-RELATIONS': 111, 'HR': 110, 'DESIGNER': 107, 'ARTS': 103, 'TEACHER': 102, 'APPAREL': 97, 'DIGITAL-MEDIA': 96, 'AGRICULTURE': 63, 'AUTOMOBILE': 36, 'BPO': 22}

## Evaluation setup
No explicit project–freelancer relevance labels existed in the supplied resume dataset. To preserve a valid evaluation workflow, a proxy evaluation set was created using category-level relevance labels. This is documented in `evaluation_pairs.csv` and is intended for exploratory retrieval benchmarking only, not as a ground-truth production target.

## TF-IDF baseline
- Precision@3: 0.0833
- Precision@5: 0.1000
- Precision@10: 0.1042

## Sentence Transformer model
- Precision@3: 0.1806
- Precision@5: 0.1667
- Precision@10: 0.1500

## Decision
The improved model is the recommended production choice because it captures semantic similarity beyond keyword overlap. The evaluation is a proxy and should be replaced with manually assessed labels for business deployment.
