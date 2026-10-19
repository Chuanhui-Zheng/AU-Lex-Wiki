import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    db_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", "postgresql://localhost/au_worklaw_atlas"
    ))
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    llm_model: str = "claude-opus-4-5"
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "anthropic"))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    enable_local_embeddings: bool = field(default_factory=lambda: os.getenv(
        "ENABLE_LOCAL_EMBEDDINGS", "false"
    ).lower() in {"1", "true", "yes"})
    enable_graph_rag: bool = field(default_factory=lambda: os.getenv(
        "ENABLE_GRAPH_RAG", "true"
    ).lower() in {"1", "true", "yes"})
    graph_max_hops: int = field(default_factory=lambda: int(os.getenv("GRAPH_MAX_HOPS", "2")))
    graph_context_sections: int = field(default_factory=lambda: int(os.getenv("GRAPH_CONTEXT_SECTIONS", "8")))
    legislation_api_base: str = "https://api.prod.legislation.gov.au/v1"
    worklaw_source_manifest: str = "config/worklaw_sources.json"
    wiki_dir: str = "wiki"
    data_dir: str = "data"
    # retrieval
    top_k_retrieve: int = 20
    top_n_rerank: int = 5
    hybrid_alpha: float = 0.7      # weight for dense vs sparse
    rrf_k: int = 60
    # chunking
    max_chunk_tokens: int = 512
    # embedding
    embed_batch_size: int = 12
    embed_dim: int = 1024

config = Config()
