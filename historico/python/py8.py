import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import serial
import threading
import time
import sqlite3
import datetime

# ===============================
# 🔹 CONFIGURAÇÃO DA PORTA SERIAL
# ===============================
PORTA_SERIAL = 'COM4'
BAUD = 9600

# ===============================
# 🔹 INICIALIZAÇÃO DO FLASK
# ===============================
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# ===============================
# 🔹 CONECTA AO ARDUINO
# ===============================
try:
    arduino = serial.Serial(PORTA_SERIAL, BAUD, timeout=1)
    print(f"Conectado ao Arduino na porta {PORTA_SERIAL}")
    print("Entre em http://localhost:5001")
except:
    arduino = None
    print("⚠ Não foi possível conectar ao Arduino. Verifique a porta.")

# ===============================
# 🔹 BANCO DE DADOS
# ===============================
def criar_banco():
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()

    # tabela jogadores
    c.execute("""
        CREATE TABLE IF NOT EXISTS jogadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            ano TEXT NOT NULL,
            data_criacao TEXT
        )
    """)

    # tabela resultados (cada questão salva)
    c.execute("""
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador_id INTEGER,
            categoria TEXT,
            acertou INTEGER,
            data_criacao TEXT,
            FOREIGN KEY(jogador_id) REFERENCES jogadores(id)
        )
    """)

    conn.commit()
    conn.close()
criar_banco()
# ===============================
# 🔹 VARIÁVEIS DO JOGO
# ===============================
acertos = 0
nome_atual = None
ano_atual = None

# ===============================
# 🔹 ROTA PRINCIPAL
# ===============================
@app.route('/')
def index():
    return render_template('index.html')

# ===============================
# 🔹 THREAD PARA LER O ARDUINO
# ===============================
def ler_serial():
    if not arduino:
        print("Arduino não conectado. Apenas o site funcionará.")
        return
    while True:
        try:
            linha = arduino.readline().decode(errors='ignore').strip()
            if linha and linha.startswith("BTN"):
                print(f"Botão pressionado: {linha}")
                socketio.emit('botao', {'botao': linha})
            time.sleep(0.01)
        except Exception as e:
            print(f"Erro lendo serial: {e}")
            break


def salvar_resultado_bd(jogador_id, categoria, acertou):
    data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("quiz.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO resultados (jogador_id, categoria, acertou, data_criacao)
        VALUES (?, ?, ?, ?)
    """, (jogador_id, categoria, acertou, data_atual))
    conn.commit()
    conn.close()

@app.route('/salvar_jogador', methods=['POST'])
def salvar_jogador():
    data = request.json
    nome = data.get("nome")
    ano = data.get("ano")
    data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("quiz.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jogadores (nome, ano, data_criacao)
        VALUES (?, ?, ?)
    """, (nome, ano, data_atual))
    jogador_id = cursor.lastrowid  # pega o ID gerado
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "id": jogador_id})


@socketio.on('acertou')
def handle_acerto(data=None):
    global acertos
    acertos += 1
    categoria = data.get("categoria") if data else "Sem categoria"
    print(f"✅ {nome_atual} acertou ({acertos} acertos) - Categoria: {categoria}")
    salvar_resultado(categoria, 1)
    if arduino:
        arduino.write(b"ACERTOU\n")

@socketio.on('errou')
def handle_erro(data=None):
    categoria = data.get("categoria") if data else "Sem categoria"
    print(f"❌ {nome_atual} errou - Categoria: {categoria}")
    salvar_resultado(categoria, 0)
    if arduino:
        arduino.write(b"ERROU\n")

@socketio.on('recompensa')
def handle_recompensa():
    global acertos
    print(f"🏆 Página da recompensa: {acertos} acertos")
    if arduino and acertos in [7, 8]:
        arduino.write(b"BONUS\n")

@socketio.on('reset')
def handle_reset():
    global acertos, nome_atual, ano_atual
    acertos = 0
    nome_atual = None
    ano_atual = None
    print("🔄 Jogo reiniciado! Acertos zerados.")

@app.route('/salvar_resultado', methods=['POST'])
def salvar_resultado():
    data = request.json
    jogador_id = data.get("jogador_id")
    categoria = data.get("categoria")
    acertou = data.get("acertou")
    data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("quiz.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO resultados (jogador_id, categoria, acertou, data_criacao
        )
        VALUES (?, ?, ?, ?)
    """, (jogador_id, categoria, acertou, data_atual))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "mensagem": "Resultado salvo com sucesso!"})
@app.route('/relatorio/<int:player_id>')
def relatorio(player_id):
    # Conectar no banco
    conn = sqlite3.connect('seu_banco.db')
    cursor = conn.cursor()
    
    # Buscar os resultados do jogador
    cursor.execute("SELECT questao, acertos, erros FROM resultados WHERE jogador_id=?", (player_id,))
    resultados = cursor.fetchall()  # [(questao1, acertos1, erros1), ...]
    
    # Buscar o nome do jogador
    cursor.execute("SELECT nome FROM jogadores WHERE id=?", (player_id,))
    jogador = cursor.fetchone()
    nome = jogador[0] if jogador else "Jogador Desconhecido"
    
    conn.close()
    
    return render_template('relatorio.html', nome=nome, resultados=resultados)
    # Totais por categoria (geral)
    cursor.execute("""
        SELECT categoria,
               SUM(acertou) AS acertos,
               COUNT(id) - SUM(acertou) AS erros
        FROM resultados
        GROUP BY categoria
    """)
    categorias = cursor.fetchall()

    conn.close()

    return render_template("relatorio.html", totais=totais, categorias=categorias)

@app.route('/participantes/<ano>')
def participantes_por_ano(ano):
    conn = sqlite3.connect("quiz.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nome FROM jogadores WHERE ano = ?", (ano,))
    jogadores = cursor.fetchall()
    conn.close()

    # Retorna lista de nomes, sem acertos/erros
    lista_nomes = [{"nome": j[0]} for j in jogadores]
    return jsonify(lista_nomes)



# ===============================
# 🔹 INICIA O SERVIDOR
# ===============================
if __name__ == '__main__':
    socketio.start_background_task(ler_serial)
    socketio.run(app, host='0.0.0.0', port=5001)
