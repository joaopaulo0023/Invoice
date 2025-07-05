import streamlit as st
import os
import re
import io
import sqlite3
import pandas as pd
import PyPDF2
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

# -------------------------------
# Configurações
# -------------------------------
BASE_PDF_DIR = r"S:\\ABRCommon\\Departamentos\\AMC Logistica\\03 - Operacoes\\06 - Expedição\\Liderança\\Pedidos"
SAVE_DIR     = r"S:\\ABRCommon\\Departamentos\\AMC Logistica\\03 - Operacoes\\06 - Expedição\\Liderança\\Pedidos_Novos"
DB_PATH      = os.path.join(BASE_PDF_DIR, "etiquetas.db")
os.makedirs(SAVE_DIR, exist_ok=True)

# -------------------------------
# Banco de Dados
# -------------------------------
@st.cache_resource
def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def criar_tabela():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS etiquetas (
            pedido TEXT,
            codigo_ref TEXT,
            idx INTEGER,
            etiqueta TEXT,
            PRIMARY KEY (pedido, codigo_ref, idx)
        )
    ''')
    conn.commit()

# -------------------------------
# Carregar/Salvar Etiquetas
# -------------------------------
def carregar_etiquetas_bd(order_number):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT codigo_ref, idx, etiqueta FROM etiquetas WHERE pedido = ?", (order_number,))
    res = cur.fetchall()
    etiquetas = {}
    for codigo_ref, idx, etiqueta in res:
        etiquetas.setdefault(codigo_ref, []).append((idx, etiqueta))
    return {k: [v for _, v in sorted(vs)] for k, vs in etiquetas.items()}

def salvar_etiquetas_bd(order_number, items):
    conn = get_db_connection()
    for disp, pdf_ref, tags in items:
        codigo_ref = pdf_ref.strip().upper()
        seen = set()
        unique_tags = []
        for tag in tags:
            # Limpa quaisquer prefixos ou caracteres indesejados
            # Extrai apenas o número da etiqueta e a quantidade entre parênteses
            m = re.search(r"([A-Za-z0-9]+)\s*\((\d+)\)", tag)
            if not m:
                continue
            etq_num, qtd = m.groups()
            core = etq_num.lstrip("0")
            if core not in seen:
                # Reconstrói no formato desejado: 'M22737022 (88)'
                clean_tag = f"{etq_num} ({qtd})"
                unique_tags.append(clean_tag)
                seen.add(core)
        # Insere/atualiza no banco
        for idx, etiqueta in enumerate(unique_tags):
            conn.execute(
                '''
                INSERT INTO etiquetas (pedido, codigo_ref, idx, etiqueta)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(pedido, codigo_ref, idx) DO UPDATE SET etiqueta = excluded.etiqueta
                ''', (order_number, codigo_ref, idx, etiqueta)
            )
    conn.commit()

# -------------------------------
# Extrair dados do PDF
# -------------------------------
@st.cache_data(show_spinner=False)
def extrair_dados_pdf(order_number):
    path = os.path.join(BASE_PDF_DIR, f"{order_number}.pdf")
    if not os.path.exists(path):
        return {}, []
    text = ""
    try:
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    except:
        return {}, []
    h = re.search(r"Lista de Separacão: (\d+)\s+Data do Pedido: (\d{2}/\d{2}/\d{2})\s+N\.\u00ba Pedido: (\d+)", text)
    if h:
        lista, data, pedido = h.groups()
    else:
        lista, data, pedido = "", "", order_number
    header = {"lista": lista, "data": data, "pedido": pedido}

    pattern = re.compile(r"(\d{9}[A-Z]{3}).*?(\d{11}).*?\(\s*(\d+)\s*\)", re.DOTALL)
    items = []
    for m in pattern.finditer(text):
        prod_code = m.group(1).strip()
        pdf_ref   = m.group(2).strip()
        qty       = m.group(3).strip()
        disp      = f"{prod_code} ({qty})"
        items.append((disp, pdf_ref))
    return header, items

# -------------------------------
# Agrupar paletes
# -------------------------------
def agrupar_paletes(items_raw: list) -> list:
    linhas = []
    seq = 1
    for disp, pdf_ref, tags in items_raw:
        codigo_curto = disp.split("(")[0].strip().upper()
        m_qtd = re.search(r"\((\d+)[\.,]?\d*\)", disp)
        qtd_original = m_qtd.group(1) if m_qtd else ""
        if "QUEBRADO" in codigo_curto:
            for tag in tags:
                m_tag   = re.match(r"(.+?)\s*\(\s*(\d+)\s*\)", tag)
                etiqueta= m_tag.group(1).strip() if m_tag else tag.strip()
                qtd_sep = m_tag.group(2).strip() if m_tag else ""
                linhas.append([str(seq), codigo_curto, qtd_original, etiqueta, qtd_sep, "", "", "", ""])
                seq += 1
        else:
            etiquetas_numeros = []
            qtds_numeros      = []
            for tag in tags:
                m_tag = re.match(r"(.+?)\s*\(\s*(\d+)\s*\)", tag)
                etiquetas_numeros.append(m_tag.group(1).strip() if m_tag else tag.strip())
                qtds_numeros.append(m_tag.group(2).strip() if m_tag else "")
            etiquetas_consol = "\n".join(etiquetas_numeros)
            qtds_consol      = "\n".join(qtds_numeros)
            linhas.append([str(seq), codigo_curto, qtd_original,
                           etiquetas_consol, qtds_consol, "", "", "", ""])
            seq += 1
    return linhas

# -------------------------------
# Verificar mesma ref
# -------------------------------
def mesma_ref(pdf_ref_j: str, ref_qr: str) -> bool:
    pdf_digits = re.sub(r"\D", "", pdf_ref_j)
    ref_digits = re.sub(r"\D", "", ref_qr)
    core_pdf   = pdf_digits.strip("0")
    core_qr    = ref_digits.strip("0")
    if not core_pdf and not core_qr:
        return True
    return core_pdf == core_qr

# -------------------------------
# Geração de PDF com Platypus
# -------------------------------
def gerar_pdf(order_number: str, header: dict, itens_para_tabela: list, dims: list) -> io.BytesIO:
    buf = io.BytesIO()
    page_size = landscape(A4)
    width, height = page_size

    left_margin = right_margin = 5 * mm
    top_margin = 70 * mm
    bottom_margin = 60 * mm

    styles = getSampleStyleSheet()

    def header_footer(canvas, doc):
        canvas.setFont("Helvetica-Bold", 16)
        canvas.drawString(left_margin, height - 15*mm, "Autoliv do Brasil Ltda.")
        canvas.setFont("Helvetica", 10)
        canvas.drawString(left_margin, height - 27*mm, "Av. Roberto Bertoletti, 551 - Taubaté - SP")
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(left_margin, height - 39*mm, "Pick Slip por Pallet")
        canvas.setFont("Helvetica", 10)
        canvas.drawRightString(width - right_margin, height - 15*mm, f"Página: {doc.page}")
        canvas.setFont("Helvetica", 9)
        canvas.drawString(
            left_margin, height - 51*mm,
            f"Lista: {header.get('lista','')}   Data: {header.get('data','')}   Pedido: {header.get('pedido','')}"
        )
        base = 40 * mm
        canvas.setStrokeColor(colors.grey)
        canvas.setLineWidth(0.5)
        canvas.line(left_margin, base + 15*mm, width - right_margin, base + 15*mm)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(left_margin, base + 13*mm, f"Total de Itens: {len(itens_para_tabela)}   Paletes: {len(dims)}")
        if dims:
            lengths = [d["length"] for d in dims]
            widths_ = [d["width"] for d in dims]
            heights = [d["height"] for d in dims]
            canvas.drawString(
                left_margin, base + 11*mm,
                f"Comprimento (mm): {min(lengths)}-{max(lengths)}   "
                f"Largura (mm): {min(widths_)}-{max(widths_)}   "
                f"Altura (mm): {min(heights)}-{max(heights)}"
            )
        canvas.drawString(left_margin, base + 5*mm, "Assinaturas:")
        fields = ["Nome/Reg Separador","Assinatura","Data","Nome/Reg Faturista","Assinatura","Data"]
        cols = [left_margin, width/2 - 20*mm, width - right_margin - 10*mm]
        for i, fld in enumerate(fields):
            x = cols[i % 3]
            y = base + (10*mm if i < 3 else 5*mm)
            canvas.drawString(x, y, fld)

    header_row = [
        "Seq","Código","Qtde Original","Etiqueta","Qtd Separada",
        "Pallet Wood","Pallet Plastic","Wit Cover","No Cover","Metalic Rack"
    ]

    data = [header_row]
    for row in itens_para_tabela:
        # Usa a quantidade pega correta (vinda do QR Code ou banco)
        linha = row[:5] + ["" for _ in range(5)]
        data.append(linha)

    col_widths = [10*mm,30*mm,25*mm,40*mm,25*mm,25*mm,25*mm,25*mm,25*mm,30*mm]

    tbl = Table(data, colWidths=col_widths, repeatRows=1, splitByRow=1)
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BOX", (4,1), (9,-1), 0.5, colors.black),
        ("ALIGN", (4,1), (9,-1), "CENTER"),
        ("LEFTPADDING", (4,1), (9,-1), 2),
        ("RIGHTPADDING", (4,1), (9,-1), 2),
        ("WORDWRAP", (0,0), (-1,-1), True),
    ]))

    doc = BaseDocTemplate(buf, pagesize=landscape(A4),
                          leftMargin=left_margin, rightMargin=right_margin,
                          topMargin=top_margin, bottomMargin=bottom_margin)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    tpl = PageTemplate(id="tpl", frames=[frame], onPage=header_footer)
    doc.addPageTemplates([tpl])

    story = [Spacer(1, 5*mm), tbl]
    doc.build(story)

    buf.seek(0)
    return buf

# ----------------------
# Início do App Streamlit
# ----------------------
st.title("Pick Slip por Pallet – Gestão de Etiquetas")

criar_tabela()

# Entrada de pedidos
orders_input = st.text_area(
    "Digite números de pedido, separados por vírgula:",
    help="Exemplo: 5904805, 5904806"
)
orders = [o.strip() for o in orders_input.split(",") if o.strip()]

if "orders_data" not in st.session_state:
    st.session_state["orders_data"] = {}

# Recarrega dados quando a lista de pedidos muda
if orders and set(orders) != set(st.session_state["orders_data"].keys()):
    st.session_state["orders_data"].clear()
    for ord_num in orders:
        h, lista_items = extrair_dados_pdf(ord_num)
        tags_por_ref = carregar_etiquetas_bd(ord_num)
        items_list = []
        for disp, pdf_ref in lista_items:
            pdf_ref_clean = pdf_ref.strip().upper()
            lista_tags = tags_por_ref.get(pdf_ref_clean, [])
            items_list.append((disp, pdf_ref_clean, lista_tags))
        st.session_state["orders_data"][ord_num] = {"header": h, "items_raw": items_list}

if not orders:
    st.info("Digite ao menos um pedido para começar.")
    st.stop()

# ----------------------
# Sidebar: seleção de pedido + expander com referências
# ----------------------
selected_order = st.sidebar.selectbox("Selecione o pedido", orders)
od = st.session_state["orders_data"][selected_order]
hdr = od.get("header", {})
items_raw = od.get("items_raw", [])

if not hdr:
    st.sidebar.warning(f"❌ Pedido {selected_order} não encontrado no diretório de PDFs.")
    st.stop()

# Normaliza items_raw
normalized = []
for item in items_raw:
    if len(item) == 3:
        normalized.append(item)
    else:
        disp_i, pdf_ref_i = item
        normalized.append((disp_i, pdf_ref_i, []))
st.session_state["orders_data"][selected_order]["items_raw"] = normalized
items_raw = normalized

# Inicializa estado para índice selecionado
if "selected_idx" not in st.session_state:
    st.session_state["selected_idx"] = None

# Expander "Referências" na sidebar
with st.sidebar.expander("Referências", expanded=True):
    for idx_item, (disp, pdf_ref, tags) in enumerate(items_raw):
        btn_key = f"select_{selected_order}_{idx_item}"
        if st.button(f"{idx_item+1}. {disp}", key=btn_key):
            st.session_state["selected_idx"] = idx_item

# ----------------------
# Função de comparação de referências (ignora zeros extras)
# ----------------------
def mesma_ref(pdf_ref_j: str, ref_qr: str) -> bool:
    pdf_digits = re.sub(r"\D", "", pdf_ref_j)
    ref_digits = re.sub(r"\D", "", ref_qr)
    core_pdf = pdf_digits.strip("0")
    core_qr  = ref_digits.strip("0")
    if not core_pdf and not core_qr:
        return True
    return core_pdf == core_qr

# Inicializa estado para QR pendente
if "pending_pick" not in st.session_state:
    st.session_state["pending_pick"] = None

# ----------------------
# Área principal: cabeçalho do pedido
# ----------------------
st.subheader(f"Pedido: {selected_order}")
st.markdown(f"**Lista:** {hdr.get('lista','')}   **Data:** {hdr.get('data','')}   **Pedido:** {hdr.get('pedido','')}")

# ----------------------
# Campo de QR Code sem botão, com on_change
# ----------------------
st.markdown("---")
st.markdown("### 📷 Escaneie / Cole a string do QR code abaixo")

qr_key = f"qr_{selected_order}"
if qr_key not in st.session_state:
    st.session_state[qr_key] = ""
if "qr_feedback" not in st.session_state:
    st.session_state["qr_feedback"] = ""

def processar_qr():
    qr_string = st.session_state[qr_key].strip()
    if not qr_string:
        return
    items = st.session_state["orders_data"][selected_order]["items_raw"]
    feedback = ""

    # 1) QR antigo: M<etiqueta> Q<quant> ZABR;<ref_prod>;
    m = re.search(r"M(\d+).*?Q(\d+).*?ZABR;([^;]+);", qr_string, re.IGNORECASE | re.DOTALL)
    if m:
        etiqueta_qr = m.group(1).strip()
        qtd_qr      = m.group(2).strip()
        ref_prod    = m.group(3).strip().upper()
        idx_item = None
        for j, (disp_j, pdf_ref_j, tags_j) in enumerate(items):
            if mesma_ref(pdf_ref_j, ref_prod):
                idx_item = j
                break
        if idx_item is None:
            feedback = f"⛔ Referência `{ref_prod}` não existe no PDF."
        else:
            disp_sel, pdf_ref_sel, tags_sel = items[idx_item]
            etiqueta_digits = re.sub(r"\D", "", etiqueta_qr).strip("0")
            existe = any(
                re.sub(r"\D", "", et.split()[0]).strip("0") == etiqueta_digits
                for et in tags_sel
            )
            if existe:
                feedback = f"⚠️ Etiqueta `{etiqueta_qr}` já cadastrada."
            else:
                tags_sel.append(f"{etiqueta_qr} ({qtd_qr})")
                items[idx_item] = (disp_sel, pdf_ref_sel, tags_sel)
                feedback = f"✅ Etiqueta `{etiqueta_qr}` (Qtd: {qtd_qr}) adicionada."
    else:
        # 2) QR novo sem etiqueta
        if qr_string.startswith("BRTA50;"):
            m_ref = re.match(r"BRTA50;(\d{11})", qr_string)
            if m_ref:
                ref_qr = m_ref.group(1).strip()
                m_qty = re.search(r"0+(\d{1,3})E", qr_string)
                if m_qty:
                    qtd_qr = m_qty.group(1).lstrip("0") or "0"
                else:
                    grupos3 = re.findall(r"(\d{3})", qr_string)
                    candidatos = [int(x) for x in grupos3] if grupos3 else []
                    qtd_qr = str(max(candidatos)) if candidatos else None
                idx_item = None
                for j, (disp_j, pdf_ref_j, tags_j) in enumerate(items):
                    if mesma_ref(pdf_ref_j, ref_qr):
                        idx_item = j
                        break
                if idx_item is None:
                    feedback = f"⛔ Referência `{ref_qr}` não existe no PDF."
                else:
                    st.session_state["pending_pick"] = {"idx": idx_item, "qtd": qtd_qr}
                    feedback = f"ℹ️ `{ref_qr}` (Qtd: {qtd_qr}) pendente. Confirme abaixo."
            else:
                feedback = "⛔ QR não reconhecido."
        else:
            m2 = re.search(r";(\d{11})(.*)", qr_string)
            if m2:
                ref_qr   = m2.group(1).strip().upper()
                data_str = m2.group(2)
                grupos3  = re.findall(r"(\d{3})", data_str)
                candidatos = [int(x) for x in grupos3] if grupos3 else []
                qtd_qr = str(max(candidatos)) if candidatos else None
                idx_item = None
                for j, (disp_j, pdf_ref_j, tags_j) in enumerate(items):
                    if mesma_ref(pdf_ref_j, ref_qr):
                        idx_item = j
                        break
                if idx_item is None:
                    feedback = f"⛔ Referência `{ref_qr}` não existe no PDF."
                else:
                    st.session_state["pending_pick"] = {"idx": idx_item, "qtd": qtd_qr}
                    feedback = f"ℹ️ `{ref_qr}` (Qtd: {qtd_qr}) pendente. Confirme abaixo."
            else:
                feedback = "⛔ QR não reconhecido."
    st.session_state["qr_feedback"] = feedback
    st.session_state[qr_key] = ""

st.text_input(
    "Cole aqui toda a linha que o leitor OCR/QR retorna:",
    key=qr_key,
    on_change=processar_qr
)

if st.session_state["qr_feedback"]:
    st.write(st.session_state["qr_feedback"])
    st.session_state["qr_feedback"] = ""

# ----------------------
# Se houver pending_pick: mostra apenas esse item na área principal
# ----------------------
pend = st.session_state.get("pending_pick")
if pend is not None:
    idx_item = pend["idx"]
    qtd_detected = pend["qtd"]
    disp_sel, pdf_ref_sel, tags_sel = items_raw[idx_item]

    st.markdown("---")
    st.markdown(f"### Confirme `{disp_sel}` (Ref: {pdf_ref_sel})")
    st.markdown(f"**Quantidade detectada:** {qtd_detected}")

    # Preenchimento e confirmação de quantidade e etiqueta
    qtd_confirm_key = f"qtd_confirm_{idx_item}"
    etq_manual_key = f"etq_manual_{idx_item}"

    if qtd_confirm_key not in st.session_state:
        st.session_state[qtd_confirm_key] = str(qtd_detected)
    if etq_manual_key not in st.session_state:
        st.session_state[etq_manual_key] = ""

    qtd_confirm = st.text_input(
        "Quantidade (ajuste se necessário):",
        value=st.session_state[qtd_confirm_key],
        key=qtd_confirm_key
    )
    etq_manual = st.text_input(
        "Número da Etiqueta:",
        value=st.session_state[etq_manual_key],
        key=etq_manual_key
    )

    if st.button("Confirmar Pick", key=f"confirm_{idx_item}"):
        if not etq_manual.strip():
            st.warning("Informe uma etiqueta antes de confirmar.")
        elif not qtd_confirm.strip().isdigit():
            st.warning("Quantidade deve ser numérica.")
        else:
            etiqueta_digits = re.sub(r"\D", "", etq_manual.strip()).strip("0")
            existentes = [re.sub(r"\D", "", et.split()[0]).strip("0") for et in tags_sel]
            if etiqueta_digits in existentes:
                st.warning(f"Etiqueta `{etq_manual}` já cadastrada.")
            else:
                tags_sel.append(f"{etq_manual.strip()} ({qtd_confirm.strip()})")
                items_raw[idx_item] = (disp_sel, pdf_ref_sel, tags_sel)
                # Limpa o estado desses campos e pendência
                if qtd_confirm_key in st.session_state:
                    del st.session_state[qtd_confirm_key]
                if etq_manual_key in st.session_state:
                    del st.session_state[etq_manual_key]
                st.rerun()

# ----------------------
# Se houver referência selecionada via sidebar, exibe detalhes na área principal
# ----------------------
sel_idx = st.session_state.get("selected_idx")
if sel_idx is not None:
    disp, pdf_ref, tags = items_raw[sel_idx]
    st.markdown("---")
    st.markdown(f"## Detalhes de `{disp}`")
    m_qtd_display = re.search(r"\((\d+[\.,]?\d*)\)", disp)
    qtd_display = m_qtd_display.group(1) if m_qtd_display else ""
    st.markdown(
        f"**Referência (PDF):** {pdf_ref}   —   "
        f"**Qtde original:** {qtd_display}   —   **Tags atuais:** {len(tags)}"
    )

    # Botão para adicionar nova etiqueta manualmente
    if st.button("➕ Adicionar Etiqueta/Quantidade", key=f"btn_add_sel_{sel_idx}"):
        tags.append("")

    # Exibe, para o item selecionado, os campos de edição de tag
    updated = []
    for idx_tag, tag in enumerate(tags):
        c1, c2 = st.columns([8, 1])
        with c1:
            novo_val = st.text_input(
                f"Etiqueta #{idx_tag+1}",
                value=tag,
                key=f"{sel_idx}_{idx_tag}"
            )
        with c2:
            if st.button("🗑️", key=f"del_{sel_idx}_{idx_tag}"):
                continue
        updated.append(novo_val)
    items_raw[sel_idx] = (disp, pdf_ref, updated.copy())

    # Aviso para etiquetas duplicadas
    dups = {e for e in updated if updated.count(e) > 1 and e.strip()}
    if dups:
        st.warning(f"⚠️ Etiquetas duplicadas em `{disp}`: {', '.join(dups)}")

# ----------------------
# Botões de ação na área principal: Salvar / Gerar PDF
# ----------------------
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    if st.button("💾 Salvar todas etiquetas"):
        to_save = []
        for disp_i, pdf_ref_i, ts in items_raw:
            ts_limpas = [t for t in ts if t.strip()]
            to_save.append((disp_i, pdf_ref_i, ts_limpas))
        salvar_etiquetas_bd(selected_order, to_save)
        st.success("Etiquetas salvas no banco!")

with c2:
    if st.button("📄 Gerar e salvar PDF deste pedido"):
        to_save = []
        for disp_i, pdf_ref_i, ts in items_raw:
            ts_limpas = [t for t in ts if t.strip()]
            to_save.append((disp_i, pdf_ref_i, ts_limpas))
        salvar_etiquetas_bd(selected_order, to_save)
        tabelinha = agrupar_paletes(items_raw)
        buf = gerar_pdf(selected_order, hdr, tabelinha, [])
        path_out = os.path.join(SAVE_DIR, f"{selected_order}.pdf")
        try:
            with open(path_out, "wb") as f:
                f.write(buf.read())
            st.success(f"PDF salvo em: {path_out}")
        except Exception as e:
            st.error(f"Erro ao salvar PDF: {e}")
