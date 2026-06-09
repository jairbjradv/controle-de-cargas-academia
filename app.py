import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone
import re
from supabase import create_client

st.set_page_config(page_title="DataGym Pro", layout="centered", page_icon="🏋️")

st.markdown("""
<style>
/* ── Fundo geral ── */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0d1117 0%, #0f1923 50%, #0d1117 100%);
    min-height: 100vh;
}
[data-testid="stHeader"] { background: transparent; }

/* ── Título ── */
h1 { color: #39ff14 !important; letter-spacing: 1px; }
h2 { color: #c8ffc8 !important; }

/* ── Abas ── */
[data-testid="stTabs"] button p { color: #8aff8a; font-weight: 600; }
[data-testid="stTabs"] button[aria-selected="true"] p { color: #39ff14 !important; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background-color: #39ff14 !important; }

/* ── Selectbox ── */
[data-testid="stSelectbox"] label { color: #8aff8a !important; font-weight: 600; }
[data-testid="stSelectbox"] > div > div {
    background-color: #1a2332 !important;
    border: 1px solid #39ff1455 !important;
    border-radius: 10px !important;
    color: #e0ffe0 !important;
}
[data-testid="stMultiSelect"] label { color: #8aff8a !important; font-weight: 600; }
[data-testid="stMultiSelect"] > div > div {
    background-color: #1a2332 !important;
    border: 1px solid #39ff1455 !important;
    border-radius: 10px !important;
}

/* ── Expanders (cards de exercício) ── */
[data-testid="stExpander"] {
    background-color: #141e2b !important;
    border: 1px solid #2a3f2a !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
}
[data-testid="stExpander"]:hover {
    border-color: #39ff1477 !important;
    box-shadow: 0 0 12px #39ff1422;
}
[data-testid="stExpander"] summary {
    color: #d4ffd4 !important;
    font-weight: 600;
    font-size: 0.97rem;
}

/* ── Inputs ── */
[data-testid="stTextInput"] label { color: #8aff8a !important; font-size: 0.85rem; }
[data-testid="stTextInput"] input {
    background-color: #1a2332 !important;
    border: 1px solid #2a4a2a !important;
    border-radius: 8px !important;
    color: #e8ffe8 !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #39ff14 !important;
    box-shadow: 0 0 6px #39ff1444 !important;
}

/* ── Botões ── */
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
    background: linear-gradient(135deg, #1a4a1a, #2d7a2d) !important;
    color: #39ff14 !important;
    border: 1px solid #39ff1466 !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    transition: all 0.2s ease;
}
[data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover {
    background: linear-gradient(135deg, #2d7a2d, #3a9a3a) !important;
    box-shadow: 0 0 14px #39ff1455 !important;
    transform: translateY(-1px);
}
[data-testid="stLinkButton"] a {
    background: linear-gradient(135deg, #1a4a1a, #2d7a2d) !important;
    color: #39ff14 !important;
    border: 1px solid #39ff1466 !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}

/* ── Barra de progresso ── */
[data-testid="stProgress"] > div > div > div > div {
    background: linear-gradient(90deg, #2d7a2d, #39ff14) !important;
}

/* ── Mensagens ── */
[data-testid="stAlert"] {
    background-color: #111c11 !important;
    border-left-color: #39ff14 !important;
    border-radius: 8px !important;
    color: #c8ffc8 !important;
}

/* ── Métrica (PR) ── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #0d1f0d, #142814) !important;
    border: 1px solid #39ff1444 !important;
    border-radius: 12px !important;
    padding: 12px !important;
}
[data-testid="stMetricLabel"] { color: #8aff8a !important; }
[data-testid="stMetricValue"] { color: #39ff14 !important; }

/* ── Divisor ── */
hr { border-color: #1e3a1e !important; }

/* ── Caption / info ── */
[data-testid="stCaptionContainer"] { color: #556655 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏋️‍♂️ Meu Diário de Cargas")

URL_TREINOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRoxuS5Rs5YY_kxRqMceEMSpiXmqsxsTyNjBW4avhGnttHpS7vuWvXVjsz1LwCAhA/pub?gid=649998402&single=true&output=csv"

DIAS = ["SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA"]

# Fix #2 — timezone BRT em vez de servidor UTC
BRT = timezone(timedelta(hours=-3))

# Cores para comparar exercícios no gráfico (até 10)
CORES_GRAFICO = [
    "#39ff14",  # verde neon
    "#00e5ff",  # ciano
    "#ffb000",  # âmbar
    "#ff4d6d",  # rosa
    "#b366ff",  # roxo
    "#ff8c42",  # laranja
    "#14ffc8",  # turquesa
    "#ffe45e",  # amarelo
    "#4d9fff",  # azul
    "#ff66d9",  # magenta
]


def hoje_brt():
    return datetime.now(BRT).strftime("%Y-%m-%d")


# Fix #7 — extrair_kg com try/except para typos como "40.5.0"
def extrair_kg(valor):
    m = re.search(r'[\d,.]+', str(valor))
    if not m:
        return None
    try:
        return float(m.group().replace(',', '.'))
    except ValueError:
        return None


# Extrai "3x12" da observação para calcular volume (séries × reps × kg)
def extrair_series_reps(obs):
    m = re.search(r'(\d+)\s*[xX×]\s*(\d+)', str(obs or ""))
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["supabase"]["url"],
        st.secrets["supabase"]["key"],
    )


# Fix #3 — cache de 30s para não bater no Supabase a cada clique
@st.cache_data(ttl=30)
def carregar_historico():
    resp = get_supabase().table("historico_cargas").select("*").order("data").execute()
    if resp.data:
        df = pd.DataFrame(resp.data)
        # Fix #6 — normaliza data para "YYYY-MM-DD" independente do formato retornado
        df["data"] = df["data"].astype(str).str[:10]
        return df
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
            descanso  = str(row.iloc[3]).strip() if len(row) >= 4 else ""
            video     = str(row.iloc[4]).strip() if len(row) >= 5 else ""
            if not video.lower().startswith("http"):
                video = ""
            if exercicio not in ("", "nan"):
                treinos[dia_atual].append({"Exercicio": exercicio, "Series": series, "Descanso": descanso, "Video": video})

    return treinos


def calcular_volume(df):
    """Volume total = séries × reps × kg dos registros com nota tipo '3x12'."""
    total = 0.0
    for _, r in df.iterrows():
        kg = extrair_kg(r["carga"])
        sr = extrair_series_reps(r.get("observacao"))
        if kg is not None and sr is not None:
            total += sr[0] * sr[1] * kg
    return total


# ── Carrega dados — Fix #4: uma única chamada ao Supabase por render ─────────
treinos      = carregar_todos_treinos(URL_TREINOS)
df_historico = carregar_historico()

tab_treino, tab_evolucao, tab_gerenciar = st.tabs(["🏋️ Treino", "📈 Evolução", "⚙️ Gerenciar"])

# ══════════════════════════════════ ABA TREINO ═══════════════════════════════
with tab_treino:
    _DIA_SEMANA = {0: "SEGUNDA-FEIRA", 1: "TERÇA-FEIRA", 2: "QUARTA-FEIRA", 3: "QUINTA-FEIRA", 4: "SEXTA-FEIRA", 5: "SÁBADO", 6: "DOMINGO"}
    _opcoes     = ["Selecione..."] + list(treinos.keys())
    _dia_hoje   = _DIA_SEMANA.get(datetime.now(BRT).weekday())
    _idx        = _opcoes.index(_dia_hoje) if _dia_hoje in _opcoes else 0

    dia_selecionado = st.selectbox(
        "Selecione o Treino do Dia:",
        _opcoes,
        index=_idx
    )

    if dia_selecionado != "Selecione...":
        exercicios = treinos.get(dia_selecionado, [])

        if not exercicios:
            st.warning("Nenhum exercício encontrado para este dia.")
        else:
            hoje_str = hoje_brt()
            total    = len(exercicios)

            feitos_hoje = [
                n.strip() for n in df_historico[
                    (df_historico["treino"] == dia_selecionado) &
                    (df_historico["data"]   == hoje_str)
                ]["exercicio"].unique().tolist()
            ] if not df_historico.empty else []

            icone = "✅" if len(feitos_hoje) == total else "🏋️"
            st.progress(len(feitos_hoje) / total, text=f"{icone} {len(feitos_hoje)}/{total} exercícios registrados hoje")

            # ── Expander por exercício ───────────────────────────────────────
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
                        obs   = st.text_input("Nota / Séries", key=f"obs_{i}",   placeholder="Ex: 3x12 RPE9")

                    ultima = hist.iloc[-1] if not hist.empty else None
                    video  = ex.get("Video", "")

                    b1, b2, b3 = st.columns([2, 2, 1])
                    with b1:
                        salvar_clicado = st.button("💾 Salvar", key=f"salvar_{i}")
                    with b2:
                        repetir_clicado = ultima is not None and st.button(
                            f"↻ Repetir {ultima['carga']}", key=f"rep_{i}"
                        )
                    with b3:
                        if video:
                            st.link_button("🎥", video)

                    # Repetir última carga com 1 toque (copia carga + nota da última sessão)
                    if repetir_clicado:
                        obs_ant = str(ultima["observacao"]).strip() \
                                  if pd.notna(ultima["observacao"]) and str(ultima["observacao"]).strip() else None
                        try:
                            get_supabase().table("historico_cargas").insert({
                                "data":       hoje_str,
                                "treino":     dia_selecionado,
                                "exercicio":  item,
                                "carga":      str(ultima["carga"]).strip(),
                                "observacao": obs_ant,
                            }).execute()
                            carregar_historico.clear()
                            st.toast(f"↻ {ultima['carga']} repetido em {item}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar — tente novamente. ({e})")

                    if salvar_clicado:
                        if not carga.strip():
                            st.warning("Digite a carga antes de salvar.")
                        else:
                            novo_kg = extrair_kg(carga)
                            valores = df_historico[df_historico["exercicio"] == item]["carga"].apply(extrair_kg).dropna() \
                                      if not df_historico.empty else pd.Series(dtype=float)
                            eh_pr   = novo_kg is not None and (valores.empty or novo_kg > valores.max())

                            # Fix #1 — try/except no insert
                            try:
                                get_supabase().table("historico_cargas").insert({
                                    "data":       hoje_str,
                                    "treino":     dia_selecionado,
                                    "exercicio":  item,
                                    "carga":      carga.strip(),
                                    "observacao": obs.strip() or None,
                                }).execute()
                                carregar_historico.clear()
                                if eh_pr:
                                    st.toast(f"🏆 PR em {item}!", icon="🏆")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao salvar — tente novamente. ({e})")

# ═════════════════════════════════ ABA EVOLUÇÃO ══════════════════════════════
with tab_evolucao:
    if df_historico.empty:
        st.info("Nenhum dado registrado ainda. Salve seu primeiro treino para ver os gráficos.")
    else:
        # ── Resumo semanal ───────────────────────────────────────────────────
        hoje_dt    = datetime.now(BRT).date()
        inicio_sem = hoje_dt - timedelta(days=hoje_dt.weekday())   # segunda desta semana
        inicio_ant = inicio_sem - timedelta(days=7)

        df_res = df_historico.copy()
        df_res["dt"] = pd.to_datetime(df_res["data"]).dt.date
        df_res["kg"] = df_res["carga"].apply(extrair_kg)

        df_sem = df_res[df_res["dt"] >= inicio_sem]
        df_ant = df_res[(df_res["dt"] >= inicio_ant) & (df_res["dt"] < inicio_sem)]

        # PRs da semana: exercício cujo máximo desta semana superou o histórico anterior
        prs_semana = 0
        for ex_nome, grupo in df_sem.groupby("exercicio"):
            max_sem   = grupo["kg"].max()
            max_antes = df_res[(df_res["exercicio"] == ex_nome) & (df_res["dt"] < inicio_sem)]["kg"].max()
            if pd.notna(max_sem) and pd.notna(max_antes) and max_sem > max_antes:
                prs_semana += 1

        vol_sem = calcular_volume(df_sem)
        vol_ant = calcular_volume(df_ant)
        delta_vol = f"{(vol_sem - vol_ant) / vol_ant * 100:+.0f}% vs semana anterior" \
                    if vol_ant > 0 and vol_sem > 0 else None

        m1, m2, m3 = st.columns(3)
        m1.metric("🗓️ Treinos na semana", df_sem["dt"].nunique())
        m2.metric("🏆 PRs na semana", prs_semana)
        m3.metric("📦 Volume (kg)", f"{vol_sem:,.0f}" if vol_sem > 0 else "—", delta=delta_vol)
        st.caption("💡 Volume = séries × reps × kg — anote no formato **3x12** na nota para contar.")

        st.markdown("---")
        st.markdown("## 📈 Evolução de Carga — Últimos 30 dias")

        col1, col2 = st.columns([1, 2])
        with col1:
            dia_grafico = st.selectbox("Dia de treino", DIAS, key="dia_grafico")
        with col2:
            exs_disp = sorted(df_historico[df_historico["treino"] == dia_grafico]["exercicio"].unique().tolist())
            exs_sel  = st.multiselect("Exercícios (até 10)", exs_disp, default=exs_disp[:1], max_selections=10) \
                       if exs_disp else []

        if not exs_disp:
            st.info(f"Nenhum registro salvo para {dia_grafico} ainda.")
        elif exs_sel:
            corte = datetime.now(BRT) - timedelta(days=30)
            series_plot = []
            for ex_nome in exs_sel:
                dfe = df_historico[
                    (df_historico["treino"]    == dia_grafico) &
                    (df_historico["exercicio"] == ex_nome)
                ].copy()
                dfe["data"] = pd.to_datetime(dfe["data"])
                dfe = dfe[dfe["data"] >= corte.replace(tzinfo=None)].copy()
                dfe["Kg"] = dfe["carga"].apply(extrair_kg)
                dfe = dfe.dropna(subset=["Kg"]).sort_values("data")
                if not dfe.empty:
                    series_plot.append((ex_nome, dfe))

            if not series_plot:
                st.info("Sem valores numéricos para plotar.")
            else:
                # Métrica de PR só quando 1 exercício selecionado
                if len(series_plot) == 1:
                    nome_unico, df_unico = series_plot[0]
                    maximo = df_unico["Kg"].max()
                    st.metric(
                        label=f"🏆 PR — {nome_unico}",
                        value=f"{maximo:.1f} kg",
                        delta=f"{df_unico['Kg'].iloc[-1] - df_unico['Kg'].iloc[-2]:.1f} kg vs anterior" if len(df_unico) >= 2 else None
                    )

                todos_kg = pd.concat([d["Kg"] for _, d in series_plot])
                y_min = max(0, todos_kg.min() * 0.9)
                y_max = todos_kg.max() * 1.12

                fig = go.Figure()
                varios = len(series_plot) > 1

                for idx, (ex_nome, dfe) in enumerate(series_plot):
                    cor = CORES_GRAFICO[idx % len(CORES_GRAFICO)]
                    extras = {} if varios else {"fill": "tozeroy", "fillcolor": "rgba(57,255,20,0.08)"}
                    fig.add_trace(go.Scatter(
                        x=dfe["data"],
                        y=dfe["Kg"],
                        mode="lines+markers",
                        name=ex_nome,
                        line=dict(color=cor, width=2.5),
                        marker=dict(size=9, color=cor, line=dict(color="#0d1117", width=2)),
                        hovertemplate="<b>" + ex_nome + "</b><br>%{x|%d/%m} — <b>%{y:.1f} kg</b><extra></extra>",
                        showlegend=varios,
                        **extras,
                    ))

                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#0d1117",
                    plot_bgcolor="#0a180a",
                    font=dict(color="#8aff8a", family="monospace"),
                    margin=dict(l=12, r=12, t=12, b=12),
                    height=260,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom", y=1.02,
                        font=dict(color="#c8ffc8", size=11),
                        bgcolor="rgba(0,0,0,0)",
                    ),
                    xaxis=dict(
                        showgrid=False,
                        tickformat="%d/%m",
                        tickfont=dict(color="#8aff8a", size=11),
                        linecolor="#1e3a1e",
                        tickcolor="#1e3a1e",
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor="#1a2e1a",
                        tickfont=dict(color="#8aff8a", size=11),
                        ticksuffix=" kg",
                        linecolor="#1e3a1e",
                        range=[y_min, y_max],
                        zeroline=False,
                    ),
                    hoverlabel=dict(
                        bgcolor="#141e2b",
                        font=dict(color="#39ff14", size=13),
                        bordercolor="rgba(57,255,20,0.4)",
                    ),
                )

                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ═════════════════════════════════ ABA GERENCIAR ═════════════════════════════
with tab_gerenciar:
    # ── Editar registro ──────────────────────────────────────────────────────
    with st.expander("✏️ Editar registro"):
        if df_historico.empty:
            st.info("Nenhum registro salvo ainda.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                dia_edit = st.selectbox("Dia", DIAS, key="dia_edit")
            with col2:
                exs_edit = sorted(df_historico[df_historico["treino"] == dia_edit]["exercicio"].unique().tolist())
                ex_edit  = st.selectbox("Exercício", exs_edit, key="ex_edit") if exs_edit else None

            if ex_edit:
                regs_edit = df_historico[
                    (df_historico["treino"]    == dia_edit) &
                    (df_historico["exercicio"] == ex_edit)
                ].copy()
                regs_edit["Label"] = regs_edit.apply(
                    lambda r: f"[#{int(r['id'])}] {pd.to_datetime(r['data']).strftime('%d/%m/%Y')}  →  {r['carga']}"
                              + (f"  ({r['observacao']})" if pd.notna(r["observacao"]) and str(r["observacao"]).strip() else ""),
                    axis=1
                )
                escolhido_edit = st.selectbox("Registro a editar", regs_edit["Label"].tolist(), key="reg_edit")
                row_edit       = regs_edit[regs_edit["Label"] == escolhido_edit].iloc[0]
                id_edit        = int(row_edit["id"])

                # Bug fix — key inclui o id: campos recarregam ao trocar de registro
                c1, c2 = st.columns(2)
                with c1:
                    nova_carga = st.text_input("Nova carga", value=str(row_edit["carga"]), key=f"edit_carga_{id_edit}")
                with c2:
                    nova_obs   = st.text_input("Nova nota", value=str(row_edit["observacao"]) if pd.notna(row_edit["observacao"]) else "", key=f"edit_obs_{id_edit}")

                if st.button("💾 Salvar edição", key="btn_salvar_edit"):
                    if not nova_carga.strip():
                        st.warning("A carga não pode ficar vazia.")
                    else:
                        try:
                            get_supabase().table("historico_cargas").update({
                                "carga":      nova_carga.strip(),
                                "observacao": nova_obs.strip() or None,
                            }).eq("id", id_edit).execute()
                            carregar_historico.clear()
                            st.success("✅ Registro atualizado!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Erro ao editar — tente novamente. ({e})")

    # ── Apagar registro — Fix #4: reutiliza df_historico já carregado ────────
    with st.expander("🗑️ Apagar registro incorreto"):
        # Fix #4 — sem segunda chamada ao Supabase
        df_del = df_historico

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

                # Fix #8 — label único com ID para evitar duplicatas de mesma carga/data
                registros["Label"] = registros.apply(
                    lambda r: f"[#{int(r['id'])}] {pd.to_datetime(r['data']).strftime('%d/%m/%Y')}  →  {r['carga']}"
                              + (f"  ({r['observacao']})" if pd.notna(r["observacao"]) and str(r["observacao"]).strip() else ""),
                    axis=1
                )
                escolhido = st.selectbox("Registro a apagar", registros["Label"].tolist(), key="reg_del")
                id_del    = int(registros[registros["Label"] == escolhido].iloc[0]["id"])

                if st.button("🗑️ Apagar este registro", key="btn_apagar"):
                    # Fix #5 — armazena id E label juntos para detectar troca de seleção
                    st.session_state["confirmar_apagar"] = {"id": id_del, "label": escolhido}

                conf = st.session_state.get("confirmar_apagar")
                if conf is not None:
                    # Fix #5 — se o usuário mudou a seleção, cancela confirmação anterior
                    if conf["id"] != id_del:
                        st.session_state["confirmar_apagar"] = None
                    else:
                        st.warning(f"⚠️ Confirma a exclusão de **{conf['label']}**?")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Sim, apagar", key="btn_sim"):
                                # Fix #1 — try/except no delete
                                try:
                                    get_supabase().table("historico_cargas").delete().eq("id", conf["id"]).execute()
                                    st.session_state["confirmar_apagar"] = None
                                    carregar_historico.clear()
                                    st.success("Registro apagado.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erro ao apagar — tente novamente. ({e})")
                        with c2:
                            if st.button("❌ Cancelar", key="btn_nao"):
                                st.session_state["confirmar_apagar"] = None
                                st.rerun()

    # ── Backup ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📥 Backup do histórico")
    if df_historico.empty:
        st.caption("Nenhum dado para exportar ainda.")
    else:
        csv_bytes = df_historico.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 Baixar histórico completo (CSV)",
            data=csv_bytes,
            file_name=f"historico_cargas_{hoje_brt()}.csv",
            mime="text/csv",
        )
        st.caption(f"{len(df_historico)} registros — abre direto no Excel.")
