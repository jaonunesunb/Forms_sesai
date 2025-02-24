from rdflib import BNode, Graph, URIRef, RDFS, OWL, RDF

def list_subclasses(g, class_uri, labels):
    subclasses = []
    for s in g.subjects(RDFS.subClassOf, URIRef(class_uri)):
        subclass_info = {
            "uri": str(s),  # Convertendo a URIRef para string
            "label": labels.get(s, str(s))  # Usando o label, ou a URI como fallback
        }
        subclasses.append(subclass_info)
    return subclasses