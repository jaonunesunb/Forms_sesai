# Forms SESAI

Este repositório contém uma aplicação composta por um backend em Flask e um frontend em React. A seguir estão as instruções para configurar o ambiente e executar cada parte do projeto.

## Requisitos

- Python 3.10 ou superior
- [Node.js](https://nodejs.org/) e npm

## Backend (Flask)

1. **Criar e ativar o ambiente virtual**
   ```bash
   python -m venv venv
   # Windows
   venv\\Scripts\\activate
   # Linux/macOS
   source venv/bin/activate
   ```

2. **Instalar as dependências**
   ```bash
   pip install -r requirements.txt
   ```

3. **Executar o servidor**
   ```bash
   python back_end/src/app.py
   ```
   O backend ficará acessível em `http://127.0.0.1:5000/`.

## Frontend (React)

1. Instale as dependências do frontend:
   ```bash
   cd front_end
   npm install
   ```

2. Inicie o servidor de desenvolvimento:
   ```bash
   npm start
   ```
   A aplicação será aberta em `http://localhost:3000/`.

## Atualização das dependências Python

Caso novas bibliotecas sejam adicionadas, atualize o arquivo `requirements.txt` com:
```bash
pip freeze > requirements.txt
```

## Contribuição

Sinta-se à vontade para abrir issues ou enviar pull requests com melhorias.
