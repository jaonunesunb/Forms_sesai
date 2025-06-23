export const loadDocuments = async () => {

	const documentsResponse = fetch('http://localhost:5000/get_subclasses?class=http://www.semanticweb.org/ontologias/SESAI/ontoAldeias_00000557');

    const [ documents ] = await Promise.all([documentsResponse]);

    const documentsJson = await documents.json();

    const documentsFinal = documentsJson.subclasses.map((document, index) => {
      return { ...document }
    });

	return documentsFinal;
}