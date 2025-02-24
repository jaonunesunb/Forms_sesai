from rdflib import BNode, Graph, URIRef, RDFS, OWL, RDF

# Carregar a ontologia OWL
def load_ontology(file_path):
    g = Graph()
    g.parse(file_path, format='xml')
    return g

# Extrair labels de classes e propriedades com preferência por português
def extract_labels(g):
    labels = {}
    labels_to_uris = {}
    
    def get_label(entity):
        for label in g.objects(entity, RDFS.label):
            if label.language and label.language.startswith('en'):
                return str(label)
        for label in g.objects(entity, RDFS.label):
            return str(label)
        return None

    for entity in g.subjects(RDF.type, OWL.Class):
        label = get_label(entity)
        if label:
            labels[entity] = label
            labels_to_uris[label] = entity
    for entity in g.subjects(RDF.type, OWL.ObjectProperty):
        label = get_label(entity)
        if label:
            labels[entity] = label
            labels_to_uris[label] = entity
    for entity in g.subjects(RDF.type, OWL.DatatypeProperty):
        label = get_label(entity)
        if label:
            labels[entity] = label
            labels_to_uris[label] = entity
    
    return labels, labels_to_uris


# Processar coleções RDF (intersectionOf, unionOf)
def process_collection(g, collection):
    items = []
    while collection and collection != RDF.nil:
        item = g.value(collection, RDF.first)
        if item:
            items.append(item)
        collection = g.value(collection, RDF.rest)
    return items

# Processar restrições booleanas (intersectionOf, unionOf)
def process_boolean_restrictions(g, restriction):
    classes = []
    for boolean_prop in [OWL.unionOf, OWL.intersectionOf]:
        if (restriction, boolean_prop, None) in g:
            collection = g.value(restriction, boolean_prop)
            items = process_collection(g, collection)
            classes.extend(items)
    return classes

# Função para extrair labels de uma classe ou restrição que pode incluir BNodes complexos
def extract_labels_from_complex_class(g, complex_class, labels):
    if isinstance(complex_class, BNode):
        if (complex_class, OWL.intersectionOf, None) in g:
            items = process_collection(g, g.value(complex_class, OWL.intersectionOf))
            return [extract_labels_from_complex_class(g, item, labels) for item in items]
        elif (complex_class, OWL.unionOf, None) in g:
            items = process_collection(g, g.value(complex_class, OWL.unionOf))
            return [extract_labels_from_complex_class(g, item, labels) for item in items]
        elif (complex_class, OWL.onProperty, None) in g:
            # Caso de uma restrição dentro de uma classe complexa
            property_uri = g.value(complex_class, OWL.onProperty)
            range_class = g.value(complex_class, OWL.allValuesFrom) or g.value(complex_class, OWL.someValuesFrom)
            return [(labels.get(property_uri, str(property_uri)), extract_labels_from_complex_class(g, range_class, labels))]
    else:
        return labels.get(complex_class, str(complex_class))

# Processar restrições com propriedades e cardinalidades
def process_restriction(g, restriction, labels):
    on_property = g.value(restriction, OWL.onProperty)
    on_class = (g.value(restriction, OWL.onClass) or 
                g.value(restriction, OWL.someValuesFrom) or 
                g.value(restriction, OWL.allValuesFrom))

    # Verificar interseções aninhadas
    if isinstance(on_class, BNode) and (on_class, OWL.intersectionOf, None) in g:
        on_class = process_collection(g, g.value(on_class, OWL.intersectionOf))
    elif (on_class, OWL.unionOf, None) in g:
        on_class = process_boolean_restrictions(g, on_class)
    else:
        on_class = [on_class]

    # Usar a função de extração de labels complexos para lidar com BNodes e outras classes
    on_class_labels = [extract_labels_from_complex_class(g, cls, labels) for cls in on_class]

    min_cardinality = g.value(restriction, OWL.minQualifiedCardinality)
    max_cardinality = g.value(restriction, OWL.maxQualifiedCardinality)
    exact_cardinality = g.value(restriction, OWL.cardinality)

    cardinality_str = None
    if min_cardinality is not None:
        cardinality_str = f"min {min_cardinality}"
    elif max_cardinality is not None:
        cardinality_str = f"max {max_cardinality}"
    elif exact_cardinality is not None:
        cardinality_str = f"exactly {exact_cardinality}"
    elif g.value(restriction, OWL.someValuesFrom):
        cardinality_str = "some"
    elif g.value(restriction, OWL.allValuesFrom):
        cardinality_str = "only"

    return (on_property, on_class_labels, cardinality_str)

def list_restrictions_and_data_properties(g, class_uri, labels, labels_to_uris):
    restrictions = []
    for _, p, o in g.triples((URIRef(class_uri), RDFS.subClassOf, None)):
        if isinstance(o, URIRef):
            continue
        if (o, OWL.intersectionOf, None) in g:
            for item in process_collection(g, g.value(o, OWL.intersectionOf)):
                if (item, OWL.onProperty, None) in g:
                    restrictions.append(process_restriction(g, item, labels))
        else:
            restrictions.append(process_restriction(g, o, labels))

    # Processar as classes relacionadas e verificar as data properties
    for restriction in restrictions:
        property_uri, related_classes, cardinality = restriction
        property_label = labels.get(property_uri, property_uri)
        
        # Flatten the list of related classes
        flattened_related_classes = []
        for related_class in related_classes:
            if isinstance(related_class, list):
                flattened_related_classes.extend(related_class)
            else:
                flattened_related_classes.append(related_class)

        related_class_labels = [labels.get(cls, cls) for cls in flattened_related_classes]
        print(f"  Property: {property_label}, Class: {related_class_labels}, Cardinality: {cardinality}")
        
        # Verificar data properties nas classes relacionadas
        for related_class in flattened_related_classes:
            # Verificar se related_class é uma label e buscar a URI correspondente
            if isinstance(related_class, str) and related_class in labels_to_uris:
                related_class = labels_to_uris[related_class]
            
            if isinstance(related_class, URIRef):
                data_props = find_data_properties_for_related_classes(g, related_class)
                if data_props:
                    print(f"    Data Types Associated with Class {labels.get(related_class, related_class)}:")
                    for prop_uri, prop_restrictions in data_props:
                        prop_label = labels.get(prop_uri, prop_uri)
                        print(f"      Property: {prop_label}, Restrictions: {prop_restrictions}")

# Função que busca as data properties associadas às classes relacionadas
def find_data_properties_for_related_classes(g, class_uri):
    data_properties = []
    
    # Iterar sobre as data properties e verificar se o domínio corresponde à classe relacionada
    for property_uri in g.subjects(RDF.type, OWL.DatatypeProperty):
        domain_class = g.value(property_uri, RDFS.domain)
        
        # Tratar o caso de múltiplos domínios (ex.: unionOf ou intersectionOf)
        if isinstance(domain_class, BNode) and (domain_class, OWL.unionOf, None) in g:
            domain_classes = process_collection(g, g.value(domain_class, OWL.unionOf))
        elif isinstance(domain_class, BNode) and (domain_class, OWL.intersectionOf, None) in g:
            domain_classes = process_collection(g, g.value(domain_class, OWL.intersectionOf))
        else:
            domain_classes = [domain_class]

        # Verifica se a classe relacionada está na lista de domínios
        if class_uri in domain_classes:
            # Verificar restrições de range, se houver
            range_description = g.value(property_uri, RDFS.range)
            restrictions = {}
            if range_description and (range_description, OWL.withRestrictions, None) in g:
                restriction_nodes = process_collection(g, g.value(range_description, OWL.withRestrictions))
                for restriction_node in restriction_nodes:
                    for p, o in g.predicate_objects(restriction_node):
                        restrictions[g.qname(p)] = str(o)
            else:
                restrictions['type'] = [range_description]
            data_properties.append((property_uri, restrictions))
    
    return data_properties


# Função para listar subclasses do primeiro nível de uma classe
def list_subclasses(g, class_uri, labels):
    subclasses = []
    for s in g.subjects(RDFS.subClassOf, URIRef(class_uri)):
        subclasses.append(s)
    return [labels.get(subclass, subclass) for subclass in subclasses]

def main():
    ontology_file = 'back_end/src/OWL/ONTAE.owl'
    class_uri = 'http://www.semanticweb.org/ontologias/ONTAE/ONTAE_00000019'  # Palestra

    g = load_ontology(ontology_file)
    
    # Extrair labels e o dicionário invertido
    labels, labels_to_uris = extract_labels(g)
    
    # Listar subclasses
    subclasses = list_subclasses(g, class_uri, labels)
    print(f"Subclasses of {labels.get(URIRef(class_uri), class_uri)}:")
    for subclass in subclasses:
        print(f"  - {subclass}")
    
    # Listar restrições e data properties associadas
    print(f"Restrictions for class {labels.get(URIRef(class_uri), class_uri)}:")
    list_restrictions_and_data_properties(g, class_uri, labels, labels_to_uris)

if __name__ == "__main__":
    main()
