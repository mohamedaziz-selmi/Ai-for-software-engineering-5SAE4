# Sentiment data preparation

This folder contains downloaded source datasets and a preprocessing pipeline only—no classifier training.

Run from this folder:

```powershell
..\rag_service\.venv\Scripts\python.exe .\prepare_sentiment_data.py
```

The script reads CSV files without modifying them and writes its outputs to `data/processed/`.

## Train and serve

```powershell
..\rag_service\.venv\Scripts\python.exe .\train_model.py
..\rag_service\.venv\Scripts\python.exe -m uvicorn api:app --port 8001
```

`train_model.py` compares TF-IDF + Logistic Regression with TF-IDF + calibrated Linear SVM using validation macro F1, saves the winning artifacts in `models/`, and writes precision, recall, F1, accuracy, and confusion-matrix reports.
