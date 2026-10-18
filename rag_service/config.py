from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SERVICE_DIR.parent
PDF_DIR = PROJECT_DIR / "rag" / "pdfs"
FULL_DATASET_DIR = PROJECT_DIR / "rag" / "cerebro_rag_full_30"
PDF_SOURCE_DIRS = (
    PDF_DIR,
    FULL_DATASET_DIR / "client_requirements",
    FULL_DATASET_DIR / "freelancer_proposals",
    FULL_DATASET_DIR / "evaluation_knowledge_base",
)
CHROMA_DIR = SERVICE_DIR / "chroma_db"
COLLECTION_NAME = "cerebro_proposal_knowledge"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Chunks are intentionally conservative for the first semantic-only baseline.
# Keep these fixed while evaluating retrieval, then tune them using the supplied
# retrieval_test_questions.csv before adding any hybrid/BM25 layer.
CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
