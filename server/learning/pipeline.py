"""
Polaris IA — Learning Pipeline v3 (Autónomo + Progreso Real)
Ciclo completamente autónomo con callbacks de progreso en tiempo real.
"""

import os
import logging
import requests
import json
import random
from datetime import datetime

from learning.scraper import extract_best_content
from learning.tokenizer_wrapper import text_to_token_ids
from memory.semantic_memory import save_memory, save_learning_event
from memory.supabase_client import get_supabase

logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GROQ_API_KEY   = os.getenv("AI_API_KEY")

# ─── Temas semilla — Todas las capacidades objetivo ───────────────────────
SEED_TOPICS = [
    # Imágenes
    "generación de imágenes con inteligencia artificial",
    "modelos de difusión stable diffusion funcionamiento",
    "GANs redes generativas adversariales",
    "DALL-E arquitectura generación de imágenes",
    "redes convolucionales CNN imágenes",
    "ControlNet imagen a imagen AI",
    "VAE autoencoder variacional imágenes",
    # Texto
    "modelos de lenguaje grande LLM GPT",
    "transformers atención BERT arquitectura",
    "fine-tuning modelos de lenguaje",
    "RLHF reinforcement learning from human feedback",
    "RAG retrieval augmented generation",
    "embeddings vectores semánticos texto",
    # Web
    "desarrollo web moderno HTML CSS JavaScript",
    "React Next.js frameworks frontend",
    "APIs REST GraphQL diseño",
    "WebSockets comunicación tiempo real",
    "generación automática de código AI GitHub Copilot",
    # Apps
    "desarrollo Android Kotlin Jetpack Compose",
    "React Native Flutter aplicaciones multiplataforma",
    "arquitectura MVVM aplicaciones móviles",
    "apps generadas con inteligencia artificial",
    # Video
    "generación de video con inteligencia artificial",
    "Sora OpenAI video generation",
    "modelos de difusión para video",
    "video frame interpolation AI",
    # Audio
    "síntesis de voz texto a voz TTS",
    "generación de música con IA",
    "Whisper reconocimiento de voz",
    # IA General
    "inteligencia artificial historia evolución",
    "aprendizaje por refuerzo reinforcement learning",
    "AGI inteligencia artificial general",
    "memory augmented neural networks",
    "neurociencia computacional cerebro",
]


# ─────────────────────────────────────────────
#  CURIOSIDAD AUTÓNOMA
# ─────────────────────────────────────────────

def generate_new_topics(learned_topic: str, learned_text: str) -> list[str]:
    """Usa Groq para generar 5 nuevos temas relacionados con lo aprendido."""
    if not GROQ_API_KEY:
        return _fallback_topics(learned_topic)

    prompt = f"""Eres el motor de curiosidad de Polaris IA.

Acabas de aprender sobre: "{learned_topic}"
Fragmento: "{learned_text[:400]}..."

Polaris aprenderá a: generar imágenes, texto, código, webs, apps, video y audio con IA.

Genera 5 temas ESPECÍFICOS en español, relacionados con lo aprendido y las capacidades anteriores.
Responde SOLO con JSON array: ["tema 1", "tema 2", "tema 3", "tema 4", "tema 5"]"""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama3-8b-8192", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200, "temperature": 0.9},
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        start, end = content.find("["), content.rfind("]") + 1
        if start >= 0 and end > start:
            topics = json.loads(content[start:end])
            topics = [t.strip() for t in topics if isinstance(t, str) and len(t) > 3]
            logger.info("🧠 +%d temas generados desde '%s'", len(topics), learned_topic)
            return topics[:5]
    except Exception as e:
        logger.warning("⚠️  Groq curiosidad: %s", e)

    return _fallback_topics(learned_topic)


def _fallback_topics(base: str) -> list[str]:
    return [f"{base} aplicaciones", f"{base} historia", f"avances en {base}"] + random.sample(SEED_TOPICS, 2)


# ─────────────────────────────────────────────
#  BÚSQUEDA WEB
# ─────────────────────────────────────────────

def search_tavily(query: str) -> list[dict]:
    if not TAVILY_API_KEY:
        return []
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": TAVILY_API_KEY, "query": query, "search_depth": "advanced", "include_raw_content": True, "max_results": 5},
            timeout=20,
        )
        resp.raise_for_status()
        return [{"content": r.get("raw_content") or r.get("content", ""), "url": r.get("url", ""), "title": r.get("title", "")} for r in resp.json().get("results", [])]
    except Exception as e:
        logger.error("❌ Tavily: %s", e)
        return []


def search_serper(query: str) -> list[dict]:
    if not SERPER_API_KEY:
        return []
    try:
        resp = requests.get(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": SERPER_API_KEY},
            params={"q": query, "gl": "es", "hl": "es", "num": 5},
            timeout=20,
        )
        resp.raise_for_status()
        return [{"content": i.get("snippet", ""), "url": i.get("link", ""), "title": i.get("title", "")} for i in resp.json().get("organic", [])]
    except Exception as e:
        logger.error("❌ Serper: %s", e)
        return []


# ─────────────────────────────────────────────
#  AGENDA
# ─────────────────────────────────────────────

def get_next_topic() -> dict | None:
    try:
        r = get_supabase().table("learning_agenda").select("id, topic, priority").eq("status", "pending").order("priority", desc=True).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logger.error("❌ get_next_topic: %s", e)
        return None


def mark_topic_done(topic_id: str) -> None:
    try:
        get_supabase().table("learning_agenda").update({"status": "done"}).eq("id", topic_id).execute()
    except Exception as e:
        logger.error("❌ mark_topic_done: %s", e)


def add_topics_to_agenda(topics: list[str], priority: int = 2) -> None:
    try:
        rows = [{"topic": t.strip()[:200], "priority": priority, "status": "pending"} for t in topics if t.strip()]
        if rows:
            get_supabase().table("learning_agenda").upsert(rows, on_conflict="topic").execute()
            logger.info("📋 +%d temas en agenda", len(rows))
    except Exception as e:
        logger.error("❌ add_topics: %s", e)


def count_pending_topics() -> int:
    try:
        r = get_supabase().table("learning_agenda").select("id", count="exact").eq("status", "pending").execute()
        return r.count or 0
    except Exception:
        return 0


def seed_agenda() -> None:
    try:
        r = get_supabase().table("learning_agenda").select("id").limit(1).execute()
        if not r.data:
            add_topics_to_agenda(SEED_TOPICS, priority=1)
            logger.info("🌱 Agenda inicializada con %d temas", len(SEED_TOPICS))
    except Exception as e:
        logger.error("❌ seed_agenda: %s", e)


# ─────────────────────────────────────────────
#  CICLO PRINCIPAL — AUTÓNOMO + PROGRESO REAL
# ─────────────────────────────────────────────

def run_learning_cycle(trainer, progress_callback=None) -> dict:
    """
    Ciclo completo de aprendizaje. progress_callback(phase, step, total, topic)
    se llama en cada fase real para mostrar progreso verdadero en el monitor.
    """
    def report(phase: str, step: int, total: int = 7, topic: str = ""):
        if progress_callback:
            try:
                progress_callback(phase, step, total, topic)
            except Exception:
                pass

    cycle_result = {
        "timestamp": datetime.utcnow().isoformat(),
        "topic": None,
        "texts_processed": 0,
        "tokens_trained": 0,
        "loss": 0.0,
        "grew": False,
        "new_topics_generated": 0,
        "error": None,
    }

    # 1. Obtener tema
    report("fetching_topic", 1)
    topic_record = get_next_topic()
    if not topic_record:
        logger.info("📭 Agenda vacía — regenerando...")
        add_topics_to_agenda(SEED_TOPICS, priority=1)
        topic_record = get_next_topic()
        if not topic_record:
            return cycle_result

    topic    = topic_record["topic"]
    topic_id = topic_record["id"]
    cycle_result["topic"] = topic
    report("fetching_topic", 1, 7, topic)
    logger.info("📚 Aprendiendo: '%s'", topic)

    try:
        # 2. Buscar en la web
        report("searching", 2, 7, topic)
        raw_results = search_tavily(topic)
        if len(raw_results) < 2:
            raw_results += search_serper(topic)

        if not raw_results:
            logger.warning("⚠️  Sin resultados para '%s'", topic)
            mark_topic_done(topic_id)
            return cycle_result

        # 3. Limpiar contenido
        report("cleaning", 3, 7, topic)
        clean_results = extract_best_content(raw_results)
        cycle_result["texts_processed"] = len(clean_results)
        total_texts = max(len(clean_results), 1)

        total_tokens = 0
        total_loss   = 0.0
        best_text    = ""

        for idx, item in enumerate(clean_results):
            text = item["text"]
            url  = item["url"]
            if len(text) > len(best_text):
                best_text = text

            # 4. Entrenar (progreso dinámico por cada texto)
            train_pct = 3 + int((idx / total_texts) * 2)
            report("training", min(train_pct, 5), 7, topic)

            token_ids = text_to_token_ids(text, max_tokens=512)
            if len(token_ids) > 20:
                n_before = trainer.model.count_neurons()
                loss = trainer.train_on_tokens(token_ids)
                total_loss   += loss
                total_tokens += len(token_ids)
                if trainer.model.count_neurons() > n_before:
                    cycle_result["grew"] = True

            # 5. Guardar en memoria
            report("saving_memory", 5, 7, topic)
            save_memory(text, topic=topic, source_url=url)
            save_learning_event(topic=topic, content=text, source_url=url)

        cycle_result["tokens_trained"] = total_tokens
        cycle_result["loss"] = round(total_loss / max(1, len(clean_results)), 4)
        mark_topic_done(topic_id)

        # 6. Generar nuevos temas (curiosidad)
        report("generating_topics", 6, 7, topic)
        new_topics = generate_new_topics(topic, best_text)
        if new_topics:
            add_topics_to_agenda(new_topics, priority=2)
            cycle_result["new_topics_generated"] = len(new_topics)

        if count_pending_topics() < 5:
            add_topics_to_agenda(random.sample(SEED_TOPICS, 5), priority=1)

        report("done", 7, 7, topic)
        logger.info("✅ '%s' | Tokens:%d | Loss:%.4f | Neuronas:%d | +%d temas",
            topic, total_tokens, cycle_result["loss"],
            trainer.model.count_neurons(), cycle_result["new_topics_generated"])

    except Exception as e:
        logger.error("❌ Error ciclo: %s", e)
        cycle_result["error"] = str(e)

    return cycle_result
