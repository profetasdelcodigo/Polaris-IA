"""
Polaris IA — FastAPI Server
Servidor principal que:
- Carga la red neuronal al arrancar
- Ejecuta el ciclo de aprendizaje cada 30 minutos (APScheduler)
- Expone API REST para consultar el estado de la IA
- Expone WebSocket para actualizaciones en tiempo real hacia Android
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

import torch
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from learning.pipeline import run_learning_cycle, seed_agenda
from learning.tokenizer_wrapper import get_vocab_size
from memory.brain_storage import load_brain, save_brain
from memory.semantic_memory import get_memory_stats
from neural.growing_mlp import GrowingMLP
from neural.trainer import PolarisTrainer, TrainingConfig

# ─────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Dimensión de entrada: usamos vocab_size reducido como bag-of-words
# (se limita a 10_000 para que la red empiece manejable)
INPUT_DIM = 10_000
LEARNING_INTERVAL_MINUTES = int(os.getenv("LEARNING_INTERVAL_MINUTES", "30"))

# ─────────────────────────────────────────────
#  ESTADO GLOBAL DE LA IA
# ─────────────────────────────────────────────

model: GrowingMLP | None = None
trainer: PolarisTrainer | None = None
scheduler: AsyncIOScheduler | None = None
last_cycle_result: dict = {}

# Clientes WebSocket conectados (para enviar updates en tiempo real)
ws_clients: list[WebSocket] = []


# ─────────────────────────────────────────────
#  CICLO DE APRENDIZAJE (background)
# ─────────────────────────────────────────────

async def learning_job():
    """
    Tarea programada: ejecuta un ciclo de aprendizaje y notifica a los clientes.
    """
    global last_cycle_result
    logger.info("⏰ Iniciando ciclo de aprendizaje programado...")

    # Ejecutar en thread separado para no bloquear el event loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_learning_cycle, trainer)
    last_cycle_result = result

    # Guardar el estado actualizado en Supabase
    await loop.run_in_executor(
        None, save_brain, model, result.get("loss", 0.0)
    )

    # Notificar a todos los clientes WebSocket conectados
    status = get_full_status()
    await broadcast_update(status)


async def broadcast_update(data: dict):
    """Envía actualización a todos los clientes WebSocket conectados."""
    disconnected = []
    for ws in ws_clients:
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        ws_clients.remove(ws)


# ─────────────────────────────────────────────
#  STARTUP / SHUTDOWN
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización al arrancar el servidor."""
    global model, trainer, scheduler

    logger.info("🚀 Arrancando Polaris IA Server...")

    # 1. Crear la red neuronal
    model = GrowingMLP(
        input_dim=INPUT_DIM,
        initial_hidden=4,
        output_dim=INPUT_DIM,  # Predice el siguiente "token" en espacio reducido
    )

    # 2. Intentar cargar el estado guardado desde Supabase
    loaded = load_brain(model)
    if not loaded:
        logger.info("🌱 Iniciando con red neuronal vacía (2 → 4 neuronas)")

    # 3. Crear el trainer
    config = TrainingConfig(
        learning_rate=1e-3,
        batch_size=16,
        epochs_per_cycle=3,
        growth_patience=5,
        neurons_per_growth=8,
        max_neurons=50_000,
        device="cuda" if torch.cuda.is_available() else "cpu",
    )
    trainer = PolarisTrainer(model, config)

    # 4. Inicializar agenda de aprendizaje
    seed_agenda()

    # 5. Arrancar el scheduler de aprendizaje
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        learning_job,
        "interval",
        minutes=LEARNING_INTERVAL_MINUTES,
        id="learning_cycle",
        next_run_time=datetime.now(),  # Ejecutar inmediatamente al arrancar
    )
    scheduler.start()
    logger.info(
        "✅ Polaris IA lista | Neuronas: %d | Ciclo cada %d min",
        model.count_neurons(),
        LEARNING_INTERVAL_MINUTES,
    )

    yield  # El servidor corre aquí

    # Shutdown: guardar estado final
    logger.info("🛑 Apagando Polaris IA — guardando estado...")
    if model and trainer:
        save_brain(model, trainer.metrics.current_loss)
    if scheduler:
        scheduler.shutdown()


# ─────────────────────────────────────────────
#  APP FASTAPI
# ─────────────────────────────────────────────

app = FastAPI(
    title="Polaris IA",
    description="Red neuronal autónoma que aprende de internet y crece sola",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  UTILIDADES
# ─────────────────────────────────────────────

def get_full_status() -> dict:
    """Construye el diccionario de estado completo de la IA."""
    if not model or not trainer:
        return {"status": "initializing"}

    arch = model.get_architecture()
    mem_stats = get_memory_stats()
    trainer_status = trainer.get_status()

    return {
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "neural_network": {
            "neurons": arch["total_neurons"],
            "params": arch["total_params"],
            "layers": arch["hidden_layers"],
            "growth_events": trainer_status["total_growth_events"],
        },
        "learning": {
            "current_loss": trainer_status["current_loss"],
            "total_texts": trainer_status["total_texts_learned"],
            "total_steps": trainer_status["total_steps"],
            "replay_buffer": trainer_status["replay_buffer_size"],
            "last_update": trainer_status["last_update"],
        },
        "memory": mem_stats,
        "last_cycle": last_cycle_result,
    }


# ─────────────────────────────────────────────
#  ENDPOINTS REST
# ─────────────────────────────────────────────

@app.get("/", summary="Verificar que el servidor está vivo")
async def root():
    return {"message": "🧠 Polaris IA está viva", "version": "1.0.0"}


@app.get("/status", summary="Estado completo de la IA")
async def status():
    """Retorna el estado completo de la red neuronal y el progreso de aprendizaje."""
    return get_full_status()


@app.get("/metrics", summary="Métricas de aprendizaje")
async def metrics():
    """Retorna métricas simplificadas para el dashboard de Android."""
    if not model or not trainer:
        return {"error": "IA no inicializada"}

    arch = model.get_architecture()
    return {
        "neurons": arch["total_neurons"],
        "connections": arch["total_params"],
        "loss": trainer.metrics.current_loss,
        "texts_learned": trainer.metrics.total_texts_learned,
        "growth_events": trainer.metrics.total_growth_events,
        "last_topic": last_cycle_result.get("topic", "Iniciando..."),
        "last_update": trainer.metrics.last_update,
    }


@app.get("/architecture", summary="Arquitectura actual de la red")
async def architecture():
    """Retorna la arquitectura de capas de la red neuronal."""
    if not model:
        return {"error": "IA no inicializada"}
    return model.get_architecture()


@app.get("/growth-log", summary="Historial de crecimiento")
async def growth_log():
    """Retorna el historial de cada vez que la red creció."""
    if not model:
        return []
    return model.growth_log[-50:]  # Últimos 50 eventos


@app.post("/trigger-cycle", summary="Forzar un ciclo de aprendizaje ahora")
async def trigger_cycle():
    """Ejecuta un ciclo de aprendizaje inmediatamente (útil para testing)."""
    asyncio.create_task(learning_job())
    return {"message": "Ciclo de aprendizaje iniciado"}


# ─────────────────────────────────────────────
#  WEBSOCKET — Actualizaciones en tiempo real
# ─────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket para recibir actualizaciones en tiempo real.
    La app Android se conecta aquí para ver la red crecer.
    """
    await ws.accept()
    ws_clients.append(ws)
    logger.info("📱 Cliente WebSocket conectado (total: %d)", len(ws_clients))

    # Enviar estado inicial al conectar
    await ws.send_text(json.dumps(get_full_status()))

    try:
        # Mantener la conexión viva — enviar ping cada 10s
        while True:
            await asyncio.sleep(10)
            status = get_full_status()
            await ws.send_text(json.dumps(status))
    except WebSocketDisconnect:
        ws_clients.remove(ws)
        logger.info("📱 Cliente WebSocket desconectado (total: %d)", len(ws_clients))
