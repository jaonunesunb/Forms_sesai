import hashlib
import json
import os
import time
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from arango import ArangoClient
import psycopg2
from psycopg2 import OperationalError
import o_parse_back_end as op
import prompt as pr

OWL_PATH = os.path.join(os.path.dirname(__file__), "OWL", "Onto_aldeias.owl")

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}},
    supports_credentials=True,
)

# Conexão com ArangoDB
ARANGO_URL = os.getenv("ARANGO_URL", "http://arango:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "owl_db")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "")
arango_client = ArangoClient(hosts=ARANGO_URL)
arango_db = arango_client.db(ARANGO_DB, username=ARANGO_USER, password=ARANGO_PASSWORD)

# Conexão com PostgreSQL
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://postgres:postgres@postgres:5432/forms",
)


def connect_pg(dsn, retries=20, delay=1):
    for i in range(retries):
        try:
            conn = psycopg2.connect(dsn)
            conn.autocommit = True
            return conn
        except OperationalError as e:
            print(f"[PG] tentativa {i+1}/{retries}: {e}")
            time.sleep(delay)
    raise

pg_conn = connect_pg(POSTGRES_DSN)
with pg_conn.cursor() as cur:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS form_submissions (
            id SERIAL PRIMARY KEY,
            data JSONB
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS arango_classes (
            class_uri TEXT PRIMARY KEY,
            label TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS arango_properties (
            property_uri TEXT PRIMARY KEY,
            label TEXT,
            domain_uri TEXT,
            range_uri TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS vertex_instances (
            id SERIAL PRIMARY KEY,
            class_uri TEXT REFERENCES arango_classes(class_uri),
            data JSONB
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS edge_instances (
            id SERIAL PRIMARY KEY,
            edge_uri TEXT,
            from_instance INTEGER REFERENCES vertex_instances(id),
            to_instance INTEGER REFERENCES vertex_instances(id),
            data JSONB
        )
        """
    )

# Variável global de idioma, com valor padrão como 'pt'
current_language = 'pt'

@app.after_request
def add_cors_headers(resp):
    # Fallback explícito (útil para preflight e erros)
    origin = request.headers.get("Origin")
    if origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        resp.headers["Access-Control-Allow-Origin"] = origin
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

# Função para alterar o idioma global
@app.route('/set_language', methods=['POST'])
def set_language():
    global current_language
    data = request.get_json()
    new_language = data.get('language')
    if new_language not in ['pt', 'en']:
        return jsonify({"error": "Idioma não suportado"}), 400

    current_language = new_language
    return jsonify({"message": f"Idioma alterado para {new_language}"}), 200

# Função para retornar o idioma atual
@app.route('/get_language', methods=['GET'])
def get_language():
    return jsonify({'language': current_language})

@app.route('/save_form_data', methods=['POST'])
def save_form_data():
    data = request.get_json()
    with pg_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO form_submissions (data) VALUES (%s)",
            (json.dumps(data),),
        )
    return jsonify({"message": "Formulário recebido com sucesso!"}), 200

@app.route('/save_instance', methods=['POST','OPTIONS'])
def save_instance():
    if request.method == 'OPTIONS':
        return ('', 204)

    payload = request.get_json(silent=True) or {}
    class_uri = payload.get('class_uri')
    data = payload.get('data')
    if not class_uri or data is None:
        return jsonify({"error": "class_uri and data are required"}), 400

    # Confere a classe no Arango e obtém label
    class_key = hashlib.sha1(class_uri.encode()).hexdigest()
    classes_col = arango_db.collection('classes')
    if not classes_col.has(class_key):
        return jsonify({"error": "Class not found"}), 404
    cls_doc = classes_col.get(class_key) or {}
    cls_label = cls_doc.get('label')

    with pg_conn.cursor() as cur:
        # 1) GARANTE a classe na tabela referenciada pela FK
        cur.execute("""
            INSERT INTO arango_classes (class_uri, label)
            VALUES (%s, %s)
            ON CONFLICT (class_uri) DO UPDATE SET label = EXCLUDED.label
        """, (class_uri, cls_label))

        # 2) (opcional) guarda o payload bruto
        cur.execute("INSERT INTO form_submissions (data) VALUES (%s)",
                    (json.dumps(payload),))

        # 3) Agora pode inserir a instância sem quebrar a FK
        cur.execute("""
            INSERT INTO vertex_instances (class_uri, data)
            VALUES (%s, %s)
            RETURNING id
        """, (class_uri, json.dumps(data)))
        instance_id = cur.fetchone()[0]

    return jsonify({"message": "Instance saved", "id": instance_id}), 200


@app.route('/save_edge', methods=['POST'])
def save_edge():
    payload = request.get_json()
    edge_uri = payload.get('edge_uri')
    from_id = payload.get('from_id')
    to_id = payload.get('to_id')
    data = payload.get('data', {})
    if not edge_uri or from_id is None or to_id is None:
        return jsonify({"error": "edge_uri, from_id and to_id are required"}), 400

    with pg_conn.cursor() as cur:
        cur.execute("SELECT 1 FROM vertex_instances WHERE id = %s", (from_id,))
        if not cur.fetchone():
            return jsonify({"error": "from_id not found"}), 404
        cur.execute("SELECT 1 FROM vertex_instances WHERE id = %s", (to_id,))
        if not cur.fetchone():
            return jsonify({"error": "to_id not found"}), 404
        cur.execute(
            """
            INSERT INTO edge_instances (edge_uri, from_instance, to_instance, data)
            VALUES (%s, %s, %s, %s) RETURNING id
            """,
            (edge_uri, from_id, to_id, json.dumps(data)),
        )
        edge_id = cur.fetchone()[0]

    return jsonify({"message": "Edge saved", "id": edge_id}), 200

# Função para buscar subclasses
@app.route('/get_subclasses', methods=['GET'])
def get_subclasses():
    class_uri = request.args.get('class')
    if not class_uri:
        return jsonify({"error": "class parameter is required"}), 400

    # Carrega a ontologia e extrai as subclasses
    g = op.load_ontology(OWL_PATH)
    labels, labels_to_uris, descriptions = op.extract_labels(g, current_language)
    subclasses = pr.list_subclasses(g, class_uri, labels)

    # Adicionar a descrição ao JSON de subclasses
    for subclass in subclasses:
        related_class_uri = subclass.get("uri")
        if related_class_uri in descriptions:
            subclass["definition"] = descriptions[related_class_uri]  # Adiciona a definição (se disponível)

    return jsonify({"subclasses": subclasses})

# Função para buscar os detalhes de uma classe
@app.route('/get_class_details', methods=['GET'])
def get_class_details():
    class_uri = request.args.get('class')
    if not class_uri:
        return jsonify({"error": "class parameter is required"}), 400

    # Carrega a ontologia e extrai os detalhes da classe
    g = op.load_ontology(OWL_PATH)
    labels, labels_to_uris, descriptions = op.extract_labels(g, current_language)
    details = op.list_restrictions_and_data_properties(g, class_uri, labels, labels_to_uris, descriptions)
    response = json.dumps(details, ensure_ascii=False)
    return Response(response, content_type='application/json; charset=utf-8')


# Endpoints utilizando dados do ArangoDB
@app.route('/get_subclasses_arango', methods=['GET'])
def get_subclasses_arango():
    class_uri = request.args.get('class')
    if not class_uri:
        return jsonify({"error": "class parameter is required"}), 400
    class_key = hashlib.sha1(class_uri.encode()).hexdigest()
    cursor = arango_db.aql.execute(
        "FOR v, e IN 1..1 OUTBOUND @start class_edges RETURN v",
        bind_vars={"start": f"classes/{class_key}"},
    )
    subclasses = list(cursor)
    return jsonify({"subclasses": subclasses})


@app.route('/get_class_details_arango', methods=['GET'])
def get_class_details_arango():
    class_uri = request.args.get('class')
    if not class_uri:
        return jsonify({"error": "class parameter is required"}), 400
    class_key = hashlib.sha1(class_uri.encode()).hexdigest()
    doc = arango_db.collection('classes').get(class_key)
    if not doc:
        return jsonify({"error": "Class not found"}), 404
    return jsonify(doc)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)