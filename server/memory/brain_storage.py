"""
Polaris IA — Brain Storage
Guarda y carga el modelo (pesos + arquitectura) en Supabase.
Los pesos van a Supabase Storage (como archivo .pt).
La arquitectura va a la tabla model_versions (JSON).
"""

import io
import json
import logging
import uuid
from datetime import datetime

import torch

from memory.supabase_client import get_supabase
from neural.growing_mlp import GrowingMLP

logger = logging.getLogger(__name__)

STORAGE_BUCKET = "polaris-brain"
WEIGHTS_FILE = "latest_weights.pt"


def save_brain(model: GrowingMLP, loss: float = 0.0) -> str:
    """
    Guarda el estado completo de la red en Supabase.
    - Pesos → Supabase Storage (archivo .pt)
    - Arquitectura + métricas → tabla model_versions

    Retorna el UUID del registro guardado.
    """
    supabase = get_supabase()
    arch = model.get_architecture()
    record_id = str(uuid.uuid4())

    # 1. Serializar pesos a bytes
    weights_bytes = model.to_bytes()

    # 2. Subir pesos a Supabase Storage
    try:
        # Intentar actualizar el archivo existente primero
        supabase.storage.from_(STORAGE_BUCKET).update(
            WEIGHTS_FILE,
            weights_bytes,
            {"content-type": "application/octet-stream"},
        )
    except Exception:
        # Si no existe, crear
        try:
            supabase.storage.from_(STORAGE_BUCKET).upload(
                WEIGHTS_FILE,
                weights_bytes,
                {"content-type": "application/octet-stream"},
            )
        except Exception as e:
            logger.error("❌ Error subiendo pesos a Storage: %s", e)

    weights_url = f"{STORAGE_BUCKET}/{WEIGHTS_FILE}"

    # 3. Guardar arquitectura en la tabla
    supabase.table("model_versions").insert({
        "id": record_id,
        "created_at": datetime.utcnow().isoformat(),
        "architecture": arch,
        "weights_storage_path": weights_url,
        "loss_metric": loss,
        "neuron_count": arch["total_neurons"],
        "connection_count": arch["total_params"],
    }).execute()

    logger.info(
        "💾 Brain guardado | Neuronas: %d | Loss: %.4f",
        arch["total_neurons"], loss,
    )
    return record_id


def load_brain(model: GrowingMLP) -> bool:
    """
    Carga el último estado guardado de la red desde Supabase.
    1. Lee la arquitectura más reciente de model_versions
    2. Descarga los pesos desde Storage
    3. Reconstruye y carga la red

    Retorna True si se cargó correctamente, False si no hay estado guardado.
    """
    supabase = get_supabase()

    # 1. Obtener la arquitectura más reciente
    result = (
        supabase.table("model_versions")
        .select("*")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        logger.info("ℹ️  No hay brain guardado. Iniciando desde cero.")
        return False

    record = result.data[0]
    arch = record["architecture"]
    logger.info("📥 Cargando arquitectura: %s", arch)

    # 2. Reconstruir la estructura de la red
    model.rebuild_from_architecture(arch)

    # 3. Descargar pesos desde Storage
    try:
        weights_bytes = supabase.storage.from_(STORAGE_BUCKET).download(WEIGHTS_FILE)
        model.load_from_bytes(weights_bytes)
        logger.info(
            "✅ Brain cargado | Neuronas: %d",
            arch["total_neurons"],
        )
        return True
    except Exception as e:
        logger.error("❌ Error descargando pesos: %s", e)
        return False


def get_latest_metrics() -> dict:
    """Obtiene las métricas del último modelo guardado."""
    supabase = get_supabase()
    result = (
        supabase.table("model_versions")
        .select("neuron_count, connection_count, loss_metric, created_at")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return {"neuron_count": 0, "connection_count": 0, "loss_metric": 0.0}
