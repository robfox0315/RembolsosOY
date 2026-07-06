"""
Dashboard Ejecutivo — Reembolsos, Disputas y Rescate por Agente
Opción Yo | NOVA para Roberto Ortega — sesión con Angela Osorio
Los cuadros validados se muestran SIEMPRE al abrir (datos fijos, no requieren upload).
Los graficos de tendencia son opcionales: se activan si subes los CSV.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Opcion Yo | Reembolsos & Rescate", layout="wide", page_icon="🧭")

TEAL, BLUE, RED, GREEN, AMBER = "#16B6C2", "#2F80ED", "#E74C3C", "#27AE60", "#F2994A"
st.markdown(f"""<style>
[data-testid="stMetricValue"] {{ color: {BLUE}; font-weight: 700; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
</style>""", unsafe_allow_html=True)

st.title("🧭 Reembolsos, Disputas y Rescate por Agente")
st.caption("Datos validados al 05-jul-2026 · Stripe (unified_payments) + HubSpot API (FID- Rescate de reembolsos)")

# ==================================================================
# DATOS FIJOS VALIDADOS — se muestran siempre, sin necesidad de subir nada
# ==================================================================
AGENTES = pd.DataFrame([
    ("Laura Pereira", 29, 13),
    ("Alonso Palacios", 24, 1),
    ("Diana Blanco", 17, 2),
    ("Glina Cardenas", 7, 1),
    ("Laura Ospina", 4, 2),
    ("Carolina Neira", 3, 2),
    ("Carlos D. Jimenez", 2, 2),
    ("Giselle Villegas", 2, 1),
    ("Ivanna Ortiz", 2, 0),
    ("Sin asignar", 6, 0),
], columns=["Agente", "Asignados", "Salvados"])
AGENTES["Tasa %"] = (AGENTES["Salvados"] / AGENTES["Asignados"] * 100).round(1)

tab1, tab2, tab3 = st.tabs([
    "📊 Resumen para Angela", "👤 Rescate por agente (mayo)", "📈 Tendencias (opcional)"
])

# ===================== TAB 1: RESUMEN =====================
with tab1:
    st.subheader("Cifras clave — listas para leer en vivo")

    st.markdown("### 💰 Junio 2026 — Reembolsos y disputas (Stripe, validado al centavo)")
    k1, k2, k3 = st.columns(3)
    k1.metric("Reembolsos", "93 casos", "$11,805.94")
    k2.metric("Disputas (con fee)", "38 casos", "$6,566.00")
    k3.metric("Total en riesgo", "$18,371.94")
    st.caption("Disputas incluyen fee de Stripe de $15 por caso. Reembolsos y disputas asignados al mes en que ocurrieron.")

    st.divider()

    st.markdown("### 🛟 Mayo 2026 — Reembolsos salvados (HubSpot)")
    s1, s2, s3 = st.columns(3)
    s1.metric("Tickets cerrados", "96")
    s2.metric("Salvados", "24")
    s3.metric("Tasa de rescate", "25%")
    st.caption("Salvado = 'Reembolso rechazado' (14) + 'Resuelto exitoso' (10). Definicion confirmada por Iva.")

    st.divider()

    st.markdown("### 🗣️ 3 puntos para la sesion")
    st.markdown("""
1. **Monto en riesgo casi se duplico** entre enero ($8.8k) y mayo ($19.3k). Junio parece bajar pero es dato incompleto — las disputas se abren semanas despues del cargo. **No reportar junio como mejora todavia.**
2. **Rescate de reembolsos**: 24 de 96 tickets salvados en mayo (25%), liderado por Laura Pereira (13 salvados, 44.8% de tasa).
3. **Hallazgo operativo**: ~43% de los tickets cierran fuera de SLA historico. Mayo tuvo un salto a ~97% de cumplimiento — vale la pena entender que cambio y replicarlo.
""")

# ===================== TAB 2: RESCATE POR AGENTE =====================
with tab2:
    st.subheader("👤 Reembolsos salvados por agente — Mayo 2026")
    st.caption("Fuente: HubSpot API, categoria FID- Rescate de reembolsos, cerrados en mayo. "
               "Salvado = Rechazado + Resuelto exitoso (definicion oficial confirmada).")

    total_asig = int(AGENTES["Asignados"].sum())
    total_salv = int(AGENTES["Salvados"].sum())
    m1, m2, m3 = st.columns(3)
    m1.metric("Total asignados", total_asig)
    m2.metric("Total salvados", total_salv)
    m3.metric("Tasa global", f"{total_salv/total_asig*100:.0f}%")

    orden = AGENTES.sort_values("Salvados", ascending=False)
    fig = go.Figure()
    fig.add_bar(x=orden["Agente"], y=orden["Asignados"], name="Asignados", marker_color=BLUE)
    fig.add_bar(x=orden["Agente"], y=orden["Salvados"], name="Salvados", marker_color=TEAL)
    fig.update_layout(barmode="group", height=400, xaxis_title="", yaxis_title="Tickets", legend_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Asignado vs. salvado vs. tasa**")
    tabla = orden.copy()
    tabla["Tasa %"] = tabla["Tasa %"].astype(str) + "%"
    st.dataframe(tabla, use_container_width=True, hide_index=True)

    st.info("⚠️ Para leer con cuidado: Laura Pereira es la unica con volumen alto y tasa alta "
            "(29 asignados, 44.8%) — el dato mas solido. Carolina Neira y Carlos Jimenez muestran 66-100% "
            "pero con solo 2-3 casos: muestra insuficiente, un caso mueve el % 33-50 puntos. "
            "No presentarlos como 'el mejor agente' sin ese contexto.")

# ===================== TAB 3: TENDENCIAS OPCIONALES =====================
with tab3:
    st.subheader("📈 Tendencia mensual (requiere subir CSV)")
    st.caption("Esta pestana es opcional. Los cuadros de las otras pestanas ya funcionan sin subir nada.")

    f_stripe = st.file_uploader("CSV de Stripe (unified_payments)", type="csv", key="stripe")

    if not f_stripe:
        st.info("Sube el CSV de Stripe para ver la tendencia mes a mes de reembolsos y disputas.")
    else:
        pay = pd.read_csv(f_stripe)
        for c in ["Refunded date (UTC)", "Dispute Date (UTC)"]:
            pay[c] = pd.to_datetime(pay[c], errors="coerce")
        for c in ["Amount Refunded", "Fee", "Disputed Amount"]:
            pay[c] = pd.to_numeric(pay[c], errors="coerce").fillna(0)
        pay["mes_refund"] = pay["Refunded date (UTC)"].dt.to_period("M")
        pay["mes_dispute"] = pay["Dispute Date (UTC)"].dt.to_period("M")

        r = pay[pay["Amount Refunded"] > 0].groupby("mes_refund").agg(monto=("Amount Refunded", "sum"))
        d = pay[pay["Dispute Status"].notna()].groupby("mes_dispute").agg(monto=("Disputed Amount", "sum"), fee=("Fee", "sum"))
        d["total"] = d["monto"] + d["fee"]

        resumen = pd.DataFrame({
            "Reembolsos ($)": r["monto"], "Disputas + fee ($)": d["total"]
        }).fillna(0)
        resumen["Total en riesgo ($)"] = resumen["Reembolsos ($)"] + resumen["Disputas + fee ($)"]
        resumen.index = resumen.index.astype(str)

        fig = go.Figure()
        fig.add_bar(x=resumen.index, y=resumen["Reembolsos ($)"], name="Reembolsos", marker_color=TEAL)
        fig.add_bar(x=resumen.index, y=resumen["Disputas + fee ($)"], name="Disputas + fee", marker_color=RED)
        fig.update_layout(barmode="stack", height=400, yaxis_title="USD", legend_title="")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(resumen.style.format({c: "${:,.2f}" for c in resumen.columns}), use_container_width=True)
        st.caption("⚠️ El ultimo mes casi siempre se ve mas bajo — las disputas llegan tarde. No reportar como mejora.")
