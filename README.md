---
title: Polaris IA
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

# 🧠 Polaris IA

Sistema de inteligencia artificial autónoma con red neuronal que crece sola.

## Estructura del proyecto

```
Polaris-IA/
├── server/                      # Backend FastAPI (Python)
│   ├── main.py                  # Servidor principal + WebSocket
│   ├── requirements.txt
│   ├── start.bat                # Arranque rápido en Windows
│   ├── test_brain.py            # Tests de integración
│   ├── neural/
│   │   ├── growing_mlp.py       # Red neuronal dinámica (PyTorch)
│   │   └── trainer.py           # Entrenamiento + Experience Replay
│   ├── memory/
│   │   ├── supabase_client.py   # Conexión Supabase
│   │   ├── brain_storage.py     # Guardar/cargar pesos
│   │   └── semantic_memory.py   # pgvector — memoria semántica
│   └── learning/
│       ├── pipeline.py          # Orquestador del ciclo de aprendizaje
│       ├── scraper.py           # Limpieza de texto web
│       └── tokenizer_wrapper.py # GPT2Tokenizer
├── android/                     # App Android (Kotlin + Compose)
│   ├── app/
│   │   └── src/main/java/com/polaris/ia/
│   │       ├── MainActivity.kt           # Pantalla principal (split 70/30)
│   │       ├── data/NeuronModels.kt      # Data classes
│   │       ├── viewmodel/PolarisViewModel.kt
│   │       └── ui/
│   │           ├── NeuralGraph.kt        # Canvas sci-fi animado
│   │           └── Dashboard.kt          # Panel de métricas
│   └── build.gradle
└── supabase/
    └── migrations/
        └── 001_initial_schema.sql        # Schema completo con pgvector
```

## Setup rápido

### 1. Configurar Supabase
Ir a Supabase Dashboard → SQL Editor y ejecutar:
```
supabase/migrations/001_initial_schema.sql
```

### 2. Configurar `.env`
```
AI_API_KEY=...
AI_PROVIDER=groq
NEXT_PUBLIC_SUPABASE_URL=https://tu-proyecto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SERPER_API_KEY=...
TAVILY_API_KEY=...
LEARNING_INTERVAL_MINUTES=30
```

### 3. Arrancar el servidor
```bat
cd server
start.bat
```

El servidor arranca en `http://localhost:8000`
- `GET /status` — Estado completo de la IA
- `GET /metrics` — Métricas para el dashboard
- `GET /architecture` — Arquitectura de la red
- `GET /growth-log` — Historial de crecimiento
- `POST /trigger-cycle` — Forzar ciclo de aprendizaje
- `WS /ws` — WebSocket en tiempo real

### 4. Ejecutar tests
```bat
cd server
venv\Scripts\python test_brain.py
```

### 5. App Android
Abrir `android/` en Android Studio y compilar.

## Cómo aprende Polaris IA

1. **Cada 30 minutos** el scheduler ejecuta un ciclo
2. Lee el próximo tema de la tabla `learning_agenda`
3. Busca información con **Tavily** (primario) + **Serper** (secundario)
4. Limpia el texto HTML y lo tokeniza con **GPT2Tokenizer**
5. Entrena la red neuronal con **predicción de siguiente token**
6. Mezcla con **Experience Replay** (20% textos anteriores)
7. Si la loss se estanca → la red **crece automáticamente** (+8 neuronas)
8. Guarda pesos en **Supabase Storage** + arquitectura en PostgreSQL
9. Guarda texto en **memoria semántica** (pgvector, 384 dims)
10. La app Android recibe el update vía **WebSocket**

## Tecnologías

| Capa | Tecnología |
|------|-----------|
| Red neuronal | PyTorch — MLP dinámico |
| Backend | FastAPI + APScheduler |
| Búsqueda web | Tavily + Serper |
| Base de datos | Supabase (PostgreSQL + pgvector) |
| Embeddings | all-MiniLM-L6-v2 (384 dims) |
| App Android | Kotlin + Jetpack Compose + Canvas |
| Deploy | Railway / Render |
