import streamlit as st
import os
import pandas as pd
import PyPDF2
import re
from datetime import datetime
import tempfile

from models import (
    incluir_data,
    deletar_linha_por_id,
    atualizar_quantidade_por_id,
    salvar_dados_pdf,
    format_num
)

# Diretórios para PDF
PDF_SEARCH_DIR = r"sqlite:///C:/Users/andre.matos/OneDrive - Autoliv/Desktop/invoice2/meubanco1.db"
BASE_PDF_DIR = os.path.join(PDF_SEARCH_DIR, 'Pedidos')

# Inicializa estado
if 'linhas' not in st.session_state: st.session_state.linhas = []
if 'paletes_quebrados' not in st.session_state: st.session_state.paletes_quebrados = []
if 'id_counter' not in st.session_state: st.session_state.id_counter = 1
if 'missing_refs' not in st.session_state: st.session_state.missing_refs = []
for key, default in [('g_sold', ''), ('g_nome', ''), ('g_data', datetime.today()), ('g_num', '')]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- Funções auxiliares ---
@st.cache_data(show_spinner=False)
def extrair_dados_pdf(input_path: str):
    pdf_path = input_path if os.path.isfile(input_path) else os.path.join(BASE_PDF_DIR, f"{input_path}.pdf")
    if not os.path.exists(pdf_path):
        return {}, []

    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""

    data_match = re.search(r"Data do Pedido[:\s]*(\d{2}/\d{2}/\d{2})", text)
    data_str = data_match.group(1) if data_match else ""

    num_match = re.search(r"N[uú]mero do Pedido[:\s]*([0-9]+)", text)
    numero_pedido = num_match.group(1) if num_match else ""

    sold_match = re.search(r"Cliente[:\s]*([0-9]+)", text)
    sold_to = sold_match.group(1) if sold_match else ""

    nome_match = re.search(r"Cliente[:\s]*[0-9]+\s+(.+?)(?:\s{2,}|$)", text, flags=re.DOTALL)
    nome_cliente = nome_match.group(1).strip() if nome_match else ""

    header = {
        "data": data_str,
        "pedido": numero_pedido,
        "sold_to": sold_to,
        "nome_cliente": nome_cliente
    }

    item_re = re.compile(r"(\d{9}[A-Z]{3}).*?\(\s*(\d+)\s*\)", flags=re.DOTALL)
    items = [{"our": ref, "pick_qty": int(q)} for ref, q in item_re.findall(text)]

    return header, items

@st.cache_data(show_spinner=False)
def extrair_referencias_excel(file):
    try:
        df = pd.read_excel(file)
        col_map = {}
        for orig in df.columns:
            low = orig.strip().lower()
            if low in ['referencia', 'referência', '2º número do item', '2° número do item']:
                col_map[orig] = 'referencia'
            elif low == 'quantidade':
                col_map[orig] = 'quantidade'
        df = df.rename(columns=col_map)
        if 'referencia' not in df.columns or 'quantidade' not in df.columns:
            return []
        df = df.dropna(subset=['referencia', 'quantidade'])
        df['referencia'] = df['referencia'].astype(str).str.upper().str.strip()
        df['quantidade'] = df['quantidade'].astype(int)
        return df[['referencia', 'quantidade']].to_dict('records')
    except Exception as e:
        st.error(f"Erro ao ler Excel: {e}")
        return []

# Processa itens e registra referências não encontradas

def processar_items(lista):
    for item in lista:
        ref = item.get('referencia')
        qtd = item.get('quantidade', 0)
        try:
            result = incluir_data(ref, qtd)
        except Exception:
            if ref not in st.session_state.missing_refs:
                st.session_state.missing_refs.append(ref)
            st.warning(f"Referência '{ref}' não encontrada no banco de dados.")
            continue

        if result is None:
            if ref not in st.session_state.missing_refs:
                st.session_state.missing_refs.append(ref)
            st.warning(f"Referência '{ref}' não encontrada no banco de dados.")
            continue

        if isinstance(result, tuple):
            resp, paletes_quebrados = result
            if not resp and not paletes_quebrados:
                if ref not in st.session_state.missing_refs:
                    st.session_state.missing_refs.append(ref)
                st.warning(f"Referência '{ref}' não encontrada no banco de dados.")
                continue
            for r in resp:
                r['id'] = st.session_state.id_counter
                st.session_state.id_counter += 1
                st.session_state.linhas.append(r)
            for novo in paletes_quebrados:
                merged = False
                for group in st.session_state.paletes_quebrados:
                    if group.get('mix_group') and group['total_caixas'] + novo['qtd_caixas'] <= 30:
                        ni = novo.copy()
                        ni['peso_bruto'] = ni.get('peso_variavel', 0)
                        group['items'].append(ni)
                        group['total_caixas'] += ni['qtd_caixas']
                        merged = True
                        break
                if merged: continue
                for idx, ig in enumerate(st.session_state.paletes_quebrados):
                    if not ig.get('mix_group') and ig['qtd_caixas'] + novo['qtd_caixas'] <= 30:
                        st.session_state.paletes_quebrados[idx] = {
                            'mix_group': True,
                            'total_caixas': ig['qtd_caixas'] + novo['qtd_caixas'],
                            'items': [ig, {**novo, 'peso_bruto': novo.get('peso_variavel', 0)}]
                        }
                        merged = True
                        break
                if not merged:
                    novo['mix_group'] = False
                    novo['id'] = st.session_state.id_counter
                    st.session_state.id_counter += 1
                    st.session_state.paletes_quebrados.append(novo)
        else:
            if ref not in st.session_state.missing_refs:
                st.session_state.missing_refs.append(ref)
            st.warning(f"Referência '{ref}' retornou resultado inesperado do banco de dados.")

# Layout do Streamlit

tabs = st.tabs(["Importar", "Manual", "Paletes", "Resumo", "Gerar PDF"])

with tabs[0]:
    st.header("Importar de Excel ou PDF")
    # limpa referências faltantes
    if 'missing_refs' in st.session_state:
        st.session_state.missing_refs = []
    exc = st.file_uploader("Excel (.xlsx):", type=['xlsx'])
    pdf = st.file_uploader("PDF (.pdf):", type=['pdf'])
    if st.button("Importar", key='import'):
        itens = []
        if exc:
            try:
                df_full = pd.read_excel(exc)
                low_cols = [c.lower() for c in df_full.columns]
                if 'ref vend.' in low_cols:
                    st.session_state['g_sold'] = str(df_full.iloc[0, low_cols.index('ref vend.')])
                if 'nome da ref. vendas' in low_cols:
                    st.session_state['g_nome'] = str(df_full.iloc[0, low_cols.index('nome da ref. vendas')])
                if 'nº pedido' in low_cols:
                    st.session_state['g_num'] = str(int(df_full.iloc[0, low_cols.index('nº pedido')]))
            except:
                pass
            itens += extrair_referencias_excel(exc)
        if pdf:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmpf:
                tmpf.write(pdf.getbuffer())
                tmp_path = tmpf.name
            hdr, pit = extrair_dados_pdf(tmp_path)
            if hdr.get("sold_to"): st.session_state["g_sold"] = hdr["sold_to"]
            if hdr.get("nome_cliente"): st.session_state["g_nome"] = hdr["nome_cliente"]
            if hdr.get("pedido"): st.session_state["g_num"] = hdr["pedido"]
            itens += [{'referencia': i['our'], 'quantidade': i['pick_qty']} for i in pit]
        if itens:
            agregados = {}
            for it in itens:
                agregados[it['referencia']] = agregados.get(it['referencia'], 0) + it['quantidade']
            processar_items([{'referencia': k, 'quantidade': v} for k, v in agregados.items()])
            st.success("Importação concluída!")
        else:
            st.warning("Nenhuma referência encontrada.")

with tabs[1]:
    st.header("Inclusão Manual")
    # limpa faltantes antes de nova inserção manual
    st.session_state.missing_refs = []
    ref = st.text_input("Referência:", key='m_ref')
    qtd = st.number_input("Quantidade:", min_value=1, step=1, key='m_qtd')
    if st.button("Adicionar", key='add_manual'):
        if ref:
            processar_items([{'referencia': ref.upper().strip(), 'quantidade': qtd}])
            st.success("Item adicionado!")
        else:
            st.error("Informe uma referência.")

with tabs[2]:
    st.header("Visão de Paletes")
    del_id = st.number_input("ID da linha para deletar:", min_value=1, step=1, key='del_id')
    if st.button("Deletar linha", key='del_line'):
        deletar_linha_por_id(del_id)
        st.success(f"Linha {del_id} deletada.")
    if st.session_state.linhas:
        st.subheader("Paletes Completos")
        st.dataframe(pd.DataFrame(st.session_state.linhas))
    if st.session_state.paletes_quebrados:
        st.subheader("Paletes Quebrados / Mistos")
        for grp in st.session_state.paletes_quebrados:
            label = "Grupo" if grp.get('mix_group') else "Palete Quebrado"
            st.write(f"{label} — Total Caixas: {grp.get('total_caixas', grp.get('qtd_caixas',0))}")
            st.dataframe(pd.DataFrame(grp.get('items', [grp])))

with tabs[3]:
    st.header("Resumo")
    resumo = {}
    for l in st.session_state.linhas:
        ref, qtd = l.get('referencia') or l.get('our'), l.get('quantidade', l.get('qtd_caixas',0))
        resumo[ref] = resumo.get(ref,0) + qtd
    for grp in st.session_state.paletes_quebrados:
        for it in grp.get('items', []):
            ref, qtd = it.get('referencia') or it.get('our'), it.get('quantidade', it.get('qtd_caixas',0))
            resumo[ref] = resumo.get(ref,0) + qtd
    # Detalhamento por referência
    if resumo:
        df_res = pd.DataFrame([{'Referência': r, 'Quantidade': q} for r,q in resumo.items()])
        st.subheader("Detalhamento por Referência")
        st.dataframe(df_res)
    else:
        st.write("Nenhum item adicionado ainda.")
    # Métricas
    total_pecas = sum(resumo.values())
    total_paletes = len(st.session_state.linhas) + len(st.session_state.paletes_quebrados)
    peso_liq = sum(item.get('peso_liquido', item.get('peso_variavel',0)) for item in st.session_state.linhas)
    peso_liq += sum(it.get('peso_liquido', it.get('peso_variavel',0)) for grp in st.session_state.paletes_quebrados for it in grp.get('items',[]))
    peso_brt = sum(item.get('peso_bruto', item.get('peso_variavel',0)) for item in st.session_state.linhas)
    peso_brt += sum(it.get('peso_bruto', it.get('peso_variavel',0)) for grp in st.session_state.paletes_quebrados for it in grp.get('items',[]))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Peças", total_pecas)
    c2.metric("Total Paletes", total_paletes)
    c3.metric("Peso Líquido (kg)", format_num(peso_liq))
    c4.metric("Peso Bruto (kg)", format_num(peso_brt))
    # Exibe referências não encontradas
    if st.session_state.missing_refs:
        st.subheader("Referências não encontradas no BD")
        for ref in st.session_state.missing_refs:
            st.write(f"- {ref}")

with tabs[4]:
    st.header("Gerar PDF da Carga")
    sold_to = st.text_input("Sold To:", key='g_sold')
    nome_cliente = st.text_input("Nome do Cliente:", key='g_nome')
    data = st.date_input("Data:", key='g_data')
    numero_pedido = st.text_input("Número do Pedido:", key='g_num')
    if st.button("Gerar PDF", key='gen_pdf'):
        if sold_to and nome_cliente and numero_pedido:
            cab = {
                'soldTo': sold_to,
                'nomeCliente': nome_cliente,
                'data': str(data),
                'numeroPedido': numero_pedido
            }
            out = salvar_dados_pdf(cab, st.session_state.linhas, st.session_state.paletes_quebrados)
            if out.endswith('.pdf'):
                st.success(f"PDF salvo: {out}")
                with open(out, 'rb') as f:
                    st.download_button("Baixar PDF", f.read(), os.path.basename(out), 'application/pdf')
                st.session_state.linhas = []
                st.session_state.paletes_quebrados = []
                st.session_state.missing_refs = []
            else:
                st.error(out)

if __name__ == '__main__':
    pass
