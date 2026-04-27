"""
Polaris IA — Learning Pipeline v2 (Autónomo)
Ciclo de aprendizaje completamente autónomo:
1. Elige el próximo tema de la agenda
2. Busca en la web (Tavily → Serper)
3. Limpia, tokeniza y entrena la red neuronal
4. Guarda en memoria semántica
5. Usa Groq para GENERAR nuevos temas relacionados (curiosidad infinita)
6. Repite para siempre — incluso con la PC apagada
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

TAVILY_API_KEY  = os.getenv("TAVILY_API_KEY")
SERPER_API_KEY  = os.getenv("SERPER_API_KEY")
GROQ_API_KEY    = os.getenv("AI_API_KEY")

# ─── Temas semilla — Cubre todas las capacidades objetivo ─────────────────
SEED_TOPICS = [
    # 🖼️  GENERACIÓN DE IMÁGENES
    "generación de imágenes con inteligencia artificial",
    "modelos de difusión stable diffusion funcionamiento",
    "GANs redes generativas adversariales",
    "DALL-E arquitectura generación de imágenes",
    "Midjourney técnicas de prompting",
    "procesamiento de imágenes visión por computadora",
    "redes convolucionales CNN imágenes",
    "ControlNet imagen a imagen AI",
    "VAE autoencoder variacional imágenes",

    # 📝  GENERACIÓN DE TEXTO
    "modelos de lenguaje grande LLM GPT",
    "transformers atención BERT arquitectura",
    "generación de texto con redes neuronales",
    "fine-tuning modelos de lenguaje",
    "tokenización NLP procesamiento texto",
    "RLHF reinforcement learning from human feedback",
    "RAG retrieval augmented generation",
    "embeddings vectores semánticos texto",

    # 🌐  DESARROLLO WEB
    "desarrollo web moderno HTML CSS JavaScript",
    "React Next.js frameworks frontend",
    "APIs REST GraphQL diseño",
    "bases de datos SQL NoSQL diseño",
    "arquitectura microservicios backend",
    "WebSockets comunicación tiempo real",
    "CSS animaciones diseño responsivo",
    "generación automática de código AI GitHub Copilot",

    # 📱  DESARROLLO DE APPS
    "desarrollo Android Kotlin Jetpack Compose",
    "desarrollo iOS Swift SwiftUI",
    "React Native Flutter aplicaciones multiplataforma",
    "arquitectura MVVM aplicaciones móviles",
    "UX UI diseño aplicaciones móviles",
    "publicación APK Google Play Store",
    "apps generadas con inteligencia artificial",

    # 🎬  GENERACIÓN DE VIDEO
    "generación de video con inteligencia artificial",
    "Sora OpenAI video generation",
    "Runway ML video synthesis",
    "modelos de difusión para video",
    "síntesis de video deepfake técnicas",
    "animación 3D automatizada con IA",
    "video frame interpolation AI",

    # 🎵  GENERACIÓN DE AUDIO
    "síntesis de voz texto a voz TTS",
    "generación de música con IA",
    "clonación de voz ElevenLabs",
    "Whisper reconocimiento de voz",

    # 🤖  IA GENERAL Y FUNDAMENTOS
    "inteligencia artificial historia evolución",
    "redes neuronales artificiales funcionamiento",
    "aprendizaje por refuerzo reinforcement learning",
    "computación cuántica algoritmos",
    "ética inteligencia artificial sesgos",
    "AGI inteligencia artificial general",
    "memory augmented neural networks",
    "neurociencia computacional cerebro",
]


# ─────────────────────────────────────────────
#  CURIOSIDAD AUTÓNOMA — Generar nuevos temas
# ─────────────────────────────────────────────

def generate_new_topics(learned_topic: str, learned_text: str) -> list[str]:
    """
    Usa Groq para generar 5 temas nuevos relacionados con lo que Polaris
    acaba de aprender. Esto crea un bucle de curiosidad infinita:
    aprende algo → genera más temas → aprende esos → genera más → ...
    """
    if not GROQ_API_KEY:
        return _fallback_topics(learned_topic)

    prompt = f"""Eres el motor de curiosidad de Polaris IA, un sistema de inteligencia artificial autónoma.

Acabas de aprender sobre: "{learned_topic}"
Fragmento aprendido: "{learned_text[:400]}..."

Polaris IA está siendo entrenada para eventualmente:
- Generar imágenes (como Stable Diffusion, DALL-E)
- Generar texto, código y contenido (como GPT)
- Crear sitios web y aplicaciones
- Generar videos y audio
- Desarrollar apps móviles (Android/iOS)

Genera exactamente 5 temas de investigación nuevos y ESPECÍFICOS que:
1. Estén relacionados con lo que se acaba de aprender
2. Contribuyan al conocimiento en alguna de las capacidades objetivo arriba
3. Sean lo suficientemente específicos para buscar en internet
4. Estén en español
5. Varíen entre diferentes dominios cuando sea posible

Responde ÚNICAMENTE con un JSON array de strings, sin explicaciones:
["tema 1", "tema 2", "tema 3", "tema 4", "tema 5"]"""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.9,
            },
            timeout=15,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Extraer el JSON del response
        start = content.find("[")
        end   = content.rfind("]") + 1
        if start >= 0 and end > start:
            topics = json.loads(content[start:end])
            topics = [t.strip() for t in topics if isinstance(t, str) and len(t) > 3]
            logger.info("🧠 Curiosidad generó %d nuevos temas desde '%s'", len(topics), learned_topic)
            return topics[:5]
    except Exception as e:
        logger.warning("⚠️  Groq curiosidad falló: %s — usando fallback", e)

    return _fallback_topics(learned_topic)


def _fallback_topics(base_topic: str) -> list[str]:
    """Genera temas por combinación cuando Groq no está disponible."""
    expansions = [
        f"{base_topic} aplicaciones prácticas",
        f"{base_topic} historia y origen",
        f"{base_topic} futuro investigación",
        f"avances recientes en {base_topic}",
        f"{base_topic} impacto en la sociedad",
    ]
    # Mezclar con algunos temas aleatorios del seed para mantener diversidad
    randoms = random.sample(SEED_TOPICS, min(2, len(SEED_TOPICS)))
    return expansions[:3] + randoms


# ─────────────────────────────────────────────
#  BÚSQUEDA WEB
# ─────────────────────────────────────────────

def search_tavily(query: str) -> list[dict]:
    """Busca con Tavily API (fuente primaria — texto limpio optimizado para IA)."""
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
            timeout=20,
        )
        resp.raise_for_status()
        return [
            {
                "content": r.get("raw_content") or r.get("content", ""),
                "url": r.get("url", ""),
                "title": r.get("title", ""),
            }
            for r in resp.json().get("results", [])
        ]
    except Exception as e:
        logger.error("❌ Tavily error: %s", e)
        return []


def search_serper(query: str) -> list[dict]:
    """Busca con Serper API (fuente secundaria — Google Search)."""
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
        return [
            {
                "content": item.get("snippet", ""),
                "url": item.get("link", ""),
                "title": item.get("title", ""),
            }
            for item in resp.json().get("organic", [])
        ]
    except Exception as e:
        logger.error("❌ Serper error: %s", e)
        return []


# ─────────────────────────────────────────────
#  AGENDA DE APRENDIZAJE
# ─────────────────────────────────────────────

def get_next_topic() -> dict | None:
    """Obtiene el próximo tema pendiente de mayor prioridad."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("learning_agenda")
            .select("id, topic, priority")
            .eq("status", "pending")
            .order("priority", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error("❌ Error obteniendo tema: %s", e)
        return None


def mark_topic_done(topic_id: str) -> None:
    """Marca un tema como aprendido."""
    try:
        get_supabase().table("learning_agenda").update({"status": "done"}).eq("id", topic_id).execute()
    except Exception as e:
        logger.error("❌ Error marcando tema: %s", e)


def add_topics_to_agenda(topics: list[str], priority: int = 2) -> None:
    """Añade nuevos temas a la agenda (ignora duplicados)."""
    try:
        supabase = get_supabase()
        rows = [
            {"topic": t.strip()[:200], "priority": priority, "status": "pending"}
            for t in topics if t.strip()
        ]
        if rows:
            supabase.table("learning_agenda").upsert(rows, on_conflict="topic").execute()
            logger.info("📋 +%d temas en agenda", len(rows))
    except Exception as e:
        logger.error("❌ Error añadiendo temas: %s", e)


def count_pending_topics() -> int:
    """Cuenta cuántos temas pendientes hay en la agenda."""
    try:
        result = get_supabase().table("learning_agenda").select("id", count="exact").eq("status", "pending").execute()
        return result.count or 0
    except Exception:
        return 0


def seed_agenda() -> None:
    """Rellena la agenda si está vacía (solo al primer inicio)."""
    try:
        supabase = get_supabase()
        result = supabase.table("learning_agenda").select("id").limit(1).execute()
        if not result.data:
            add_topics_to_agenda(SEED_TOPICS, priority=1)
            logger.info("🌱 Agenda inicializada con %d temas base", len(SEED_TOPICS))
    except Exception as e:
        logger.error("❌ Error inicializando agenda: %s", e)


# ─────────────────────────────────────────────
#  CICLO PRINCIPAL — AUTÓNOMO E INFINITO
# ─────────────────────────────────────────────

def run_learning_cycle(trainer) -> dict:
    """
    Ciclo completo de aprendizaje autónomo:
    1. Toma un tema de la agenda
    2. Busca en la web
    3. Entrena la red neuronal
    4. GENERA nuevos temas con Groq (curiosidad)
    5. Si la agenda está casi vacía, regenera más temas
    → La IA nunca para de aprender, incluso con la PC apagada.
    """
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

    # ── 1. Obtener próximo tema ────────────────
    topic_record = get_next_topic()
    if not topic_record:
        logger.info("📭 Agenda vacía — regenerando temas desde seed...")
        add_topics_to_agenda(SEED_TOPICS, priority=1)
        topic_record = get_next_topic()
        if not topic_record:
            return cycle_result

    topic    = topic_record["topic"]
    topic_id = topic_record["id"]
    cycle_result["topic"] = topic
    logger.info("📚 [CICLO] Aprendiendo: '%s'", topic)

    try:
        # ── 2. Buscar en la web ────────────────
        raw_results = search_tavily(topic)
        if len(raw_results) < 2:
            raw_results += search_serper(topic)

        if not raw_results:
            logger.warning("⚠️  Sin resultados para '%s'", topic)
            mark_topic_done(topic_id)
            return cycle_result

        # ── 3. Limpiar contenido ───────────────
        clean_results = extract_best_content(raw_results)
        cycle_result["texts_processed"] = len(clean_results)

        total_tokens = 0
        total_loss   = 0.0
        best_text    = ""

        for item in clean_results:
            text = item["text"]
            url  = item["url"]

            if len(text) > len(best_text):
                best_text = text

            # ── 4. Tokenizar y entrenar ────────
            token_ids = text_to_token_ids(text, max_tokens=512)
            if len(token_ids) > 20:
                neurons_before = trainer.model.count_neurons()
                loss = trainer.train_on_tokens(token_ids)
                total_loss   += loss
                total_tokens += len(token_ids)

                if trainer.model.count_neurons() > neurons_before:
                    cycle_result["grew"] = True

            # ── 5. Guardar en memoria semántica ─
            save_memory(text, topic=topic, source_url=url)
            save_learning_event(topic=topic, content=text, source_url=url)

        cycle_result["tokens_trained"] = total_tokens
        cycle_result["loss"] = round(total_loss / max(1, len(clean_results)), 4)

        # ── 6. Marcar tema como aprendido ──────
        mark_topic_done(topic_id)

        # ── 7. GENERAR NUEVOS TEMAS (Curiosidad) ──────────────────────────────
        # Siempre genera nuevos temas relacionados con lo aprendido
        new_topics = generate_new_topics(topic, best_text)
        if new_topics:
            add_topics_to_agenda(new_topics, priority=2)
            cycle_result["new_topics_generated"] = len(new_topics)

        # ── 8. Si la agenda tiene pocos temas, añadir más ─────────────────────
        pending = count_pending_topics()
        if pending < 5:
            logger.info("📋 Agenda baja (%d temas) — añadiendo temas extra", pending)
            extra = random.sample(SEED_TOPICS, min(5, len(SEED_TOPICS)))
            add_topics_to_agenda(extra, priority=1)

        logger.info(
            "✅ Ciclo OK | '%s' | Tokens: %d | Loss: %.4f | Neuronas: %d | +%d temas nuevos",
            topic, total_tokens, cycle_result["loss"],
            trainer.model.count_neurons(), cycle_result["new_topics_generated"],
        )

    except Exception as e:
        logger.error("❌ Error en ciclo de aprendizaje: %s", e)
        cycle_result["error"] = str(e)

    return cycle_result
