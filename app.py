import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Check-in da Aula", layout="centered")

# =========================
# Config
# =========================
DATA_DIR = "data"
RESP_PATH = os.path.join(DATA_DIR, "checkin_respostas.csv")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

FEELINGS = [
    ("😀 Animado(a)", "Alta energia / motivação"),
    ("🙂 Bem", "Ok para acompanhar"),
    ("😐 Neutro(a)", "Nem bem nem mal"),
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
        return pd.DataFrame(columns=["timestamp", "feeling", "detail", "comment", "turma"])
    df = pd.read_csv(RESP_PATH)
    # garantias
    for c in ["timestamp", "feeling", "detail", "comment", "turma"]:
        if c not in df.columns:
            df[c] = ""
    return df

def append_row(row: dict):
    df_row = pd.DataFrame([row])
    if not os.path.exists(RESP_PATH):
        df_row.to_csv(RESP_PATH, index=False, encoding="utf-8-sig")
    else:
        df_row.to_csv(RESP_PATH, mode="a", header=False, index=False, encoding="utf-8-sig")

def require_admin():
    """Login simples via sessão + secrets."""
    if "ADMIN_USER" not in st.secrets or "ADMIN_PASS" not in st.secrets:
        st.error("Admin não configurado. Defina ADMIN_USER e ADMIN_PASS em st.secrets.")
        st.stop()

    if st.session_state.get("admin_ok"):
        return True

    with st.form("admin_login", border=True):
        st.subheader("🔒 Acesso do Admin")
        u = st.text_input("Usuário", value="", autocomplete="username")
        p = st.text_input("Senha", value="", type="password", autocomplete="current-password")
        ok = st.form_submit_button("Entrar")

    if ok:
        if u == st.secrets["ADMIN_USER"] and p == st.secrets["ADMIN_PASS"]:
            st.session_state["admin_ok"] = True
            st.success("Acesso autorizado.")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")
    return False

# =========================
# UI
# =========================
st.title("📍 Check-in da Aula")
st.write("Responda rapidinho para o professor ajustar a aula de hoje.")

tab_aluno, tab_admin = st.tabs(["👩‍🎓 Check-in (Aluno)", "📊 Painel (Admin)"])

# -------------------------
# Aluno
# -------------------------
with tab_aluno:
    with st.form("checkin_form", border=True):
        st.subheader("Como você está se sentindo hoje?")
        turma = st.text_input("Turma (opcional)", placeholder="Ex.: 1º semestre A / Noite")

        labels = [x[0] for x in FEELINGS]
        chosen = st.radio("Escolha 1 opção:", labels, horizontal=False)

        # pega detalhe
        detail = dict(FEELINGS).get(chosen, "")

        comment = st.text_area(
            "Comentário (opcional):",
            placeholder="Ex.: 'Tive dificuldade com Scanner' ou 'preciso de mais exemplos de variáveis'.",
            max_chars=200,
        )

        sent = st.form_submit_button("✅ Enviar check-in")

    if sent:
        append_row({
            "timestamp": now_iso(),
            "feeling": chosen,
            "detail": detail,
            "comment": (comment or "").strip(),
            "turma": (turma or "").strip(),
        })
        st.success("Obrigado! Check-in registrado. ✅")

# -------------------------
# Admin
# -------------------------
with tab_admin:
    if require_admin():
        df = load_df()

        st.subheader("Visão geral")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Respostas", len(df))
        with col2:
            st.metric("Turmas (distintas)", df["turma"].replace("", pd.NA).dropna().nunique())
        with col3:
            if len(df) > 0:
                st.metric("Última resposta", str(df["timestamp"].iloc[-1]))
            else:
                st.metric("Última resposta", "-")

        if len(df) == 0:
            st.info("Ainda não há respostas.")
        else:
            # ---- filtro por turma
            turmas = ["(Todas)"] + sorted(df["turma"].replace("", "(Sem turma)").unique().tolist())
            turma_sel = st.selectbox("Filtrar por turma:", turmas)

            dff = df.copy()
            dff["turma"] = dff["turma"].replace("", "(Sem turma)")
            if turma_sel != "(Todas)":
                dff = dff[dff["turma"] == turma_sel]

            # ---- gráficos
            st.markdown("### 📊 Distribuição de sentimentos")
            order = [x[0] for x in FEELINGS]
            counts = dff["feeling"].value_counts().reindex(order).fillna(0).astype(int)

            st.bar_chart(counts)

            st.markdown("### 🕒 Evolução (por ordem de envio)")
            # índice temporal simples (ordem)
            timeline = dff[["timestamp", "feeling"]].copy()
            timeline["n"] = range(1, len(timeline) + 1)

            # mapeia sentimentos para uma escala (só para visualizar tendência)
            scale_map = {
                "😀 Animado(a)": 3,
                "🙂 Bem": 2,
                "😐 Neutro(a)": 1,
                "😕 Confuso(a)": 0,
                "😣 Ansioso(a)": -1,
                "😴 Cansado(a)": -2,
            }
            timeline["score"] = timeline["feeling"].map(scale_map).fillna(0).astype(int)
            timeline = timeline.set_index("n")

            st.line_chart(timeline["score"])

            st.markdown("### 💬 Comentários (para ajustes rápidos)")
            comments = dff[dff["comment"].astype(str).str.strip() != ""][["timestamp", "feeling", "comment", "turma"]]
            if len(comments) == 0:
                st.caption("Sem comentários ainda.")
            else:
                st.dataframe(comments.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)

            st.divider()

            # ---- ações admin
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
                    confirm = st.checkbox("Confirmo que desejo apagar tudo.")
                    if st.button("Apagar agora", type="primary", disabled=not confirm, use_container_width=True):
                        if os.path.exists(RESP_PATH):
                            os.remove(RESP_PATH)
                        st.success("Respostas apagadas.")
                        st.rerun()

        st.divider()
        if st.button("Sair do admin"):
            st.session_state["admin_ok"] = False
            st.rerun()
