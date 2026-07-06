"""
Dashboard de Reembolsos y Disputas — Opción Yo
Fuente: exportación unified_payments (Stripe)
Autor: NOVA para Roberto Ortega
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Opción Yo | Reembolsos & Disputas", layout="wide", page_icon="💳")

TEAL = "#16B6C2"
BLUE = "#2F80ED"
RED = "#E74C3C"
GREY = "#8A94A6"
GREEN = "#27AE60"
AMBER = "#F2994A"

st.markdown(f"""
<style>
[data-testid="stMetricValue"] {{ color: {BLUE}; font-weight: 700; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
h1, h2, h3 {{ color: #1a1a2e; }}
</style>
""", unsafe_allow_html=True)

DATE_COLS = ["Created date (UTC)", "Refunded date (UTC)", "Dispute Date (UTC)", "Dispute Evidence Due (UTC)"]
NUM_COLS = ["Amount", "Amount Refunded", "Fee", "Disputed Amount"]

DISPUTE_STATUS_LABELS = {
    "won": "Ganada", "lost": "Perdida",
    "under_review": "En revisión", "needs_response": "Necesita respuesta"
}

# ------------------------------------------------------------------
# CARGA ACUMULATIVA DE ARCHIVOS (dedup por id)
# ------------------------------------------------------------------
st.title("💳 Reembolsos y Disputas — Opción Yo")
st.caption("Fuente: exportación de pagos (Stripe/unified_payments). Sube uno o varios CSV — se acumulan sin duplicar.")

if "payments_df" not in st.session_state:
    st.session_state.payments_df = pd.DataFrame()

uploaded = st.file_uploader("Cargar CSV de pagos", type="csv", accept_multiple_files=True)

if uploaded:
    frames = [st.session_state.payments_df] if not st.session_state.payments_df.empty else []
    for f in uploaded:
        frames.append(pd.read_csv(f))
    combined = pd.concat(frames, ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset="id", keep="last")
    st.session_state.payments_df = combined
    dupes = before - len(combined)
    if dupes:
        st.toast(f"{dupes} filas duplicadas por 'id' fueron ignoradas.")

df = st.session_state.payments_df.copy()

if df.empty:
    st.info("Carga el archivo unified_payments.csv para comenzar.")
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
    mes_sel = st.selectbox("Mes de análisis", all_months, index=0)
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
tab1, tab2, tab3, tab6, tab4, tab5 = st.tabs([
    "📊 Resumen Ejecutivo", "💸 Reembolsos", "⚠️ Disputas", "👤 Rescate por agente", "🚨 Pendientes urgentes", "📋 Detalle de casos"
])

# ===================== TAB 6: RESCATE POR AGENTE (datos HubSpot, mayo 2026) =====================
with tab6:
    st.subheader("👤 Reembolsos salvados por agente — Mayo 2026")
    st.caption("Fuente: HubSpot API, categoría FID- Rescate de reembolsos, cerrados en mayo 2026. "
               "Salvado = 'Reembolso rechazado' + 'Resuelto exitoso' (definición confirmada por Iva).")

    AGENTES = pd.DataFrame([
        ("Laura Pereira", 29, 13), ("Alonso Palacios", 24, 1), ("Diana Blanco", 17, 2),
        ("Glina Cárdenas", 7, 1), ("Laura Ospina", 4, 2), ("Carolina Neira", 3, 2),
        ("Carlos D. Jiménez", 2, 2), ("Giselle Villegas", 2, 1), ("Ivanna Ortiz", 2, 0),
        ("Sin asignar", 6, 0),
    ], columns=["Agente", "Asignados", "Salvados"])
    AGENTES["Tasa %"] = (AGENTES["Salvados"] / AGENTES["Asignados"] * 100).round(1)
    AGENTES = AGENTES.sort_values("Salvados", ascending=False)

    ta, tb, tc = st.columns(3)
    ta.metric("Tickets cerrados", int(AGENTES["Asignados"].sum()))
    tb.metric("Reembolsos salvados", int(AGENTES["Salvados"].sum()))
    tc.metric("Tasa de rescate global", f"{AGENTES['Salvados'].sum()/AGENTES['Asignados'].sum()*100:.0f}%")

    fig_ag = go.Figure()
    fig_ag.add_bar(x=AGENTES["Agente"], y=AGENTES["Asignados"], name="Asignados", marker_color=BLUE)
    fig_ag.add_bar(x=AGENTES["Agente"], y=AGENTES["Salvados"], name="Salvados", marker_color=TEAL)
    fig_ag.update_layout(barmode="group", height=400, xaxis_title="", yaxis_title="Tickets", legend_title="")
    st.plotly_chart(fig_ag, use_container_width=True)

    tabla_ag = AGENTES.copy()
    tabla_ag["Tasa %"] = tabla_ag["Tasa %"].astype(str) + "%"
    st.dataframe(tabla_ag, use_container_width=True, hide_index=True)

    st.info("⚠️ Laura Pereira es la única con volumen alto y tasa alta (29 asignados, 44.8%) — el dato más sólido. "
            "Carolina Neira y Carlos Jiménez muestran 66-100% pero con solo 2-3 casos: muestra insuficiente, "
            "un caso mueve el % 33-50 puntos. No presentar como 'el mejor agente' sin ese contexto.")
    st.caption("Datos fijos de mayo (vía API). Se harán dinámicos cuando el export de HubSpot incluya la columna Ticket owner.")

# ===================== TAB 1: RESUMEN =====================
with tab1:
    st.subheader(f"Resumen — {period.strftime('%B %Y').capitalize()}")

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
        fig.update_layout(height=320, margin=dict(t=20, b=20), showlegend=False)
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
        fig.update_layout(height=320, margin=dict(t=20, b=20), showlegend=False)
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
        fig.update_layout(height=350, margin=dict(t=20, b=20), legend_title="")
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
    fig.update_layout(height=350, margin=dict(t=20, b=20), xaxis_title="", yaxis_title="Monto USD ($)")
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
        fig.update_layout(height=350, margin=dict(t=20, b=20), xaxis_title="", yaxis_title="Casos")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Fuente: `Dispute Reason`.")
    with cc2:
        st.markdown("**Por estado**")
        status_colors = {"Ganada": GREEN, "Perdida": RED, "En revisión": AMBER, "Necesita respuesta": AMBER}
        estado = disputes_m.groupby("Dispute Status Label").agg(casos=("id", "count"), monto=("Disputed Amount", "sum")).reset_index()
        fig = px.pie(estado, names="Dispute Status Label", values="casos",
                      color="Dispute Status Label", color_discrete_map=status_colors, hole=0.45)
        fig.update_layout(height=350, margin=dict(t=20, b=20))
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

# ===================== TAB 4: PENDIENTES URGENTES =====================
with tab4:
    st.subheader("🚨 Disputas que requieren acción de nuestro lado")
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
    st.subheader("🕒 Esperando resolución del banco emisor")
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
