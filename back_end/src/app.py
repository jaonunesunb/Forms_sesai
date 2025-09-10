import json
import os
import hashlib
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from arango import ArangoClient
import psycopg2
import o_parse_back_end as op
import prompt as pr

app = Flask(__name__)
CORS(app)

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
pg_conn = psycopg2.connect(POSTGRES_DSN)
pg_conn.autocommit = True
with pg_conn.cursor() as cur:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS form_submissions (
            id SERIAL PRIMARY KEY,
            data JSONB
        )
        """
    )

# Variável global de idioma, com valor padrão como 'pt'
current_language = 'pt'

# em app.py
import time
import psycopg2
from psycopg2 import OperationalError

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

# Função para buscar subclasses
@app.route('/get_subclasses', methods=['GET'])
def get_subclasses():
    class_uri = request.args.get('class')
    if not class_uri:
        return jsonify({"error": "class parameter is required"}), 400

    # Carrega a ontologia e extrai as subclasses
    g = op.load_ontology('back_end/src/OWL/Onto_aldeias.owl')
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
    g = op.load_ontology('back_end/src/OWL/Onto_aldeias.owl')
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
    app.run(debug=True)
    import os
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)