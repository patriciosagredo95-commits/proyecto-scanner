-- Esquema de base de datos para el proyecto Scanner.
-- Idempotente: seguro de correr múltiples veces (CREATE TABLE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS master_products (
    nombre                  TEXT PRIMARY KEY,
    escuadria               TEXT,
    espesor_mm               NUMERIC(8,2),
    ancho_mm                 NUMERIC(8,2),
    largo_nominal_mm         NUMERIC(10,2),
    destino                  TEXT,
    tipo                     TEXT,
    asignacion                TEXT,
    destino_recuperacion      TEXT,
    pct_recuperacion          NUMERIC(6,4),
    ancho_recuperacion        NUMERIC(8,2),
    obs_ancho                 TEXT,
    obs_espesor                TEXT,
    fecha_referencia          DATE,
    origen                    TEXT NOT NULL DEFAULT 'historico' CHECK (origen IN ('historico', 'manual')),
    pendiente_revision        BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runs (
    id                         BIGSERIAL PRIMARY KEY,
    run_numero                 INTEGER NOT NULL UNIQUE,
    nombre_archivo              TEXT NOT NULL,
    fecha                       DATE NOT NULL,
    turno                       SMALLINT NOT NULL CHECK (turno IN (1, 2)),
    escuadria_archivo           TEXT,
    descripcion_archivo          TEXT,
    es_rechazo                  BOOLEAN NOT NULL DEFAULT FALSE,
    operador                    TEXT,
    hora_comienzo                TIMESTAMP,
    hora_fin                     TIMESTAMP,
    cantidad_total_pcs           INTEGER,
    largo_total_m                 NUMERIC(12,2),
    volumen_total_m3              NUMERIC(12,4),
    volumen_nominal_total_m3       NUMERIC(12,4),
    filas_activas                 INTEGER NOT NULL DEFAULT 0,
    filas_excluidas               INTEGER NOT NULL DEFAULT 0,
    productos_nuevos              INTEGER NOT NULL DEFAULT 0,
    creado_en                     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_runs_fecha ON runs(fecha);
CREATE INDEX IF NOT EXISTS idx_runs_es_rechazo ON runs(es_rechazo);

-- cantidad_pcs >= 0 (no > 0): el histórico trae ~93 filas legítimas con
-- cantidad 0 (algunas incluso con volumen > 0, anomalías propias del scanner)
-- que se preservan tal cual por fidelidad de los datos ya registrados. La
-- regla de negocio "excluir Cantidad=0" solo aplica a la ingesta de RUNs
-- nuevos (ver scanner_app/parsing/run_file.py), no se aplica retroactivamente.
-- Las columnas de clasificación (escuadria..obs_espesor) son una FOTO de la
-- Tabla Maestra al momento de ingestar esta fila -- no un JOIN en vivo. Así,
-- si más adelante se corrige la clasificación de un Nombre en master_products,
-- el histórico ya registrado no cambia retroactivamente (coherente con cómo
-- se veía en los reportes/pivots originales, que reflejan la clasificación
-- vigente el día que se registró cada pieza, no la de hoy).
CREATE TABLE IF NOT EXISTS production_facts (
    id                         BIGSERIAL PRIMARY KEY,
    run_id                      BIGINT REFERENCES runs(id) ON DELETE CASCADE,
    fuente                      TEXT NOT NULL CHECK (fuente IN ('historico', 'run')),
    nombre                      TEXT NOT NULL REFERENCES master_products(nombre),
    fecha                        DATE NOT NULL,
    turno                        SMALLINT NOT NULL CHECK (turno IN (1, 2)),
    es_rechazo                   BOOLEAN NOT NULL DEFAULT FALSE,
    escuadria                    TEXT,
    espesor_mm                    NUMERIC(8,2),
    ancho_mm                      NUMERIC(8,2),
    largo_nominal_mm              NUMERIC(10,2),
    destino                       TEXT,
    tipo                          TEXT,
    asignacion                     TEXT,
    destino_recuperacion           TEXT,
    pct_recuperacion                NUMERIC(6,4),
    ancho_recuperacion              NUMERIC(8,2),
    obs_ancho                       TEXT,
    obs_espesor                      TEXT,
    volumen_nominal_m3            NUMERIC(12,4),
    largo_pct                     NUMERIC(7,4),
    cantidad_pcs                  INTEGER NOT NULL CHECK (cantidad_pcs >= 0),
    largo_m                       NUMERIC(12,4),
    largo_promedio_m               NUMERIC(10,4),
    volumen_nominal_pct            NUMERIC(7,4),
    rend_ln_pct                    NUMERIC(8,6),
    rend_vol_n_pct                  NUMERIC(8,6),
    creado_en                       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_facts_nombre ON production_facts(nombre);
CREATE INDEX IF NOT EXISTS idx_facts_fecha ON production_facts(fecha);
CREATE INDEX IF NOT EXISTS idx_facts_run_id ON production_facts(run_id);
CREATE INDEX IF NOT EXISTS idx_facts_fecha_turno ON production_facts(fecha, turno);

-- Estas ALTER deben ir ANTES de (re)crear v_production: la vista usa `f.*`,
-- y en Postgres una vista congela su lista de columnas al momento de crearse
-- -- si las columnas se agregaran a la tabla DESPUÉS de crear la vista, la
-- vista jamás las mostraría hasta volver a crearse.
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS escuadria TEXT;
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS espesor_mm NUMERIC(8,2);
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS ancho_mm NUMERIC(8,2);
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS largo_nominal_mm NUMERIC(10,2);
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS destino TEXT;
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS tipo TEXT;
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS asignacion TEXT;
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS destino_recuperacion TEXT;
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS pct_recuperacion NUMERIC(6,4);
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS ancho_recuperacion NUMERIC(8,2);
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS obs_ancho TEXT;
ALTER TABLE production_facts ADD COLUMN IF NOT EXISTS obs_espesor TEXT;

-- DROP + CREATE (no CREATE OR REPLACE): Postgres no permite que un REPLACE
-- quite columnas de una vista existente, y esta vista sí las pierde entre
-- migraciones (ej. al eliminar destino_origen de master_products).
-- Ya no hace JOIN a master_products: la clasificación vive directo en
-- production_facts (foto histórica), master_products solo resuelve nombres
-- nuevos al momento de ingestar.
DROP VIEW IF EXISTS v_production;
CREATE VIEW v_production AS
SELECT f.*,
       r.run_numero, r.operador, r.escuadria_archivo, r.descripcion_archivo
FROM production_facts f
LEFT JOIN runs r ON r.id = f.run_id;

-- === Migraciones idempotentes (van después de las vistas: una vista puede
-- depender de una columna que una migración posterior elimina) ===
-- 'destino_origen' se eliminó de la tabla maestra; la vista de arriba ya no
-- la referencia, así que en este punto la columna queda libre de dependencias.
ALTER TABLE master_products DROP COLUMN IF EXISTS destino_origen;
-- 'calidad' se agregó y luego se eliminó: casi nunca tenía dato (el
-- histórico nunca la trajo), así que se descartó como columna de la tabla maestra.
ALTER TABLE master_products DROP COLUMN IF EXISTS calidad;
