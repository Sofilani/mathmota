import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template
from flask_socketio import SocketIO
import serial
import threading
import time
import sqlite3
import datetime


PORTA_SERIAL = 'COM4'
BAUD = 9600

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


try:
    arduino = serial.Serial(PORTA_SERIAL, BAUD, timeout=1)
    print(f"Conectado ao Arduino na porta {PORTA_SERIAL}")
    print("Entre em http://localhost:5001")
except:
    arduino = None
    print("⚠ Não foi possível conectar ao Arduino. Verifique a porta.")


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


acertos = 0
nome_atual = None
ano_atual = None


@app.route('/')
def index():
    return render_template('index.html')


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
    
def salvar_resultados(jogador_id, resultados):
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    data = datetime.datetime.now().isoformat()
    for r in resultados:
        c.execute("INSERT INTO resultados (jogador_id, categoria, acertou, data) VALUES (?, ?, ?, ?)",
                  (jogador_id, r['categoria'], int(r['acertou']), data))
    conn.commit()
    conn.close()


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

@app.route('/jogadores/<ano>')
def get_jogadores(ano):
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()
    c.execute("SELECT nome, ano FROM jogadores WHERE ano=?", (ano,))
    jogadores = [{"nome": row[0], "ano": row[1]} for row in c.fetchall()]
    conn.close()
    return {"jogadores": jogadores}


@app.route('/relatorio/<nome>')
def relatorio(nome):
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()

    # Pega o ID do jogador
    c.execute("SELECT id FROM jogadores WHERE nome=?", (nome,))
    jogador = c.fetchone()

    if not jogador:
        conn.close()
        return {"resultados": []}  # jogador não encontrado

    jogador_id = jogador[0]

    # Busca resultados
    c.execute("""
        SELECT categoria, acertou, data 
        FROM resultados 
        WHERE jogador_id=? 
        ORDER BY data ASC
    """, (jogador_id,))

    resultados = [{"categoria": row[0], "acertou": row[1], "data": row[2]} for row in c.fetchall()]
    conn.close()
    return {"resultados": resultados}




if __name__ == '__main__':
    socketio.start_background_task(ler_serial)
    socketio.run(app, host='0.0.0.0', port=5001)
