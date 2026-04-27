"""
Polaris IA — Supabase Client
Conexión singleton con Supabase para todo el servidor.
"""

import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase() -> Client:
    """
    Retorna la instancia singleton del cliente de Supabase.
    Se crea la primera vez que se llama.
    """
    global _client
    if _client is None:
        url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

        if not url or not key:
            raise EnvironmentError(
                "❌ Faltan variables de entorno: "
                "NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_ANON_KEY"
            )

        _client = create_client(url, key)
        logger.info("✅ Conexión con Supabase establecida")

    return _client
