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


# ===== INICIA O SERVIDOR =====
if __name__ == '__main__':
    socketio.start_background_task(ler_serial)
    socketio.run(app, host='0.0.0.0', port=5001)
    
