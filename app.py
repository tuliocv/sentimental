import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Missão Java — Check-in", layout="centered")

# =========================
# Config
# =========================
DATA_DIR = "data"
RESP_PATH = os.path.join(DATA_DIR, "checkin_respostas.csv")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Sistema de níveis (tema)
LEVELS = [
    ("🛸 Recruta", "Primeiro contato — tudo novo"),
    ("👽 Explorador", "Curioso(a), mas ainda confuso(a)"),
    ("🧑‍🚀 Navegador", "Estou acompanhando com pequenos ajustes"),
    ("🤖 Construtor", "Consigo praticar e resolver exercícios"),
    ("🚀 Comandante", "Estou voando alto hoje"),
]

# Sentimentos (inclui ET Explorador)
FEELINGS = [
    ("🚀 Empolgado(a)", "Alta energia / motivação"),
    ("🙂 Tranquilo(a)", "Ok para acompanhar"),
    ("😐 Neutro(a)", "Nem bem nem mal"),
    ("👽 ET Explorador", "Curioso(a), mas preciso de mais exemplos e explicação passo a passo"),
    ("😕 Confuso(a)", "Preciso de mais exemplos"),
    ("😣 Ansioso(a)", "Estou travado(a) / preocupado(a)"),
    ("😴 Cansado(a)", "Baixa energia hoje"),
]

# =========================
# Helpers
# =========================
def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def load_df() -> pd.DataFrame:
    if not os.path.exists(RESP_PATH):
        return pd.DataFrame(columns=["timestamp", "level", "level_detail", "feeling", "detail", "comment", "turma"])
    df = pd.read_csv(RESP_PATH)
    for c in ["timestamp", "level", "level_detail", "feeling", "detail", "comment", "turma"]:
        if c not in df.columns:
            df[c] = ""
    return df

def append_row(row: dict):
    df_row = pd.DataFrame([row])
    if not os.path.exists(RESP_PATH):
        df_row.to_csv(RESP_PATH, index=False, encoding="utf-8-sig")
    else:
        df_row.to_csv(RESP_PATH, mode="a", header=False, index=False, encoding="utf-8-sig")

def require_admin_sidebar() -> bool:
    """Login simples do admin na SIDEBAR (senha via st.secrets)."""
    if "ADMIN_USER" not in st.secrets or "ADMIN_PASS" not in st.secrets:
        st.sidebar.error("Admin não configurado (ADMIN_USER/ADMIN_PASS em st.secrets).")
        return False

    if st.session_state.get("admin_ok"):
        return True

    st.sidebar.markdown("### 🔒 Painel do Admin")
    with st.sidebar.form("admin_login_sidebar", border=True):
        u = st.text_input("Usuário", value="", key="admin_user", autocomplete="username")
        p = st.text_input("Senha", value="", key="admin_pass", type="password", autocomplete="current-password")
        ok = st.form_submit_button("Entrar")

    if ok:
        if u == st.secrets["ADMIN_USER"] and p == st.secrets["ADMIN_PASS"]:
            st.session_state["admin_ok"] = True
            st.sidebar.success("Acesso autorizado.")
            time.sleep(0.3)
            st.rerun()
        else:
            st.sidebar.error("Usuário ou senha inválidos.")
    return False

def admin_panel(df: pd.DataFrame):
    st.subheader("📊 Painel do Admin — Missão Java")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Respostas", len(df))
    with col2:
        st.metric("Turmas (distintas)", df["turma"].replace("", pd.NA).dropna().nunique())
    with col3:
        st.metric("Última resposta", str(df["timestamp"].iloc[-1]) if len(df) else "-")

    if len(df) == 0:
        st.info("Ainda não há respostas.")
        return

    dff = df.copy()
    dff["turma"] = dff["turma"].replace("", "(Sem turma)")

    turmas = ["(Todas)"] + sorted(dff["turma"].unique().tolist())
    turma_sel = st.selectbox("Filtrar por turma:", turmas, key="turma_filter")
    if turma_sel != "(Todas)":
        dff = dff[dff["turma"] == turma_sel]

    # Gráfico de níveis
    st.markdown("### 🧑‍🚀 Nível da tripulação (autoavaliação)")
    level_order = [x[0] for x in LEVELS]
    level_counts = dff["level"].value_counts().reindex(level_order).fillna(0).astype(int)
    st.bar_chart(level_counts)

    # Gráfico de sentimentos
    st.markdown("### 📊 Como a turma está se sentindo")
    feeling_order = [x[0] for x in FEELINGS]
    feeling_counts = dff["feeling"].value_counts().reindex(feeling_order).fillna(0).astype(int)
    st.bar_chart(feeling_counts)

    # Evolução (score combinado simples)
    st.markdown("### 🕒 Tendência (por ordem de envio)")
    timeline = dff[["timestamp", "level", "feeling"]].copy()
    timeline["n"] = range(1, len(timeline) + 1)

    level_score = {
        "🛸 Recruta": 0,
        "👽 Explorador": 1,
        "🧑‍🚀 Navegador": 2,
        "🔨 Construtor": 3,
        "🚀 Comandante": 4,
    }
    feeling_score = {
        "🚀 Empolgado(a)": 3,
        "🙂 Tranquilo(a)": 2,
        "😐 Neutro(a)": 1,
        "👽 ET Explorador": 0,
        "😕 Confuso(a)": 0,
        "😣 Ansioso(a)": -1,
        "😴 Cansado(a)": -2,
    }

    timeline["score"] = (
        timeline["level"].map(level_score).fillna(0).astype(int)
        + timeline["feeling"].map(feeling_score).fillna(0).astype(int)
    )
    timeline = timeline.set_index("n")
    st.line_chart(timeline["score"])

    # Comentários
    st.markdown("### 💬 Sinais do espaço (comentários)")
    comments = dff[dff["comment"].astype(str).str.strip() != ""][["timestamp", "level", "feeling", "comment", "turma"]]
    if len(comments) == 0:
        st.caption("Sem comentários ainda.")
    else:
        st.dataframe(
            comments.sort_values("timestamp", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    c1, c2 = st.columns([1, 1])
    with c1:
        st.download_button(
            "⬇️ Baixar respostas (CSV)",
            data=dff.to_csv(index=False).encode("utf-8-sig"),
            file_name="checkin_respostas.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with c2:
        with st.popover("🧹 Limpar respostas (admin)"):
            st.warning("Isso apaga TODAS as respostas salvas neste app.")
            confirm = st.checkbox("Confirmo que desejo apagar tudo.", key="confirm_clear")
            if st.button("Apagar agora", type="primary", disabled=not confirm, use_container_width=True):
                if os.path.exists(RESP_PATH):
                    os.remove(RESP_PATH)
                st.success("Respostas apagadas.")
                st.rerun()

# =========================
# Mini visual do ET (sem imagem externa)
# =========================
ET_MINI = r'''
'''

# =========================
# UI
# =========================
st.markdown("## 👽 Missão Java — Check-in da Tripulação")
st.caption("Um check-in rápido para o professor ajustar a aula em tempo real.")

# Admin na lateral esquerda
admin_ok = require_admin_sidebar()

# ======= MODO ADMIN: NÃO MOSTRA FORM DO ALUNO =======
if admin_ok:
    df = load_df()
    admin_panel(df)

    st.divider()
    if st.button("Sair do admin"):
        st.session_state["admin_ok"] = False
        st.rerun()

# ======= MODO ALUNO: SÓ MOSTRA O CHECK-IN =======
else:
    # Cabeçalho temático
    cA, cB = st.columns([2, 1], vertical_alignment="center")
    with cA:
        st.write("### Status da tripulação (30 segundos)")
        st.write("Marque seu **nível** e como você está se sentindo hoje. Isso ajuda a deixar a aula mais assertiva.")
    with cB:
        st.markdown(ET_MINI, unsafe_allow_html=True)

    with st.form("checkin_form", border=True):
        st.subheader("1) Qual seu nível hoje?")
        level_labels = [x[0] for x in LEVELS]
        level_chosen = st.radio("Escolha 1 nível:", level_labels, horizontal=False)
        level_detail = dict(LEVELS).get(level_chosen, "")

        st.subheader("2) Como você está se sentindo?")
        turma = st.text_input("Turma (opcional)", placeholder="Ex.: 1º semestre A / Noite")

        feeling_labels = [x[0] for x in FEELINGS]
        feeling_chosen = st.radio("Escolha 1 opção:", feeling_labels, horizontal=False)
        feeling_detail = dict(FEELINGS).get(feeling_chosen, "")

        comment = st.text_area(
            "Comentário (opcional):",
            placeholder="Ex.: 'me perdi no Scanner' ou 'quero mais exemplos de variáveis'.",
            max_chars=200,
        )

        sent = st.form_submit_button("✅ Enviar check-in")

    if sent:
        append_row(
            {
                "timestamp": now_iso(),
                "level": level_chosen,
                "level_detail": level_detail,
                "feeling": feeling_chosen,
                "detail": feeling_detail,
                "comment": (comment or "").strip(),
                "turma": (turma or "").strip(),
            }
        )
        st.success("Check-in registrado! 🚀 Obrigado por ajudar a ajustar a aula.")

    st.caption("Não é bug, é funcionalidade não documentada. 👽")
