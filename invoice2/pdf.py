import pandas as pd
from sqlalchemy import create_engine

# --- Configurações ---
# Caminho do arquivo Excel (substitua pelo caminho do seu arquivo)
excel_file = 'Preparacao_Cargas_Pallet_Completo.xlsx'
# Nome da planilha que contém os dados (pode ser o nome ou o índice da planilha)
sheet_name = 'Sheet1'  # ou, por exemplo, 0 se for a primeira planilha

# Nome do banco de dados a ser criado (no caso, um arquivo SQLite)
sqlite_db = 'meubanco.db'
# Nome da tabela onde os dados serão inseridos
nome_tabela = 'dados'

# --- Leitura dos Dados do Excel ---
try:
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    print("Arquivo Excel lido com sucesso!")
except Exception as e:
    print(f"Erro ao ler o arquivo Excel: {e}")
    exit(1)

# --- Conexão com o Banco de Dados SQL ---
try:
    # Cria a engine para o SQLite. Para outros bancos, ajuste a string de conexão.
    engine = create_engine(f'sqlite:///{sqlite_db}')
    print(f"Conexão com o banco de dados '{sqlite_db}' estabelecida com sucesso!")
except Exception as e:
    print(f"Erro ao conectar ao banco de dados: {e}")
    exit(1)

# --- Inserção dos Dados no Banco de Dados ---
try:
    # Se a tabela já existir, o parâmetro if_exists='replace' substitui a tabela.
    # Você pode usar 'append' para adicionar os dados à tabela existente.
    df.to_sql(nome_tabela, engine, if_exists='replace', index=False)
    print(f"Dados exportados com sucesso para a tabela '{nome_tabela}' no banco de dados '{sqlite_db}'!")
except Exception as e:
    print(f"Erro ao exportar os dados para o banco de dados: {e}")




