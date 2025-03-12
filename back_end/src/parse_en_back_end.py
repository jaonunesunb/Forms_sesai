from rdflib import BNode, Graph, URIRef, RDFS, OWL, RDF

# Global language variable (initialized as 'en' for English)
LANGUAGE = 'en'

# Load the OWL ontology
def load_ontology(file_path):
    g = Graph()
    g.parse(file_path, format='xml')
    return g

# Extract labels of classes and properties, preferring the defined language
def extract_labels(g, language='pt'):
    labels = {}
    labels_to_uris = {}

    # Function that returns the label in the defined language
    def get_label(entity):
        # Try to first get the label in the selected language
        for label in g.objects(entity, RDFS.label):
            if label.language and label.language.startswith(language):
                return str(label)

        # If there is no label in the selected language, get any available label
        for label in g.objects(entity, RDFS.label):
            return str(label)

        return None

    # Iterate over classes, object properties, and data properties to extract labels
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

# Process RDF collections (intersectionOf, unionOf)
def process_collection(g, collection):
    items = []
    while collection and collection != RDF.nil:
        item = g.value(collection, RDF.first)
        if item:
            items.append(item)
        collection = g.value(collection, RDF.rest)
    return items

# Process boolean restrictions (intersectionOf, unionOf)
def process_boolean_restrictions(g, restriction):
    classes = []
    for boolean_prop in [OWL.unionOf, OWL.intersectionOf]:
        if (restriction, boolean_prop, None) in g:
            collection = g.value(restriction, boolean_prop)
            items = process_collection(g, collection)
            classes.extend(items)
    return classes

# Function to extract labels from a class or restriction that can include complex BNodes
def extract_labels_from_complex_class(g, complex_class, labels):
    if isinstance(complex_class, BNode):
        if (complex_class, OWL.intersectionOf, None) in g:
            items = process_collection(g, g.value(complex_class, OWL.intersectionOf))
            return [extract_labels_from_complex_class(g, item, labels) for item in items]
        elif (complex_class, OWL.unionOf, None) in g:
            items = process_collection(g, g.value(complex_class, OWL.unionOf))
            return [extract_labels_from_complex_class(g, item, labels) for item in items]
        elif (complex_class, OWL.onProperty, None) in g:
            property_uri = g.value(complex_class, OWL.onProperty)
            range_class = g.value(complex_class, OWL.allValuesFrom) or g.value(complex_class, OWL.someValuesFrom)
            return [(labels.get(property_uri, str(property_uri)), extract_labels_from_complex_class(g, range_class, labels))]
    else:
        return labels.get(complex_class, str(complex_class))

# Process restrictions with properties and cardinalities
def process_restriction(g, restriction, labels):
    on_property = g.value(restriction, OWL.onProperty)
    on_class = (g.value(restriction, OWL.onClass) or 
                g.value(restriction, OWL.someValuesFrom) or 
                g.value(restriction, OWL.allValuesFrom))

    if on_class is None:
        on_class = []

    # Check for nested intersections
    if isinstance(on_class, BNode) and (on_class, OWL.intersectionOf, None) in g:
        on_class = process_collection(g, g.value(on_class, OWL.intersectionOf))
    elif isinstance(on_class, BNode) and (on_class, OWL.unionOf, None) in g:
        on_class = process_collection(g, g.value(on_class, OWL.unionOf))
        on_class_labels = [labels.get(cls, str(cls)) for cls in on_class]
        return (on_property, on_class_labels, "union")

    if not isinstance(on_class, list):
        on_class = [on_class]

    on_class_labels = [extract_labels_from_complex_class(g, cls, labels) for cls in on_class]

    # Check for cardinalities
    min_cardinality = g.value(restriction, OWL.minQualifiedCardinality) or g.value(restriction, OWL.minCardinality)
    max_cardinality = g.value(restriction, OWL.maxQualifiedCardinality) or g.value(restriction, OWL.maxCardinality)
    exact_cardinality = g.value(restriction, OWL.qualifiedCardinality) or g.value(restriction, OWL.cardinality)

    cardinality_str = None
    if min_cardinality is not None:
        cardinality_str = f"min {min_cardinality}"
    elif max_cardinality is not None:
        cardinality_str = f"max {max_cardinality}"
    elif exact_cardinality is not None:
        cardinality_str = f"exactly {exact_cardinality}"
    elif (restriction, OWL.someValuesFrom, None) in g:
        cardinality_str = "some"
    elif (restriction, OWL.allValuesFrom, None) in g:
        cardinality_str = "only"

    return (on_property, on_class_labels, cardinality_str)

# Update logic to handle dates and times correctly
def list_restrictions_and_data_properties(g, class_uri, labels, labels_to_uris):
    restrictions = []

    def get_restrictions_recursive(uri):
        if str(uri) == 'hhttp://www.semanticweb.org/ontologias/OntoSesai/sesai_00000317':
            return

        for _, p, o in g.triples((URIRef(uri), RDFS.subClassOf, None)):
            if isinstance(o, URIRef):
                get_restrictions_recursive(o)
            if isinstance(o, BNode) or isinstance(o, URIRef):
                if (o, OWL.intersectionOf, None) in g:
                    for item in process_collection(g, g.value(o, OWL.intersectionOf)):
                        if (item, OWL.onProperty, None) in g:
                            restrictions.append(process_restriction(g, item, labels))
                else:
                    restrictions.append(process_restriction(g, o, labels))

    get_restrictions_recursive(class_uri)

    data_fields = []
    for restriction in restrictions:
        if len(restriction) == 3:
            property_uri, related_classes, cardinality = restriction

            for related_class in related_classes:
                if isinstance(related_class, (list, tuple)):
                    related_class_str = ' - '.join(
                        [labels.get(cls, str(cls)) for cls in related_class]
                    )
                else:
                    if isinstance(related_class, str) and related_class in labels_to_uris:
                        related_class = labels_to_uris[related_class]
                    related_class_str = labels.get(related_class, str(related_class))

                # Handle exactly 1 for date and time
                if cardinality == "exactly 1":
                    data_fields.append({
                        "property": str(property_uri),
                        "label": labels.get(property_uri, property_uri),
                        "relatedClass": related_class_str,
                        "dataType": ["http://www.w3.org/2001/XMLSchema#time"] if "horário" in related_class_str else ["http://www.w3.org/2001/XMLSchema#date"],
                        "cardinality": cardinality 
                    })
                else:
                    subclasses = list_subclasses(g, related_class, labels)
                    if subclasses:
                        data_fields.append({
                            "property": str(property_uri),
                            "label": labels.get(property_uri, property_uri),
                            "relatedClass": related_class_str,
                            "subclasses": subclasses,
                            "cardinality": cardinality
                        })
                    else:
                        data_props = find_data_properties_for_related_classes(g, related_class)
                        if data_props:
                            for prop_uri, prop_restrictions in data_props:
                                data_fields.append({
                                    "property": str(property_uri),
                                    "label": labels.get(property_uri, property_uri),
                                    "dataType": prop_restrictions.get('type', ['http://www.w3.org/2001/XMLSchema#string']),
                                    "restrictions": prop_restrictions,
                                    "relatedClass": related_class_str,
                                    "cardinality": cardinality
                                })
                        else:
                            data_fields.append({
                                "property": str(property_uri),
                                "label": labels.get(property_uri, property_uri),
                                "relatedClass": related_class_str,
                                "cardinality": cardinality,
                                "status": "under construction"
                            })

    return data_fields

def list_subclasses(g, class_uri, labels):
    subclasses = []
    for s in g.subjects(RDFS.subClassOf, URIRef(class_uri)):
        data_properties = find_data_properties_for_related_classes(g, s)  # Buscar data properties para cada subclasse

        # Apenas incluir as subclasses que têm propriedades de dados associadas
        subclass_info = {
            "uri": str(s),
            "label": labels.get(s, str(s)),
            "dataProperties": [{
                "property": str(dp[0]),
                "dataType": dp[1].get('type', ['http://www.w3.org/2001/XMLSchema#string']),
                "restrictions": dp[1]
            } for dp in data_properties if dp[1]]  # Inclui propriedades de dados com restrições
        }

        subclasses.append(subclass_info)
    return subclasses

# Função para encontrar propriedades de dados associadas a uma classe, verificando o domain da propriedade
def find_data_properties_for_related_classes(g, class_uri):
    data_properties = []

    for property_uri in g.subjects(RDF.type, OWL.DatatypeProperty):
        # Verificar se a classe faz parte do domínio da propriedade de dados
        for domain_class in g.objects(property_uri, RDFS.domain):
            if str(domain_class) == str(class_uri):  # Verifica se a classe está no domínio
                range_description = g.value(property_uri, RDFS.range)
                restrictions = {}

                # Verifica se há restrições específicas como xsd:maxLength dentro de owl:withRestrictions
                if range_description and (range_description, OWL.withRestrictions, None) in g:
                    restriction_nodes = process_collection(g, g.value(range_description, OWL.withRestrictions))
                    for restriction_node in restriction_nodes:
                        for p, o in g.predicate_objects(restriction_node):
                            restrictions[g.qname(p)] = str(o)

                # Caso não haja restrições explícitas, define o tipo de dados como o range padrão
                else:
                    restrictions['type'] = [range_description]

                data_properties.append((property_uri, restrictions))

    return data_properties



