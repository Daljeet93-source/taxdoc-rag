"""Model providers: Ollama (local, free) or AWS Bedrock (Claude + Titan embeddings).

Both expose the same two functions, so the rest of the code doesn't care which is used:
    embed(texts) -> list[list[float]]
    chat(system, user) -> (text, usage_dict)
"""

import json
import time
import urllib.request

from .config import settings


class ProviderError(RuntimeError):
    pass


# ---------------------------------------------------------------- Ollama (local)

def _ollama_post(path: str, payload: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        settings.ollama_url + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except OSError as e:
        raise ProviderError(
            f"Could not reach Ollama at {settings.ollama_url}. Is `ollama serve` running? ({e})"
        ) from e


def ollama_embed(texts: list[str]) -> list[list[float]]:
    out = _ollama_post("/api/embed", {"model": settings.ollama_embed_model, "input": texts})
    return out["embeddings"]


def ollama_chat(system: str, user: str) -> tuple[str, dict]:
    out = _ollama_post(
        "/api/chat",
        {
            "model": settings.ollama_chat_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "format": "json",
            "stream": False,
            "options": {"temperature": settings.temperature},
        },
    )
    usage = {"input_tokens": out.get("prompt_eval_count", 0), "output_tokens": out.get("eval_count", 0)}
    return out["message"]["content"], usage


# ---------------------------------------------------------------- AWS Bedrock

_bedrock = None


def _bedrock_client():
    global _bedrock
    if _bedrock is None:
        import boto3  # imported lazily so Ollama users don't need boto3

        _bedrock = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    return _bedrock


def bedrock_embed(texts: list[str]) -> list[list[float]]:
    client = _bedrock_client()
    vectors = []
    for text in texts:  # Titan embeds one text per call
        resp = client.invoke_model(
            modelId=settings.bedrock_embed_model,
            body=json.dumps({"inputText": text, "normalize": True}),
        )
        vectors.append(json.loads(resp["body"].read())["embedding"])
    return vectors


def bedrock_chat(system: str, user: str) -> tuple[str, dict]:
    if not settings.bedrock_chat_model:
        raise ProviderError("Set BEDROCK_CHAT_MODEL in .env (copy the model or inference profile ID from the Bedrock console).")
    resp = _bedrock_client().converse(
        modelId=settings.bedrock_chat_model,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": user}]}],
        inferenceConfig={"temperature": settings.temperature, "maxTokens": 800},
    )
    text = resp["output"]["message"]["content"][0]["text"]
    usage = {"input_tokens": resp["usage"]["inputTokens"], "output_tokens": resp["usage"]["outputTokens"]}
    return text, usage


# ---------------------------------------------------------------- dispatch

def embed(texts: list[str], batch: int = 32) -> list[list[float]]:
    fn = {"ollama": ollama_embed, "bedrock": bedrock_embed}.get(settings.embed_provider)
    if fn is None:
        raise ProviderError(f"Embeddings disabled (EMBED_PROVIDER={settings.embed_provider})")
    out: list[list[float]] = []
    for i in range(0, len(texts), batch):
        out.extend(fn(texts[i : i + batch]))
    return out


def chat(system: str, user: str) -> tuple[str, dict]:
    fn = {"ollama": ollama_chat, "bedrock": bedrock_chat}.get(settings.llm_provider)
    if fn is None:
        raise ProviderError(f"LLM disabled (LLM_PROVIDER={settings.llm_provider})")
    start = time.perf_counter()
    text, usage = fn(system, user)
    usage["latency_s"] = round(time.perf_counter() - start, 2)
    return text, usage
