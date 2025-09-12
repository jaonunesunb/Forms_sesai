-- 010_seed_min.sql
SET search_path = sesai, public;

-- UF mínimas para teste
INSERT INTO uf (uf_code, name) VALUES
  ('AM','Amazonas'),
  ('PA','Pará'),
  ('BA','Bahia')
ON CONFLICT DO NOTHING;

-- Municípios de exemplo (ids fictícios ou reais IBGE)
INSERT INTO municipio (id_ibge, name, uf_code) VALUES
  (1302603, 'Manaus', 'AM'),
  (1501402, 'Belém',  'PA'),
  (2927408, 'Salvador','BA')
ON CONFLICT DO NOTHING;

-- DSEI de exemplo (UF coerente com município-sede)
INSERT INTO dsei (name, uf_code, sede_municipio_id) VALUES
  ('DSEI Alto Rio Negro', 'AM', 1302603),
  ('DSEI Guamá-Tocantins', 'PA', 1501402)
ON CONFLICT DO NOTHING;

-- Polos base
INSERT INTO polo_base (name, dsei_id, municipio_id)
SELECT 'Polo Base A', d.id, 1302603 FROM dsei d WHERE d.name='DSEI Alto Rio Negro'
ON CONFLICT DO NOTHING;

INSERT INTO polo_base (name, dsei_id, municipio_id)
SELECT 'Polo Base B', d.id, 1501402 FROM dsei d WHERE d.name='DSEI Guamá-Tocantins'
ON CONFLICT DO NOTHING;

-- Aldeias
INSERT INTO aldeia (name, dsei_id, polo_base_id, municipio_id, latitude, longitude)
SELECT 'Aldeia Yara', d.id, pb.id, 1302603, -3.1190, -60.0217
FROM dsei d JOIN polo_base pb ON pb.dsei_id = d.id
WHERE d.name='DSEI Alto Rio Negro' AND pb.name='Polo Base A'
ON CONFLICT DO NOTHING;

-- Usuário
INSERT INTO users (email, full_name, role) VALUES
  ('admin@example.com', 'Admin Local', 'admin')
ON CONFLICT DO NOTHING;

-- Form e campos de exemplo
INSERT INTO form (name, version, status, created_by)
SELECT 'Formulário Básico', 1, 'active', u.id FROM users u WHERE u.email='admin@example.com'
ON CONFLICT DO NOTHING;

-- Catálogo de campos (exemplo simples; sincronize com Ontologia/Arango depois)
INSERT INTO field_catalog (class_uri, label, description, datatype, constraints) VALUES
  ('http://ex#NomePessoa', 'Nome', 'Nome completo', 'xsd:string', '{"maxLength":200}'),
  ('http://ex#DataNascimento', 'Data de Nascimento', 'Nascimento do indivíduo', 'xsd:date', '{}'),
  ('http://ex#IsGestante', 'Gestante', 'Se é gestante', 'xsd:boolean', '{}')
ON CONFLICT DO NOTHING;

-- Vincula campos ao formulário
INSERT INTO form_field (form_id, field_id, ord, required)
SELECT f.id, fc.id, ROW_NUMBER() OVER ()::int, TRUE
FROM form f
JOIN field_catalog fc ON fc.class_uri IN ('http://ex#NomePessoa','http://ex#DataNascimento','http://ex#IsGestante')
WHERE f.name='Formulário Básico' AND f.version=1
ON CONFLICT DO NOTHING;
