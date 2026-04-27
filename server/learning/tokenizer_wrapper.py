"""
Polaris IA — Tokenizer Wrapper
Wrapper sobre GPT2Tokenizer de HuggingFace.
Convierte texto en listas de IDs de tokens listos para entrenar la red.
"""

import logging
from transformers import GPT2Tokenizer

logger = logging.getLogger(__name__)

_tokenizer: GPT2Tokenizer | None = None

# Tamaño del vocabulario de GPT2 — la red usará esto como output_dim
VOCAB_SIZE = 50257


def get_tokenizer() -> GPT2Tokenizer:
    """Singleton del tokenizador GPT2."""
    global _tokenizer
    if _tokenizer is None:
        logger.info("⏳ Cargando tokenizador GPT2...")
        _tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        _tokenizer.pad_token = _tokenizer.eos_token
        logger.info("✅ Tokenizador listo (vocab: %d tokens)", VOCAB_SIZE)
    return _tokenizer


def text_to_token_ids(text: str, max_tokens: int = 1024) -> list[int]:
    """
    Convierte texto en una lista de IDs de tokens.

    Args:
        text:       Texto a tokenizar.
        max_tokens: Máximo de tokens a generar (evita textos muy largos).

    Retorna lista de IDs de tokens.
    """
    tokenizer = get_tokenizer()
    tokens = tokenizer.encode(
        text,
        add_special_tokens=True,
        max_length=max_tokens,
        truncation=True,
    )
    return tokens


def token_ids_to_text(token_ids: list[int]) -> str:
    """Convierte IDs de tokens de vuelta a texto (para debugging)."""
    tokenizer = get_tokenizer()
    return tokenizer.decode(token_ids, skip_special_tokens=True)


def get_vocab_size() -> int:
    """Retorna el tamaño del vocabulario."""
    return VOCAB_SIZE
