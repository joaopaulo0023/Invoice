import sqlite3
from datetime import date, timedelta

# --- Conexão com o banco de dados ---
conn = sqlite3.connect('escalas.db')
c = conn.cursor()

# --- Criação da tabela ---
c.execute('''
    CREATE TABLE IF NOT EXISTS escalas (
        data TEXT PRIMARY KEY,
        trem TEXT,
        separacao TEXT,
        guarda TEXT,
        carregamento TEXT,
        gate TEXT,
        toyota_psa_nissan TEXT,
        separacao_1 TEXT,
        faturamento TEXT,
        lider TEXT
    )
''')

# --- Alternância entre Cleber e Roberval ---
def generate_schedule(year):
    idx = 0
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)

    while start_date <= end_date:
        if start_date.weekday() < 5:  # Apenas dias úteis (segunda a sexta)
            # Alterna entre Cleber e Roberval
            gate_op = "Cleber" if idx % 2 == 0 else "Roberval"
            toyota_psa_nissan_op = "Roberval" if idx % 2 == 0 else "Cleber"
            idx += 1

            # Definir escala fixa com operadores definidos
            c.execute('''
                INSERT OR REPLACE INTO escalas (
                    data, trem, separacao, guarda, carregamento, gate, toyota_psa_nissan, separacao_1, faturamento, lider
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                start_date.isoformat(),     # Data
                "Anderson Silva",           # Trem (1º turno)
                "Rodrigo Lima",             # Separação (3º turno)
                "Rodrigo Lima",             # Guarda (3º turno)
                "Marcio Marcelino",         # Carregamento (3º turno)
                gate_op,                    # Gate (Alterna entre Cleber e Roberval)
                toyota_psa_nissan_op,       # Toyota, Psa e Nissan (Alterna entre Cleber e Roberval)
                "Rodrigo Lima",             # Separação_1 (3º turno)
                "Marcio Marcelino",         # Faturamento (3º turno)
                "João Paulo"                # Líder (2º turno)
            ))
        
        start_date += timedelta(days=1)  # Avança para o próximo dia

    conn.commit()

# --- Gera as escalas para o ano atual ---
year = date.today().year
generate_schedule(year)

print(f"✅ Escalas para o ano {year} geradas com sucesso!")

conn.close()
