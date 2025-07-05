import streamlit as st
import pandas as pd
import streamlit_authenticator as stauth
from models import session, Usuario

st.set_page_config(
    page_title="SHIPMENT FOLLOW UP - TIME EXPEDIÇÃO",
    layout="wide"
)

# Carrega credenciais do banco
lista_usuario = session.query(Usuario).all()
credentials = {
    "usernames": {
        u.email: {"name": u.nome, "password": u.senha}
        for u in lista_usuario
    }
}

authenticator = stauth.Authenticate(
    credentials,
    "credenciais_hashco",
    "fsyfus%$67fs76AH7",
    cookie_expiry_days=30,
)

# 1) RENDERIZA o formulário de login na página principal
authenticator.login(location="main")

# 2) LÊ status de autenticação no session_state
auth_status = st.session_state.get("authentication_status")

if auth_status:
    # Usuário autenticado com sucesso
    user_name = st.session_state["name"]
    user_email = st.session_state["username"]

    # Carrega objeto Usuario do banco
    usuario = session.query(Usuario).filter_by(email=user_email).first()

    # Define navegação com base em admin
    menu = {
        "Home": [st.Page("homepage.py", title="Logística")],
        "Invoice": [
            st.Page("invoices.py", title="Invoices"),
            st.Page("cor_db.py", title="Alterar_bd"),
            st.Page("shipment-follow-up.py", title="Shipment Follow‑Up"),
        ],
	"Conta": [               
                st.Page("criar_conta.py", title="Criar Conta"),
            ],

    }
    pg = st.navigation(menu)
    pg.run()

elif auth_status is False:
    st.error("Combinação de usuário e senha inválidas")
else:
    st.warning("Por favor, preencha usuário e senha para entrar")
