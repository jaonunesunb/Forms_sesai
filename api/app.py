from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"message": "Hello from Flask on Vercel!"})

# Certifique-se de que o nome da função seja handler
def handler(event, context):
    return app(event, context)
