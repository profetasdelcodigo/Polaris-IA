"""
Polaris IA — Semantic Memory
Memoria semántica con sentence-transformers + pgvector en Supabase.
La IA convierte cada texto aprendido en un vector y lo guarda.
Cuando necesita "recordar" algo, busca por similitud semántica.
"""

import logging
import uuid
from datetime import datetime

from sentence_transformers import SentenceTransformer

from memory.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Modelo de embeddings: 90MB, 384 dimensiones — rápido y eficiente
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_embedder: SentenceTransformer | None = None


def get_embedder() -> SentenceTransformer:
    """Singleton del modelo de embeddings."""
    global _embedder
    if _embedder is None:
        logger.info("⏳ Cargando modelo de embeddings '%s'...", EMBEDDING_MODEL)
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("✅ Modelo de embeddings listo")
    return _embedder


def save_memory(content: str, topic: str = "", source_url: str = "") -> str:
    """
    Convierte el texto en un vector y lo guarda en Supabase (tabla semantic_memory).

    Args:
        content:    Texto a memorizar.
        topic:      Tema del texto (ej: "inteligencia artificial").
        source_url: URL de donde se obtuvo el texto.

    Retorna el UUID del registro guardado.
    """
    supabase = get_supabase()
    embedder = get_embedder()

    # Generar embedding
    vector = embedder.encode(content[:2000]).tolist()  # Limitar a 2000 chars

    record_id = str(uuid.uuid4())
    supabase.table("semantic_memory").insert({
        "id": record_id,
        "content": content[:5000],
        "topic": topic,
        "source_url": source_url,
        "embedding": vector,
        "learned_at": datetime.utcnow().isoformat(),
    }).execute()

    logger.info("🧠 Memoria guardada | Tema: '%s' | Source: %s", topic, source_url[:60])
    return record_id


def search_memory(query: str, threshold: float = 0.6, limit: int = 5) -> list[dict]:
    """
    Busca en la memoria semántica por similitud al query.

    Args:
        query:     Texto de consulta (lo que la IA quiere "recordar").
        threshold: Mínima similitud (0-1). 0.6 = moderadamente similar.
        limit:     Máximo de resultados.

    Retorna lista de registros relevantes con su similitud.
    """
    supabase = get_supabase()
    embedder = get_embedder()

    query_vector = embedder.encode(query).tolist()

    try:
        result = supabase.rpc("match_memory", {
            "query_embedding": query_vector,
            "match_threshold": threshold,
            "match_count": limit,
        }).execute()
        return result.data or []
    except Exception as e:
        logger.error("❌ Error buscando en memoria semántica: %s", e)
        return []


def save_learning_event(topic: str, content: str, source_url: str) -> None:
    """
    Registra en el historial de aprendizaje qué aprendió la IA, cuándo y de dónde.
    Esta tabla sirve para el replay buffer persistente en Supabase.
    """
    supabase = get_supabase()
    supabase.table("learning_history").insert({
        "id": str(uuid.uuid4()),
        "topic": topic,
        "source_url": source_url,
        "content": content[:5000],
        "learned_at": datetime.utcnow().isoformat(),
    }).execute()


def get_replay_samples(limit: int = 20) -> list[dict]:
    """
    Obtiene muestras aleatorias del historial de aprendizaje para el replay buffer.
    Estas muestras se mezclan con los datos nuevos durante el entrenamiento.
    """
    supabase = get_supabase()
    result = (
        supabase.table("learning_history")
        .select("topic, content, source_url")
        .order("learned_at", desc=False)
        .limit(limit)
        .execute()
    )
    return result.data or []


def get_memory_stats() -> dict:
    """Retorna estadísticas de la memoria semántica."""
    supabase = get_supabase()
    try:
        count_result = (
            supabase.table("semantic_memory")
            .select("id", count="exact")
            .execute()
        )
        history_result = (
            supabase.table("learning_history")
            .select("id", count="exact")
            .execute()
        )
        return {
            "semantic_memories": count_result.count or 0,
            "learning_events": history_result.count or 0,
        }
    except Exception:
        return {"semantic_memories": 0, "learning_events": 0}
