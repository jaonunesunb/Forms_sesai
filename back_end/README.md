# Projeto Adaptative User Interface Eventos UnB

## Configuração do Ambiente Virtual

Certifique-se de ter o Python instalado em seu sistema. Use os seguintes comandos para configurar e ativar o ambiente virtual:

```bash
# Crie o ambiente virtual
python -m venv venv
```

- Ative o ambiente virtual (Windows)

```bash
venv\Scripts\activate
```

- Ative o ambiente virtual (Linux/macOS)

```bash
source venv/bin/activate
```

- Instalação das Dependências

Com o ambiente virtual ativado, instale as dependências do projeto usando o comando a seguir:

```bash
pip install -r requirements.txt
```

Este comando instalará todas as bibliotecas necessárias listadas no arquivo requirements.txt.

## Inicialização do Aplicativo

Após instalar as dependências, você pode iniciar o aplicativo Flask com o seguinte comando:
Como Rodar o Backend
Inicie o servidor Flask:

```bash
python src/app.py
```

O aplicativo estará acessível em http://127.0.0.1:5000/.

## Endpoints Disponíveis

`/get_subclasses`

* Descrição: Retorna as subclasses de uma classe especificada.

* Método: GET

* Parâmetros:
- class: URI da classe para a qual você deseja listar as subclasses.

Exemplo de Uso:

GET `http://127.0.0.1:5000/get_subclasses?class=http://www.semanticweb.org/ontologias/ONTAE/ONTAE_00000000`

`/get_class_details`

* Descrição: Retorna as restrições e propriedades de dados associadas a uma classe especificada.

* Método: GET

* Parâmetros:

* class: URI da classe para a qual você deseja listar os detalhes.

Exemplo de Uso:

GET `http://127.0.0.1:5000/get_class_details?class=http://www.semanticweb.org/ontologias/ONTAE/ONTAE_00000019`

## Classe Recomendada para Testes
Para testar o funcionamento correto do sistema, recomenda-se usar a classe Palestra com a seguinte URI:

URI: `http://www.semanticweb.org/ontologias/ONTAE/ONTAE_00000019`

Essa classe está completamente configurada com data properties, permitindo que o sistema extraia corretamente as restrições e propriedades necessárias para a geração do formulário dinâmico.

## Observações Importantes
Data Properties: Algumas classes na ontologia ainda não têm data properties associadas, o que significa que, ao consultá-las, o sistema não retornará resultados ou detalhes completos. É altamente recomendado completar a definição dessas propriedades na ontologia antes de usá-las no sistema.

## Atualização de Dependências

Se você adicionar ou remover bibliotecas durante o desenvolvimento, certifique-se de atualizar o arquivo requirements.txt com o seguinte comando:

```bash
pip freeze > requirements.txt
```

Isso garantirá que as versões corretas das bibliotecas sejam instaladas por outros colaboradores.

## Contribuição

Sinta-se à vontade para contribuir com melhorias, correções de bugs ou novos recursos. Faça um fork do repositório, crie uma branch para suas alterações e envie um pull request quando estiver pronto.

Obrigado por contribuir para o meu projeto de TCC!

Este README fornece instruções claras sobre como configurar o ambiente virtual, instalar as dependências, iniciar o aplicativo e atualizar o arquivo `requirements.txt`. Certifique-se de personalizar as instruções com detalhes específicos do seu projeto, se necessário.
