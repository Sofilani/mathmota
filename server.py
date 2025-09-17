import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import serial
import threading
import time

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
            if linha and linha.startswith("BTN"):
                print(f"Botão pressionado: {linha}")
                socketio.emit('botao', {'botao': linha})
            time.sleep(0.01)
        except Exception as e:
            print(f"Erro lendo serial: {e}")
            break

# ===== EVENTOS SOCKETIO =====
@socketio.on('acertou')
def handle_acerto():
    global acertos
    acertos += 1
    print(f"✅ Usuário acertou ({acertos} acertos até agora)")
    if arduino:
        arduino.write(b"ACERTOU\n")

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
    print("Jogo reiniciado! Acertos zerados.")

@socketio.on('errou')
def handle_erro():
    if arduino:
        arduino.write(b"ERROU\n")

# ===== INICIA O SERVIDOR =====
if __name__ == '__main__':
    socketio.start_background_task(ler_serial)
    socketio.run(app, host='0.0.0.0', port=5001)

