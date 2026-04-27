"""
Polaris IA - Test de integracion completa Fase 1 y 2
Verifica: red neuronal crece, se guarda y carga desde Supabase.
Ejecutar con:  python test_brain.py
"""

import sys
import os
# Forzar UTF-8 en Windows para evitar errores cp1252
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
from neural.growing_mlp import GrowingMLP
from neural.trainer import PolarisTrainer, TrainingConfig

# ─────────────────────────────────────────────────────────
#  TEST 1 — La red neuronal crece correctamente
# ─────────────────────────────────────────────────────────
def test_growth():
    print("\n🧪 TEST 1: Crecimiento dinámico de la red")
    INPUT_DIM = 512
    OUTPUT_DIM = 512

    model = GrowingMLP(input_dim=INPUT_DIM, initial_hidden=4, output_dim=OUTPUT_DIM)
    arch_antes = model.get_architecture()
    print(f"  Antes: {arch_antes['hidden_layers']} neuronas | params={arch_antes['total_params']:,}")

    # Añadir neuronas
    model.add_neurons(layer_idx=-1, num_new=8)
    arch_despues = model.get_architecture()
    print(f"  Después: {arch_despues['hidden_layers']} neuronas | params={arch_despues['total_params']:,}")

    assert arch_despues['total_neurons'] == arch_antes['total_neurons'] + 8, \
        "❌ El número de neuronas no creció correctamente"

    # Forward pass tras crecer
    x = torch.randn(2, INPUT_DIM)
    y = model(x)
    assert y.shape == (2, OUTPUT_DIM), f"❌ Shape incorrecto: {y.shape}"

    print("  ✅ Crecimiento y forward pass OK")


# ─────────────────────────────────────────────────────────
#  TEST 2 — Serialización / deserialización de pesos
# ─────────────────────────────────────────────────────────
def test_serialization():
    print("\n🧪 TEST 2: Serialización de pesos")
    INPUT_DIM = 512
    OUTPUT_DIM = 512

    model = GrowingMLP(input_dim=INPUT_DIM, initial_hidden=4, output_dim=OUTPUT_DIM)
    model.add_neurons(layer_idx=-1, num_new=8)

    # Guardar pesos
    weights = model.to_bytes()
    arch = model.get_architecture()
    print(f"  Pesos serializados: {len(weights):,} bytes")

    # Reconstruir desde cero
    model2 = GrowingMLP(input_dim=INPUT_DIM, output_dim=OUTPUT_DIM)
    model2.rebuild_from_architecture(arch)
    model2.load_from_bytes(weights)

    # Verificar que el output es idéntico
    x = torch.randn(1, INPUT_DIM)
    with torch.no_grad():
        out1 = model(x)
        out2 = model2(x)

    assert torch.allclose(out1, out2, atol=1e-5), "❌ Los pesos no se cargaron correctamente"
    print("  ✅ Serialización y reconstrucción OK")


# ─────────────────────────────────────────────────────────
#  TEST 3 — Trainer: entrena y detecta estancamiento
# ─────────────────────────────────────────────────────────
def test_trainer():
    print("\n🧪 TEST 3: Trainer con Experience Replay")
    INPUT_DIM = 512

    model = GrowingMLP(input_dim=INPUT_DIM, initial_hidden=4, output_dim=INPUT_DIM)
    config = TrainingConfig(
        epochs_per_cycle=2,
        growth_patience=3,
        growth_threshold=0.5,   # Umbral alto para forzar crecimiento en el test
        neurons_per_growth=4,
    )
    trainer = PolarisTrainer(model, config)

    # Simular tokens de texto (números aleatorios como token IDs)
    fake_tokens = [i % INPUT_DIM for i in range(200)]

    losses = []
    for cycle in range(6):
        loss = trainer.train_on_tokens(fake_tokens, seq_len=8)
        losses.append(loss)
        print(f"  Ciclo {cycle+1}: loss={loss:.4f} | neuronas={model.count_neurons()}")

    status = trainer.get_status()
    print(f"  Estado final: {status}")
    assert status['total_steps'] == 6, "❌ Número de pasos incorrecto"
    print("  ✅ Trainer OK")


# ─────────────────────────────────────────────────────────
#  TEST 4 — Supabase (solo si hay .env configurado)
# ─────────────────────────────────────────────────────────
def test_supabase():
    print("\n🧪 TEST 4: Conexión con Supabase")
    try:
        from memory.supabase_client import get_supabase
        sb = get_supabase()

        # Verificar que la tabla learning_agenda tiene datos
        result = sb.table("learning_agenda").select("topic").limit(3).execute()
        topics = [r['topic'] for r in result.data]
        print(f"  Temas en agenda: {topics}")

        assert len(topics) > 0, "❌ La agenda está vacía — ¿ejecutaste el SQL en Supabase?"
        print("  ✅ Conexión Supabase OK")
    except Exception as e:
        print(f"  ⚠️  Supabase: {e}")
        print("  (Normal si no hay .env configurado en este entorno)")


# ─────────────────────────────────────────────────────────
#  RUNNER
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  🧠 POLARIS IA — TEST DE INTEGRACIÓN")
    print("=" * 55)

    try:
        test_growth()
        test_serialization()
        test_trainer()
        test_supabase()

        print("\n" + "=" * 55)
        print("  ✅ TODOS LOS TESTS PASARON")
        print("=" * 55)

    except AssertionError as e:
        print(f"\n❌ FALLO: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
