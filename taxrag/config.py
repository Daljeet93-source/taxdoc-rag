"""All settings come from environment variables (or a .env file) so nothing is hard-coded."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path = ROOT / ".env") -> None:
    """Tiny .env loader so we don't need an extra dependency."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    docs_dir: Path = ROOT / os.getenv("DOCS_DIR", "data/docs")
    index_dir: Path = ROOT / os.getenv("INDEX_DIR", "data/index")

    # "ollama" (fully local), "bedrock" (AWS), or "none" (keyword search only, no LLM)
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
    embed_provider: str = os.getenv("EMBED_PROVIDER", "ollama")

    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    ollama_chat_model: str = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
    ollama_embed_model: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

    aws_region: str = os.getenv("AWS_REGION", "ap-southeast-2")
    bedrock_chat_model: str = os.getenv("BEDROCK_CHAT_MODEL", "")
    bedrock_embed_model: str = os.getenv("BEDROCK_EMBED_MODEL", "amazon.titan-embed-text-v2:0")

    chunk_chars: int = int(os.getenv("CHUNK_CHARS", "900"))
    top_k: int = int(os.getenv("TOP_K", "5"))
    temperature: float = float(os.getenv("TEMPERATURE", "0"))


settings = Settings()
