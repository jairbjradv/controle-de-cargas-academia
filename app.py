import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
from supabase import create_client

st.set_page_config(page_title="DataGym Pro", layout="centered")
st.title("🏋️‍♂️ Meu Diário de Cargas")

URL_TREINOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRoxuS5Rs5YY_kxRqMceEMSpiXmqsxsTyNjBW4avhGnttHpS7vuWvXVjsz1LwCAhA/pub?gid=649998402&single=true&output=csv"

DIAS = ["SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA"]


def extrair_kg(valor):
    m = re.search(r'[\d,.]+', str(valor))
    return float(m.group().replace(',', '.')) if m else None


@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


def carregar_historico():
    resp = get_supabase().table("historico_cargas").select("*").order("data").execute()
    if resp.data:
        return pd.DataFrame(resp.data)
    return pd.DataFrame(columns=["id", "data", "treino", "exercicio", "carga", "observacao"])


@st.cache_data(ttl=120)
def carregar_todos_treinos(url):
    try:
        df = pd.read_csv(url, header=None, dtype=str)
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")
        return {}

    treinos = {}
    dia_atual = None
    pular_cabecalho = False

    for _, row in df.iterrows():
        val = str(row.iloc[0]).strip()
        dia_encontrado = next((d for d in DIAS if d in val), None)
        if dia_encontrado:
            dia_atual = dia_encontrado
            treinos[dia_atual] = []
            pular_cabecalho = True
            continue
        if pular_cabecalho:
            pular_cabecalho = False
            continue
        if val in ("", "nan", "None"):
            continue
        if dia_atual and len(row) >= 3:
            exercicio = str(row.iloc[1]).strip()
            series    = str(row.iloc[2]).strip()
            if exercicio not in ("", "nan"):
                treinos[dia_atual].append({"Exercicio": exercicio, "Series": series})

    return treinos


# ── Carrega dados ────────────────────────────────────────────────────────────
treinos      = carregar_todos_treinos(URL_TREINOS)
df_historico = carregar_historico()

# ── Seleção do dia ───────────────────────────────────────────────────────────
dia_selecionado = st.selectbox(
    "Selecione o Treino do Dia:",
    ["Selecione..."] + list(treinos.keys())
)

if dia_selecionado != "Selecione...":
    exercicios = treinos.get(dia_selecionado, [])

    if not exercicios:
        st.warning("Nenhum exercício encontrado para este dia.")
    else:
        hoje_str = datetime.today().strftime("%Y-%m-%d")
        total    = len(exercicios)

        feitos_hoje = [
            n.strip() for n in df_historico[
                (df_historico["treino"] == dia_selecionado) &
                (df_historico["data"]   == hoje_str)
            ]["exercicio"].unique().tolist()
        ] if not df_historico.empty else []

        st.success(f"{'✅' if len(feitos_hoje) == total else '🏋️'} {len(feitos_hoje)}/{total} exercícios registrados hoje")

        # ── Expander por exercício ───────────────────────────────────────────
        for i, ex in enumerate(exercicios):
            item     = ex["Exercicio"].strip()
            alvo     = ex["Series"]
            ja_feito = item in feitos_hoje
            titulo   = f"✅ FEITO — {item}" if ja_feito else f"🏋️ {item}"

            with st.expander(f"{titulo}  |  *{alvo}*", expanded=False):

                hist = df_historico[
                    (df_historico["exercicio"] == item) &
                    (df_historico["treino"]    == dia_selecionado)
                ].tail(3) if not df_historico.empty else pd.DataFrame()

                if not hist.empty:
                    for _, h in hist.iloc[::-1].iterrows():
                        data_fmt = pd.to_datetime(h["data"]).strftime("%d/%m")
                        obs_txt  = f" — *{h['observacao']}*" if pd.notna(h["observacao"]) and str(h["observacao"]).strip() else ""
                        st.warning(f"📅 {data_fmt}  →  **{h['carga']}**{obs_txt}")
                else:
                    st.caption("ℹ️ Nenhum peso registrado anteriormente.")

                c1, c2 = st.columns(2)
                with c1:
                    carga = st.text_input("Carga Atual",   key=f"carga_{i}", placeholder="Ex: 40kg")
                with c2:
                    obs   = st.text_input("Nota / Séries", key=f"obs_{i}",   placeholder="Ex: RPE 9")

                if st.button("💾 Salvar", key=f"salvar_{i}"):
                    if not carga.strip():
                        st.warning("Digite a carga antes de salvar.")
                    else:
                        novo_kg = extrair_kg(carga)
                        valores = df_historico[df_historico["exercicio"] == item]["carga"].apply(extrair_kg).dropna() \
                                  if not df_historico.empty else pd.Series(dtype=float)
                        eh_pr   = novo_kg is not None and (valores.empty or novo_kg > valores.max())

                        get_supabase().table("historico_cargas").insert({
                            "data":       hoje_str,
                            "treino":     dia_selecionado,
                            "exercicio":  item,
                            "carga":      carga.strip(),
                            "observacao": obs.strip() or None,
                        }).execute()

                        if eh_pr:
                            st.toast(f"🏆 PR em {item}!", icon="🏆")
                        st.rerun()

# ── Apagar registro ──────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🗑️ Apagar registro incorreto"):
    df_del = carregar_historico()

    if df_del.empty:
        st.info("Nenhum registro salvo ainda.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            dia_del = st.selectbox("Dia", DIAS, key="dia_del")
        with col2:
            exs_del = sorted(df_del[df_del["treino"] == dia_del]["exercicio"].unique().tolist())
            ex_del  = st.selectbox("Exercício", exs_del, key="ex_del") if exs_del else None

        if ex_del:
            registros = df_del[
                (df_del["treino"]    == dia_del) &
                (df_del["exercicio"] == ex_del)
            ].copy()
            registros["Label"] = registros.apply(
                lambda r: f"{pd.to_datetime(r['data']).strftime('%d/%m/%Y')}  →  {r['carga']}"
                          + (f"  ({r['observacao']})" if pd.notna(r["observacao"]) and str(r["observacao"]).strip() else ""),
                axis=1
            )
            escolhido = st.selectbox("Registro a apagar", registros["Label"].tolist(), key="reg_del")
            id_del    = int(registros[registros["Label"] == escolhido].iloc[0]["id"])

            if st.button("🗑️ Apagar este registro", key="btn_apagar"):
                st.session_state["confirmar_apagar"] = id_del

            if st.session_state.get("confirmar_apagar") is not None:
                st.warning(f"⚠️ Confirma a exclusão de **{escolhido}**?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Sim, apagar", key="btn_sim"):
                        get_supabase().table("historico_cargas").delete().eq("id", st.session_state["confirmar_apagar"]).execute()
                        st.session_state["confirmar_apagar"] = None
                        st.success("Registro apagado.")
                        st.rerun()
                with c2:
                    if st.button("❌ Cancelar", key="btn_nao"):
                        st.session_state["confirmar_apagar"] = None
                        st.rerun()

# ── Gráfico de evolução ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown("## 📈 Evolução de Carga — Últimos 30 dias")

if df_historico.empty:
    st.info("Nenhum dado registrado ainda. Salve seu primeiro treino para ver os gráficos.")
else:
    col1, col2 = st.columns(2)
    with col1:
        dia_grafico = st.selectbox("Dia de treino", DIAS, key="dia_grafico")
    with col2:
        exs_disp = sorted(df_historico[df_historico["treino"] == dia_grafico]["exercicio"].unique().tolist())
        ex_grafico = st.selectbox("Exercício", exs_disp, key="ex_grafico") if exs_disp else None

    if not exs_disp:
        st.info(f"Nenhum registro salvo para {dia_grafico} ainda.")
    elif ex_grafico:
        corte   = datetime.today() - timedelta(days=30)
        df_plot = df_historico[
            (df_historico["treino"]    == dia_grafico) &
            (df_historico["exercicio"] == ex_grafico)
        ].copy()
        df_plot["data"] = pd.to_datetime(df_plot["data"])
        df_plot = df_plot[df_plot["data"] >= corte].copy()
        df_plot["Kg"]   = df_plot["carga"].apply(extrair_kg)
        df_plot = df_plot.dropna(subset=["Kg"]).sort_values("data")

        if df_plot.empty:
            st.info("Sem valores numéricos para plotar.")
        else:
            df_plot["Data_str"] = df_plot["data"].dt.strftime("%d/%m")
            maximo = df_plot["Kg"].max()
            st.metric(
                label=f"🏆 PR — {ex_grafico}",
                value=f"{maximo:.1f} kg",
                delta=f"{df_plot['Kg'].iloc[-1] - df_plot['Kg'].iloc[-2]:.1f} kg vs anterior" if len(df_plot) >= 2 else None
            )
            st.line_chart(df_plot.set_index("Data_str")["Kg"], use_container_width=True)
