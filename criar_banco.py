import sqlite3

def criar_banco():
    conn = sqlite3.connect("quiz.db")
    c = conn.cursor()

    

    # Tabela de alunos
    c.execute('''CREATE TABLE IF NOT EXISTS alunos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        ano TEXT NOT NULL
    )''')

    # Tabela de resultados (agora guarda cada questão)
    c.execute('''CREATE TABLE IF NOT EXISTS resultados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        aluno_id INTEGER NOT NULL,
        categoria TEXT NOT NULL,
        acertou INTEGER NOT NULL,
        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(aluno_id) REFERENCES alunos(id)
    )''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    criar_banco()
