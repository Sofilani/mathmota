import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import serial
import threading
import time
import sqlite3



PORTA_SERIAL = 'COM4'
BAUD = 9600

# ===== INICIALIZAÇÃO DO FLASK =====
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# ===== CONECTA AO ARDUINO =====
try:
    arduino = serial.Serial(PORTA_SERIAL, BAUD, timeout=1)
    print(f"Conectado ao Arduino na porta {PORTA_SERIAL}")
    print("Entre em http://localhost:5001")
except:
    arduino = None
    print("⚠ Não foi possível conectar ao Arduino. Verifique a porta.")

acertos = 0 
# ===== ROTA PRINCIPAL (CARREGA O SITE) =====
@app.route('/')
def index():
    return render_template('index.html')

# ===== THREAD PARA LER O ARDUINO E ENVIAR AO NAVEGADOR =====
def ler_serial():
    if not arduino:
        print("Arduino não conectado. Apenas o site funcionará.")
        return
    while True:
        try:
            linha = arduino.readline().decode(errors='ignore').strip()
            if linha:
                if linha.startswith("BTN"):
                    print(f"Botão pressionado: {linha}")
                    socketio.emit('botao', {'botao': linha})
            time.sleep(0.01)
        except Exception as e:
            print(f"Erro lendo serial: {e}")
            break

# ===== EVENTO DE ACERTO (vem do site) =====
@socketio.on('acertou')
def handle_acerto():
    global acertos
    acertos += 1
    print(f"✅ Usuário acertou ({acertos} acertos até agora)")

    if arduino:
        arduino.write(b"ACERTOU\n")  # aciona servo1 e servo2
       
@socketio.on('recompensa')
def handle_recompensa():
    global acertos
    print(f"Pagina da recompensa: {acertos} acertos")

    if arduino and acertos in [7, 8]:
        arduino.write(b"BONUS\n")       
@socketio.on('reset')
def handle_reset():
    global acertos
    acertos = 0
    print(" Jogo reiniciado! Acertos zerados.")

@socketio.on('errou')
def handle_erro():
    if arduino:
        arduino.write(b"ERROU\n")

def conectar():
    conn = sqlite3.connect("quiz.db")
    conn.row_factory = sqlite3.Row  # permite acessar por nome de coluna
    return conn

@app.route("/salvar_resultado", methods=["POST"])
def salvar_resultado():
    dados = request.json
    nome = dados["nome"]
    ano = dados["ano"]
    resultados = dados["resultados"]  

    conn = conectar()
    c = conn.cursor()

    # Verifica se aluno já existe
    c.execute("SELECT id FROM alunos WHERE nome=? AND ano=?", (nome, ano))
    aluno = c.fetchone()
    if aluno:
        aluno_id = aluno["id"]
    else:
        c.execute("INSERT INTO alunos (nome, ano) VALUES (?, ?)", (nome, ano))
        aluno_id = c.lastrowid

    # Salva resultado
    for resultado in resultados:
        c.execute(
            "INSERT INTO resultados (aluno_id, categoria, acertou, data) VALUES (?, ?, ?, datetime('now'))",
            (aluno_id, resultado["categoria"], int(resultado["acertou"]))
        )


    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

@app.route("/resultados/<ano>")
def resultados_ano(ano):
    conn = conectar()
    c = conn.cursor()

    c.execute("""
    SELECT alunos.nome, resultados.acertos, resultados.erros, resultados.data
    FROM resultados
    JOIN alunos ON alunos.id = resultados.aluno_id
    WHERE alunos.ano = ?
    ORDER BY resultados.rowid DESC
    """, (ano,))


    rows = c.fetchall()
    conn.close()

    # transforma em lista de listas para o JS
    return jsonify([[r["nome"], r["acertos"], r["erros"], r["data"]] for r in rows])


# ===== INICIA O SERVIDOR =====
if __name__ == '__main__':
    socketio.start_background_task(ler_serial)
    socketio.run(app, host='0.0.0.0', port=5001)
    


