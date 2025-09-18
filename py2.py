import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template
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
            ano TEXT NOT NULL
        )
    """)

    # tabela resultados (cada questão salva)
    c.execute("""
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador_id INTEGER,
            categoria TEXT,
            acertou INTEGER,
            data TEXT,
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

# ===============================
# 🔹 FUNÇÃO PARA SALVAR RESULTADOS
# ===============================
def salvar_resultado(categoria, acertou):
    global nome_atual, ano_atual
    if not nome_atual or not ano_atual:
        print("⚠ Nenhum jogador ativo. Resultado não salvo.")
        return

    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()

    # procura jogador atual
    c.execute("SELECT id FROM jogadores WHERE nome=? AND ano=?", (nome_atual, ano_atual))
    jogador = c.fetchone()

    if jogador:
        jogador_id = jogador[0]
    else:
        # cria novo jogador caso não exista
        c.execute("INSERT INTO jogadores (nome, ano) VALUES (?, ?)", (nome_atual, ano_atual))
        jogador_id = c.lastrowid

    data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO resultados (jogador_id, categoria, acertou, data)
        VALUES (?, ?, ?, ?)
    """, (jogador_id, categoria, acertou, data_atual))

    conn.commit()
    conn.close()
    print(f"💾 Resultado salvo no banco para {nome_atual} - {categoria}: {'Acertou' if acertou else 'Errou'}")

# ===============================
# 🔹 EVENTOS SOCKET.IO
# ===============================
@socketio.on('novo_jogador')
def handle_novo_jogador(data):
    global nome_atual, ano_atual, acertos
    nome_atual = data.get("nome")
    ano_atual = data.get("ano")
    acertos = 0

    print(f"🎮 Novo jogador: {nome_atual} ({ano_atual})")

    # já salva no banco ao iniciar se não existir
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    c.execute("SELECT id FROM jogadores WHERE nome=? AND ano=?", (nome_atual, ano_atual))
    jogador = c.fetchone()
    if not jogador:
        c.execute("INSERT INTO jogadores (nome, ano) VALUES (?, ?)", (nome_atual, ano_atual))
        conn.commit()
    conn.close()

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

@socketio.on('pegar_jogadores')
def handle_pegar_jogadores():
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    c.execute("SELECT id, nome, ano FROM jogadores")
    jogadores = [{"id": row[0], "nome": row[1], "ano": row[2]} for row in c.fetchall()]
    conn.close()
    socketio.emit('lista_jogadores', jogadores)
@socketio.on('pegar_relatorio')
def handle_pegar_relatorio(data):
    jogador_id = data['jogador_id']
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    # pegar nome e ano do jogador
    c.execute("SELECT nome, ano FROM jogadores WHERE id=?", (jogador_id,))
    jogador = c.fetchone()
    if not jogador:
        socketio.emit('relatorio_jogador', {"html": "<p>Aluno não encontrado</p>"})
        return
    nome, ano = jogador

    # pegar resultados
    c.execute("SELECT categoria, acertou FROM resultados WHERE jogador_id=?", (jogador_id,))
    resultados = c.fetchall()
    conn.close()

    # gerar HTML similar ao reportScreen
    acertos = sum(r[1] for r in resultados)
    erros = len(resultados) - acertos

    categorias = {}
    for cat, acertou in resultados:
        if cat not in categorias:
            categorias[cat] = {"acertos":0, "erros":0, "total":0}
        categorias[cat]["total"] += 1
        if acertou: categorias[cat]["acertos"] += 1
        else: categorias[cat]["erros"] += 1

    html = f"<h2>{nome} ({ano}) - Acertos: {acertos}/{len(resultados)}</h2>"
    for cat, val in categorias.items():
        html += f"<p>{cat}: {val['acertos']} acertos, {val['erros']} erros</p>"
    html += f"<p>Total de erros: {erros}</p>"

    socketio.emit('relatorio_jogador', {"html": html})


# ===============================
# 🔹 INICIA O SERVIDOR
# ===============================
if __name__ == '__main__':
    socketio.start_background_task(ler_serial)
    socketio.run(app, host='0.0.0.0', port=5001)
