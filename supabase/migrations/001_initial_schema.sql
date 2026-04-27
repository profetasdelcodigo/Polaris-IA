-- ============================================================
--  POLARIS IA — Schema inicial de Supabase
--  Ejecutar en: Supabase Dashboard → SQL Editor
-- ============================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ────────────────────────────────────────────
--  1. VERSIONES DEL MODELO
--  Guarda cada snapshot de la arquitectura + link a pesos
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_versions (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  architecture  JSONB NOT NULL,            -- {"hidden_layers":[4,12,20], "total_neurons":36}
  weights_storage_path TEXT,               -- path en Supabase Storage
  loss_metric   FLOAT DEFAULT 0,
  neuron_count  INT   DEFAULT 0,
  connection_count INT DEFAULT 0
);

-- ────────────────────────────────────────────
--  2. AGENDA DE APRENDIZAJE
--  Temas que la IA aún necesita estudiar
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS learning_agenda (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  topic      TEXT NOT NULL UNIQUE,
  priority   INT  DEFAULT 1,
  status     TEXT DEFAULT 'pending',       -- pending | learning | done
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────
--  3. HISTORIAL DE APRENDIZAJE
--  Registro de todo lo que la IA ha aprendido
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS learning_history (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  topic      TEXT,
  source_url TEXT,
  content    TEXT NOT NULL,
  learned_at TIMESTAMPTZ DEFAULT NOW()
);

-- ────────────────────────────────────────────
--  4. MEMORIA SEMÁNTICA (pgvector)
--  Cada texto aprendido convertido en vector para búsqueda semántica
-- ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS semantic_memory (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  content    TEXT NOT NULL,
  topic      TEXT,
  source_url TEXT,
  embedding  VECTOR(384),                  -- all-MiniLM-L6-v2 produce 384 dims
  learned_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice para búsqueda por similitud coseno (IVFFlat — rápido)
CREATE INDEX IF NOT EXISTS idx_semantic_memory_embedding
ON semantic_memory
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- ────────────────────────────────────────────
--  5. FUNCIÓN DE BÚSQUEDA SEMÁNTICA
--  Usada por semantic_memory.py para el método search_memory()
-- ────────────────────────────────────────────
CREATE OR REPLACE FUNCTION match_memory(
  query_embedding  VECTOR(384),
  match_threshold  FLOAT   DEFAULT 0.6,
  match_count      INT     DEFAULT 5
)
RETURNS TABLE (
  id         UUID,
  content    TEXT,
  source_url TEXT,
  topic      TEXT,
  similarity FLOAT
)
LANGUAGE SQL STABLE AS $$
  SELECT
    id,
    content,
    source_url,
    topic,
    1 - (embedding <=> query_embedding) AS similarity
  FROM semantic_memory
  WHERE 1 - (embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;

-- ────────────────────────────────────────────
--  6. POLÍTICAS RLS (Row Level Security)
--  Permite que el servidor Python escriba y lea
-- ────────────────────────────────────────────
ALTER TABLE model_versions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_agenda   ENABLE ROW LEVEL SECURITY;
ALTER TABLE learning_history  ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_memory   ENABLE ROW LEVEL SECURITY;

-- Política: permitir todo con la anon key (para desarrollo)
-- En producción, cambiar a service_role key en el servidor
CREATE POLICY "allow_all_model_versions"
  ON model_versions FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "allow_all_learning_agenda"
  ON learning_agenda FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "allow_all_learning_history"
  ON learning_history FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "allow_all_semantic_memory"
  ON semantic_memory FOR ALL USING (true) WITH CHECK (true);

-- ────────────────────────────────────────────
--  7. SUPABASE REALTIME
--  Habilitar para que Android reciba updates automáticos
-- ────────────────────────────────────────────
ALTER PUBLICATION supabase_realtime ADD TABLE model_versions;
ALTER PUBLICATION supabase_realtime ADD TABLE learning_history;

-- ────────────────────────────────────────────
--  8. DATOS INICIALES — agenda de aprendizaje
-- ────────────────────────────────────────────
INSERT INTO learning_agenda (topic, priority, status) VALUES
  ('inteligencia artificial', 10, 'pending'),
  ('redes neuronales artificiales', 9, 'pending'),
  ('aprendizaje automático machine learning', 9, 'pending'),
  ('Python programación avanzada', 8, 'pending'),
  ('ciencia de datos', 8, 'pending'),
  ('procesamiento de lenguaje natural NLP', 7, 'pending'),
  ('deep learning avanzado', 7, 'pending'),
  ('algoritmos de optimización', 6, 'pending'),
  ('matemáticas para IA', 6, 'pending'),
  ('historia de la inteligencia artificial', 5, 'pending')
ON CONFLICT (topic) DO NOTHING;

-- ============================================================
--  VERIFICACIÓN — Ejecutar esto para confirmar que todo creó bien
-- ============================================================
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public'
-- ORDER BY table_name;
