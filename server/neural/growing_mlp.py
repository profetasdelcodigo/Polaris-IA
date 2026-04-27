"""
Polaris IA — Growing MLP
Red neuronal que empieza vacía y crece dinámicamente.
Basado en el mejor código de Copilot + corrección crítica de Gemini
(el optimizador se reconstruye tras cada expansión).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import io
from datetime import datetime


# ─────────────────────────────────────────────
#  CAPA LINEAL EXPANDIBLE
# ─────────────────────────────────────────────

class ExpandableLinear(nn.Module):
    """
    Capa lineal que puede añadir neuronas de entrada o salida
    sin perder los pesos ya aprendidos.
    """

    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features)
        # Inicialización pequeña para no romper el flujo al añadir neuronas
        nn.init.normal_(self.linear.weight, mean=0.0, std=0.01)
        nn.init.constant_(self.linear.bias, 0.0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.linear(x)

    def expand_out(self, add_neurons: int) -> None:
        """
        Añade `add_neurons` neuronas de SALIDA.
        Los pesos nuevos se inicializan con varianza pequeña para
        no alterar lo que ya aprendió la red.
        """
        old_weight = self.linear.weight.data.clone()
        old_bias = self.linear.bias.data.clone()
        in_f = self.linear.in_features
        old_out = self.linear.out_features
        new_out = old_out + add_neurons

        new_linear = nn.Linear(in_f, new_out)
        nn.init.normal_(new_linear.weight, mean=0.0, std=0.01)
        nn.init.constant_(new_linear.bias, 0.0)

        # Copiar pesos antiguos — las nuevas filas quedan inicializadas arriba
        new_linear.weight.data[:old_out, :] = old_weight
        new_linear.bias.data[:old_out] = old_bias

        self.linear = new_linear

    def expand_in(self, add_inputs: int) -> None:
        """
        Expande la entrada cuando la capa anterior creció.
        Los pesos nuevos se inicializan a 0 para comenzar sin ruido.
        """
        old_weight = self.linear.weight.data.clone()
        in_f = self.linear.in_features
        out_f = self.linear.out_features
        new_in = in_f + add_inputs

        new_linear = nn.Linear(new_in, out_f)
        nn.init.zeros_(new_linear.weight)
        nn.init.zeros_(new_linear.bias)

        # Copiar pesos antiguos — las nuevas columnas quedan en 0
        new_linear.weight.data[:, :in_f] = old_weight
        new_linear.bias.data = self.linear.bias.data.clone()

        self.linear = new_linear

    @property
    def in_features(self) -> int:
        return self.linear.in_features

    @property
    def out_features(self) -> int:
        return self.linear.out_features


# ─────────────────────────────────────────────
#  RED NEURONAL QUE CRECE
# ─────────────────────────────────────────────

class GrowingMLP(nn.Module):
    """
    Red neuronal de Polaris IA.

    - Empieza desde cero (sin pesos preentrenados)
    - Crece dinámicamente cuando la loss se estanca
    - Guarda un historial de cada vez que creció
    """

    def __init__(self, input_dim: int, initial_hidden: int = 4, output_dim: int = 50257):
        """
        Args:
            input_dim:      Tamaño del embedding de entrada (depende del tokenizador).
            initial_hidden: Neuronas iniciales en la capa oculta (empieza pequeña).
            output_dim:     Vocabulario del tokenizador (GPT2 = 50257 tokens).
        """
        super().__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.growth_log: list[dict] = []  # Historial de crecimiento

        # Capa de entrada → capa oculta inicial
        self.layers = nn.ModuleList([
            ExpandableLinear(input_dim, initial_hidden)
        ])

        # Capa de salida (predecir siguiente token del vocabulario)
        self.output_layer = ExpandableLinear(initial_hidden, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass por todas las capas ocultas + capa de salida.
        x shape: (batch_size, input_dim)
        """
        for layer in self.layers:
            x = F.relu(layer(x))
        return self.output_layer(x)

    # ── Crecimiento dinámico ──────────────────

    def add_neurons(self, layer_idx: int = -1, num_new: int = 8) -> None:
        """
        Añade neuronas a una capa oculta existente.
        Si layer_idx = -1, añade a la ÚLTIMA capa oculta.

        ⚠️  Después de llamar esto, DEBES reconstruir el optimizador.
        """
        if layer_idx == -1:
            layer_idx = len(self.layers) - 1

        if not (0 <= layer_idx < len(self.layers)):
            raise IndexError(f"layer_idx {layer_idx} fuera de rango (0-{len(self.layers)-1})")

        # Expandir la capa seleccionada
        self.layers[layer_idx].expand_out(num_new)

        # Expandir la entrada de la capa siguiente (o output_layer)
        if layer_idx + 1 < len(self.layers):
            self.layers[layer_idx + 1].expand_in(num_new)
        else:
            self.output_layer.expand_in(num_new)

        # Registrar en el historial
        self.growth_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "add_neurons",
            "layer": layer_idx,
            "neurons_added": num_new,
            "architecture": self.get_architecture(),
        })

    def add_layer(self, hidden_size: int = 32) -> None:
        """
        Añade una nueva capa oculta al final (antes de la output_layer).

        ⚠️  Después de llamar esto, DEBES reconstruir el optimizador.
        """
        # La nueva capa recibe la salida de la última capa oculta
        prev_out = self.layers[-1].out_features
        new_layer = ExpandableLinear(prev_out, hidden_size)

        # La output_layer debe adaptar su entrada
        self.output_layer.expand_in(hidden_size - self.layers[-1].out_features)

        # Si el output_layer ya tiene el tamaño correcto, reconstruirlo limpio
        old_out_features = self.output_layer.in_features
        if old_out_features != hidden_size:
            self.output_layer = ExpandableLinear(hidden_size, self.output_dim)

        self.layers.append(new_layer)

        self.growth_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": "add_layer",
            "new_layer_size": hidden_size,
            "architecture": self.get_architecture(),
        })

    # ── Estadísticas ─────────────────────────

    def get_architecture(self) -> dict:
        """Devuelve la arquitectura actual como diccionario."""
        return {
            "input_dim": self.input_dim,
            "hidden_layers": [layer.out_features for layer in self.layers],
            "output_dim": self.output_dim,
            "total_neurons": self.count_neurons(),
            "total_params": self.count_params(),
        }

    def count_neurons(self) -> int:
        """Cuenta el total de neuronas (excluyendo capa de salida)."""
        return sum(layer.out_features for layer in self.layers)

    def count_params(self) -> int:
        """Cuenta el total de parámetros entrenables."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def should_grow(self, recent_losses: list[float], patience: int = 5, threshold: float = 0.01) -> bool:
        """
        Decide si la red necesita más neuronas.
        Retorna True si la loss no mejoró más de `threshold` en `patience` pasos.
        """
        if len(recent_losses) < patience:
            return False
        window = recent_losses[-patience:]
        improvement = abs(window[0] - window[-1]) / (abs(window[0]) + 1e-8)
        return improvement < threshold

    # ── Serialización ────────────────────────

    def to_bytes(self) -> bytes:
        """Serializa los pesos a bytes para guardar en Supabase Storage."""
        buffer = io.BytesIO()
        torch.save(self.state_dict(), buffer)
        buffer.seek(0)
        return buffer.read()

    def load_from_bytes(self, data: bytes) -> None:
        """Carga pesos desde bytes (leídos de Supabase Storage)."""
        buffer = io.BytesIO(data)
        state_dict = torch.load(buffer, map_location="cpu", weights_only=True)
        self.load_state_dict(state_dict)

    def rebuild_from_architecture(self, arch: dict) -> None:
        """
        Reconstruye la estructura de la red desde un diccionario de arquitectura.
        Llamar ANTES de load_from_bytes al restaurar una sesión guardada.
        """
        hidden_layers = arch["hidden_layers"]
        self.input_dim = arch["input_dim"]
        self.output_dim = arch["output_dim"]

        # Reconstruir capas ocultas
        self.layers = nn.ModuleList()
        prev = self.input_dim
        for h in hidden_layers:
            self.layers.append(ExpandableLinear(prev, h))
            prev = h

        # Reconstruir capa de salida
        self.output_layer = ExpandableLinear(prev, self.output_dim)


# ─────────────────────────────────────────────
#  TEST RÁPIDO (ejecutar directamente)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("🧠 Polaris IA — Test de red neuronal dinámica\n")

    INPUT_DIM = 128    # Tamaño de embedding de entrada (simplificado para test)
    OUTPUT_DIM = 1000  # Vocabulario reducido para test

    model = GrowingMLP(input_dim=INPUT_DIM, initial_hidden=4, output_dim=OUTPUT_DIM)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    print(f"📐 Arquitectura inicial: {model.get_architecture()}")
    print(f"🔢 Neuronas: {model.count_neurons()} | Parámetros: {model.count_params():,}\n")

    # Simular un forward pass
    x = torch.randn(4, INPUT_DIM)
    y = model(x)
    print(f"✅ Forward pass OK. Output shape: {y.shape}")

    # Simular que la loss se estanca → crecer
    fake_losses = [1.0, 0.999, 0.998, 0.998, 0.997]
    if model.should_grow(fake_losses, patience=5, threshold=0.01):
        print("\n⚡ Loss estancada — Añadiendo 8 neuronas a la última capa...")
        model.add_neurons(layer_idx=-1, num_new=8)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)  # ⚠️ RECONSTRUIR SIEMPRE
        print(f"📐 Nueva arquitectura: {model.get_architecture()}")
        print(f"🔢 Neuronas: {model.count_neurons()} | Parámetros: {model.count_params():,}")

    # Test de serialización
    print("\n💾 Serializando pesos...")
    weights_bytes = model.to_bytes()
    print(f"✅ Pesos serializados: {len(weights_bytes):,} bytes")

    # Test de reconstrucción
    arch = model.get_architecture()
    model2 = GrowingMLP(input_dim=INPUT_DIM, output_dim=OUTPUT_DIM)
    model2.rebuild_from_architecture(arch)
    model2.load_from_bytes(weights_bytes)
    print(f"✅ Red reconstruida correctamente desde bytes")
    print(f"\n📋 Historial de crecimiento: {model.growth_log}")
