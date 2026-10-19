from dataclasses import dataclass
import os

@dataclass(frozen=True)
class ServiceConfig:
    gateway_port: int = int(os.getenv("GATEWAY_PORT", "8900"))
    fraud_port: int = int(os.getenv("FRAUD_SERVICE_PORT", "8901"))
    job_port: int = int(os.getenv("JOB_DESCRIPTION_SERVICE_PORT", "8902"))
    demand_port: int = int(os.getenv("DEMAND_SERVICE_PORT", "8903"))
    product_port: int = int(os.getenv("PRODUCT_LISTING_SERVICE_PORT", "8904"))
    frontend_port: int = int(os.getenv("FRONTEND_PORT", "8905"))
    host: str = os.getenv("CEREBRO_HOST", "127.0.0.1")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    local_llm_model: str = os.getenv("LOCAL_LLM_MODEL", "gemma3:4b")

CONFIG = ServiceConfig()
