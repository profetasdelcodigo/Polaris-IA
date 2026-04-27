"""
Polaris IA — Learning Pipeline
Orquestador principal del ciclo de aprendizaje autónomo.
Cada ciclo: lee agenda → busca en web → limpia → tokeniza → entrena → guarda.
"""

import os
import logging
import requests
from datetime import datetime

from learning.scraper import extract_best_content
from learning.tokenizer_wrapper import text_to_token_ids
from memory.semantic_memory import save_memory, save_learning_event, get_replay_samples
from memory.supabase_client import get_supabase

logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Temas iniciales con los que Polaris IA comenzará a aprender
SEED_TOPICS = [
    "inteligencia artificial",
    "redes neuronales artificiales",
    "aprendizaje automático",
    "Python programación",
    "ciencia de datos",
    "procesamiento de lenguaje natural",
    "deep learning avanzado",
    "algoritmos de machine learning",
]


# ─────────────────────────────────────────────
#  BÚSQUEDA WEB
# ─────────────────────────────────────────────

def search_tavily(query: str) -> list[dict]:
    """
    Busca con Tavily API (optimizado para IA — devuelve texto limpio).
    Es la fuente primaria de aprendizaje.
    """
    if not TAVILY_API_KEY:
        logger.warning("⚠️  TAVILY_API_KEY no configurada")
        return []
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "advanced",
                "include_raw_content": True,
                "max_results": 5,
            },
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        # Adaptar al formato estándar
        return [
            {
                "content": r.get("raw_content") or r.get("content", ""),
                "url": r.get("url", ""),
                "title": r.get("title", ""),
            }
            for r in results
        ]
    except Exception as e:
        logger.error("❌ Tavily error: %s", e)
        return []


def search_serper(query: str) -> list[dict]:
    """
    Busca con Serper API (Google Search).
    Se usa como fuente secundaria cuando Tavily no da resultados.
    """
    if not SERPER_API_KEY:
        logger.warning("⚠️  SERPER_API_KEY no configurada")
        return []
    try:
        resp = requests.get(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY},
            params={"q": query, "gl": "es", "hl": "es", "num": 5},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        # Serper devuelve snippets, no el contenido completo
        for item in data.get("organic", []):
            results.append({
                "content": item.get("snippet", ""),
                "url": item.get("link", ""),
                "title": item.get("title", ""),
            })
        return results
    except Exception as e:
        logger.error("❌ Serper error: %s", e)
        return []


# ─────────────────────────────────────────────
#  AGENDA DE APRENDIZAJE
# ─────────────────────────────────────────────

def get_next_topic() -> str | None:
    """
    Obtiene el próximo tema pendiente de la agenda en Supabase.
    Retorna None si no hay temas pendientes.
    """
    supabase = get_supabase()
    result = (
        supabase.table("learning_agenda")
        .select("id, topic")
        .eq("status", "pending")
        .order("priority", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def mark_topic_done(topic_id: str) -> None:
    """Marca un tema como aprendido en la agenda."""
    supabase = get_supabase()
    supabase.table("learning_agenda").update({"status": "done"}).eq("id", topic_id).execute()


def add_topics_to_agenda(topics: list[str]) -> None:
    """Añade nuevos temas descubiertos a la agenda."""
    supabase = get_supabase()
    rows = [
        {"topic": t, "priority": 1, "status": "pending"}
        for t in topics
        if t.strip()
    ]
    if rows:
        supabase.table("learning_agenda").upsert(rows, on_conflict="topic").execute()
        logger.info("📋 Añadidos %d temas a la agenda", len(rows))


def seed_agenda() -> None:
    """
    Rellena la agenda con temas iniciales si está vacía.
    Solo se ejecuta una vez al inicio.
    """
    supabase = get_supabase()
    result = supabase.table("learning_agenda").select("id").limit(1).execute()
    if not result.data:
        add_topics_to_agenda(SEED_TOPICS)
        logger.info("🌱 Agenda inicializada con %d temas base", len(SEED_TOPICS))


# ─────────────────────────────────────────────
#  CICLO PRINCIPAL DE APRENDIZAJE
# ─────────────────────────────────────────────

def run_learning_cycle(trainer) -> dict:
    """
    Ejecuta un ciclo completo de aprendizaje:
    1. Obtiene un tema de la agenda
    2. Busca información con Tavily + Serper
    3. Limpia y filtra el contenido
    4. Tokeniza y entrena la red neuronal
    5. Guarda en la memoria semántica de Supabase
    6. Descubre nuevos temas y los añade a la agenda

    Args:
        trainer: Instancia de PolarisTrainer

    Retorna un diccionario con el resultado del ciclo.
    """
    cycle_result = {
        "timestamp": datetime.utcnow().isoformat(),
        "topic": None,
        "texts_processed": 0,
        "tokens_trained": 0,
        "loss": 0.0,
        "grew": False,
        "error": None,
    }

    # 1. Obtener próximo tema
    topic_record = get_next_topic()
    if not topic_record:
        logger.info("📭 Agenda vacía — reiniciando con temas base")
        seed_agenda()
        return cycle_result

    topic = topic_record["topic"]
    topic_id = topic_record["id"]
    cycle_result["topic"] = topic
    logger.info("📚 Aprendiendo sobre: '%s'", topic)

    try:
        # 2. Buscar información
        raw_results = search_tavily(topic)
        if len(raw_results) < 2:
            # Tavily no tuvo suficiente — complementar con Serper
            raw_results += search_serper(topic)

        if not raw_results:
            logger.warning("⚠️  Sin resultados para '%s'", topic)
            mark_topic_done(topic_id)
            return cycle_result

        # 3. Limpiar y filtrar contenido
        clean_results = extract_best_content(raw_results)
        cycle_result["texts_processed"] = len(clean_results)

        total_tokens = 0
        total_loss = 0.0

        for item in clean_results:
            text = item["text"]
            url = item["url"]

            # 4. Tokenizar y entrenar
            token_ids = text_to_token_ids(text, max_tokens=512)
            if len(token_ids) > 20:
                loss = trainer.train_on_tokens(token_ids)
                total_loss += loss
                total_tokens += len(token_ids)

            # 5. Guardar en memoria semántica
            save_memory(text, topic=topic, source_url=url)
            save_learning_event(topic=topic, content=text, source_url=url)

        cycle_result["tokens_trained"] = total_tokens
        cycle_result["loss"] = round(total_loss / max(1, len(clean_results)), 4)

        # 6. Marcar tema como aprendido
        mark_topic_done(topic_id)

        # 7. Verificar si la red creció en este ciclo
        neurons_before = trainer.metrics.total_growth_events
        cycle_result["grew"] = trainer.metrics.total_growth_events > neurons_before

        logger.info(
            "✅ Ciclo completado | Tema: '%s' | Tokens: %d | Loss: %.4f | Neuronas: %d",
            topic,
            total_tokens,
            cycle_result["loss"],
            trainer.model.count_neurons(),
        )

    except Exception as e:
        logger.error("❌ Error en ciclo de aprendizaje: %s", e)
        cycle_result["error"] = str(e)

    return cycle_result
