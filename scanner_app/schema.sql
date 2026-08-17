-- Esquema de base de datos para el proyecto Scanner.
-- Idempotente: seguro de correr múltiples veces (CREATE TABLE IF NOT EXISTS).
--
-- Toda la clasificación (Escuadria/Tipo/Asignación/Destino Recuperación/Calidad)
-- se deriva automáticamente del contenido de cada archivo RUN (ver
-- scanner_app/ingest/clasificador.py) -- no hay más carga manual ni histórico
-- externo. Para un reset destructivo real (DROP + recarga completa), ver
-- scripts/seed_inicial.py --reset -- este archivo nunca hace DROP.

CREATE TABLE IF NOT EXISTS master_products (
    nombre                  TEXT PRIMARY KEY,
    escuadria               TEXT,
    espesor_mm               NUMERIC(8,2),
    ancho_mm                 NUMERIC(8,2),
    calidad                  TEXT,
    tipo                      TEXT,
    asignacion                TEXT,
    destino_recuperacion      TEXT,
    fecha_referencia          DATE,
    creado_en                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runs (
    id                         BIGSERIAL PRIMARY KEY,
    run_numero                 INTEGER NOT NULL UNIQUE,
    nombre_archivo              TEXT NOT NULL,
    fecha                       DATE NOT NULL,
    turno                       SMALLINT NOT NULL CHECK (turno IN (1, 2, 3)),
    escuadria_archivo           TEXT,
    es_rechazo                  BOOLEAN NOT NULL DEFAULT FALSE,
    operador                    TEXT,
    hora_comienzo                TIMESTAMP,
    hora_fin                     TIMESTAMP,
    cantidad_total_pcs           INTEGER,
    largo_total_m                 NUMERIC(12,2),
    volumen_total_m3              NUMERIC(12,4),
    volumen_nominal_total_m3       NUMERIC(12,4),
    total_cortes                   INTEGER,
    filas_activas                 INTEGER NOT NULL DEFAULT 0,
    filas_excluidas               INTEGER NOT NULL DEFAULT 0,
    productos_nuevos              INTEGER NOT NULL DEFAULT 0,
    creado_en                     TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Migración idempotente para bases ya creadas antes de que existiera esta
-- columna (CREATE TABLE IF NOT EXISTS de arriba no altera tablas existentes).
ALTER TABLE runs ADD COLUMN IF NOT EXISTS total_cortes INTEGER;
CREATE INDEX IF NOT EXISTS idx_runs_fecha ON runs(fecha);
CREATE INDEX IF NOT EXISTS idx_runs_es_rechazo ON runs(es_rechazo);

-- Las columnas de clasificación (escuadria..destino_recuperacion) son una
-- FOTO de la clasificación calculada al momento de ingestar esta fila -- no
-- un JOIN en vivo contra master_products. Así, si una carga posterior del
-- mismo Nombre recalcula una clasificación distinta (ej. cambia el ranking de
-- Asignación por el mix de ese run), el histórico ya registrado no cambia
-- retroactivamente.
CREATE TABLE IF NOT EXISTS production_facts (
    id                         BIGSERIAL PRIMARY KEY,
    run_id                      BIGINT REFERENCES runs(id) ON DELETE CASCADE,
    fuente                      TEXT NOT NULL CHECK (fuente IN ('run')),
    nombre                      TEXT NOT NULL REFERENCES master_products(nombre),
    fecha                        DATE NOT NULL,
    turno                        SMALLINT NOT NULL CHECK (turno IN (1, 2, 3)),
    es_rechazo                   BOOLEAN NOT NULL DEFAULT FALSE,
    escuadria                    TEXT,
    espesor_mm                    NUMERIC(8,2),
    ancho_mm                      NUMERIC(8,2),
    calidad                       TEXT,
    tipo                          TEXT,
    asignacion                     TEXT,
    destino_recuperacion           TEXT,
    volumen_nominal_m3            NUMERIC(12,4),
    largo_pct                     NUMERIC(7,4),
    cantidad_pcs                  INTEGER NOT NULL CHECK (cantidad_pcs >= 0),
    largo_m                       NUMERIC(12,4),
    largo_promedio_m               NUMERIC(10,4),
    largo_maximo                   NUMERIC(10,2),
    largo_minimo                   NUMERIC(10,2),
    volumen_nominal_pct            NUMERIC(7,4),
    creado_en                       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_facts_nombre ON production_facts(nombre);
CREATE INDEX IF NOT EXISTS idx_facts_fecha ON production_facts(fecha);
CREATE INDEX IF NOT EXISTS idx_facts_run_id ON production_facts(run_id);
CREATE INDEX IF NOT EXISTS idx_facts_fecha_turno ON production_facts(fecha, turno);

DROP VIEW IF EXISTS v_production;
CREATE VIEW v_production AS
SELECT f.*,
       r.run_numero, r.operador, r.escuadria_archivo,
       r.cantidad_total_pcs, r.total_cortes
FROM production_facts f
LEFT JOIN runs r ON r.id = f.run_id;
