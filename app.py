import streamlit as st
import streamlit.components.v1 as components
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

/* ── Selectbox ── */
[data-testid="stSelectbox"] label { color: #8aff8a !important; font-weight: 600; }
[data-testid="stSelectbox"] > div > div {
    background-color: #1a2332 !important;
    border: 1px solid #39ff1455 !important;
    border-radius: 10px !important;
    color: #e0ffe0 !important;
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

/* ── Botão Salvar ── */
[data-testid="stButton"] button {
    background: linear-gradient(135deg, #1a4a1a, #2d7a2d) !important;
    color: #39ff14 !important;
    border: 1px solid #39ff1466 !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    transition: all 0.2s ease;
}
[data-testid="stButton"] button:hover {
    background: linear-gradient(135deg, #2d7a2d, #3a9a3a) !important;
    box-shadow: 0 0 14px #39ff1455 !important;
    transform: translateY(-1px);
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

/* ── Gráfico ── */
[data-testid="stVegaLiteChart"] { border-radius: 12px; }

/* ── Caption / info ── */
[data-testid="stCaptionContainer"] { color: #556655 !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏋️‍♂️ Meu Diário de Cargas")

URL_TREINOS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRoxuS5Rs5YY_kxRqMceEMSpiXmqsxsTyNjBW4avhGnttHpS7vuWvXVjsz1LwCAhA/pub?gid=649998402&single=true&output=csv"

DIAS = ["SEGUNDA-FEIRA", "TERÇA-FEIRA", "QUARTA-FEIRA", "QUINTA-FEIRA", "SEXTA-FEIRA"]

# Fix #2 — timezone BRT em vez de servidor UTC
BRT = timezone(timedelta(hours=-3))


def timer_html(segundos: int) -> str:
    return f"""
<div style="background:#0d1f0d;border:1px solid #39ff1444;border-radius:10px;padding:8px 16px;display:flex;align-items:center;gap:16px;font-family:monospace">
  <div>
    <div style="font-size:0.7rem;color:#8aff8a;">⏱️ Descanso</div>
    <div id="display" style="font-size:1.8rem;color:#39ff14;font-weight:bold;line-height:1.1">{segundos//60:02d}:{segundos%60:02d}</div>
  </div>
  <button onclick="toggle()" id="btn"
    style="background:linear-gradient(135deg,#1a4a1a,#2d7a2d);color:#39ff14;border:1px solid #39ff1466;
           border-radius:8px;padding:6px 18px;font-size:0.85rem;font-weight:700;cursor:pointer">
    ▶ Iniciar
  </button>
  <button onclick="reset()"
    style="background:#141e2b;color:#8aff8a;border:1px solid #2a3f2a;
           border-radius:8px;padding:6px 12px;font-size:0.85rem;cursor:pointer">
    ↺
  </button>
</div>
<script>
  var total={segundos}, left={segundos}, iv=null, running=false;
  function fmt(s){{return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}}
  function beep(){{
    var ctx=new(window.AudioContext||window.webkitAudioContext)();
    [0,0.4,0.8].forEach(function(t){{
      var o=ctx.createOscillator(), g=ctx.createGain();
      o.connect(g); g.connect(ctx.destination);
      o.frequency.value=880; o.type='sine';
      g.gain.setValueAtTime(0.6,ctx.currentTime+t);
      g.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+t+0.35);
      o.start(ctx.currentTime+t); o.stop(ctx.currentTime+t+0.35);
    }});
  }}
  function toggle(){{
    if(running){{clearInterval(iv);running=false;document.getElementById('btn').innerHTML='▶ Continuar';}}
    else{{
      if(left<=0)return;
      running=true;document.getElementById('btn').innerHTML='⏸ Pausar';
      iv=setInterval(function(){{
        left--;document.getElementById('display').innerHTML=fmt(left);
        if(left<=0){{clearInterval(iv);running=false;document.getElementById('btn').innerHTML='✅ Feito';
          document.getElementById('display').style.color='#fff';beep();}}
      }},1000);
    }}
  }}
  function reset(){{clearInterval(iv);running=false;left=total;
    document.getElementById('display').innerHTML=fmt(total);
    document.getElementById('display').style.color='#39ff14';
    document.getElementById('btn').innerHTML='▶ Iniciar';}}
</script>"""


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
            if exercicio not in ("", "nan"):
                treinos[dia_atual].append({"Exercicio": exercicio, "Series": series, "Descanso": descanso})

    return treinos


# ── Carrega dados — Fix #4: uma única chamada ao Supabase por render ─────────
treinos      = carregar_todos_treinos(URL_TREINOS)
df_historico = carregar_historico()

# ── Seleção do dia ───────────────────────────────────────────────────────────
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

        st.success(f"{'✅' if len(feitos_hoje) == total else '🏋️'} {len(feitos_hoje)}/{total} exercícios registrados hoje")

        # ── Expander por exercício ───────────────────────────────────────────
        for i, ex in enumerate(exercicios):
            item     = ex["Exercicio"].strip()
            alvo     = ex["Series"]
            descanso = ex.get("Descanso", "")
            seg_desc = int(extrair_kg(descanso) or 90)
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

                components.html(timer_html(seg_desc), height=70)

                if st.button("💾 Salvar", key=f"salvar_{i}"):
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

# ── Apagar registro — Fix #4: reutiliza df_historico já carregado ────────────
st.markdown("---")
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
        corte   = datetime.now(BRT) - timedelta(days=30)
        df_plot = df_historico[
            (df_historico["treino"]    == dia_grafico) &
            (df_historico["exercicio"] == ex_grafico)
        ].copy()
        df_plot["data"] = pd.to_datetime(df_plot["data"])
        df_plot = df_plot[df_plot["data"] >= corte.replace(tzinfo=None)].copy()
        df_plot["Kg"]   = df_plot["carga"].apply(extrair_kg)
        df_plot = df_plot.dropna(subset=["Kg"]).sort_values("data")

        if df_plot.empty:
            st.info("Sem valores numéricos para plotar.")
        else:
            maximo = df_plot["Kg"].max()
            st.metric(
                label=f"🏆 PR — {ex_grafico}",
                value=f"{maximo:.1f} kg",
                delta=f"{df_plot['Kg'].iloc[-1] - df_plot['Kg'].iloc[-2]:.1f} kg vs anterior" if len(df_plot) >= 2 else None
            )

            y_min = max(0, df_plot["Kg"].min() * 0.9)
            y_max = df_plot["Kg"].max() * 1.12

            fig = go.Figure()

            # Área sombreada (trace base transparente)
            fig.add_trace(go.Scatter(
                x=df_plot["data"].dt.strftime("%d/%m"),
                y=df_plot["Kg"],
                fill="tozeroy",
                fillcolor="rgba(57,255,20,0.08)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False,
                hoverinfo="skip",
            ))

            # Linha principal
            fig.add_trace(go.Scatter(
                x=df_plot["data"].dt.strftime("%d/%m"),
                y=df_plot["Kg"],
                mode="lines+markers",
                line=dict(color="#39ff14", width=2.5),
                marker=dict(size=9, color="#39ff14", line=dict(color="#0d1117", width=2)),
                hovertemplate="<b>%{x}</b><br><b>%{y:.1f} kg</b><extra></extra>",
                showlegend=False,
            ))

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0a180a",
                font=dict(color="#8aff8a", family="monospace"),
                margin=dict(l=12, r=12, t=12, b=12),
                height=260,
                xaxis=dict(
                    showgrid=False,
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
                    font_color="#39ff14",
                    bordercolor="#39ff1466",
                    font_size=13,
                ),
            )

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
