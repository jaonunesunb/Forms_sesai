# back_end/src/load_owl_to_arango.py
import os, hashlib
from arango import ArangoClient
from rdflib import Graph, RDF, RDFS, OWL, URIRef, XSD
import o_parse_back_end as op

ARANGO_URL = os.getenv("ARANGO_URL", "http://arango:8529")
ARANGO_DB = os.getenv("ARANGO_DB", "owl_db")
ARANGO_USER = os.getenv("ARANGO_USER", "root")
ARANGO_PASSWORD = os.getenv("ARANGO_PASSWORD", "")

client = ArangoClient(hosts=ARANGO_URL)

def ensure_db():
    sys_db = client.db("_system", username=ARANGO_USER, password=ARANGO_PASSWORD or None)
    if not sys_db.has_database(ARANGO_DB):
        sys_db.create_database(ARANGO_DB)
    return client.db(ARANGO_DB, username=ARANGO_USER, password=ARANGO_PASSWORD or None)

def ensure_col(db, name, edge=False):
    if not db.has_collection(name):
        db.create_collection(name, edge=edge)
    return db.collection(name)

def sha(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

# --- helpers de anotação/descrição ---
SKOS_PREF = URIRef("http://www.w3.org/2004/02/skos/core#prefLabel")
SKOS_ALT  = URIRef("http://www.w3.org/2004/02/skos/core#altLabel")
IAO_DEF   = URIRef("http://purl.obolibrary.org/obo/IAO_0000115")

def get_annotations(g: Graph, e):
    out = {}
    # labels multilíngues
    out["labels"] = [str(l) for l in g.objects(e, RDFS.label)]
    out["prefLabel"] = [str(l) for l in g.objects(e, SKOS_PREF)]
    out["altLabel"]  = [str(l) for l in g.objects(e, SKOS_ALT)]
    # description/definition
    desc = next((str(d) for d in g.objects(e, IAO_DEF)), None) \
        or next((str(c) for c in g.objects(e, RDFS.comment)), None)
    if desc: out["description"] = desc
    # metadados comuns
    out["seeAlso"]     = [str(u) for u in g.objects(e, RDFS.seeAlso)]
    out["isDefinedBy"] = [str(u) for u in g.objects(e, RDFS.isDefinedBy)]
    out["versionInfo"] = [str(v) for v in g.objects(e, OWL.versionInfo)]
    dep = next((str(v).lower() for v in g.objects(e, OWL.deprecated)), None)
    if dep in ("true","1","yes"): out["deprecated"] = True
    return out

def list_xsd_facets(g: Graph, node):
    """Para ranges com owl:onDatatype + owl:withRestrictions."""
    facets = {}
    if (node, OWL.onDatatype, None) in g:
        dt = g.value(node, OWL.onDatatype)
        facets["onDatatype"] = str(dt) if dt else None
        coll = g.value(node, OWL.withRestrictions)
        # coll é uma RDF list de BNodes com xsd facets
        def items(c):
            res = []
            while c and c != RDF.nil:
                res.append(g.value(c, RDF.first))
                c = g.value(c, RDF.rest)
            return res
        for itm in items(coll):
            for p, o in g.predicate_objects(itm):
                facets[str(p)] = str(o)
    return facets

def load_owl(file_path: str, language: str = "pt") -> None:
    db = ensure_db()

    # coleções
    col_classes            = ensure_col(db, "classes")
    col_obj_props          = ensure_col(db, "obj_props")
    col_data_props         = ensure_col(db, "data_props")
    e_class_subclass       = ensure_col(db, "class_subclass", edge=True)
    e_class_equivalent     = ensure_col(db, "class_equivalent", edge=True)
    e_class_disjoint       = ensure_col(db, "class_disjoint", edge=True)
    e_prop_subproperty     = ensure_col(db, "prop_subproperty", edge=True)
    e_prop_inverse         = ensure_col(db, "prop_inverse", edge=True)
    e_domain_obj           = ensure_col(db, "domain_obj", edge=True)
    e_range_obj            = ensure_col(db, "range_obj", edge=True)
    e_domain_data          = ensure_col(db, "domain_data", edge=True)

    # ontologia
    g = op.load_ontology(file_path)
    labels, labels_to_uris, descriptions = op.extract_labels(g, language)  # <<< assinatura correta
    # (labels/descriptions já cobrem classes; abaixo guardamos anotações extras para tudo)

    # --- CLASSES ---
    class_uris = set(g.subjects(RDF.type, OWL.Class))
    for c in class_uris:
        uri = str(c); key = sha(uri)
        label = labels.get(c, uri)
        doc = {"_key": key, "uri": uri, "label": label, "kind": "class"}
        if descriptions.get(uri): doc["description"] = descriptions[uri]
        ann = get_annotations(g, c)
        if ann: doc["annotations"] = ann
        col_classes.insert(doc, overwrite=True)

    # edges de classe
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(s, URIRef) and isinstance(o, URIRef) and s in class_uris and o in class_uris:
            e = {"_from": f"classes/{sha(str(s))}", "_to": f"classes/{sha(str(o))}"}
            e_class_subclass.insert(e, overwrite=True)
    for s, o in g.subject_objects(OWL.equivalentClass):
        if isinstance(s, URIRef) and isinstance(o, URIRef) and s in class_uris and o in class_uris:
            e = {"_from": f"classes/{sha(str(s))}", "_to": f"classes/{sha(str(o))}"}
            e_class_equivalent.insert(e, overwrite=True)
    for s, o in g.subject_objects(OWL.disjointWith):
        if isinstance(s, URIRef) and isinstance(o, URIRef) and s in class_uris and o in class_uris:
            e = {"_from": f"classes/{sha(str(s))}", "_to": f"classes/{sha(str(o))}"}
            e_class_disjoint.insert(e, overwrite=True)

    # --- OBJECT PROPERTIES ---
    obj_props = set(g.subjects(RDF.type, OWL.ObjectProperty))
    for p in obj_props:
        uri = str(p); key = sha(uri)
        doc = {
            "_key": key, "uri": uri,
            "label": labels.get(p, uri),
            "kind": "objectProperty",
            "characteristics": []
        }
        ann = get_annotations(g, p)
        if ann.get("description"): doc["description"] = ann["description"]
        # características
        if (p, RDF.type, OWL.FunctionalProperty) in g:        doc["characteristics"].append("Functional")
        if (p, RDF.type, OWL.InverseFunctionalProperty) in g: doc["characteristics"].append("InverseFunctional")
        if (p, RDF.type, OWL.SymmetricProperty) in g:         doc["characteristics"].append("Symmetric")
        if (p, RDF.type, OWL.TransitiveProperty) in g:        doc["characteristics"].append("Transitive")
        if (p, RDF.type, OWL.ReflexiveProperty) in g:         doc["characteristics"].append("Reflexive")
        if (p, RDF.type, OWL.IrreflexiveProperty) in g:       doc["characteristics"].append("Irreflexive")
        inv = g.value(p, OWL.inverseOf)
        if inv: doc["inverseOf"] = str(inv)
        col_obj_props.insert(doc, overwrite=True)

        # domínio / alcance
        for d in g.objects(p, RDFS.domain):
            if isinstance(d, URIRef) and d in class_uris:
                e_domain_obj.insert({"_from": f"obj_props/{key}", "_to": f"classes/{sha(str(d))}"}, overwrite=True)
        for r in g.objects(p, RDFS.range):
            if isinstance(r, URIRef) and r in class_uris:
                e_range_obj.insert({"_from": f"obj_props/{key}", "_to": f"classes/{sha(str(r))}"}, overwrite=True)

    # inversas e subProperty
    for s, o in g.subject_objects(OWL.inverseOf):
        if s in obj_props and o in obj_props:
            e_prop_inverse.insert({"_from": f"obj_props/{sha(str(s))}", "_to": f"obj_props/{sha(str(o))}"}, overwrite=True)
    for s, o in g.subject_objects(RDFS.subPropertyOf):
        # pode ser entre object ou data; conectaremos quando ambos existirem em suas coleções
        if s in obj_props and o in obj_props:
            e_prop_subproperty.insert({"_from": f"obj_props/{sha(str(s))}", "_to": f"obj_props/{sha(str(o))}"}, overwrite=True)

    # --- DATA PROPERTIES ---
    data_props = set(g.subjects(RDF.type, OWL.DatatypeProperty))
    for p in data_props:
        uri = str(p); key = sha(uri)
        doc = {
            "_key": key, "uri": uri,
            "label": labels.get(p, uri),
            "kind": "dataProperty",
            "characteristics": [],
            "range_datatypes": [],
            "xsd_facets": {}
        }
        ann = get_annotations(g, p)
        if ann.get("description"): doc["description"] = ann["description"]
        if (p, RDF.type, OWL.FunctionalProperty) in g: doc["characteristics"].append("Functional")

        # domain
        for d in g.objects(p, RDFS.domain):
            if isinstance(d, URIRef) and d in class_uris:
                e_domain_data.insert({"_from": f"data_props/{key}", "_to": f"classes/{sha(str(d))}"}, overwrite=True)

        # range (xsd direto ou nó com owl:onDatatype / withRestrictions)
        for r in g.objects(p, RDFS.range):
            if isinstance(r, URIRef):
                doc["range_datatypes"].append(str(r))
            else:
                facets = list_xsd_facets(g, r)
                if facets:
                    if facets.get("onDatatype"):
                        doc["range_datatypes"].append(facets["onDatatype"])
                    doc["xsd_facets"].update({k: v for k, v in facets.items() if k != "onDatatype"})

        col_data_props.insert(doc, overwrite=True)

    # subProperty entre data props
    for s, o in g.subject_objects(RDFS.subPropertyOf):
        if s in data_props and o in data_props:
            e_prop_subproperty.insert({"_from": f"data_props/{sha(str(s))}", "_to": f"data_props/{sha(str(o))}"}, overwrite=True)

if __name__ == "__main__":
    default_owl = os.path.join(os.path.dirname(__file__), "OWL", "Onto_aldeias.owl")
    owl_file = os.getenv("OWL_FILE", default_owl)
    load_owl(owl_file, language=os.getenv("OWL_LANG", "pt"))
