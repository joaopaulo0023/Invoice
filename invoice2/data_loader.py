import streamlit as st 
import pandas as pd

@st.cache_data
def carregar_dados():
    tabela = pd.read_excel("Base.xlsx")
    return tabela


def carregar_dados1():
    tabela = pd.read_excel("logistica.xlsx", parse_dates=['data'])
    return tabela