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

# ===================== TAB 6: RESCATE POR AGENTE (HubSpot API en vivo) =====================
with tab6:
    st.subheader("👤 Reembolsos salvados por agente")
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
            meses = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
                     7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
            month = st.selectbox("Mes", list(meses.keys()), format_func=lambda m: meses[m],
                                 index=min(hoy.month - 1, 11))
        with cC:
            st.write("")
            st.write("")
            actualizar = st.button("🔄 Actualizar datos", use_container_width=True)

        try:
            with st.spinner("Consultando HubSpot..."):
                df_ag, resoluciones = hs_construir_tabla_agentes(token, year, month)

            if df_ag.empty:
                st.info(f"No hay tickets de rescate cerrados en {meses[month]} {year}.")
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
                st.markdown("**💰 Cálculo de comisión por agente**")
                pct = st.number_input("% de comisión sobre monto salvado", min_value=0.0, max_value=100.0,
                                      value=5.0, step=0.5, format="%.1f")
                df_ag["Comisión USD"] = (df_ag["Monto salvado"] * pct / 100).round(2)

                fig_ag = go.Figure()
                fig_ag.add_bar(x=df_ag["Agente"], y=df_ag["Asignados"], name="Asignados", marker_color=BLUE)
                fig_ag.add_bar(x=df_ag["Agente"], y=df_ag["Salvados"], name="Salvados", marker_color=TEAL)
                fig_ag.update_layout(barmode="group", height=400, xaxis_title="", yaxis_title="Tickets", legend_title="")
                st.plotly_chart(fig_ag, use_container_width=True)

                tabla = df_ag.copy()
                tabla["Tasa %"] = tabla["Tasa %"].astype(str) + "%"
                tabla["Monto salvado"] = tabla["Monto salvado"].apply(lambda x: f"${x:,.2f}")
                tabla["Comisión USD"] = tabla["Comisión USD"].apply(lambda x: f"${x:,.2f}")
                st.dataframe(tabla[["Agente", "Asignados", "Salvados", "Tasa %", "Monto salvado", "Comisión USD"]],
                             use_container_width=True, hide_index=True)

                # Exportar para nómina
                import io as _io
                buf = _io.StringIO()
                df_ag[["Agente", "Asignados", "Salvados", "Monto salvado", "Comisión USD"]].to_csv(buf, index=False)
                st.download_button(f"⬇️ Descargar comisiones {meses[month]} {year} (CSV)", buf.getvalue(),
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
