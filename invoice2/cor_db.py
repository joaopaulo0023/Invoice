import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import shutil
import os
from datetime import datetime

st.title("Editar Banco de Dados SQLite com Backup em Dois Locais")

# Banco principal na rede
sqlite_db_url = "sqlite:///C:/Users/andre.matos/OneDrive - Autoliv/Desktop/invoice2/meubanco1.db"
db_file = sqlite_db_url.replace("sqlite:///", "")

# Backup 1: OneDrive
backup1 = r"C:/Users/andre.matos/OneDrive - Autoliv/Desktop/invoice2\meubanco1.db"

# Backup 2: Pasta local “Backups” com timestamp
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_folder2 = r"C:\Backups"
os.makedirs(backup_folder2, exist_ok=True)
backup2 = os.path.join(backup_folder2, f"meubanco1_{ts}.db")

tabela = "dados"

st.subheader("Editar Dados no Banco e Sincronizar Backups")

try:
    engine = create_engine(sqlite_db_url)
    df = pd.read_sql(f"SELECT * FROM {tabela}", engine)

    if df.empty:
        st.info("Nenhum dado encontrado.")
    else:
        edit_df = st.data_editor(df, num_rows="dynamic")

        if st.button("Salvar Alterações"):
            try:
                # 1) Atualiza banco
                edit_df.to_sql(tabela, engine, if_exists="replace", index=False)

                # 2) Para cada backup, copia se for arquivo diferente
                for dest in (backup1, backup2):
                    src = os.path.abspath(db_file)
                    dst = os.path.abspath(dest)
                    if src != dst:
                        shutil.copy(src, dst)
                        st.write(f"✔ Backup sincronizado em: `{dest}`")
                    else:
                        st.write(f"ℹ️ Ignorado (origem == destino): `{dest}`")

                st.success("Todos os processos concluídos com sucesso!")
            except Exception as e:
                st.error(f"Erro ao salvar ou sincronizar backups: {e}")
except Exception as e:
    st.error(f"Erro ao carregar dados do banco: {e}")
