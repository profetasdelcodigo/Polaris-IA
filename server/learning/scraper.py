"""
Polaris IA — Web Scraper
Limpia el texto crudo obtenido de las APIs de búsqueda.
Elimina HTML, scripts, exceso de espacios y contenido irrelevante.
"""

import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Longitud mínima para considerar un texto útil
MIN_TEXT_LENGTH = 100


def clean_html(raw: str) -> str:
    """Elimina etiquetas HTML y devuelve texto plano limpio."""
    soup = BeautifulSoup(raw, "lxml")
    # Eliminar scripts, estilos y elementos no visibles
    for tag in soup(["script", "style", "meta", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return _normalize_whitespace(text)


def clean_text(raw: str) -> str:
    """
    Limpia texto plano (ya sin HTML):
    - Elimina caracteres extraños
    - Normaliza espacios y saltos de línea
    - Elimina líneas muy cortas (menús, botones, etc.)
    """
    # Quitar URLs embebidas en texto
    text = re.sub(r"https?://\S+", "", raw)
    # Quitar caracteres especiales no alfanuméricos (excepto puntuación básica)
    text = re.sub(r"[^\w\s.,;:!?\"'()\-\n]", " ", text)
    text = _normalize_whitespace(text)

    # Filtrar líneas muy cortas (probablemente navegación o basura)
    lines = [line for line in text.splitlines() if len(line.strip()) > 30]
    return " ".join(lines)


def is_useful(text: str) -> bool:
    """Determina si un texto tiene suficiente contenido para entrenar."""
    cleaned = clean_text(text)
    return len(cleaned) >= MIN_TEXT_LENGTH


def extract_best_content(search_results: list[dict]) -> list[dict]:
    """
    Filtra y limpia una lista de resultados de búsqueda.
    Cada resultado debe tener las claves 'content' y opcionalmente 'url', 'title'.

    Retorna solo los resultados con contenido útil, limpios.
    """
    useful = []
    for result in search_results:
        raw = result.get("content", result.get("raw_content", ""))
        if not raw:
            continue

        # Limpiar según el tipo de contenido
        if "<" in raw and ">" in raw:
            text = clean_html(raw)
        else:
            text = clean_text(raw)

        if is_useful(text):
            useful.append({
                "text": text[:8000],  # Limitar a 8000 chars por seguridad
                "url": result.get("url", result.get("href", "")),
                "title": result.get("title", ""),
            })

    logger.info("📋 Resultados útiles: %d / %d", len(useful), len(search_results))
    return useful


def _normalize_whitespace(text: str) -> str:
    """Normaliza espacios múltiples y saltos de línea."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()
