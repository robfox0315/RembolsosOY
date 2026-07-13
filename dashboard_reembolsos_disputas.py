"""
Dashboard de Reembolsos y Disputas — Opción Yo
Fuente: exportación unified_payments (Stripe)
Autor: NOVA para Roberto Ortega
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime, timezone

HUBSPOT_BASE = "https://api.hubapi.com"
CATEGORIA_RESCATE = "FID- Rescate de reembolsos"

def _mes_bounds_ms(year, month):
    """Devuelve (inicio, fin) del mes en milisegundos UTC para filtrar closed_date."""
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if month == 12 else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

def _es_salvado(resolucion):
    """Salvado = Reembolso rechazado + Resuelto exitoso (ISSUE_FIXED). Match flexible por si el API devuelve códigos internos."""
    if not resolucion:
        return False
    r = str(resolucion).lower()
    return ("rechazado" in r) or ("exitoso" in r) or ("issue_fixed" in r)

@st.cache_data(ttl=600, show_spinner=False)
def hs_fetch_owners(token):
    headers = {"Authorization": f"Bearer {token}"}
    owners, after = {}, None
    while True:
        params = {"limit": 100}
        if after:
            params["after"] = after
        r = requests.get(f"{HUBSPOT_BASE}/crm/v3/owners/", headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        for o in data.get("results", []):
            nombre = f"{o.get('firstName','')} {o.get('lastName','')}".strip() or o.get("email", f"ID {o.get('id')}")
            owners[str(o["id"])] = nombre
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return owners

@st.cache_data(ttl=600, show_spinner=False)
def hs_fetch_rescate(token, start_ms, end_ms):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{HUBSPOT_BASE}/crm/v3/objects/tickets/search"
    resultados, after = [], None
    while True:
        body = {
            "filterGroups": [{"filters": [
                {"propertyName": "hs_ticket_category", "operator": "EQ", "value": CATEGORIA_RESCATE},
                {"propertyName": "closed_date", "operator": "BETWEEN", "value": start_ms, "highValue": end_ms},
            ]}],
            "properties": ["hubspot_owner_id", "hs_resolution", "closed_date", "hs_ticket_category", "monto_de_reembolso"],
            "limit": 100,
        }
        if after:
            body["after"] = after
        r = requests.post(url, headers=headers, json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        resultados.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    return resultados

def hs_construir_tabla_agentes(token, year, month):
    """Devuelve DataFrame [Agente, Asignados, Salvados, Monto salvado, Tasa %] + desglose de resoluciones."""
    start_ms, end_ms = _mes_bounds_ms(year, month)
    owners = hs_fetch_owners(token)
    tickets = hs_fetch_rescate(token, start_ms, end_ms)

    filas, resoluciones = {}, {}
    for t in tickets:
        props = t.get("properties", {})
        oid = str(props.get("hubspot_owner_id") or "Sin asignar")
        agente = owners.get(oid, "Sin asignar" if oid == "Sin asignar" else f"ID {oid}")
        reso = props.get("hs_resolution")
        try:
            monto = float(props.get("monto_de_reembolso") or 0)
        except (ValueError, TypeError):
            monto = 0.0
        resoluciones[reso or "(sin resolución)"] = resoluciones.get(reso or "(sin resolución)", 0) + 1
        if agente not in filas:
            filas[agente] = {"Asignados": 0, "Salvados": 0, "Monto salvado": 0.0}
        filas[agente]["Asignados"] += 1
        if _es_salvado(reso):
            filas[agente]["Salvados"] += 1
            filas[agente]["Monto salvado"] += monto

    df = pd.DataFrame([{"Agente": a, **v} for a, v in filas.items()])
    if not df.empty:
        df["Tasa %"] = (df["Salvados"] / df["Asignados"] * 100).round(1)
        df = df.sort_values("Salvados", ascending=False)
    return df, resoluciones

from datetime import datetime, timedelta
from pathlib import Path
import io
import re

MESES_ES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

def mes_es(period):
    """Convierte un pandas.Period (mensual) a texto en español, ej. 'Junio 2026'."""
    return f"{MESES_ES[period.month]} {period.year}"

st.set_page_config(page_title="Opción Yo · Panel Financiero", layout="wide", page_icon="◆",
                   initial_sidebar_state="collapsed")

# ============================ SISTEMA DE DISEÑO ============================
# Selector de tema — el usuario elige, no se fuerza
if "tema" not in st.session_state:
    st.session_state.tema = "Claro"

_tc1, _tc2 = st.columns([4, 1])
with _tc2:
    st.session_state.tema = st.selectbox("🎨 Tema de color", ["Claro", "Oscuro"],
                                         index=0 if st.session_state.tema == "Claro" else 1)
MODO = st.session_state.tema

# Acentos de marca (constantes en ambos temas)
TEAL = "#0EA5B5"
TEAL_DK = "#0E7C86"
BLUE = "#2563EB"
RED = "#DC2626"
GREEN = "#16A34A"
AMBER = "#D97706"

# Paletas que cambian según el tema elegido
if MODO == "Oscuro":
    BG = "#0B1220"        # fondo app
    CARD = "#141C2B"      # tarjetas
    INK = "#E8EEF6"       # texto principal
    SLATE = "#94A3B8"     # texto secundario
    LINE = "#243244"      # bordes
    GRID = "#1E293B"      # grillas de gráficos
else:
    BG = "#F8FAFC"
    CARD = "#FFFFFF"
    INK = "#0F172A"
    SLATE = "#64748B"
    LINE = "#E2E8F0"
    GRID = "#E2E8F0"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

/* ---- Tema aplicado según selección del usuario ---- */
.stApp, .main, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
  background: {BG} !important;
}}
[data-testid="stSidebar"] {{ background: {CARD} !important; }}
.stApp, .stApp p, .stApp span, .stApp label, .stApp li,
[data-testid="stMarkdownContainer"] {{ color: {INK} !important; }}
[data-testid="stFileUploader"] section {{ background: {CARD} !important; border-color: {LINE} !important; }}

html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, sans-serif; }}

/* Ocultar footer de Streamlit; se conserva el header con el menú de Settings */
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding-top: 1rem; padding-bottom: 3rem; max-width: 1400px; }}

/* Tipografía de títulos */
h1, h2, h3 {{ font-family: 'Space Grotesk', sans-serif; color: {INK} !important; letter-spacing: -0.02em; }}
h2 {{ font-size: 1.35rem !important; font-weight: 600 !important; margin-top: 0.5rem !important; }}
h3 {{ font-size: 1.05rem !important; font-weight: 600 !important; }}

/* Header de marca */
.brand-header {{
  background: linear-gradient(135deg, {TEAL_DK} 0%, {TEAL} 100%);
  border-radius: 16px; padding: 26px 32px; margin-bottom: 22px;
  box-shadow: 0 10px 30px -12px rgba(14,124,134,0.45);
}}
.brand-header .eyebrow {{
  font-size: 0.72rem; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase;
  color: rgba(255,255,255,0.78); margin-bottom: 6px;
}}
.brand-header .title {{
  font-family: 'Space Grotesk', sans-serif; font-size: 1.75rem; font-weight: 700;
  color: #fff; letter-spacing: -0.02em; line-height: 1.15;
}}
.brand-header .subtitle {{ color: rgba(255,255,255,0.85); font-size: 0.9rem; margin-top: 4px; }}

/* Métricas tipo tarjeta */
[data-testid="stMetric"] {{
  background: {CARD}; border: 1px solid {LINE}; border-radius: 14px;
  padding: 18px 20px; box-shadow: 0 1px 3px rgba(15,23,42,0.04);
  border-left: 3px solid {TEAL};
}}
[data-testid="stMetricLabel"] p {{
  font-size: 0.75rem !important; font-weight: 600 !important; color: {SLATE} !important;
  text-transform: uppercase; letter-spacing: 0.04em;
}}
[data-testid="stMetricValue"] {{
  font-family: 'Space Grotesk', sans-serif !important; color: {INK} !important;
  font-weight: 700 !important; font-variant-numeric: tabular-nums;
}}
[data-testid="stMetricDelta"] {{ font-weight: 600 !important; }}

/* Tabs refinadas */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{
  font-weight: 600; font-size: 0.9rem; color: {SLATE};
  padding: 10px 16px; border-radius: 8px 8px 0 0;
}}
.stTabs [aria-selected="true"] {{ color: {TEAL} !important; background: rgba(14,165,181,0.10); }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {TEAL} !important; height: 3px; }}

/* Tablas */
[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 12px; overflow: hidden; }}

/* Botones */
.stButton button, .stDownloadButton button {{
  border-radius: 10px; font-weight: 600; border: 1px solid {LINE};
  transition: all 0.15s ease;
}}
.stDownloadButton button {{ background: {TEAL_DK}; color: #fff; border: none; }}
.stDownloadButton button:hover {{ background: {TEAL}; }}

/* Divisores */
hr {{ border-color: {LINE}; margin: 1.5rem 0; }}

/* Cajas de alerta */
[data-testid="stAlert"] {{ border-radius: 12px; }}
</style>
""", unsafe_allow_html=True)

DATE_COLS = ["Created date (UTC)", "Refunded date (UTC)", "Dispute Date (UTC)", "Dispute Evidence Due (UTC)"]
NUM_COLS = ["Amount", "Amount Refunded", "Fee", "Disputed Amount"]

DISPUTE_STATUS_LABELS = {
    "won": "Ganada", "lost": "Perdida",
    "under_review": "En revisión", "needs_response": "Necesita respuesta"
}

# Plantilla de estilo unificada para gráficos Plotly (se adapta al tema)
PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, sans-serif", size=13, color=INK),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=30, b=30, l=10, r=10),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    colorway=[TEAL, BLUE, AMBER, GREEN, RED],
)

# ------------------------------------------------------------------
# HEADER DE MARCA
# ------------------------------------------------------------------
st.markdown(f"""
<div class="brand-header">
  <div class="eyebrow">Opción Yo · Operaciones</div>
  <div class="title">Panel Financiero — Reembolsos, Disputas y Rescate</div>
  <div class="subtitle">Stripe + HubSpot · datos validados contra la fuente</div>
</div>
""", unsafe_allow_html=True)
st.caption("Datos actualizados automáticamente · Stripe (pagos) + HubSpot (rescates) · verificados cargo por cargo.")

if "payments_df" not in st.session_state:
    st.session_state.payments_df = pd.DataFrame()

# ------------------------------------------------------------------
# CARGA AUTOMÁTICA DE DATOS (desde el repo — sin intervención del usuario)
# ------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
STRIPE_FILE = DATA_DIR / "stripe_pagos.csv.gz"
FID_FILE = DATA_DIR / "fid_rescate.csv.gz"

@st.cache_data(ttl=3600, show_spinner="Cargando datos...")
def cargar_datos_repo(ruta, mtime):
    """Lee un CSV (.gz o plano) del repo. mtime fuerza recarga si el archivo cambia."""
    return pd.read_csv(ruta, compression="gzip" if str(ruta).endswith(".gz") else None, low_memory=False)

# Cargar pagos de Stripe automáticamente
if st.session_state.payments_df.empty and STRIPE_FILE.exists():
    try:
        st.session_state.payments_df = cargar_datos_repo(STRIPE_FILE, STRIPE_FILE.stat().st_mtime)
    except Exception as e:
        st.error(f"No se pudieron cargar los datos de pagos: {e}")

# Uploader oculto — solo para actualizar los datos, no estorba a quien solo consulta
with st.expander("Actualizar datos (solo para administradores)"):
    st.caption("Los datos se cargan automáticamente desde el repositorio. "
               "Sube un CSV nuevo solo si necesitas incorporar información más reciente.")
    uploaded = st.file_uploader("Cargar CSV de pagos (Stripe)", type=["csv", "gz"], accept_multiple_files=True)
    if uploaded:
        frames = [st.session_state.payments_df] if not st.session_state.payments_df.empty else []
        for f in uploaded:
            frames.append(pd.read_csv(f, compression="gzip" if f.name.endswith(".gz") else None, low_memory=False))
        combined = pd.concat(frames, ignore_index=True)
        before = len(combined)
        combined = combined.drop_duplicates(subset="id", keep="last")
        st.session_state.payments_df = combined
        dupes = before - len(combined)
        if dupes:
            st.toast(f"{dupes} filas duplicadas por 'id' fueron ignoradas.")

df = st.session_state.payments_df.copy()

if df.empty:
    st.warning("No se encontraron datos de pagos. Verifica que exista el archivo `data/stripe_pagos.csv.gz` "
               "en el repositorio, o súbelo manualmente desde la sección de arriba.")
    st.stop()

for c in DATE_COLS:
    if c in df.columns:
        df[c] = pd.to_datetime(df[c], errors="coerce")
for c in NUM_COLS:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

df["Dispute Status Label"] = df["Dispute Status"].map(DISPUTE_STATUS_LABELS).fillna(df["Dispute Status"])
df["is_refund"] = df["Amount Refunded"] > 0
df["is_dispute"] = df["Dispute Status"].notna()

# ------------------------------------------------------------------
# SELECTOR DE PERIODO Y CRITERIO DE FECHA
# ------------------------------------------------------------------
all_months = sorted(set(
    df["Refunded date (UTC)"].dropna().dt.to_period("M").astype(str).tolist() +
    df["Dispute Date (UTC)"].dropna().dt.to_period("M").astype(str).tolist()
), reverse=True)

c1, c2 = st.columns([1, 2])
with c1:
    # Por defecto abre en el último mes COMPLETO (el mes en curso está incompleto y engaña)
    mes_actual = pd.Timestamp.now().to_period("M").strftime("%Y-%m")
    idx_def = next((i for i, m in enumerate(all_months) if m != mes_actual), 0)
    mes_sel = st.selectbox("Mes de análisis", all_months, index=idx_def)
with c2:
    st.caption("Un reembolso/disputa se asigna al mes en que **ocurrió** (fecha de reembolso / fecha de disputa), no al mes del cobro original.")

period = pd.Period(mes_sel, freq="M")
p_start, p_end = period.start_time, (period + 1).start_time

refunds_m = df[(df["Refunded date (UTC)"] >= p_start) & (df["Refunded date (UTC)"] < p_end)].copy()
disputes_m = df[(df["Dispute Date (UTC)"] >= p_start) & (df["Dispute Date (UTC)"] < p_end)].copy()

refunds_m["pago_mismo_mes"] = (refunds_m["Created date (UTC)"] >= p_start) & (refunds_m["Created date (UTC)"] < p_end)
disputes_m["pago_mismo_mes"] = (disputes_m["Created date (UTC)"] >= p_start) & (disputes_m["Created date (UTC)"] < p_end)

n_refunds = len(refunds_m)
monto_refunds = refunds_m["Amount Refunded"].sum()
n_disputes = len(disputes_m)
monto_disputas = disputes_m["Disputed Amount"].sum()
fee_disputas = disputes_m["Fee"].sum()
total_disputas = monto_disputas + fee_disputas
gran_total = monto_refunds + total_disputas
n_casos_totales = n_refunds + n_disputes

# ------------------------------------------------------------------
# TABS
# ------------------------------------------------------------------
tab1, tab2, tab3, tab6, tab7, tab4, tab5 = st.tabs([
    "Resumen ejecutivo", "Reembolsos", "Disputas", "Rescate por agente", "Comisiones", "Pendientes urgentes", "Detalle de casos"
])

# ===================== TAB 7: COMISIONES POR CSV (sin token) =====================
with tab7:
    st.subheader("Comisiones por rescate")
    st.caption("Datos auditados: cada rescate verificado cargo por cargo contra Stripe. "
               "Salvado = 'Reembolso rechazado' + 'Resuelto exitoso'. "
               "No comisionan las disputas (las gestiona Admin) ni los rescates que no se sostuvieron.")

    # Carga automática del archivo de rescates desde el repo
    fid = None
    if FID_FILE.exists():
        try:
            fid = cargar_datos_repo(FID_FILE, FID_FILE.stat().st_mtime)
        except Exception as e:
            st.error(f"No se pudo cargar el archivo de rescates: {e}")

    # Uploader oculto — solo para administradores que quieran actualizar
    with st.expander("Actualizar datos de rescates (solo administradores)"):
        st.caption("Los datos se cargan automáticamente desde el repositorio.")
        cU1, cU2 = st.columns(2)
        with cU1:
            f_fid = st.file_uploader("CSV de tickets FID- Rescate", type=["csv", "gz"], key="fid_csv")
        with cU2:
            f_stripe_c = st.file_uploader("CSV de Stripe (para detectar contradicciones)", type=["csv", "gz"], key="stripe_com")
        st.markdown("""
**Cómo exportar el CSV del FID:** HubSpot → CRM → Tickets → filtrar por Categoría =
`FID- Rescate de reembolsos` → Exportar, incluyendo: Propietario del ticket, Resolución,
Fecha de cierre, Monto de reembolso y Associated Contact.
""")

    if f_fid is not None:
        fid = pd.read_csv(f_fid, compression="gzip" if f_fid.name.endswith(".gz") else None)

    if fid is None or fid.empty:
        st.warning("No se encontraron datos de rescates. Verifica que exista `data/fid_rescate.csv.gz` "
                   "en el repositorio, o súbelo desde la sección de arriba.")
    else:
        fid = fid.copy()
        col_agente, col_reso, col_fecha, col_monto, col_contact = \
            "Propietario del ticket", "Resolución", "Fecha de cierre", "Monto de reembolso", "Associated Contact"

        faltan = [c for c in [col_agente, col_reso, col_fecha] if c not in fid.columns]
        if faltan:
            st.error(f"Al CSV le faltan columnas necesarias: {', '.join(faltan)}. Reexporta incluyéndolas.")
        else:
            def _es_salvado_csv(r):
                if pd.isna(r):
                    return False
                r = str(r).lower()
                return ("rechazado" in r) or ("exitoso" in r) or ("issue_fixed" in r)

            fid["_salvado"] = fid[col_reso].apply(_es_salvado_csv)
            fid["_mes"] = pd.to_datetime(fid[col_fecha], errors="coerce").dt.to_period("M").astype(str)
            fid["_agente"] = fid[col_agente].fillna("Sin asignar")
            tiene_monto = col_monto in fid.columns
            fid["_monto"] = pd.to_numeric(fid[col_monto], errors="coerce").fillna(0) if tiene_monto else 0
            if not tiene_monto:
                st.warning("⚠️ El CSV no trae **Monto de reembolso** — el monto y la comisión saldrán en $0. "
                           "Reexporta con esa columna para calcular pagos.")

            # ---------- #4: detección de contradictorios con Stripe ----------
            contradictorios = pd.DataFrame()
            if col_contact in fid.columns:
                pay_c = pd.read_csv(f_stripe_c, compression="gzip" if f_stripe_c.name.endswith(".gz") else None) if f_stripe_c is not None else df
                if "Customer Email" in pay_c.columns and "Amount Refunded" in pay_c.columns:
                    def _mail(s):
                        m = re.search(r"\(([^)]+@[^)]+)\)", str(s))
                        return (m.group(1) if m else str(s)).lower().strip()
                    fid["_email"] = fid[col_contact].apply(_mail)
                    pay_c["_email"] = pay_c["Customer Email"].astype(str).str.lower().str.strip()
                    reembolsados = set(pay_c[pd.to_numeric(pay_c["Amount Refunded"], errors="coerce").fillna(0) > 0]["_email"])
                    salv = fid[fid["_salvado"]].copy()
                    salv["_contradice"] = salv["_email"].isin(reembolsados)
                    contradictorios = salv[salv["_contradice"]]

            # ---------- Selector de mes ----------
            meses_disp = sorted(fid["_mes"].dropna().unique(), reverse=True)
            modo = st.radio("Periodo", ["Un mes", "Acumulado del año (YTD)"], horizontal=True)
            if modo == "Un mes":
                mes_sel = st.selectbox("Mes a liquidar", meses_disp)
                sub = fid[fid["_mes"] == mes_sel]
                etiqueta = mes_sel
            else:
                sub = fid
                etiqueta = "YTD_" + (meses_disp[0][:4] if meses_disp else "2026")

            # ---------- REGLA DE NEGOCIO: comisionable = rescate verificado cargo por cargo ----------
            # Un caso solo comisiona si: (a) el cargo que se salvó SIGUE pagado en Stripe, y
            # (b) NO terminó en disputa (las disputas las gestiona Admin, no el asesor).
            if "Comisionable" in fid.columns:
                fid["_comisionable"] = fid["_salvado"] & fid["Comisionable"].astype(str).str.strip().str.lower().isin(["sí", "si", "yes", "true"])
                fid["_fue_disputa"] = fid.get("Fue a disputa", pd.Series("No", index=fid.index)).astype(str).str.strip().str.lower().isin(["sí", "si", "yes", "true"])
            else:
                fid["_comisionable"] = fid["_salvado"]
                fid["_fue_disputa"] = False
                st.warning("⚠️ El CSV no trae la columna **Comisionable**. No se pueden excluir disputas ni rescates "
                           "fallidos. Usa el CSV maestro auditado (v4) para un cálculo correcto.")

            # recalcular el subconjunto del periodo con las nuevas banderas
            if modo == "Un mes":
                sub = fid[fid["_mes"] == mes_sel]
            else:
                sub = fid

            # excluir contradictorios del pago si existen
            excluir_contra = False
            if not contradictorios.empty:
                st.error(f"⚠️ **{len(contradictorios)} caso(s) contradictorio(s):** marcados como salvados pero "
                         f"con reembolso en Stripe. Pagar comisión por ellos = pagar de más.")
                excluir_contra = st.checkbox("Excluir casos contradictorios del cálculo de comisión", value=True)

            n_excluidos = int(sub["_salvado"].sum() - sub["_comisionable"].sum())
            if n_excluidos > 0 and "Estado del rescate" in sub.columns:
                detalle = sub.loc[sub["_salvado"] & ~sub["_comisionable"], "Estado del rescate"].value_counts()
                motivos = " · ".join(f"{v} {k.lower()}" for k, v in detalle.items())
                monto_excl = sub.loc[sub["_salvado"] & ~sub["_comisionable"], "_monto"].sum()
                st.info(f"ℹ️ **{n_excluidos} caso(s) salvado(s) NO comisionan (${monto_excl:,.2f}):** {motivos}. "
                        "Las disputas las gestiona Admin (no el asesor), y un rescate que terminó reembolsado no fue efectivo. "
                        "Verificado cargo por cargo contra Stripe.")

            def _agrupar(df):
                if excluir_contra and not contradictorios.empty:
                    df = df[~df.index.isin(contradictorios.index)]
                g = df.groupby("_agente").apply(lambda x: pd.Series({
                    "Asignados": len(x),
                    "Salvados": int(x["_salvado"].sum()),
                    "No comisionan": int((x["_salvado"] & ~x["_comisionable"]).sum()),
                    "Comisionables": int(x["_comisionable"].sum()),
                    "Monto salvado": float(x.loc[x["_salvado"], "_monto"].sum()),
                    "Monto comisionable": float(x.loc[x["_comisionable"], "_monto"].sum()),
                })).reset_index().rename(columns={"_agente": "Agente"})
                g["Tasa %"] = (g["Salvados"] / g["Asignados"] * 100).round(1)
                return g.sort_values("Comisionables", ascending=False)

            g = _agrupar(sub)

            t1, t2, t3, t4, t5 = st.columns(5)
            t1.metric("Tickets", int(g["Asignados"].sum()))
            t2.metric("Salvados", int(g["Salvados"].sum()))
            t3.metric("No comisionan", int(g["No comisionan"].sum()))
            t4.metric("Comisionables", int(g["Comisionables"].sum()))
            t5.metric("Monto comisionable", f"${g['Monto comisionable'].sum():,.0f}")
            st.caption("La comisión se calcula **solo sobre el monto comisionable** — excluye los casos que "
                       "terminaron en disputa, ya que esos los gestiona Admin y no el asesor.")

            # ---------- Esquema de comisión configurable ----------
            st.markdown("**Esquema de comisión (configurable)**")
            tipo_com = st.radio("Tipo", ["Porcentaje plano", "Escalonado por tramos"], horizontal=True)
            if tipo_com == "Porcentaje plano":
                pct = st.number_input("% sobre monto comisionable", 0.0, 100.0, 5.0, 0.5, format="%.1f", key="pctplano")
                g["Comisión USD"] = (g["Monto comisionable"] * pct / 100).round(2)
            else:
                base_criterio = st.selectbox("Los tramos se miden por", ["Monto comisionable (USD)", "Cantidad de comisionables"])
                cc1, cc2, cc3 = st.columns(3)
                with cc1:
                    pct_base = st.number_input("% base", 0.0, 100.0, 5.0, 0.5, format="%.1f")
                with cc2:
                    umbral = st.number_input("Umbral para % alto", 0.0, 1_000_000.0, 1000.0, 50.0)
                with cc3:
                    pct_alto = st.number_input("% alto (si supera umbral)", 0.0, 100.0, 8.0, 0.5, format="%.1f")
                base_col = "Monto comisionable" if base_criterio.startswith("Monto") else "Comisionables"
                g["% aplicado"] = g[base_col].apply(lambda v: pct_alto if v >= umbral else pct_base)
                g["Comisión USD"] = (g["Monto comisionable"] * g["% aplicado"] / 100).round(2)
                st.caption(f"Se aplica {pct_alto}% a quienes superan {umbral:,.0f} en '{base_criterio}', {pct_base}% al resto.")

            fig = go.Figure()
            fig.add_bar(x=g["Agente"], y=g["Comisionables"], name="Comisionables", marker_color=TEAL)
            fig.add_bar(x=g["Agente"], y=g["No comisionan"], name="No comisionan (disputa o falló)", marker_color=AMBER)
            fig.update_layout(**PLOTLY_LAYOUT, barmode="stack", height=400, yaxis_title="Casos salvados")
            st.plotly_chart(fig, use_container_width=True)

            show = g.copy()
            show["Tasa %"] = show["Tasa %"].astype(str) + "%"
            for c in ["Monto salvado", "Monto comisionable", "Comisión USD"]:
                show[c] = show[c].apply(lambda x: f"${x:,.2f}")
            cols_show = ["Agente", "Asignados", "Salvados", "No comisionan", "Comisionables",
                         "Monto comisionable", "Comisión USD"]
            if "% aplicado" in show.columns:
                show["% aplicado"] = show["% aplicado"].astype(str) + "%"
                cols_show.insert(6, "% aplicado")
            st.dataframe(show[cols_show], use_container_width=True, hide_index=True)

            buf = io.StringIO()
            g.to_csv(buf, index=False)
            st.download_button(f"⬇️ Descargar liquidación ({etiqueta})", buf.getvalue(),
                               file_name=f"comisiones_{etiqueta}.csv", mime="text/csv")

            # ---------- Desglose por cliente dentro de cada agente ----------
            st.divider()
            st.markdown("**Detalle por cliente recuperado (por agente)**")
            st.caption("Cada cliente cuyo reembolso fue salvado. Los casos marcados 'Fue a disputa = Sí' "
                       "**no generan comisión** (los gestiona Admin), pero se muestran para trazabilidad.")

            salvados_det = sub[sub["_salvado"]].copy()
            if excluir_contra and not contradictorios.empty:
                salvados_det = salvados_det[~salvados_det.index.isin(contradictorios.index)]

            cols_det = [c for c in [col_contact, col_reso, col_monto, "Estado del rescate", "Cargo salvado (fecha)",
                                    "Estado de disputa", col_fecha]
                        if c in salvados_det.columns]
            agentes_orden = g.sort_values("Comisionables", ascending=False)["Agente"].tolist()

            for ag in agentes_orden:
                filas_ag = salvados_det[salvados_det["_agente"] == ag]
                if filas_ag.empty:
                    continue
                comis_ag = filas_ag[filas_ag["_comisionable"]]
                monto_ag = comis_ag["_monto"].sum()
                n_disp_ag = int((~filas_ag["_comisionable"]).sum())
                titulo = f"{ag} · {len(comis_ag)} comisionables · ${monto_ag:,.2f}"
                if n_disp_ag:
                    titulo += f"  (+{n_disp_ag} no comisionan)"
                with st.expander(titulo):
                    tabla_det = filas_ag[cols_det].copy()
                    rename_map = {col_contact: "Cliente", col_reso: "Resolución",
                                  col_monto: "Monto recuperado", col_fecha: "Fecha de cierre"}
                    tabla_det = tabla_det.rename(columns=rename_map)
                    if "Monto recuperado" in tabla_det.columns:
                        tabla_det["Monto recuperado"] = pd.to_numeric(tabla_det["Monto recuperado"], errors="coerce").fillna(0).apply(lambda x: f"${x:,.2f}")
                    st.dataframe(tabla_det, use_container_width=True, hide_index=True)

            # ---------- #1: comparativa mes vs mes ----------
            st.divider()
            st.markdown("**Salvados por agente, mes a mes**")
            piv = fid[fid["_salvado"]].pivot_table(index="_agente", columns="_mes",
                                                    values=col_reso, aggfunc="count", fill_value=0)
            if piv.shape[1] >= 2:
                ult, penult = piv.columns[-1], piv.columns[-2]
                piv["Δ vs mes previo"] = piv[ult] - piv[penult]
            st.dataframe(piv, use_container_width=True)
            st.caption("Cada columna es un mes. La última columna muestra el cambio del mes más reciente vs. el anterior.")

            # ---------- #4: lista de contradictorios ----------
            if not contradictorios.empty:
                st.divider()
                st.markdown("**Casos a revisar antes de pagar** (marcados salvados en HubSpot pero reembolsados en Stripe)")
                cols_contra = [c for c in [col_agente, col_contact, col_reso, col_fecha] if c in contradictorios.columns]
                st.dataframe(contradictorios[cols_contra], use_container_width=True, hide_index=True)
                bufc = io.StringIO()
                contradictorios[cols_contra].to_csv(bufc, index=False)
                st.download_button("⬇️ Descargar casos a revisar", bufc.getvalue(),
                                   file_name="casos_contradictorios.csv", mime="text/csv")

            with st.expander("Verificar: resoluciones contadas como salvado"):
                chk = sub.groupby(col_reso)["_salvado"].agg(["count", "first"]).reset_index()
                chk.columns = ["Resolución", "Tickets", "¿Salvado?"]
                chk["¿Salvado?"] = chk["¿Salvado?"].map({True: "Sí", False: "No"})
                st.dataframe(chk, use_container_width=True, hide_index=True)

# ===================== TAB 6: RESCATE POR AGENTE (HubSpot API en vivo) =====================
with tab6:
    st.subheader("Reembolsos salvados por agente")
    st.caption("Fuente: HubSpot API en vivo · categoría FID- Rescate de reembolsos · "
               "Salvado = 'Reembolso rechazado' + 'Resuelto exitoso'.")

    # Token desde Streamlit Secrets (nunca en el código)
    token = None
    try:
        token = st.secrets["HUBSPOT_TOKEN"]
    except Exception:
        token = None

    if not token:
        st.warning("🔑 Falta configurar el token de HubSpot para actualizar en vivo.")
        st.markdown("""
**Cómo activarlo (una sola vez):**
1. En HubSpot: **Configuración → Integraciones → Private Apps → Create a private app**
2. En *Scopes*, marca lectura de tickets: `crm.objects.tickets.read` y `crm.objects.owners.read`
3. Copia el token que empieza con `pat-...`
4. En Streamlit Cloud: tu app → **Settings → Secrets** → pega:
   ```
   HUBSPOT_TOKEN = "pat-xxxxxxxx"
   ```
5. Guarda. La app se reinicia y esta pestaña se actualiza sola.
""")
        st.info("Mientras tanto, referencia validada de mayo 2026: 96 tickets, 24 salvados (25%), líder Laura Pereira (13).")
    else:
        hoy = datetime.now()
        cA, cB, cC = st.columns([1, 1, 1])
        with cA:
            year = st.selectbox("Año", list(range(2026, hoy.year + 1)), index=0)
        with cB:
            month = st.selectbox("Mes", list(MESES_ES.keys()), format_func=lambda m: MESES_ES[m],
                                 index=min(hoy.month - 1, 11))
        with cC:
            st.write("")
            st.write("")
            actualizar = st.button("🔄 Actualizar datos", use_container_width=True)

        try:
            with st.spinner("Consultando HubSpot..."):
                df_ag, resoluciones = hs_construir_tabla_agentes(token, year, month)

            if df_ag.empty:
                st.info(f"No hay tickets de rescate cerrados en {MESES_ES[month]} {year}.")
            else:
                total_asig = int(df_ag["Asignados"].sum())
                total_salv = int(df_ag["Salvados"].sum())
                total_monto = df_ag["Monto salvado"].sum()
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Tickets cerrados", total_asig)
                m2.metric("Reembolsos salvados", total_salv)
                m3.metric("Tasa de rescate", f"{total_salv/total_asig*100:.0f}%")
                m4.metric("Monto salvado", f"${total_monto:,.0f}")

                if total_monto == 0:
                    st.warning("⚠️ **El monto salvado está en $0.** El campo `Monto de reembolso` no se está llenando "
                               "en el pipeline FID- Rescate. La comisión no se puede calcular hasta que se capture ese dato "
                               "(ver instrucciones para el equipo). El conteo de salvados sí es correcto.")

                # Calculadora de comisión
                st.markdown("**Cálculo de comisión por agente**")
                pct = st.number_input("% de comisión sobre monto salvado", min_value=0.0, max_value=100.0,
                                      value=5.0, step=0.5, format="%.1f")
                df_ag["Comisión USD"] = (df_ag["Monto salvado"] * pct / 100).round(2)

                fig_ag = go.Figure()
                fig_ag.add_bar(x=df_ag["Agente"], y=df_ag["Asignados"], name="Asignados", marker_color=BLUE)
                fig_ag.add_bar(x=df_ag["Agente"], y=df_ag["Salvados"], name="Salvados", marker_color=TEAL)
                fig_ag.update_layout(**PLOTLY_LAYOUT, barmode="group", height=400, yaxis_title="Tickets")
                st.plotly_chart(fig_ag, use_container_width=True)

                tabla = df_ag.copy()
                tabla["Tasa %"] = tabla["Tasa %"].astype(str) + "%"
                tabla["Monto salvado"] = tabla["Monto salvado"].apply(lambda x: f"${x:,.2f}")
                tabla["Comisión USD"] = tabla["Comisión USD"].apply(lambda x: f"${x:,.2f}")
                st.dataframe(tabla[["Agente", "Asignados", "Salvados", "Tasa %", "Monto salvado", "Comisión USD"]],
                             use_container_width=True, hide_index=True)

                # Exportar para nómina
                buf = io.StringIO()
                df_ag[["Agente", "Asignados", "Salvados", "Monto salvado", "Comisión USD"]].to_csv(buf, index=False)
                st.download_button(f"⬇️ Descargar comisiones {MESES_ES[month]} {year} (CSV)", buf.getvalue(),
                                   file_name=f"comisiones_{year}_{month:02d}.csv", mime="text/csv")

                with st.expander("Verificar: resoluciones encontradas este mes"):
                    st.caption("Confirma que 'Reembolso rechazado' y 'Resuelto exitoso' se estén contando como salvados.")
                    st.dataframe(pd.DataFrame(
                        [{"Resolución": k, "Tickets": v, "¿Cuenta como salvado?": "Sí" if _es_salvado(k) else "No"}
                         for k, v in sorted(resoluciones.items(), key=lambda x: -x[1])]
                    ), use_container_width=True, hide_index=True)

                st.caption("⚠️ Con muestras pequeñas (n<5) una tasa alta puede ser engañosa: un solo caso mueve el % 20-50 puntos. "
                           "Prioriza agentes con volumen alto Y tasa alta.")
        except requests.exceptions.HTTPError as e:
            st.error(f"Error de HubSpot: {e.response.status_code}. Verifica que el token tenga permisos de tickets y owners.")
        except Exception as e:
            st.error(f"No se pudo consultar HubSpot: {e}")

# ===================== TAB 1: RESUMEN =====================
with tab1:
    st.subheader(f"Resumen — {mes_es(period)}")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Casos totales", n_casos_totales)
    k2.metric("Reembolsos", n_refunds, f"${monto_refunds:,.2f}")
    k3.metric("Disputas", n_disputes, f"${total_disputas:,.2f}")
    k4.metric("Monto total (reembolsos + disputas)", f"${gran_total:,.2f}")
    st.caption("Monto de disputas incluye fee de disputa Stripe ($15 por caso) sobre `Disputed Amount` + `Fee`.")

    st.divider()

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**Reembolsos: pago del mismo mes vs. mes(es) anterior(es)**")
        same = refunds_m["pago_mismo_mes"].sum()
        prev = n_refunds - same
        fig = go.Figure(go.Bar(
            x=["Pago mismo mes", "Pago mes(es) anterior(es)"],
            y=[same, prev],
            marker_color=[TEAL, BLUE],
            text=[same, prev], textposition="outside"
        ))
        fig.update_layout(**{k:v for k,v in PLOTLY_LAYOUT.items() if k!="legend"}, height=320, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fuente: `Created date (UTC)` vs. `Refunded date (UTC)`.")
    with cc2:
        st.markdown("**Disputas: pago del mismo mes vs. mes(es) anterior(es)**")
        same_d = disputes_m["pago_mismo_mes"].sum()
        prev_d = n_disputes - same_d
        fig = go.Figure(go.Bar(
            x=["Pago mismo mes", "Pago mes(es) anterior(es)"],
            y=[same_d, prev_d],
            marker_color=[TEAL, BLUE],
            text=[same_d, prev_d], textposition="outside"
        ))
        fig.update_layout(**{k:v for k,v in PLOTLY_LAYOUT.items() if k!="legend"}, height=320, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fuente: `Created date (UTC)` vs. `Dispute Date (UTC)`.")

    st.divider()
    st.markdown("**Tendencia diaria — casos por día**")
    if not refunds_m.empty or not disputes_m.empty:
        r_daily = refunds_m.groupby(refunds_m["Refunded date (UTC)"].dt.date).size().rename("Reembolsos")
        d_daily = disputes_m.groupby(disputes_m["Dispute Date (UTC)"].dt.date).size().rename("Disputas")
        daily = pd.concat([r_daily, d_daily], axis=1).fillna(0).reset_index().rename(columns={"index": "Fecha"})
        fig = px.line(daily, x="Fecha", y=["Reembolsos", "Disputas"],
                       color_discrete_map={"Reembolsos": TEAL, "Disputas": RED}, markers=True)
        fig.update_layout(**PLOTLY_LAYOUT, height=350)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fuente: conteo diario por `Refunded date (UTC)` y `Dispute Date (UTC)`.")

# ===================== TAB 2: REEMBOLSOS =====================
with tab2:
    st.subheader("Reembolsos del mes")
    r1, r2, r3 = st.columns(3)
    r1.metric("Casos", n_refunds)
    r2.metric("Monto total", f"${monto_refunds:,.2f}")
    r3.metric("Monto promedio", f"${(monto_refunds/n_refunds if n_refunds else 0):,.2f}")

    st.markdown("**Origen del pago reembolsado**")
    grp = refunds_m.groupby("pago_mismo_mes").agg(casos=("id", "count"), monto=("Amount Refunded", "sum")).reset_index()
    grp["pago_mismo_mes"] = grp["pago_mismo_mes"].map({True: "Pago mismo mes", False: "Pago mes(es) anterior(es)"})
    st.dataframe(grp.rename(columns={"pago_mismo_mes": "Origen del pago", "casos": "Casos", "monto": "Monto USD"}),
                 use_container_width=True, hide_index=True)

    st.markdown("**Tipo de cargo reembolsado**")
    def _clasificar_cargo(desc):
        if pd.isna(desc):
            return "Otro"
        d = str(desc).strip()
        if d.startswith("Invoice"):
            return "Invoice"
        if d.startswith("Subscription creation"):
            return "Subscription creation"
        if d.startswith("Subscription update"):
            return "Subscription update"
        return d if d else "Otro"

    refunds_m["tipo_cargo"] = refunds_m["Description"].apply(_clasificar_cargo)
    tipo = refunds_m.groupby("tipo_cargo").agg(casos=("id", "count"), monto=("Amount Refunded", "sum")).reset_index().sort_values("monto", ascending=False)
    fig = px.bar(tipo, x="tipo_cargo", y="monto", text="casos", color_discrete_sequence=[TEAL])
    fig.update_traces(texttemplate="%{text} casos", textposition="outside")
    fig.update_layout(**PLOTLY_LAYOUT, height=350, yaxis_title="Monto USD ($)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Fuente: prefijo de `Description` (Invoice / Subscription creation / Subscription update).")

    st.markdown("**Clientes con más de 1 reembolso en el mes**")
    top_all = refunds_m.groupby("Customer Email").agg(casos=("id", "count"), monto=("Amount Refunded", "sum")).reset_index()
    top = top_all[top_all["casos"] > 1].sort_values("casos", ascending=False)
    if top.empty:
        st.caption("Ningún cliente tuvo más de 1 reembolso este mes — buena señal, no hay reincidencia.")
    else:
        st.dataframe(top.rename(columns={"Customer Email": "Cliente", "casos": "Casos", "monto": "Monto USD"}),
                     use_container_width=True, hide_index=True)

# ===================== TAB 3: DISPUTAS =====================
with tab3:
    st.subheader("Disputas del mes")
    d1, d2, d3 = st.columns(3)
    d1.metric("Casos", n_disputes)
    d2.metric("Monto disputado + fee", f"${total_disputas:,.2f}")
    d3.metric("Fee acumulado ($15/caso)", f"${fee_disputas:,.2f}")

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**Por motivo de disputa**")
        motivo = disputes_m.groupby("Dispute Reason").agg(casos=("id", "count"), monto=("Disputed Amount", "sum")).reset_index().sort_values("casos", ascending=False)
        fig = px.bar(motivo, x="Dispute Reason", y="casos", text="casos", color_discrete_sequence=[BLUE])
        fig.update_traces(textposition="outside")
        fig.update_layout(**PLOTLY_LAYOUT, height=350, yaxis_title="Casos")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fuente: `Dispute Reason`.")
    with cc2:
        st.markdown("**Por estado**")
        status_colors = {"Ganada": GREEN, "Perdida": RED, "En revisión": AMBER, "Necesita respuesta": AMBER}
        estado = disputes_m.groupby("Dispute Status Label").agg(casos=("id", "count"), monto=("Disputed Amount", "sum")).reset_index()
        fig = px.pie(estado, names="Dispute Status Label", values="casos",
                      color="Dispute Status Label", color_discrete_map=status_colors, hole=0.45)
        fig.update_layout(**PLOTLY_LAYOUT, height=350)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fuente: `Dispute Status` (won/lost/under_review/needs_response).")

    st.markdown("**Tasa de éxito en disputas resueltas (ganadas vs. perdidas)**")
    resolved = disputes_m[disputes_m["Dispute Status"].isin(["won", "lost"])]
    if len(resolved):
        win_rate = (resolved["Dispute Status"] == "won").mean() * 100
        st.metric("% Disputas ganadas (sobre resueltas)", f"{win_rate:.1f}%",
                   help=f"{(resolved['Dispute Status']=='won').sum()} ganadas de {len(resolved)} resueltas")
    else:
        st.caption("Sin disputas resueltas (ganadas/perdidas) en este mes.")

    # -------- Análisis histórico: ¿en qué motivos ganamos o perdemos? --------
    st.divider()
    st.markdown("### ¿En qué tipo de disputa ganamos o perdemos?")
    st.caption("Cruce de motivo de disputa contra resultado, sobre TODAS las disputas cargadas (no solo el mes). "
               "Ayuda a decidir dónde reforzar evidencia o proceso.")

    hist = df[df["Dispute Status"].notna()].copy()
    resueltas_h = hist[hist["Dispute Status"].isin(["won", "lost"])]

    if resueltas_h.empty:
        st.info("No hay disputas resueltas (ganadas/perdidas) en los datos cargados.")
    else:
        analisis = resueltas_h.groupby("Dispute Reason").apply(lambda g: pd.Series({
            "Resueltas": len(g),
            "Ganadas": int((g["Dispute Status"] == "won").sum()),
            "Perdidas": int((g["Dispute Status"] == "lost").sum()),
            "Monto en juego": g["Disputed Amount"].sum(),
        })).reset_index()
        analisis["Tasa de éxito %"] = (analisis["Ganadas"] / analisis["Resueltas"] * 100).round(1)
        analisis = analisis.sort_values("Resueltas", ascending=False)

        cA, cB = st.columns([3, 2])
        with cA:
            fig = go.Figure()
            fig.add_bar(y=analisis["Dispute Reason"], x=analisis["Ganadas"], name="Ganadas",
                        orientation="h", marker_color=GREEN)
            fig.add_bar(y=analisis["Dispute Reason"], x=analisis["Perdidas"], name="Perdidas",
                        orientation="h", marker_color=RED)
            fig.update_layout(**PLOTLY_LAYOUT, height=360, barmode="stack", xaxis_title="Disputas resueltas")
            st.plotly_chart(fig, use_container_width=True)
        with cB:
            tabla_h = analisis.copy()
            tabla_h["Tasa de éxito %"] = tabla_h["Tasa de éxito %"].astype(str) + "%"
            tabla_h["Monto en juego"] = tabla_h["Monto en juego"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(tabla_h[["Dispute Reason", "Resueltas", "Ganadas", "Tasa de éxito %", "Monto en juego"]]
                         .rename(columns={"Dispute Reason": "Motivo"}),
                         use_container_width=True, hide_index=True)

        # Alerta automática del punto débil
        peor = analisis[analisis["Resueltas"] >= 5].sort_values("Tasa de éxito %").head(1)
        if not peor.empty:
            r = peor.iloc[0]
            st.warning(f"🚩 **Punto débil:** en disputas por **{r['Dispute Reason']}** se ganan solo "
                       f"{r['Tasa de éxito %']:.0f}% ({int(r['Ganadas'])} de {int(r['Resueltas'])} resueltas). "
                       f"Es el tipo donde más se pierde con volumen — revisar qué evidencia se está enviando o si hay un problema de proceso detrás.")

# ===================== TAB 4: PENDIENTES URGENTES =====================
with tab4:
    st.subheader("Disputas que requieren acción de nuestro lado")
    st.caption("`needs_response` = todavía no enviamos evidencia (acción nuestra, con fecha límite real). "
               "`under_review` = ya enviamos evidencia, esperando resolución del banco emisor (no es una tarea pendiente nuestra).")

    hoy = pd.Timestamp.now().normalize()

    # --- Acción requerida: solo needs_response ---
    accion = df[df["Dispute Status"] == "needs_response"].copy()
    accion["dias_restantes"] = (accion["Dispute Evidence Due (UTC)"] - hoy).dt.days
    accion = accion.sort_values("dias_restantes")

    vencidas = accion[accion["dias_restantes"] < 0]
    urgentes = accion[(accion["dias_restantes"] >= 0) & (accion["dias_restantes"] <= 7)]

    m1, m2, m3 = st.columns(3)
    m1.metric("Pendientes de enviar evidencia", len(accion))
    m2.metric("⏰ Vencen en ≤ 7 días", len(urgentes))
    m3.metric("🔴 Vencidas sin evidencia enviada", len(vencidas))

    if len(vencidas):
        st.error(f"{len(vencidas)} disputa(s) VENCIERON sin que enviáramos evidencia — riesgo de pérdida automática.")
        st.dataframe(vencidas[["Customer Email", "Disputed Amount", "Dispute Reason", "Dispute Evidence Due (UTC)", "dias_restantes"]]
                     .rename(columns={"Customer Email": "Cliente", "Disputed Amount": "Monto USD",
                                       "Dispute Reason": "Motivo", "Dispute Evidence Due (UTC)": "Vencimiento",
                                       "dias_restantes": "Días (negativo=vencido)"}),
                     use_container_width=True, hide_index=True)

    if len(urgentes):
        st.warning(f"{len(urgentes)} disputa(s) vencen en los próximos 7 días — enviar evidencia antes de la fecha.")
        st.dataframe(urgentes[["Customer Email", "Disputed Amount", "Dispute Reason", "Dispute Evidence Due (UTC)", "dias_restantes"]]
                     .rename(columns={"Customer Email": "Cliente", "Disputed Amount": "Monto USD",
                                       "Dispute Reason": "Motivo", "Dispute Evidence Due (UTC)": "Vencimiento",
                                       "dias_restantes": "Días restantes"}),
                     use_container_width=True, hide_index=True)

    if accion.empty:
        st.success("No hay disputas esperando envío de evidencia. Al día.")

    st.divider()

    # --- Esperando al banco: under_review (informativo, no es riesgo operativo nuestro) ---
    st.subheader("Esperando resolución del banco emisor")
    en_revision = df[df["Dispute Status"] == "under_review"].copy()
    en_revision["dias_en_espera"] = (hoy - en_revision["Dispute Date (UTC)"]).dt.days
    en_revision = en_revision.sort_values("dias_en_espera", ascending=False)

    st.metric("Disputas en revisión por el banco", len(en_revision))
    if not en_revision.empty:
        st.caption("Ya enviamos evidencia en estos casos. El banco emisor decide — no requieren acción nuestra, solo seguimiento.")
        st.dataframe(en_revision[["Customer Email", "Disputed Amount", "Dispute Reason", "Dispute Date (UTC)", "dias_en_espera"]]
                     .rename(columns={"Customer Email": "Cliente", "Disputed Amount": "Monto USD",
                                       "Dispute Reason": "Motivo", "Dispute Date (UTC)": "Fecha de disputa",
                                       "dias_en_espera": "Días esperando al banco"}),
                     use_container_width=True, hide_index=True)

    st.caption("Vista no filtrada por mes — muestra todas las disputas abiertas en el dataset cargado.")

# ===================== TAB 5: DETALLE =====================
with tab5:
    st.subheader("Detalle de casos del mes")
    tipo_caso = st.radio("Ver", ["Reembolsos", "Disputas", "Ambos"], horizontal=True)

    cols_r = ["id", "Customer Email", "Created date (UTC)", "Refunded date (UTC)", "Amount", "Amount Refunded", "Description"]
    cols_d = ["id", "Customer Email", "Created date (UTC)", "Dispute Date (UTC)", "Disputed Amount", "Fee",
              "Dispute Reason", "Dispute Status Label", "Dispute Evidence Due (UTC)"]

    if tipo_caso == "Reembolsos":
        tabla = refunds_m[cols_r]
    elif tipo_caso == "Disputas":
        tabla = disputes_m[cols_d]
    else:
        tabla = refunds_m[cols_r].merge(disputes_m[cols_d], on=["id", "Customer Email", "Created date (UTC)"], how="outer")

    st.dataframe(tabla, use_container_width=True, hide_index=True)

    buf = io.StringIO()
    tabla.to_csv(buf, index=False)
    st.download_button("⬇️ Descargar CSV de este detalle", buf.getvalue(),
                        file_name=f"detalle_{tipo_caso.lower()}_{mes_sel}.csv", mime="text/csv")
