import os
import sys
from typing import Iterable, List
from arango import ArangoClient
from rdflib import Graph as RDFGraph, RDF, RDFS, OWL, URIRef, BNode
from rdflib.collection import Collection

IAO_DEF = URIRef("http://purl.obolibrary.org/obo/IAO_0000115")

# ---------- Conexão / Estruturas ----------

def get_db():
    url = os.getenv("ARANGO_URL", "http://localhost:8529")
    username = os.getenv("ARANGO_USER", "root")
    password = os.getenv("ARANGO_PASSWORD", "")
    db_name = os.getenv("ARANGO_DB", "ontology")

    client = ArangoClient(hosts=url)
    sys_db = client.db("_system", username=username, password=password)
    if not sys_db.has_database(db_name):
        sys_db.create_database(db_name)

    return client.db(db_name, username=username, password=password)


def get_graph():
    db = get_db()
    graph_name = os.getenv("ARANGO_GRAPH", "ontology_graph")
    if not db.has_graph(graph_name):
        graph = db.create_graph(graph_name)
    else:
        graph = db.graph(graph_name)

    # Vértices
    if not graph.has_vertex_collection("Classes"):
        graph.create_vertex_collection("Classes")
    if not graph.has_vertex_collection("Properties"):
        graph.create_vertex_collection("Properties")

    # Arestas (classe -> classe)
    if not graph.has_edge_definition("Edges"):
        graph.create_edge_definition(
            edge_collection="Edges",
            from_vertex_collections=["Classes"],
            to_vertex_collections=["Classes"],
        )

    return graph


def _key(uri: str) -> str:
    # chave curta a partir do fragmento/localName
    return uri.split("#")[-1].split("/")[-1]


def _get_label(g: RDFGraph, entity):
    lang = os.getenv("ARANGO_LANG", "pt")
    for label in g.objects(entity, RDFS.label):
        if getattr(label, "language", None) and str(label.language).startswith(lang):
            return str(label)
    for label in g.objects(entity, RDFS.label):
        return str(label)
    return str(entity)


def _get_definition(g: RDFGraph, entity):
    lang = os.getenv("ARANGO_LANG", "pt")

    # IAO:0000115 (definition)
    for definition in g.objects(entity, IAO_DEF):
        if getattr(definition, "language", None) and str(definition.language).startswith(lang):
            return str(definition)
    for definition in g.objects(entity, IAO_DEF):
        return str(definition)

    # rdfs:comment (fallback)
    for comment in g.objects(entity, RDFS.comment):
        if getattr(comment, "language", None) and str(comment.language).startswith(lang):
            return str(comment)
    for comment in g.objects(entity, RDFS.comment):
        return str(comment)
    return None


def _expand_union_list(g: RDFGraph, node) -> List[URIRef]:
    """Se domain/range for uma union (owl:unionOf), retorna a lista de classes."""
    classes = []
    for union in g.objects(node, OWL.unionOf):
        try:
            for member in Collection(g, union):
                if isinstance(member, (URIRef,)):
                    classes.append(member)
        except Exception:
            pass
    return classes


def _expand_to_classes(g: RDFGraph, node) -> List[URIRef]:
    """
    Aceita: classe URIRef; nó em branco com owl:unionOf; ignora restrições.
    """
    out: List[URIRef] = []
    if isinstance(node, URIRef):
        out.append(node)
    elif isinstance(node, BNode):
        out.extend(_expand_union_list(g, node))
        # restrições/expressões mais complexas são ignoradas aqui (poderia-se tratar someValuesFrom etc.)
    return out


def _ensure_class_vertex(classes_coll, g: RDFGraph, cls_uri: URIRef):
    c_key = _key(str(cls_uri))
    if not classes_coll.has(c_key):
        doc = {"_key": c_key, "uri": str(cls_uri), "label": _get_label(g, cls_uri)}
        definition = _get_definition(g, cls_uri)
        if definition:
            doc["definition"] = definition
        classes_coll.insert(doc)


# ---------- Importação ----------

def insert_ontology(g: RDFGraph):
    """
    Importa uma ontologia OWL para ArangoDB:
    - Vértices em 'Classes' (OWL.Class / RDFS.Class)
    - Vértices em 'Properties' (Object/Datatype)
    - Arestas em 'Edges' (type=subClassOf; type=objectProperty com domain->range)
    """
    graph = get_graph()
    classes = graph.vertex_collection("Classes")
    properties = graph.vertex_collection("Properties")
    edges = graph.edge_collection("Edges")

    # Classes (OWL.Class ou RDFS.Class)
    seen_classes = set()
    for cls in set(list(g.subjects(RDF.type, OWL.Class)) + list(g.subjects(RDF.type, RDFS.Class))):
        if not isinstance(cls, URIRef):
            continue
        key = _key(str(cls))
        seen_classes.add(str(cls))
        if not classes.has(key):
            doc = {"_key": key, "uri": str(cls), "label": _get_label(g, cls)}
            definition = _get_definition(g, cls)
            if definition:
                doc["definition"] = definition
            classes.insert(doc)

    # subClassOf
    for child, _, parent in g.triples((None, RDFS.subClassOf, None)):
        if not isinstance(child, URIRef) or not isinstance(parent, URIRef):
            # ignorar restrições complexas aqui
            continue
        _ensure_class_vertex(classes, g, child)
        _ensure_class_vertex(classes, g, parent)
        edge_doc = {
            "_from": f"Classes/{_key(str(child))}",
            "_to": f"Classes/{_key(str(parent))}",
            "type": "subClassOf",
        }
        # Evitar duplicatas baratas (Arango não tem upsert trivial via edge_collection)
        exists = list(get_db().aql.execute(
            "FOR e IN Edges FILTER e.type=='subClassOf' AND e._from==@f AND e._to==@t RETURN 1",
            bind_vars={"f": edge_doc["_from"], "t": edge_doc["_to"]},
        ))
        if not exists:
            edges.insert(edge_doc)

    # Object Properties
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        if not isinstance(prop, URIRef):
            continue
        p_key = _key(str(prop))
        if not properties.has(p_key):
            p_doc = {
                "_key": p_key,
                "uri": str(prop),
                "label": _get_label(g, prop),
                "kind": "object",
            }
            definition = _get_definition(g, prop)
            if definition:
                p_doc["definition"] = definition

            domains_raw = list(g.objects(prop, RDFS.domain))
            ranges_raw = list(g.objects(prop, RDFS.range))
            domains: List[URIRef] = []
            ranges: List[URIRef] = []
            for d in domains_raw:
                domains.extend(_expand_to_classes(g, d))
            for r in ranges_raw:
                ranges.extend(_expand_to_classes(g, r))

            p_doc["domains"] = [str(d) for d in domains]
            p_doc["ranges"] = [str(r) for r in ranges]
            properties.insert(p_doc)
        else:
            # opcional: atualizar domains/ranges se necessário (poderia usar replace/patch)
            pass

        # criar arestas domain -> range rotuladas com a propriedade
        domains = [URIRef(u) for u in properties.get(p_key).get("domains", [])]
        ranges = [URIRef(u) for u in properties.get(p_key).get("ranges", [])]
        for d in domains or []:
            _ensure_class_vertex(classes, g, d)
        for r in ranges or []:
            _ensure_class_vertex(classes, g, r)
        for d in domains or []:
            for r in ranges or []:
                edge_doc = {
                    "_from": f"Classes/{_key(str(d))}",
                    "_to": f"Classes/{_key(str(r))}",
                    "type": "objectProperty",
                    "property": p_key,
                    "propertyUri": str(prop),
                }
                exists = list(get_db().aql.execute(
                    "FOR e IN Edges FILTER e.type=='objectProperty' "
                    "AND e._from==@f AND e._to==@t AND e.property==@p RETURN 1",
                    bind_vars={"f": edge_doc["_from"], "t": edge_doc["_to"], "p": p_key},
                ))
                if not exists:
                    edges.insert(edge_doc)

    # Datatype Properties (armazenar metadados; sem arestas classe->classe)
    for dprop in g.subjects(RDF.type, OWL.DatatypeProperty):
        if not isinstance(dprop, URIRef):
            continue
        p_key = _key(str(dprop))
        if not properties.has(p_key):
            p_doc = {
                "_key": p_key,
                "uri": str(dprop),
                "label": _get_label(g, dprop),
                "kind": "datatype",
            }
            definition = _get_definition(g, dprop)
            if definition:
                p_doc["definition"] = definition

            domains_raw = list(g.objects(dprop, RDFS.domain))
            domains: List[URIRef] = []
            for d in domains_raw:
                domains.extend(_expand_to_classes(g, d))

            ranges = [str(r) for r in g.objects(dprop, RDFS.range)]
            p_doc["domains"] = [str(d) for d in domains]
            p_doc["ranges"] = ranges  # tipicamente datatypes XSD
            properties.insert(p_doc)

    return True


# ---------- Consultas úteis (AQL) ----------

def aql_subclasses(of_class_key: str) -> List[dict]:
    """Lista subclasses (filhos diretos) da classe."""
    db = get_db()
    return list(db.aql.execute(
        """
        LET parent_id = CONCAT('Classes/', @k)
        FOR e IN Edges
          FILTER e.type == 'subClassOf' AND e._to == parent_id
          LET child = DOCUMENT(e._from)
          RETURN { _key: child._key, uri: child.uri, label: child.label }
        """,
        bind_vars={"k": of_class_key},
    ))


def aql_outgoing_properties(from_class_key: str) -> List[dict]:
    """Lista propriedades-objeto que saem de uma classe, com o alvo."""
    db = get_db()
    return list(db.aql.execute(
        """
        LET from_id = CONCAT('Classes/', @k)
        FOR e IN Edges
          FILTER e.type == 'objectProperty' AND e._from == from_id
          LET prop = DOCUMENT(CONCAT('Properties/', e.property))
          LET target = DOCUMENT(e._to)
          RETURN {
            propertyKey: e.property,
            propertyUri: e.propertyUri,
            propertyLabel: prop.label,
            to: { _key: target._key, uri: target.uri, label: target.label }
          }
        """,
        bind_vars={"k": from_class_key},
    ))


# ---------- CLI ----------

def import_owl_file(path: str):
    g = RDFGraph()
    g.parse(path)
    ok = insert_ontology(g)
    print("Import finished:", ok)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ontology_arango.py /caminho/para/arquivo.owl")
        sys.exit(1)
    import_owl_file(sys.argv[1])
