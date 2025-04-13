from flask_restx import Api, Resource, fields, Namespace
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
import requests
import os

# Defina basedir ANTES de usar
basedir = os.path.abspath(os.path.dirname(__file__))

# Cria a pasta instance se não existir - AGORA COM basedir DEFINIDO
if not os.path.exists(os.path.join(basedir, 'instance')):
    os.makedirs(os.path.join(basedir, 'instance'))

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuração do banco de dados (usando basedir que já está definido)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance/idosos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Idoso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    idade = db.Column(db.Integer, nullable=False)
    nome_responsavel = db.Column(db.String(100), nullable=False)
    celular_responsavel = db.Column(db.String(15), nullable=False)
    cep = db.Column(db.String(9), nullable=False)
    logradouro = db.Column(db.String(100))
    numero = db.Column(db.String(10))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))

    # ===== SWAGGER CONFIGURATION =====
api = Api(
    app,
    version='1.0',
    title='API Cadastro de Idosos',
    description='Documentação para integração com Frontend React',
    doc='/swagger-ui',
    default='Cadastro',
    default_label='Endpoints principais'
)

ns = Namespace('idosos', description='Operações com idosos')
api.add_namespace(ns)

modelo_idoso = api.model('Idoso', {
    'id': fields.Integer(readOnly=True),
    'nome': fields.String(required=True, example='Fulano da Silva'),
    'idade': fields.Integer(required=True, example=75),
    'nome_responsavel': fields.String(required=True, example='Responsável Legal'),
    'celular_responsavel': fields.String(required=True, example='(11) 98765-4321'),
    'cep': fields.String(required=True, example='01001000'),
    'logradouro': fields.String(example='Rua das Flores'),
    'numero': fields.String(required=True, example='123'),
    'bairro': fields.String(example='Centro'),
    'cidade': fields.String(example='São Paulo'),
    'uf': fields.String(example='SP')
})

modelo_cep = api.model('CEP', {
    'logradouro': fields.String,
    'bairro': fields.String,
    'cidade': fields.String,
    'uf': fields.String,
    'cep': fields.String
})

# Cria o banco de dados
db_path = Path("idosos.db")
if db_path.exists():
    db_path.unlink()  # Remove o arquivo vazio

# Criação do banco de dados
with app.app_context():
    db.create_all()
    db_path = os.path.join(basedir, 'instance/idosos.db')
    if os.path.exists(db_path):
        print(f"Banco criado em: {db_path}")
    else:
        print("Banco de dados não foi criado!")

# Adicione esta rota temporária para teste
@app.route('/teste')
def teste():
    return jsonify({"status": "API operacional", "banco": "Conectado"})

@app.route('/status')
def status():
    return jsonify({
        "status": "API está funcionando",
        "documentacao": "http://localhost:5000/swagger-ui",
        "rotas": {
            "cadastrar_idoso": "POST /idosos",
            "buscar_cep": "GET /cep/<cep>",
            "listar_idosos": "GET /idosos"
        }
    })


@app.route('/caminho_banco')
def mostra_caminho():
    return jsonify({
        "caminho_absoluto": os.path.abspath('instance/idosos.db'),
        "existe": os.path.exists('instance/idosos.db')
    })


# ===== ROTAS DOCUMENTADAS COM SWAGGER =====
@ns.route('')
class IdosoListResource(Resource):
    @ns.doc('list_idosos')
    @ns.marshal_list_with(modelo_idoso)
    def get(self):
        """Lista todos os idosos cadastrados"""
        try:
            idosos = Idoso.query.all()
            return [{
                "id": idoso.id,
                "nome": idoso.nome,
                "idade": idoso.idade,
                "nome_responsavel": idoso.nome_responsavel,
                "celular_responsavel": idoso.celular_responsavel,
                "cep": idoso.cep,
                "logradouro": idoso.logradouro,
                "numero": idoso.numero,
                "bairro": idoso.bairro,
                "cidade": idoso.cidade,
                "uf": idoso.uf
            } for idoso in idosos], 200
        except Exception as e:
            return {"erro": str(e)}, 500

    @ns.doc('create_idoso')
    @ns.expect(modelo_idoso)
    @ns.marshal_with(modelo_idoso, code=201)
    def post(self):
        """Cadastra um novo idoso"""
        try:
            dados = request.json
            
            campos_obrigatorios = ['nome', 'idade', 'nome_responsavel', 'celular_responsavel', 'cep']
            if not all(campo in dados for campo in campos_obrigatorios):
                return {"erro": "Campos obrigatórios faltando"}, 400

            novo_idoso = Idoso(
                nome=dados['nome'],
                idade=dados['idade'],
                nome_responsavel=dados['nome_responsavel'],
                celular_responsavel=dados['celular_responsavel'],
                cep=dados['cep'],
                logradouro=dados.get('logradouro', ''),
                numero=dados.get('numero', ''),
                bairro=dados.get('bairro', ''),
                cidade=dados.get('cidade', ''),
                uf=dados.get('uf', '')
            )

            db.session.add(novo_idoso)
            db.session.commit()

            idoso_salvo = db.session.get(Idoso, novo_idoso.id)
            print("Dados salvos no banco:", {
                "logradouro": idoso_salvo.logradouro,
                "numero": idoso_salvo.numero,
                "bairro": idoso_salvo.bairro,
                "cidade": idoso_salvo.cidade,
                "uf": idoso_salvo.uf
            })

            return db.session.get(Idoso, novo_idoso.id), 201

        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@ns.route('/<int:id>')
@ns.param('id', 'ID do idoso')
class IdosoResource(Resource):
    @ns.doc('get_idoso')
    @ns.marshal_with(modelo_idoso)
    @ns.response(404, 'Idoso não encontrado')
    def get(self, id):
        """Busca um idoso pelo ID"""
        idoso = db.session.get(Idoso, id)
        if not idoso:
            ns.abort(404, "Idoso não encontrado")
        return idoso

    @ns.doc('delete_idoso')
    @ns.response(204, 'Idoso removido')
    def delete(self, id):
        """Remove um idoso"""
        try:
            idoso = db.session.get(Idoso, id)
            if not idoso:
                return {"erro": "Idoso não encontrado"}, 404

            db.session.delete(idoso)
            db.session.commit()
            return '', 204

        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

    @ns.doc('update_idoso')
    @ns.expect(modelo_idoso)
    @ns.marshal_with(modelo_idoso)
    def put(self, id):
        """Atualiza dados do idoso"""
        try:
            idoso = db.session.get(Idoso, id)
            if not idoso:
                return {"erro": "Idoso não encontrado"}, 404

            dados = request.json
            
            if 'nome' in dados:
                idoso.nome = dados['nome']
            if 'idade' in dados:
                idoso.idade = dados['idade']
            if 'nome_responsavel' in dados:
                idoso.nome_responsavel = dados['nome_responsavel']
            if 'celular_responsavel' in dados:
                idoso.celular_responsavel = dados['celular_responsavel']
            if 'cep' in dados:
                idoso.cep = dados['cep']
            if 'logradouro' in dados:
                idoso.logradouro = dados['logradouro']
            if 'numero' in dados:
                idoso.numero = dados['numero']
            if 'bairro' in dados:
                idoso.bairro = dados['bairro']
            if 'cidade' in dados:
                idoso.cidade = dados['cidade']
            if 'uf' in dados:
                idoso.uf = dados['uf']

            db.session.commit()
            return db.session.get(Idoso, id)

        except Exception as e:
            db.session.rollback()
            return {"erro": str(e)}, 500

@app.route('/cep/<cep>', methods=['GET'])
def buscar_endereco(cep):
    try:
        # Limpa o CEP (remove traços e espaços)
        cep_limpo = ''.join(filter(str.isdigit, cep))
        
        if len(cep_limpo) != 8:
            return jsonify({"erro": "CEP deve conter 8 dígitos"}), 400
        
        # Faz a requisição para o ViaCEP
        response = requests.get(f'https://viacep.com.br/ws/{cep_limpo}/json/')
        data = response.json()
        
        if 'erro' in data:
            return jsonify({"erro": "CEP não encontrado"}), 404

        # Formata a resposta
        return jsonify({
            "logradouro": data.get('logradouro', ''),
            "bairro": data.get('bairro', ''),
            "cidade": data.get('localidade', ''),
            "uf": data.get('uf', ''),
            "cep": data.get('cep', '')
        })

    except requests.exceptions.RequestException as e:
        return jsonify({"erro": "Falha na conexão com o serviço de CEP"}), 502
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
