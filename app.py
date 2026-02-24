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

LEVELS = [
    ("🛸 Recruta", "Primeiro contato — tudo novo"),
    ("👽 Explorador", "Curioso(a), mas ainda confuso(a)"),
    ("🧑‍🚀 Navegador", "Estou acompanhando com pequenos ajustes"),
    ("🔨 Construtor", "Consigo praticar e resolver exercícios"),
    ("🚀 Comandante", "Estou voando alto hoje"),
]

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
# ETs + clima
# =========================
ET_FELIZ = r"""
<pre style="text-align:center; font-size:16px; margin:0;">
    👽✨
    /|\
    / \
</pre>
"""
ET_PREOCUPADO = r"""
<pre style="text-align:center; font-size:16px; margin:0;">
    👽💭
    /|\
    / \
</pre>
"""
ET_CANSADO = r"""
<pre style="text-align:center; font-size:16px; margin:0;">
    👽😴
    /|\
    / \
</pre>
"""
ET_NEUTRO = r"""
<pre style="text-align:center; font-size:16px; margin:0;">
    👽
    /|\
    / \
</pre>
"""

def climate_summary(df: pd.DataFrame):
    """
    Retorna (clima, et_visual, mensagem, tipo_alerta)
    tipo_alerta ∈ {"success","info","warning","error"}
    """
    if df is None or len(df) == 0:
        return (
            "sem_dados",
            ET_NEUTRO,
            "Ainda não há check-ins. Assim que chegarem respostas, o termômetro da turma aparece aqui 👽",
            "info",
        )

    counts = df["feeling"].value_counts()

    positivos = counts.get("🚀 Empolgado(a)", 0) + counts.get("🙂 Tranquilo(a)", 0)
    neutros = counts.get("😐 Neutro(a)", 0)
    confusos = (
        counts.get("👽 ET Explorador", 0)
        + counts.get("😕 Confuso(a)", 0)
        + counts.get("😣 Ansioso(a)", 0)
    )
    cansados = counts.get("😴 Cansado(a)", 0)

    total = int(positivos + neutros + confusos + cansados)
    if total == 0:
        return ("sem_dados", ET_NEUTRO, "Ainda não há check-ins válidos 👽", "info")

    p_pos = positivos / total
    p_neu = neutros / total
    p_con = confusos / total
    p_can = cansados / total

    if p_pos >= 0.50:
        return (
            "positivo",
            ET_FELIZ,
            "🚀 Clima bom! A turma está pronta para avançar. Sugestão: manter o ritmo e propor um mini-desafio final.",
            "success",
        )

    # crítico: confusão alta + ansiedade relevante
    if p_con >= 0.45 and counts.get("😣 Ansioso(a)", 0) >= max(1, int(total * 0.15)):
        return (
            "critico",
            ET_PREOCUPADO,
            "🛑 Clima de alerta: há bastante confusão/ansiedade. Sugestão: desacelerar, fazer 1 exemplo ao vivo passo a passo e checar entendimento.",
            "error",
        )

    if p_con >= 0.45:
        return (
            "confuso",
            ET_PREOCUPADO,
            "👽 Muitos ETs exploradores hoje. Sugestão: reforçar o modelo mental (Entrada → Processamento → Saída) e resolver 1 exercício guiado antes da lista.",
            "warning",
        )

    if p_can >= 0.35:
        return (
            "cansado",
            ET_CANSADO,
            "😴 Turma com baixa energia. Sugestão: atividade curta em duplas, com metas pequenas e feedback rápido.",
            "warning",
        )

    if p_neu >= 0.40:
        return (
            "neutro",
            ET_NEUTRO,
            "😐 Clima neutro. Sugestão: aquecer com um exercício simples (2–3 min) e depois seguir com prática guiada.",
            "info",
        )

    return (
        "misto",
        ET_NEUTRO,
        "👽 Clima misto. Sugestão: começar com exemplo curto e abrir 2 minutos para dúvidas antes do próximo exercício.",
        "info",
    )

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

    clima, et_visual, msg, kind = climate_summary(df)
    st.markdown(et_visual, unsafe_allow_html=True)
    if kind == "success":
        st.success(msg)
    elif kind == "warning":
        st.warning(msg)
    elif kind == "error":
        st.error(msg)
    else:
        st.info(msg)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Respostas", len(df))
    with col2:
        # normaliza turma aqui também
        turma_norm = df["turma"].fillna("").astype(str).str.strip().replace("", pd.NA)
        st.metric("Turmas (distintas)", turma_norm.dropna().nunique())
    with col3:
        st.metric("Última resposta", str(df["timestamp"].iloc[-1]) if len(df) else "-")

    if len(df) == 0:
        st.info("Ainda não há respostas.")
        return

    dff = df.copy()

    # ✅ CORREÇÃO DO TypeError: garante string e remove NaN antes de ordenar
    dff["turma"] = (
        dff["turma"]
        .fillna("")
        .astype(str)
        .str.strip()
        .replace("", "(Sem turma)")
    )

    turmas = ["(Todas)"] + sorted(dff["turma"].unique().tolist())
    turma_sel = st.selectbox("Filtrar por turma:", turmas, key="turma_filter")
    if turma_sel != "(Todas)":
        dff = dff[dff["turma"] == turma_sel]

    st.markdown("### 🧑‍🚀 Nível da tripulação (autoavaliação)")
    level_order = [x[0] for x in LEVELS]
    level_counts = dff["level"].value_counts().reindex(level_order).fillna(0).astype(int)
    st.bar_chart(level_counts)

    st.markdown("### 📊 Como a turma está se sentindo")
    feeling_order = [x[0] for x in FEELINGS]
    feeling_counts = dff["feeling"].value_counts().reindex(feeling_order).fillna(0).astype(int)
    st.bar_chart(feeling_counts)

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
# Mini ET (lado aluno)
# =========================
ET_MINI = r'''
<pre style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas;
            line-height: 1.1; margin: 0; font-size: 16px; text-align: center;">
      👽
     /|\
     / \
</pre>
'''

# =========================
# UI
# =========================
st.markdown("## 👽 Missão Java — Check-in da Tripulação")
st.caption("Um check-in rápido para o professor ajustar a aula em tempo real.")

admin_ok = require_admin_sidebar()

# ======= MODO ADMIN =======
if admin_ok:
    df = load_df()
    admin_panel(df)

    st.divider()
    if st.button("Sair do admin"):
        st.session_state["admin_ok"] = False
        st.rerun()

# ======= MODO ALUNO (sem st.form para descrições atualizarem em tempo real) =======
else:
    cA, cB = st.columns([2, 1], vertical_alignment="center")
    with cA:
        st.write("### Status da tripulação")
        st.write("Marque seu **nível** e como você está se sentindo hoje. Isso ajuda a deixar a aula mais assertiva.")
    with cB:
        st.markdown(ET_MINI, unsafe_allow_html=True)

    st.subheader("1) Qual seu nível hoje?")
    level_labels = [x[0] for x in LEVELS]
    level_chosen = st.radio("Escolha 1 nível:", level_labels, horizontal=False, key="level_choice")
    level_detail = dict(LEVELS).get(level_chosen, "")
    st.caption(f"📌 {level_detail}")

    st.subheader("2) Como você está se sentindo?")
    turma = st.text_input("Turma (opcional)", placeholder="Ex.: 1º semestre", key="turma_txt")

    feeling_labels = [x[0] for x in FEELINGS]
    feeling_chosen = st.radio("Escolha 1 opção:", feeling_labels, horizontal=False, key="feeling_choice")
    feeling_detail = dict(FEELINGS).get(feeling_chosen, "")
    st.caption(f"💬 {feeling_detail}")

    comment = st.text_area(
        "Comentário (opcional):",
        placeholder="Ex.: 'me perdi na declaração de variáveis' ou 'quero mais exemplos de variáveis'.",
        max_chars=200,
        key="comment_txt",
    )

    sent = st.button("✅ Enviar check-in", type="primary", use_container_width=True)

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
        st.success("Check-in registrado! 🚀 Obrigado por ajudar!")

    st.caption("99% dos problemas em programação são culpa do ponto e vírgula. O outro 1% é falta dele. 👽")
