import os
import json
import logging
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

# --- Arango: adaptador local (evita colisão com o pacote 'python-arango') ---
# Crie 'arango_utils.py' com a função db_get_subclasses(class_uri) conforme combinado.
from arango_utils import db_get_subclasses

# --- Parser/OWL existente no projeto ---
import o_parse_back_end as op  # mantém suas funções de parse

# --- SQLAlchemy / Postgres ---
from sqlalchemy import create_engine, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

# -----------------------------------------------------------------------------
# Configuração básica
# -----------------------------------------------------------------------------
load_dotenv()  # lê variáveis do .env

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # UTF-8 nas respostas JSON
CORS(app)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("forms_sesai.api")

# Idioma padrão para labels/descrições
current_language = os.getenv("ARANGO_LANG", "pt")

# Caminho do OWL usado pelas rotas de detalhes (fallback para o seu caminho atual)
ONT_PATH = os.getenv("ONT_PATH", "back_end/src/OWL/Onto_aldeias.owl")

# URL do Postgres (pode vir do .env)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres",
)

# -----------------------------------------------------------------------------
# SQLAlchemy models / infra
# -----------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, echo=False, future=True)


class Base(DeclarativeBase):
    pass


class FormSubmission(Base):
    __tablename__ = "form_submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


def ensure_tables():
    Base.metadata.create_all(engine)


# -----------------------------------------------------------------------------
# Rotas utilitárias
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    return jsonify({"ok": True})


# -----------------------------------------------------------------------------
# Idioma (pt/en)
# -----------------------------------------------------------------------------
@app.post("/set_language")
def set_language():
    global current_language
    data = request.get_json(silent=True) or {}
    new_language = data.get("language")
    if new_language not in ["pt", "en"]:
        return jsonify({"error": "Idioma não suportado"}), 400
    current_language = new_language
    return jsonify({"message": f"Idioma alterado para {new_language}"}), 200


@app.get("/get_language")
def get_language():
    return jsonify({"language": current_language})


# -----------------------------------------------------------------------------
# Persistência simples em arquivo (mantido para compatibilidade)
# -----------------------------------------------------------------------------
@app.post("/save_form_data")
def save_form_data_file():
    data = request.get_json(force=True) or {}
    with open("form_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return jsonify({"message": "Formulário recebido com sucesso!"}), 200


# -----------------------------------------------------------------------------
# Persistência no Postgres (ABox)
# -----------------------------------------------------------------------------
@app.post("/api/forms")
def save_form_db():
    """
    Espera JSON:
    {
      "class_key": "ONTAE_00000019",
      "payload": { ...campos do formulário... }
    }
    """
    try:
        data: Dict[str, Any] = request.get_json(force=True) or {}
        class_key = data.get("class_key")
        payload = data.get("payload")
        if not class_key or payload is None:
            return jsonify({"error": "Informe class_key e payload"}), 400

        with Session(engine) as sess:
            fs = FormSubmission(class_key=class_key, payload=payload)
            sess.add(fs)
            sess.commit()
            return jsonify({"id": fs.id, "class_key": fs.class_key}), 201
    except Exception as e:
        log.exception("Erro ao salvar no Postgres")
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# Ontologia no Arango (TBox): subclasses
# -----------------------------------------------------------------------------
@app.get("/get_subclasses")
def get_subclasses():
    """
    Ex.: /get_subclasses?class=http://www.semanticweb.org/ontologias/ONTAE/ONTAE_00000019
    Retorna: { "subclasses": [ { _key, uri, label }, ... ] }
    """
    class_uri = request.args.get("class")
    if not class_uri:
        return jsonify({"error": "class parameter is required"}), 400

    try:
        subclasses = db_get_subclasses(class_uri)
        return jsonify({"subclasses": subclasses})
    except Exception as e:
        log.exception("Erro consultando subclasses no Arango")
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# Detalhes da classe via parser local (usa seu o_parse_back_end)
# -----------------------------------------------------------------------------
@app.get("/get_class_details")
def get_class_details():
    """
    Ex.: /get_class_details?class=<URI-da-classe>
    Usa o parser local para montar campos (data properties, restrições, etc.)
    com preferência de idioma atual.
    """
    class_uri = request.args.get("class")
    if not class_uri:
        return jsonify({"error": "class parameter is required"}), 400

    try:
        g = op.load_ontology(ONT_PATH)
        labels, labels_to_uris, descriptions = op.extract_labels(g, current_language)
        details = op.list_restrictions_and_data_properties(
            g, class_uri, labels, labels_to_uris, descriptions
        )
        # garantir utf-8 no retorno
        return Response(
            json.dumps(details, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
        )
    except FileNotFoundError:
        return jsonify({"error": f"Arquivo OWL não encontrado em '{ONT_PATH}'"}), 404
    except Exception as e:
        log.exception("Erro ao obter detalhes da classe")
        return jsonify({"error": str(e)}), 500


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    ensure_tables()  # cria a tabela no Postgres se não existir
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
