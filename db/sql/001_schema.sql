-- 001_schema.sql
-- Schema & core tables
CREATE SCHEMA IF NOT EXISTS sesai;
SET search_path = sesai, public;

-- 1) Geografia e estrutura administrativa
CREATE TABLE IF NOT EXISTS uf (
  uf_code CHAR(2) PRIMARY KEY,
  name    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS municipio (
  id_ibge     INTEGER PRIMARY KEY,           -- código IBGE (7 dígitos cabe em int)
  name        TEXT NOT NULL,
  uf_code     CHAR(2) NOT NULL REFERENCES uf(uf_code) ON UPDATE CASCADE,
  UNIQUE (name, uf_code)
);

CREATE TABLE IF NOT EXISTS dsei (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  uf_code     CHAR(2) NOT NULL REFERENCES uf(uf_code) ON UPDATE CASCADE,
  sede_municipio_id INTEGER REFERENCES municipio(id_ibge) ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS polo_base (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  dsei_id     INTEGER NOT NULL REFERENCES dsei(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  municipio_id INTEGER REFERENCES municipio(id_ibge) ON UPDATE CASCADE,
  UNIQUE (dsei_id, name)
);

CREATE TABLE IF NOT EXISTS aldeia (
  id           SERIAL PRIMARY KEY,
  name         TEXT NOT NULL,
  dsei_id      INTEGER NOT NULL REFERENCES dsei(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  polo_base_id INTEGER NOT NULL REFERENCES polo_base(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  municipio_id INTEGER REFERENCES municipio(id_ibge) ON UPDATE CASCADE,
  latitude     NUMERIC(9,6),
  longitude    NUMERIC(9,6),
  UNIQUE (name, municipio_id)
);

-- 2) Usuários
CREATE TABLE IF NOT EXISTS users (
  id            SERIAL PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,
  full_name     TEXT,
  role          TEXT,                    -- ex.: admin, agente, pesquisador...
  password_hash TEXT,
  active        BOOLEAN NOT NULL DEFAULT TRUE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3) Formulários e campos
CREATE TABLE IF NOT EXISTS form (
  id            SERIAL PRIMARY KEY,
  name          TEXT NOT NULL,
  version       INTEGER NOT NULL DEFAULT 1,
  status        TEXT NOT NULL DEFAULT 'active',
  arango_form_uri TEXT,
  created_by    INTEGER REFERENCES users(id) ON UPDATE CASCADE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (name, version)
);

CREATE TABLE IF NOT EXISTS field_catalog (
  id           SERIAL PRIMARY KEY,
  class_uri    TEXT NOT NULL UNIQUE,     -- URI da classe (Ontologia/Arango)
  label        TEXT NOT NULL,
  description  TEXT,
  datatype     TEXT,                     -- ex.: xsd:string, xsd:date, xsd:integer...
  constraints  JSONB NOT NULL DEFAULT '{}'::jsonb  -- ex.: {"maxLength": 50, "pattern": "^[A-Z]"}
);

CREATE TABLE IF NOT EXISTS form_field (
  id             SERIAL PRIMARY KEY,
  form_id        INTEGER NOT NULL REFERENCES form(id) ON UPDATE CASCADE ON DELETE CASCADE,
  field_id       INTEGER NOT NULL REFERENCES field_catalog(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  ord            INTEGER NOT NULL DEFAULT 0,
  required       BOOLEAN NOT NULL DEFAULT FALSE,
  default_value  JSONB,
  UNIQUE (form_id, field_id)
);

-- 4) Submissões e valores (EAV tipado)
CREATE TABLE IF NOT EXISTS submission (
  id             BIGSERIAL PRIMARY KEY,
  form_id        INTEGER NOT NULL REFERENCES form(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  form_version   INTEGER NOT NULL,
  aldeia_id      INTEGER NOT NULL REFERENCES aldeia(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  submitted_by   INTEGER REFERENCES users(id) ON UPDATE CASCADE,
  submitted_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  status         TEXT NOT NULL DEFAULT 'ok',
  raw_payload    JSONB,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by     INTEGER REFERENCES users(id) ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS submission_value (
  submission_id  BIGINT NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  form_field_id  INTEGER NOT NULL REFERENCES form_field(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  field_id       INTEGER NOT NULL REFERENCES field_catalog(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  form_version   INTEGER NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by     INTEGER REFERENCES users(id) ON UPDATE CASCADE,
  value_text     TEXT,
  value_num      NUMERIC,
  value_bool     BOOLEAN,
  value_date     DATE,
  value_ts       TIMESTAMPTZ,
  value_json     JSONB,
  PRIMARY KEY (submission_id, form_field_id)
);

-- 5) (Opcional) lookup de classes/propriedades do Arango
CREATE TABLE IF NOT EXISTS arango_classes (
  class_uri TEXT PRIMARY KEY,
  label     TEXT
);

CREATE TABLE IF NOT EXISTS arango_properties (
  property_uri TEXT PRIMARY KEY,
  label        TEXT,
  domain_uri   TEXT,
  range_uri    TEXT
);

-- 6) Log de auditoria
CREATE TABLE IF NOT EXISTS audit_log (
  id         BIGSERIAL PRIMARY KEY,
  user_id    INTEGER REFERENCES users(id) ON UPDATE CASCADE ON DELETE SET NULL,
  action     TEXT NOT NULL,
  payload    JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7) Metadados de sincronização
CREATE TABLE IF NOT EXISTS ontology_sync (
  id         SERIAL PRIMARY KEY,
  source_uri TEXT NOT NULL,
  signature  TEXT NOT NULL,
  payload    JSONB,
  synced_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_uri, signature)
);

CREATE TABLE IF NOT EXISTS form_definition_signature (
  form_id   INTEGER PRIMARY KEY REFERENCES form(id) ON DELETE CASCADE,
  signature TEXT NOT NULL,
  field_ids INTEGER[] NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
