import json
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import o_parse_back_end as op 
import prompt as pr

app = Flask(__name__)
CORS(app)

# Variável global de idioma, com valor padrão como 'pt'
current_language = 'pt'

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
    data = request.get_json()  # Recebe os dados do formulário
    print(data)  # Verifique os dados no console
    # Salva os dados do formulário em um arquivo JSON
    with open('form_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return jsonify({"message": "Formulário recebido com sucesso!"}), 200

# Função para buscar subclasses
@app.route('/get_subclasses', methods=['GET'])
def get_subclasses():
    class_uri = request.args.get('class')
    if not class_uri:
        return jsonify({"error": "class parameter is required"}), 400

    # Carrega a ontologia e extrai as subclasses
    g = op.load_ontology('back_end/src/OWL/docs_sesai.owl')
    labels, _ = op.extract_labels(g, current_language)
    subclasses = pr.list_subclasses(g, class_uri, labels)

    # Retorna subclasses como um JSON com uri e label
    return jsonify({"subclasses": subclasses})

# Função para buscar os detalhes de uma classe
@app.route('/get_class_details', methods=['GET'])
def get_class_details():
    class_uri = request.args.get('class')
    if not class_uri:
        return jsonify({"error": "class parameter is required"}), 400

    # Carrega a ontologia e extrai os detalhes da classe
    g = op.load_ontology('back_end/src/OWL/docs_sesai.owl')
    labels, labels_to_uris = op.extract_labels(g, current_language)
    details = op.list_restrictions_and_data_properties(g, class_uri, labels, labels_to_uris)

    response = json.dumps(details, ensure_ascii=False)
    return Response(response, content_type='application/json; charset=utf-8')

if __name__ == '__main__':
    app.run(debug=True)
