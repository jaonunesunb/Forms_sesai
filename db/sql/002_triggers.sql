-- 002_triggers.sql
SET search_path = sesai, public;

-- Enforce: se houver município-sede, DSEI.uf_code deve bater com UF do município
CREATE OR REPLACE FUNCTION fn_enforce_dsei_uf() RETURNS TRIGGER AS $$
DECLARE muni_uf CHAR(2);
BEGIN
  IF NEW.sede_municipio_id IS NOT NULL THEN
    SELECT uf_code INTO muni_uf FROM municipio WHERE id_ibge = NEW.sede_municipio_id;
    IF muni_uf IS NULL THEN
      RAISE EXCEPTION 'Município-sede % inexistente', NEW.sede_municipio_id;
    END IF;
    IF NEW.uf_code IS DISTINCT FROM muni_uf THEN
      RAISE EXCEPTION 'DSEI.UF(%) difere da UF(%) do município-sede', NEW.uf_code, muni_uf;
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_dsei_uf ON dsei;
CREATE TRIGGER trg_dsei_uf
BEFORE INSERT OR UPDATE ON dsei
FOR EACH ROW EXECUTE FUNCTION fn_enforce_dsei_uf();

-- Enforce: aldeia.dsei_id deve ser igual ao dsei_id do seu polo base
CREATE OR REPLACE FUNCTION fn_enforce_aldeia_dsei() RETURNS TRIGGER AS $$
DECLARE pb_dsei INTEGER;
BEGIN
  SELECT dsei_id INTO pb_dsei FROM polo_base WHERE id = NEW.polo_base_id;
  IF pb_dsei IS NULL THEN
    RAISE EXCEPTION 'Polo Base % inexistente', NEW.polo_base_id;
  END IF;
  IF NEW.dsei_id IS DISTINCT FROM pb_dsei THEN
    RAISE EXCEPTION 'Aldeia.DSEI(%) difere do DSEI(%) do Polo Base %', NEW.dsei_id, pb_dsei, NEW.polo_base_id;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_aldeia_dsei ON aldeia;
CREATE TRIGGER trg_aldeia_dsei
BEFORE INSERT OR UPDATE ON aldeia
FOR EACH ROW EXECUTE FUNCTION fn_enforce_aldeia_dsei();

-- Função utilitária para versionamento automático de formulários
CREATE OR REPLACE FUNCTION ensure_form_version(
  p_name TEXT,
  p_field_ids INTEGER[],
  p_created_by INTEGER DEFAULT NULL,
  p_arango_form_uri TEXT DEFAULT NULL,
  p_status TEXT DEFAULT 'active'
) RETURNS INTEGER AS $$
DECLARE
  v_sorted_ids INTEGER[];
  v_signature TEXT;
  v_latest RECORD;
  v_new_id INTEGER;
BEGIN
  IF p_field_ids IS NULL OR array_length(p_field_ids, 1) IS NULL THEN
    RAISE EXCEPTION 'ensure_form_version requer ao menos um campo';
  END IF;

  SELECT ARRAY(SELECT DISTINCT id ORDER BY id)
    INTO v_sorted_ids
  FROM unnest(p_field_ids) AS t(id);

  v_signature := md5(array_to_string(v_sorted_ids, ','));

  SELECT f.id, f.version, s.signature
    INTO v_latest
  FROM form f
  LEFT JOIN form_definition_signature s ON s.form_id = f.id
  WHERE f.name = p_name
  ORDER BY f.version DESC
  LIMIT 1;

  IF FOUND AND v_latest.signature = v_signature THEN
    UPDATE form
      SET status = COALESCE(p_status, status),
          arango_form_uri = COALESCE(p_arango_form_uri, arango_form_uri)
    WHERE id = v_latest.id;
    RETURN v_latest.id;
  END IF;

  IF FOUND THEN
    UPDATE form
      SET status = 'archived'
    WHERE id = v_latest.id AND status = 'active';
  END IF;

  INSERT INTO form (name, version, status, created_by, arango_form_uri)
  VALUES (
    p_name,
    COALESCE(v_latest.version, 0) + 1,
    COALESCE(p_status, 'active'),
    p_created_by,
    p_arango_form_uri
  )
  RETURNING id INTO v_new_id;

  INSERT INTO form_definition_signature (form_id, signature, field_ids)
  VALUES (v_new_id, v_signature, v_sorted_ids);

  INSERT INTO form_field (form_id, field_id, ord)
  SELECT v_new_id, fc.id, ROW_NUMBER() OVER (ORDER BY fc.label)
  FROM field_catalog fc
  WHERE fc.id = ANY(v_sorted_ids);

  RETURN v_new_id;
END;
$$ LANGUAGE plpgsql;
