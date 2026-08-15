"""
Governed RAG retrieval using FAISS + local embeddings.
Retrieves policy clauses scoped by claim type.
"""
import os
from typing import List, Optional
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from app.core.config import settings
from app.core.logging import logger


# Global variables - loaded once at startup
_vector_store: Optional[FAISS] = None
_embedding_model = None


def get_embedding_model():
    """Lazy-load the local embedding model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _embedding_model = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},  # Use CPU, no GPU needed
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embedding_model


def load_policies_into_faiss() -> FAISS:
    """
    Read all policy .txt files from data/policies/,
    split into chunks, embed them, and store in FAISS.
    """
    policy_dir = settings.POLICY_DIR
    if not policy_dir.exists():
        raise FileNotFoundError(f"Policy directory not found: {policy_dir}")
    
    # Read all .txt files
    policy_files = list(policy_dir.glob("*.txt"))
    logger.info(f"Found {len(policy_files)} policy files")
    
    documents = []
    for file_path in policy_files:
        # Extract policy type from filename (health_policy.txt -> health)
        policy_type = file_path.stem.replace("_policy", "")
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Create LangChain Document with metadata
        doc = Document(
            page_content=content,
            metadata={
                "policy_type": policy_type,
                "source": str(file_path.name),
            }
        )
        documents.append(doc)
        logger.info(f"Loaded {file_path.name} ({len(content)} chars)")
    
    # Split documents into smaller chunks for better retrieval
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,      # Each chunk is ~500 characters
        chunk_overlap=50,    # 50 chars overlap between chunks
        separators=["\n\n", "\n", ".", " "],  # Split at paragraphs, then sentences
    )
    chunks = text_splitter.split_documents(documents)
    logger.info(f"Split into {len(chunks)} chunks")
    
    # Create FAISS vector store from chunks
    embeddings = get_embedding_model()
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    # Save to disk for faster reloads
    faiss_dir = settings.CHROMA_PERSIST_DIR  # Reusing this path for FAISS
    faiss_dir.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(faiss_dir))
    logger.info(f"FAISS index saved to {faiss_dir}")
    
    return vector_store


def get_vector_store() -> FAISS:
    """
    Get or create the FAISS vector store.
    Loads from disk if available, otherwise rebuilds from policy files.
    """
    global _vector_store
    
    if _vector_store is not None:
        return _vector_store
    
    faiss_dir = settings.CHROMA_PERSIST_DIR
    index_file = faiss_dir / "index.faiss"
    
    # Try to load existing index
    if index_file.exists():
        logger.info("Loading existing FAISS index from disk")
        embeddings = get_embedding_model()
        _vector_store = FAISS.load_local(
            str(faiss_dir),
            embeddings,
            allow_dangerous_deserialization=True,  # Safe since we created it
        )
        return _vector_store
    
    # Build from scratch
    logger.info("Building FAISS index from policy files")
    _vector_store = load_policies_into_faiss()
    return _vector_store


async def retrieve_policy_context(
    query: str,
    claim_type: str,
    k: int = 3,
) -> List[str]:
    """
    Retrieve relevant policy clauses for a given claim.
    
    GOVERNED: Only retrieves chunks where metadata['policy_type'] matches claim_type.
    """
    vector_store = get_vector_store()
    
    # Build filter: only search documents of matching policy type
    # FAISS doesn't support metadata filtering natively, so we:
    # 1. Retrieve more results than needed
    # 2. Filter manually by metadata
    # 3. Return up to k matching results
    
    results = vector_store.similarity_search(query, k=k * 3)
    
    # Filter by policy type (governed retrieval)
    filtered = [
        doc for doc in results
        if doc.metadata.get("policy_type") == claim_type
    ]
    
    # Take top k after filtering
    top_k = filtered[:k]
    
    if not top_k:
        logger.warning(f"No policy context found for claim_type={claim_type}")
        return []
    
    # Return formatted citations with source
    citations = []
    for doc in top_k:
        source = doc.metadata.get("source", "unknown")
        # Truncate to first 300 chars for readability
        text = doc.page_content[:300].replace("\n", " ")
        citations.append(f"[{source}] {text}...")
    
    logger.info(f"Retrieved {len(citations)} policy citations for {claim_type}")
    return citations