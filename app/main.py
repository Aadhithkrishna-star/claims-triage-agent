"""
FastAPI application entry point.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.api import routes


def create_application() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Enterprise AI agent for regulated insurance claims triage",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(routes.router, prefix=settings.API_V1_PREFIX)
    
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        settings.POLICY_DIR.mkdir(parents=True, exist_ok=True)
        settings.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        
        # PHASE 3: Pre-load FAISS index
        from app.services.rag.retriever import get_vector_store
        try:
            get_vector_store()
            logger.info("FAISS vector store loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load FAISS index: {e}")
        
        # PHASE 5: Initialize audit database
        from app.services.audit.logger import init_audit_db
        try:
            init_audit_db()
            logger.info("Audit database initialized")
        except Exception as e:
            logger.warning(f"Could not initialize audit database: {e}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info(f"Shutting down {settings.APP_NAME}")
    
    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
