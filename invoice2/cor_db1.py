import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import shutil
import os

# --- Título da interface ---
st.title("Editar Banco de Dados SQLite com Backup em Dois Locais")

# Parâmetros para o banco de dados principal (rede)
sqlite_db_url = (
    "sqlite:///C:/Users/andre.matos/OneDrive - Autoliv/Desktop/invoice2/database/meubanco1.db"
)
# Caminho físico do arquivo .db principal (sem o prefixo sqlite:///)
db_file = sqlite_db_url.replace("sqlite:///", "")

# Caminho de backup local no OneDrive
one_drive_db_file = (
    r"C:/Users/andre.matos/OneDrive - Autoliv/Desktop/invoice2/database/meubanco1.db"
)

nome_tabela = "dados"

# --- Exibir e Editar Dados Existentes ---
st.subheader("Editar Dados no Banco de Dados Principal e Sincronizar Backup")

try:
    engine = create_engine(sqlite_db_url)
    df_bd = pd.read_sql(f"SELECT * FROM {nome_tabela}", engine)

    if df_bd.empty:
        st.info("Nenhum dado encontrado na tabela.")
    else:
        # Editor dinâmico
        edited_df = st.data_editor(df_bd, num_rows="dynamic")

        if st.button("Salvar Alterações"):
            try:
                # 1) Salva no banco principal (rede)
                edited_df.to_sql(nome_tabela, engine, if_exists="replace", index=False)

                # 2) Atualiza o arquivo .db na pasta de backup do OneDrive
                #    (sobrescreve a cópia existente)
                shutil.copy(db_file, one_drive_db_file)

                st.success(
                    "✔ Banco principal atualizado com sucesso!\n"
                    f"✔ Backup sincronizado em: `{one_drive_db_file}`"
                )
            except Exception as e:
                st.error(f"Erro ao salvar ou sincronizar backup: {e}")
except Exception as e:
    st.error(f"Erro ao carregar dados do banco de dados: {e}")
