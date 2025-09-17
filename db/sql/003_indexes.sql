-- 003_indexes.sql
SET search_path = sesai, public;

-- chaves e consultas frequentes
CREATE UNIQUE INDEX IF NOT EXISTS idx_municipio_name_uf ON municipio (name, uf_code);
CREATE INDEX IF NOT EXISTS idx_municipio_name ON municipio (name);

CREATE INDEX IF NOT EXISTS idx_form_field_form_ord ON form_field(form_id, ord);

CREATE INDEX IF NOT EXISTS idx_submission_form ON submission(form_id);
CREATE INDEX IF NOT EXISTS idx_submission_aldeia ON submission(aldeia_id);
CREATE INDEX IF NOT EXISTS idx_submission_submitted_at ON submission(submitted_at);
CREATE INDEX IF NOT EXISTS idx_submission_created_at ON submission(created_at);

CREATE INDEX IF NOT EXISTS idx_subval_text ON submission_value (value_text);
CREATE INDEX IF NOT EXISTS idx_subval_num  ON submission_value (value_num);
CREATE INDEX IF NOT EXISTS idx_subval_date ON submission_value (value_date);
CREATE INDEX IF NOT EXISTS idx_subval_ts   ON submission_value (value_ts);
CREATE INDEX IF NOT EXISTS idx_subval_json ON submission_value USING GIN (value_json);
CREATE INDEX IF NOT EXISTS idx_subval_created_at ON submission_value (created_at);

CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);