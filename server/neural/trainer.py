"""
Polaris IA — Trainer
Bucle de entrenamiento con Experience Replay.
La red aprende nuevo texto mientras recuerda lo aprendido antes.
"""

import torch
import torch.nn as nn
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from neural.growing_mlp import GrowingMLP

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuración del ciclo de entrenamiento."""
    learning_rate: float = 1e-3
    batch_size: int = 16
    epochs_per_cycle: int = 3
    replay_buffer_size: int = 5000       # Máx ejemplos guardados en buffer
    replay_ratio: float = 0.2            # 20% ejemplos antiguos, 80% nuevos
    growth_patience: int = 5             # Pasos sin mejora antes de crecer
    growth_threshold: float = 0.01       # Mínima mejora para NO crecer
    neurons_per_growth: int = 8          # Neuronas que se añaden al crecer
    max_neurons: int = 10_000            # Límite para no crecer infinitamente
    device: str = "cpu"                  # "cuda" si tienes GPU


@dataclass
class TrainingMetrics:
    """Métricas del estado actual del entrenamiento."""
    current_loss: float = 0.0
    total_steps: int = 0
    total_growth_events: int = 0
    total_texts_learned: int = 0
    last_update: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    loss_history: list[float] = field(default_factory=list)


class PolarisTrainer:
    """
    Entrenador de Polaris IA.

    Flujo de cada ciclo:
    1. Recibe textos nuevos (del pipeline de búsqueda)
    2. Los convierte en pares (input_ids, target_id)
    3. Mezcla con ejemplos del replay buffer (20% antiguos)
    4. Entrena la red
    5. Si la loss se estanca → la red crece automáticamente
    6. Guarda el estado en Supabase
    """

    def __init__(self, model: GrowingMLP, config: TrainingConfig = None):
        self.model = model
        self.config = config or TrainingConfig()
        self.device = torch.device(self.config.device)
        self.model.to(self.device)

        self.optimizer = torch.optim.Adam(model.parameters(), lr=self.config.learning_rate)
        self.loss_fn = nn.CrossEntropyLoss()

        # Buffer de Experience Replay — almacena (input_tensor, target_tensor)
        self.replay_buffer: deque = deque(maxlen=self.config.replay_buffer_size)

        self.metrics = TrainingMetrics()

    # ─────────────────────────────────────────
    #  ENTRENAMIENTO PRINCIPAL
    # ─────────────────────────────────────────

    def train_on_tokens(self, token_ids: list[int], seq_len: int = 16) -> float:
        """
        Entrena la red con una lista de tokens usando predicción del siguiente token.

        Args:
            token_ids: Lista de IDs de tokens del texto aprendido.
            seq_len:   Longitud de la secuencia de contexto.

        Returns:
            Loss promedio del ciclo.
        """
        if len(token_ids) <= seq_len:
            logger.warning("Texto demasiado corto para entrenar (tokens: %d)", len(token_ids))
            return 0.0

        # Generar pares (contexto → siguiente token)
        new_examples = self._create_training_pairs(token_ids, seq_len)

        if not new_examples:
            return 0.0

        # Mezclar con replay buffer
        batch = self._mix_with_replay(new_examples)

        # Entrenar
        total_loss = 0.0
        for epoch in range(self.config.epochs_per_cycle):
            epoch_loss = self._train_batch(batch)
            total_loss += epoch_loss
            self.metrics.loss_history.append(epoch_loss)
            # Mantener solo las últimas 50 pérdidas
            if len(self.metrics.loss_history) > 50:
                self.metrics.loss_history.pop(0)

        avg_loss = total_loss / self.config.epochs_per_cycle
        self.metrics.current_loss = avg_loss
        self.metrics.total_steps += 1
        self.metrics.total_texts_learned += 1
        self.metrics.last_update = datetime.utcnow().isoformat()

        # Añadir nuevos ejemplos al replay buffer
        self.replay_buffer.extend(new_examples)

        # Evaluar si la red necesita crecer
        grew = self._check_and_grow()
        if grew:
            logger.info("🧠 Red creció. Arquitectura: %s", self.model.get_architecture())

        logger.info("📚 Ciclo completado. Loss: %.4f | Neuronas: %d",
                    avg_loss, self.model.count_neurons())

        return avg_loss

    # ─────────────────────────────────────────
    #  MÉTODOS PRIVADOS
    # ─────────────────────────────────────────

    def _create_training_pairs(
        self, token_ids: list[int], seq_len: int
    ) -> list[tuple[torch.Tensor, torch.Tensor]]:
        """
        Crea pares (embedding de contexto, id del siguiente token).
        Usa embedding simple de one-hot para no depender de una capa Embedding
        separada — esto mantiene la red más flexible para crecer.
        """
        pairs = []
        vocab_size = self.model.input_dim  # Input dim = one-hot size simplificado

        for i in range(len(token_ids) - seq_len):
            context = token_ids[i : i + seq_len]
            target = token_ids[i + seq_len]

            # Representar el contexto como promedio de one-hots (bag-of-words simple)
            bow = torch.zeros(vocab_size)
            for tid in context:
                if tid < vocab_size:
                    bow[tid] += 1.0
            bow = bow / (seq_len + 1e-8)  # Normalizar

            target_tensor = torch.tensor(target, dtype=torch.long)
            pairs.append((bow, target_tensor))

        return pairs

    def _mix_with_replay(
        self, new_examples: list[tuple]
    ) -> list[tuple[torch.Tensor, torch.Tensor]]:
        """Mezcla nuevos ejemplos con una muestra del replay buffer."""
        if not self.replay_buffer:
            return new_examples

        replay_count = max(1, int(len(new_examples) * self.config.replay_ratio))
        replay_count = min(replay_count, len(self.replay_buffer))

        # Muestrear ejemplos aleatorios del buffer
        indices = torch.randperm(len(self.replay_buffer))[:replay_count]
        replay_sample = [list(self.replay_buffer)[i] for i in indices]

        return new_examples + replay_sample

    def _train_batch(self, batch: list[tuple]) -> float:
        """Ejecuta un paso de entrenamiento sobre el batch completo."""
        self.model.train()
        self.optimizer.zero_grad()

        total_loss = 0.0
        batch_size = self.config.batch_size

        for start in range(0, len(batch), batch_size):
            mini_batch = batch[start : start + batch_size]
            inputs = torch.stack([x for x, _ in mini_batch]).to(self.device)
            targets = torch.stack([y for _, y in mini_batch]).to(self.device)

            # Forward
            outputs = self.model(inputs)

            # Asegurar que los targets estén dentro del rango del vocabulario
            vocab_size = outputs.shape[-1]
            targets = targets.clamp(0, vocab_size - 1)

            loss = self.loss_fn(outputs, targets)
            loss.backward()
            total_loss += loss.item()

        # Gradient clipping para estabilidad
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
        self.optimizer.step()

        return total_loss / max(1, len(batch) // batch_size)

    def _check_and_grow(self) -> bool:
        """
        Verifica si la red debe crecer y la expande si es necesario.
        Retorna True si creció.
        """
        if self.model.count_neurons() >= self.config.max_neurons:
            return False

        if self.model.should_grow(
            self.metrics.loss_history,
            patience=self.config.growth_patience,
            threshold=self.config.growth_threshold,
        ):
            self.model.add_neurons(layer_idx=-1, num_new=self.config.neurons_per_growth)
            self.metrics.total_growth_events += 1

            # ⚠️ CRÍTICO: Reconstruir el optimizador tras expandir la red
            self.optimizer = torch.optim.Adam(
                self.model.parameters(), lr=self.config.learning_rate
            )
            return True

        return False

    def get_status(self) -> dict:
        """Retorna el estado completo del entrenador para la API."""
        arch = self.model.get_architecture()
        return {
            "neurons": arch["total_neurons"],
            "params": arch["total_params"],
            "architecture": arch["hidden_layers"],
            "current_loss": self.metrics.current_loss,
            "total_steps": self.metrics.total_steps,
            "total_texts_learned": self.metrics.total_texts_learned,
            "total_growth_events": self.metrics.total_growth_events,
            "replay_buffer_size": len(self.replay_buffer),
            "last_update": self.metrics.last_update,
        }
