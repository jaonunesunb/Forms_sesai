import os
import hashlib
from arango import ArangoClient
from rdflib import RDFS, URIRef
import o_parse_back_end as op

ARANGO_URL = os.getenv("ARANGO_URL", "http://arango:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "owl_db")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "")

client = ArangoClient(hosts=ARANGO_URL)

# garante que o banco de dados exista
def ensure_database():
    sys_db = client.db("_system", username=ARANGO_USER, password=ARANGO_PASSWORD)
    if not sys_db.has_database(ARANGO_DB):
        sys_db.create_database(ARANGO_DB)
    return client.db(ARANGO_DB, username=ARANGO_USER, password=ARANGO_PASSWORD)


def load_owl(file_path: str) -> None:
    db = ensure_database()
    if not db.has_collection("classes"):
        db.create_collection("classes")
    if not db.has_collection("class_edges"):
        db.create_collection("class_edges", edge=True)
    classes_col = db.collection("classes")
    edges_col = db.collection("class_edges")

    g = op.load_ontology(file_path)
    labels, _, descriptions = op.extract_labels(g)

    for class_uri, label in labels.items():
        key = hashlib.sha1(str(class_uri).encode()).hexdigest()
        doc = {
            "_key": key,
            "uri": str(class_uri),
            "label": label,
            "description": descriptions.get(str(class_uri)),
        }
        classes_col.insert(doc, overwrite=True)

    for subj, obj in g.subject_objects(RDFS.subClassOf):
        if isinstance(subj, URIRef) and isinstance(obj, URIRef):
            from_key = hashlib.sha1(str(subj).encode()).hexdigest()
            to_key = hashlib.sha1(str(obj).encode()).hexdigest()
            edge_doc = {
                "_from": f"classes/{from_key}",
                "_to": f"classes/{to_key}",
            }
            edges_col.insert(edge_doc, overwrite=True)


if __name__ == "__main__":
    owl_file = os.getenv("OWL_FILE", "back_end/src/OWL/Onto_aldeias.owl")
    load_owl(owl_file)
