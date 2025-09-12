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
