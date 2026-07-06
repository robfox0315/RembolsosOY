"""
Dashboard Ejecutivo — Auditoría Reembolsos & Disputas
Opción Yo | Preparado por NOVA para Roberto Ortega — sesión con Angela Osorio
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Opción Yo | Auditoría Reembolsos", layout="wide", page_icon="🧭")

TEAL, BLUE, RED, GREEN, AMBER, GREY = "#16B6C2", "#2F80ED", "#E74C3C", "#27AE60", "#F2994A", "#8A94A6"

st.markdown(f"""<style>
[data-testid="stMetricValue"] {{ color: {BLUE}; font-weight: 700; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
</style>""", unsafe_allow_html=True)

st.title("🧭 Auditoría Ejecutiva — Reembolsos & Disputas")
st.caption("Cruce Stripe (pagos reales) × HubSpot (proceso operativo). Preparado para sesión con Angela Osorio.")

# ------------------------------------------------------------------
# CARGA DE ARCHIVOS
# ------------------------------------------------------------------
c1, c2 = st.columns(2)
with c1:
    f_stripe = st.file_uploader("CSV de Stripe (unified_payments)", type="csv", key="stripe")
with c2:
    f_hs = st.file_uploader("CSV de tickets HubSpot (export reembolsos)", type="csv", key="hs")

if not f_stripe or not f_hs:
    st.info("Sube ambos archivos para generar el análisis completo.")
    st.stop()

pay = pd.read_csv(f_stripe)
hs = pd.read_csv(f_hs)

for c in ["Created date (UTC)", "Refunded date (UTC)", "Dispute Date (UTC)"]:
    pay[c] = pd.to_datetime(pay[c], errors="coerce")
for c in ["Amount", "Amount Refunded", "Fee", "Disputed Amount"]:
    pay[c] = pd.to_numeric(pay[c], errors="coerce").fillna(0)
hs["Fecha de cierre"] = pd.to_datetime(hs["Fecha de cierre"], errors="coerce")
hs["Fecha de creación"] = pd.to_datetime(hs["Fecha de creación"], errors="coerce")

pay["mes_refund"] = pay["Refunded date (UTC)"].dt.to_period("M")
pay["mes_dispute"] = pay["Dispute Date (UTC)"].dt.to_period("M")
hs["mes_cierre"] = hs["Fecha de cierre"].dt.to_period("M")

def to_days(t):
    try:
        h, m, s = str(t).split(":")
        return (int(h) + int(m) / 60 + int(s) / 3600) / 24
    except Exception:
        return None
hs["dias_cierre"] = hs["Tiempo entre la creación y el cierre (HH:mm:ss)"].apply(to_days)

tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "⚠️ Hallazgos de calidad de dato", "💰 Tendencia financiera", "⏱️ SLA operativo",
    "👤 Salvados por agente (mayo)", "📋 Resumen para Angela"
])

# ===================== TAB 0: HALLAZGOS =====================
with tab0:
    st.subheader("Hallazgos críticos — leer antes de presentar cualquier número")

    solo_con_evento = ((pay["Amount Refunded"] > 0) | (pay["Dispute Status"].notna())).mean()
    if solo_con_evento > 0.95:
        st.error(
            "**Hallazgo #1 — El CSV de Stripe está pre-filtrado.** "
            f"El {solo_con_evento*100:.0f}% de las filas ya tiene reembolso o disputa. "
            "Esto **no es la tasa real de reembolso de la empresa** — es 100% por construcción del export. "
            "No presentar '% de pagos reembolsados' con este archivo sin el universo completo de pagos."
        )

    cat_por_mes = hs.groupby(["mes_cierre", "Categoría"]).size().unstack(fill_value=0)
    if "ADMIN- Reembolso" in cat_por_mes.columns:
        serie = cat_por_mes["ADMIN- Reembolso"]
        if len(serie) >= 4 and serie.iloc[-3:].sum() < serie.iloc[:3].sum() * 0.3:
            st.warning(
                "**Hallazgo #2 — Migración de categoría no documentada en HubSpot.** "
                "La categoría `ADMIN- Reembolso` cae drásticamente a mitad de periodo. "
                "Probable migración a `FID- Rescate de reembolsos` sin registro formal. "
                "**No comparar categorías entre meses antes/después de la caída sin confirmar con Iva.**"
            )

    fid_total = (hs["Categoría"] == "FID- Rescate de reembolsos").sum()
    if fid_total < 5:
        st.warning(
            f"**Hallazgo #3 — Este export de HubSpot no captura bien `FID- Rescate de reembolsos`** "
            f"(solo {fid_total} tickets en este archivo). Para esa categoría, la fuente correcta es consulta directa "
            "a la API de HubSpot, no este CSV — el saved view usado para exportar excluye ese pipeline."
        )

    st.caption("Estos hallazgos se recalculan automáticamente cada vez que subes un nuevo par de archivos.")

# ===================== TAB 1: TENDENCIA FINANCIERA =====================
with tab1:
    st.subheader("Reembolsos y disputas por mes (dataset filtrado de Stripe)")
    st.caption("⚠️ Corresponde solo a pagos con reembolso/disputa (ver Hallazgo #1) — útil para tendencia, no para tasa global.")

    r = pay[pay["Amount Refunded"] > 0].groupby("mes_refund").agg(casos=("id", "count"), monto=("Amount Refunded", "sum"))
    d = pay[pay["Dispute Status"].notna()].groupby("mes_dispute").agg(casos=("id", "count"), monto=("Disputed Amount", "sum"), fee=("Fee", "sum"))
    d["total"] = d["monto"] + d["fee"]

    resumen = pd.DataFrame({
        "Reembolsos (casos)": r["casos"], "Reembolsos ($)": r["monto"],
        "Disputas (casos)": d["casos"], "Disputas + fee ($)": d["total"]
    }).fillna(0)
    resumen["Total en riesgo ($)"] = resumen["Reembolsos ($)"] + resumen["Disputas + fee ($)"]
    resumen.index = resumen.index.astype(str)

    fig = go.Figure()
    fig.add_bar(x=resumen.index, y=resumen["Reembolsos ($)"], name="Reembolsos", marker_color=TEAL)
    fig.add_bar(x=resumen.index, y=resumen["Disputas + fee ($)"], name="Disputas + fee", marker_color=RED)
    fig.update_layout(barmode="stack", height=400, yaxis_title="USD", legend_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(resumen.style.format({c: "${:,.2f}" for c in resumen.columns if "$" in c}), use_container_width=True)

    ultimo_mes = resumen.index[-1]
    st.caption(f"⚠️ El último mes ({ultimo_mes}) casi siempre se ve más bajo de lo real — las disputas pueden abrirse "
               "semanas después del cargo original. No reportar como 'mejora' hasta el siguiente corte.")

# ===================== TAB 2: SLA OPERATIVO =====================
with tab2:
    st.subheader("Cumplimiento de SLA — tickets de reembolso/disputa")

    sla = hs[hs["Estado de ANS de tiempo hasta cierre"].isin(["ANS completado a tiempo", "ANS completado tarde"])].copy()
    sla["a_tiempo"] = sla["Estado de ANS de tiempo hasta cierre"] == "ANS completado a tiempo"
    trend = sla.groupby("mes_cierre").agg(total=("a_tiempo", "count"), a_tiempo=("a_tiempo", "sum"), dias_prom=("dias_cierre", "mean"))
    trend["pct_a_tiempo"] = (trend["a_tiempo"] / trend["total"] * 100).round(1)
    trend.index = trend.index.astype(str)

    k1, k2, k3 = st.columns(3)
    k1.metric("% SLA cumplido (histórico)", f"{sla['a_tiempo'].mean()*100:.1f}%")
    k2.metric("Tiempo promedio a cierre", f"{hs['dias_cierre'].mean():.1f} días")
    k3.metric("Mediana días a cierre", f"{hs['dias_cierre'].median():.1f} días")

    fig = px.line(trend.reset_index(), x="mes_cierre", y="pct_a_tiempo", markers=True,
                   color_discrete_sequence=[GREEN])
    fig.add_hline(y=80, line_dash="dash", line_color=AMBER, annotation_text="Meta 80%")
    fig.update_layout(height=350, yaxis_title="% completado a tiempo", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(trend.rename(columns={"total": "Total tickets", "a_tiempo": "A tiempo",
                                         "dias_prom": "Días promedio cierre", "pct_a_tiempo": "% a tiempo"}),
                 use_container_width=True)
    st.caption("Nota: mayo muestra un salto fuerte en cumplimiento — vale la pena identificar qué cambió ese mes y replicarlo.")

# ===================== TAB 3: SALVADOS POR AGENTE =====================
with tab3:
    st.subheader("👤 Reembolsos salvados por agente — Mayo 2026")
    st.caption("Fuente: consulta directa a HubSpot API (categoría `FID- Rescate de reembolsos`), 05-jul-2026. "
               "El CSV de export estándar no incluye el propietario del ticket — pendiente agregar esa columna a futuros exports.")

    st.success("✅ **Definición confirmada (05-jul-2026):** 'salvado' = Rechazado + Resuelto exitoso "
               "(mismos tickets migrados de categoría). Total mayo = **24 de 96** (25%).")

    datos = [
        ("Laura Pereira", 11, 2, 0, 11, 5, 29),
        ("Alonso Palacios", 1, 0, 0, 22, 1, 24),
        ("Diana Blanco", 0, 2, 15, 0, 0, 17),
        ("Glina Cárdenas", 1, 0, 0, 6, 0, 7),
        ("Laura Ospina", 0, 2, 2, 0, 0, 4),
        ("Carolina Neira", 1, 1, 0, 0, 1, 3),
        ("Ivanna Ortiz", 0, 0, 0, 0, 2, 2),
        ("Carlos D. Jiménez", 0, 2, 0, 0, 0, 2),
        ("Giselle Villegas", 0, 1, 0, 0, 1, 2),
        ("Sin asignar", 0, 0, 0, 4, 2, 6),
    ]
    cols = ["Agente", "Rechazado", "Resuelto exitoso", "Sin rescate", "Aprobado", "Duplicado/Won't do", "Total tickets"]
    df_ag = pd.DataFrame(datos, columns=cols)

    definicion = st.radio("Definición de 'salvado'", ["Amplia: Rechazado + Resuelto exitoso (oficial)", "Estricta: solo Rechazado"], horizontal=True)
    if definicion.startswith("Amplia"):
        df_ag["Salvados"] = df_ag["Rechazado"] + df_ag["Resuelto exitoso"]
    else:
        df_ag["Salvados"] = df_ag["Rechazado"]

    df_ag = df_ag.sort_values("Salvados", ascending=False)

    total_salvados = int(df_ag["Salvados"].sum())
    total_asignados = int(df_ag["Total tickets"].sum())
    tasa_global = total_salvados / total_asignados * 100 if total_asignados else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Total tickets cerrados (mayo)", total_asignados)
    m2.metric("Reembolsos salvados", total_salvados)
    m3.metric("Tasa de rescate", f"{tasa_global:.0f}%")
    st.caption("14 'Reembolso rechazado' + 10 'Resuelto exitoso' = 24 salvados sobre 96 tickets.")

    # Tabla por agente con tasa individual
    tabla_ag = df_ag[["Agente", "Total tickets", "Salvados"]].copy()
    tabla_ag = tabla_ag.rename(columns={"Total tickets": "Asignados"})
    tabla_ag["Tasa"] = (tabla_ag["Salvados"] / tabla_ag["Asignados"] * 100).round(1).astype(str) + "%"
    tabla_ag.loc[tabla_ag["Asignados"] == 0, "Tasa"] = "—"

    fig = px.bar(df_ag, x="Agente", y="Salvados", text="Salvados", color_discrete_sequence=[TEAL])
    fig.update_traces(textposition="outside")
    fig.update_layout(height=380, xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Asignado vs. salvado por agente**")
    st.dataframe(tabla_ag, use_container_width=True, hide_index=True)

    st.info("⚠️ **Para leer con cuidado:** Laura Pereira es la única con volumen alto **y** tasa alta "
            "(29 asignados, 44.8%) — el dato más sólido. Carolina Neira y Carlos Jiménez muestran 66-100% "
            "pero con n=2-3: muestra insuficiente, un solo caso mueve el % 33-50 puntos. No presentarlos como "
            "'el mejor agente' sin ese contexto.")

    with st.expander("Ver desglose completo por resolución"):
        st.dataframe(df_ag[cols + ["Salvados"]], use_container_width=True, hide_index=True)

# ===================== TAB 4: RESUMEN PARA ANGELA =====================
with tab4:
    st.subheader("📋 Resumen ejecutivo — 30 segundos")

    total_r = pay[pay["Amount Refunded"] > 0]["Amount Refunded"].sum()
    total_d = pay[pay["Dispute Status"].notna()]["Disputed Amount"].sum() + pay[pay["Dispute Status"].notna()]["Fee"].sum()
    sla_pct = sla["a_tiempo"].mean() * 100 if len(sla) else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Total en riesgo (histórico, dataset filtrado)", f"${total_r+total_d:,.0f}")
    k2.metric("% SLA cumplido histórico", f"{sla_pct:.0f}%")
    k3.metric("Tendencia mensual", "↑ ene-may, jun aún incompleto")

    st.markdown("""
**3 puntos para llevar a la sesión:**
1. El SLA de cierre está en **{:.0f}%** de cumplimiento histórico — mejoró fuerte en mayo, vale la pena entender por qué y replicarlo.
2. El monto en riesgo (reembolsos + disputas) **casi se duplicó** entre enero y mayo — junio parece bajar pero es dato incompleto (disputas llegan tarde).
3. El ranking de "salvados por agente" está confirmado: **24 de 96 tickets salvados en mayo (25%)**, liderado por Laura Pereira.
""".format(sla_pct))

    st.divider()
    st.markdown("**📌 Cifras clave para leer en vivo**")
    cA, cB = st.columns(2)
    with cA:
        st.markdown("**Junio — Stripe (validado)**")
        st.table(pd.DataFrame({
            "Métrica": ["Reembolsos", "Disputas (con fee)", "Total en riesgo"],
            "Cifra": ["93 casos · $11,805.94", "38 casos · $6,566.00", "$18,371.94"]
        }))
    with cB:
        st.markdown("**Mayo — Salvados (HubSpot)**")
        st.table(pd.DataFrame({
            "Métrica": ["Tickets cerrados", "Salvados", "Tasa de rescate"],
            "Cifra": ["96", "24 (14 rechazados + 10 resueltos)", "25%"]
        }))
