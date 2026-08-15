"""
Application configuration loaded from environment variables.
Uses FREE tier: Groq for LLM, local sentence-transformers for embeddings.
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Claims Triage Agent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    POLICY_DIR: Path = DATA_DIR / "policies"
    
    API_V1_PREFIX: str = "/api/v1"
    
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    CHROMA_PERSIST_DIR: Path = DATA_DIR / "chroma_db"
    AUDIT_DB_PATH: Path = DATA_DIR / "audit.db"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()