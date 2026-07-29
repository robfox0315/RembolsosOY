"""
╔══════════════════════════════════════════════════════════════╗
║  DASHBOARD CONVERSACIONES Y PUSHES AUTOMÁTICOS · OPCIÓN YO    ║
║  Para: Angela Osorio (Gerencia)                               ║
║  Alcance: sesiones de WhatsApp + envíos automáticos y su      ║
║  costo estimado. NO incluye incidencias técnicas              ║
║  (dashboard aparte: Incidencias Técnicas).                    ║
║  Stack: Streamlit ≥1.40 · Pandas ≥2.1 · Plotly ≥5.20         ║
║  Ejecutar: python -m streamlit run app.py                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

# ══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Conversaciones y Pushes · Opción Yo",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Detección de tema (claro/oscuro) ────────────────────────────
# Los gráficos de Plotly se renderizan en un iframe aparte y NO heredan el CSS
# de Streamlit, así que necesitamos saber el tema activo para elegir colores de
# texto legibles a mano (si no, el texto oscuro queda invisible en modo oscuro).
try:
    IS_DARK = st.context.theme.type == "dark"
except Exception:
    IS_DARK = False

# ── Paleta corporativa (consistente con dashboards ATC / Refunds / Incidencias) ──
OY_TEAL      = "#16B6C2"
OY_TEAL_DARK = "#0E8E99"
OY_BLUE      = "#2F80ED"
OY_OK        = "#27AE60"
OY_WARN      = "#E5484D"
OY_AMBER     = "#F2A33C"
OY_INK       = "#16323A"
OY_PURPLE    = "#7E57C2"
COLOR_SEQ    = [OY_TEAL, OY_BLUE, OY_AMBER, OY_PURPLE, "#EC4899",
                "#26A69A", "#FF7043", "#42A5F5", "#9CCC65", "#5C6BC0"]

# Colores de texto para gráficos, adaptados al tema activo
OY_CHART_TEXT  = "#E8EEF0" if IS_DARK else OY_INK
OY_CHART_TITLE = "#5FD8E3" if IS_DARK else OY_TEAL_DARK

REGION = {"1": "EE.UU./Canadá", "34": "España", "52": "México", "58": "Venezuela",
          "57": "Colombia", "507": "Panamá", "44": "UK", "56": "Chile",
          "39": "Italia", "49": "Alemania", "61": "Australia", "593": "Ecuador",
          "506": "Costa Rica", "41": "Suiza", "51": "Perú", "33": "Francia",
          "351": "Portugal", "31": "Países Bajos", "54": "Argentina",
          "353": "Irlanda"}

# ── CSS (idéntico lenguaje visual a los otros dashboards de Opción Yo, compatible con modo oscuro) ──
st.markdown("""
<style>
:root{--oy-teal:#16B6C2;--oy-td:#0E8E99;--oy-blue:#2F80ED;
      --oy-ok:#27AE60;--oy-warn:#E5484D;--oy-amb:#F2A33C;--oy-ink:#16323A;}
/* No forzamos fondo — dejamos que Streamlit use su propio tema (claro u oscuro) */
.block-container{padding-top:1.5rem;}
h1,h2,h3{color:var(--oy-teal);}
[data-testid="stMetricValue"]{font-size:1.7rem!important;font-weight:800;}
[data-testid="stMetricLabel"]{font-size:.78rem!important;font-weight:600;opacity:.85;}

.oy-header{display:flex;align-items:center;gap:18px;
  background:linear-gradient(100deg,var(--oy-td) 0%,var(--oy-teal) 48%,#27D0DC 100%);
  padding:20px 28px;border-radius:16px;margin:2px 0 12px;
  box-shadow:0 8px 22px rgba(22,182,194,.28);overflow:visible;}
.oy-logo{font-weight:800;font-size:2rem;color:#fff;line-height:1.2;
  letter-spacing:.4px;white-space:nowrap;padding:2px 18px 2px 0;
  border-right:2px solid rgba(255,255,255,.4);display:flex;align-items:center;}
.oy-logo span{color:#0A4750;margin-left:6px;}
.oy-htxt{display:flex;flex-direction:column;justify-content:center;}
.oy-htitle{color:#fff;font-weight:800;font-size:1.14rem;margin:0;line-height:1.3;}
.oy-hsub{color:#EAFCFE;font-size:.82rem;margin:3px 0 0;line-height:1.2;}

.sec{background:var(--oy-teal);color:#fff;padding:.4rem 1rem;
  border-radius:8px;font-weight:700;margin:.2rem 0 .7rem;
  font-size:.95rem;display:inline-block;}
.sec.red{background:var(--oy-warn);}
.sec.amb{background:var(--oy-amb);}
.sec.ok{background:var(--oy-ok);}
.sec.blue{background:var(--oy-blue);}
.sec.purple{background:#7E57C2;}

.kpi-grid{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px;}
.kpi{flex:1;min-width:130px;background:var(--oy-teal);border-radius:12px;
  padding:11px 13px;color:#fff;box-shadow:0 4px 12px rgba(22,182,194,.20);}
.kpi.alt{background:var(--oy-blue);}
.kpi.ok{background:var(--oy-ok);}
.kpi.warn{background:var(--oy-warn);}
.kpi.amber{background:var(--oy-amb);}
.kpi.dark{background:var(--oy-td);}
.kpi.purple{background:#7E57C2;}
.kpi .l{font-size:.7rem;opacity:.9;font-weight:600;text-transform:uppercase;letter-spacing:.4px;}
.kpi .v{font-size:1.5rem;font-weight:800;margin-top:2px;}
.kpi .d{font-size:.69rem;opacity:.93;margin-top:2px;}

.crit{background:#FDECEA;border-left:5px solid var(--oy-warn);
  padding:.6rem 1rem;border-radius:6px;margin-bottom:.7rem;color:#7a1f1c;}
.alrt{background:#FFF6E6;border-left:5px solid var(--oy-amb);
  padding:.6rem 1rem;border-radius:6px;margin-bottom:.7rem;color:#7a531a;}
.good{background:#EAF7EF;border-left:5px solid var(--oy-ok);
  padding:.6rem 1rem;border-radius:6px;margin-bottom:.7rem;color:#1d6b3a;}
.info{background:#E9F6F8;border-left:5px solid var(--oy-teal);
  padding:.7rem 1rem;border-radius:6px;margin-bottom:.7rem;color:#0E6873;}

.stTabs [data-baseweb="tab-list"]{gap:3px;flex-wrap:wrap;}
.stTabs [data-baseweb="tab"]{background:#F1FAFB;border-radius:8px 8px 0 0;
  padding:5px 10px;font-weight:600;color:var(--oy-td);}
.stTabs [aria-selected="true"]{background:var(--oy-teal)!important;color:#fff!important;}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="oy-header"><div class="oy-logo">opción<span> yo</span></div>'
    '<div class="oy-htxt"><p class="oy-htitle">💬 Conversaciones y Pushes Automáticos</p></div></div>',
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════
#  AUTENTICACIÓN OPCIONAL (mismo patrón que otros dashboards OY)
# ══════════════════════════════════════════════════════════════
def _secret(k):
    try:
        return st.secrets.get(k)
    except Exception:
        return None


def require_auth():
    pw = _secret("app_password")
    if not pw or st.session_state.get("auth_ok"):
        return
    st.markdown('<div class="oy-header"><div class="oy-logo">opción<span> yo</span></div>'
                '<div><p class="oy-htitle">Acceso restringido</p>'
                '<p class="oy-hsub">Introduce la contraseña para continuar</p></div></div>',
                unsafe_allow_html=True)
    with st.form("login"):
        inp = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            if inp == pw:
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
    st.stop()


require_auth()


# ══════════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES
# ══════════════════════════════════════════════════════════════
def kpi(label, value, delta="", kind=""):
    d = f'<div class="d">{delta}</div>' if delta else ""
    return f'<div class="kpi {kind}"><div class="l">{label}</div><div class="v">{value}</div>{d}</div>'


def sfig(fig, h=340):
    layout_kwargs = dict(
        height=h, margin=dict(t=46, b=10, l=10, r=10),
        font=dict(color=OY_CHART_TEXT, family="Segoe UI,sans-serif"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color=OY_CHART_TEXT)),
    )
    # Solo tocamos el título si el gráfico realmente tiene uno — si no, Plotly
    # renderiza literalmente el texto "undefined" al setear title_font sin title.text.
    titulo_actual = fig.layout.title.text if fig.layout.title else None
    if titulo_actual:
        layout_kwargs["title"] = dict(text=titulo_actual, font=dict(color=OY_CHART_TITLE, size=14))
    fig.update_layout(**layout_kwargs)
    fig.update_xaxes(color=OY_CHART_TEXT, gridcolor="rgba(128,128,128,.25)")
    fig.update_yaxes(color=OY_CHART_TEXT, gridcolor="rgba(128,128,128,.25)")
    return fig


def safe_pct(n, d):
    return round(float(n) / float(d) * 100, 1) if d else 0.0


def fmt_usd(v):
    return f"${v:,.2f}"


def boton_descarga(df, nombre_archivo, key, label="⬇️ Descargar esta tabla (.csv)"):
    """Botón de descarga CSV reutilizable — mismo patrón que el dashboard ATC."""
    st.download_button(label, df.to_csv(index=False).encode("utf-8-sig"),
                        file_name=nombre_archivo, mime="text/csv", key=key)


def _norm_txt(s):
    """Normaliza texto para comparar nombres de campañas sin que tildes/mayúsculas generen falsos 'sin match'."""
    import unicodedata
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s


def find_data_file(name: str):
    """Busca el archivo tanto en data/ como en la raíz del repo (tolerante a estructura)."""
    candidates = [
        os.path.join("data", name),
        name,
        os.path.join(os.path.dirname(__file__), "data", name),
        os.path.join(os.path.dirname(__file__), name),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


# ══════════════════════════════════════════════════════════════
#  DATA WAREHOUSE DE TREBLE (ClickHouse, client_analytics) · EN VIVO
#  Esquema verificado contra la documentación oficial de Treble
#  (help.treble.ai/es/docs/data-warehouse) — nada de esto es adivinado.
#  Tablas usadas: fact_deployment_daily, fact_sessions, dim_hsm.
# ══════════════════════════════════════════════════════════════
def _dwh_client():
    """Sin caché de conexión a propósito: el puente externo (que nunca falla) crea una
    conexión nueva en cada consulta — replicamos exactamente esa arquitectura acá para
    eliminar cualquier posibilidad de reutilizar una conexión que quedó en mal estado."""
    try:
        cfg = st.secrets["treble_dwh"]
    except Exception:
        return None, "No se encontró el bloque [treble_dwh] en Secrets — revisa que esté guardado tal cual."
    try:
        import clickhouse_connect
    except Exception as e:
        return None, f"La librería clickhouse-connect no está instalada en el servidor: {e}. Revisa requirements.txt."
    try:
        cliente = clickhouse_connect.get_client(
            host=cfg["host"], port=int(cfg.get("port", 8443)),
            username=cfg["username"], password=cfg["password"],
            database=cfg.get("database", "client_analytics"),
            secure=True, connect_timeout=10,
        )
        return cliente, None
    except Exception as e:
        return None, f"No se pudo crear el cliente: {str(e)[:200]}"


@st.cache_data(ttl=600, show_spinner=False)
def dwh_status():
    """Prueba la conexión y devuelve (ok, mensaje, lista_de_tablas)."""
    client, error = _dwh_client()
    if client is None:
        return False, error, []
    try:
        client.query("SELECT 1")
        tablas = [r[0] for r in client.query("SHOW TABLES").result_rows]
        return True, "Conexión al Data Warehouse de Treble activa.", tablas
    except Exception as e:
        return False, f"No se pudo conectar: {str(e)[:200]}", []


@st.cache_data(ttl=300, show_spinner=False)
def dwh_query(sql: str):
    """Ejecuta una consulta SQL contra el DWH y devuelve un DataFrame, o None si falla."""
    client, _ = _dwh_client()
    if client is None:
        return None
    try:
        return client.query_df(sql)
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner="⏳ Consultando Data Warehouse (pushes)…")
def dwh_general_report(dias=210):
    """Reconstruye el equivalente al Reporte general de pushes desde fact_deployment_daily.
    Excluye filas con poll_name vacío — sin nombre no podemos identificar qué campaña es,
    y mezclarlas todas bajo un nombre en blanco ensuciaría el reporte. Ver panel de
    Diagnóstico DWH para saber cuánto volumen queda afuera por este motivo."""
    sql = f"""
        SELECT
            day AS date,
            poll_name AS name,
            sum(sent) AS successful,
            sum(delivered) AS delivered,
            round(sum(responded) * 1.0 / nullIf(sum(sent), 0), 4) AS response_rate
        FROM client_analytics.fact_deployment_daily
        WHERE day >= today() - {int(dias)}
          AND poll_name != '' AND poll_name IS NOT NULL
        GROUP BY day, poll_name
        ORDER BY day
    """
    df = dwh_query(sql)
    if df is None or df.empty:
        return None
    df["date"] = pd.to_datetime(df["date"])
    df["name_clean"] = df["name"].astype(str).str.strip()
    return df


@st.cache_data(ttl=300, show_spinner="⏳ Consultando Data Warehouse (sesiones)…")
def dwh_sessions(dias=32):
    """Reconstruye el equivalente al reporte de sesiones desde fact_sessions."""
    sql = f"""
        SELECT
            session_id, created_at AS session_started_timestamp,
            finished_at AS session_finished_timestamp,
            inbound_outbound AS session_type, status AS session_status,
            country_code AS user_country_code, poll_id, poll_name
        FROM client_analytics.fact_sessions
        WHERE created_at >= now() - INTERVAL {int(dias)} DAY
    """
    df = dwh_query(sql)
    if df is None or df.empty:
        return None
    for c in ["session_started_timestamp", "session_finished_timestamp"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    # whatsapp_link_campaign_name en el CSV era el link de tracking de la campaña saliente.
    # fact_sessions no tiene ese campo exacto — usamos poll_name (el flujo/plantilla que
    # disparó la sesión), que es lo más cercano y real disponible. NO usamos channel_cellphone
    # (eso es solo el número de teléfono del canal, etiquetarlo como "campaña" sería incorrecto).
    df["whatsapp_link_campaign_name"] = df["poll_name"]
    # Campos que el CSV traía y fact_sessions no tiene — se dejan vacíos, no inventados
    df["first_message_timestamp"] = pd.NaT
    df["last_message_timestamp"] = pd.NaT
    return df


@st.cache_data(ttl=300, show_spinner="⏳ Consultando tasa de respuesta real…")
def dwh_respuesta_push(poll_name: str, dias: int = 180):
    """Tasa de entrega/respuesta real y granular para un push específico, desde fact_deployment_status
    (una fila por intento de envío individual — el dato más preciso que existe)."""
    nombre_esc = poll_name.replace("'", "''")
    sql = f"""
        SELECT
            count() AS enviados,
            countIf(timestamp_delivered > '2000-01-01') AS entregados,
            countIf(timestamp_responded > '2000-01-01') AS respondidos
        FROM client_analytics.fact_deployment_status
        WHERE trim(poll_name) = '{nombre_esc}' AND timestamps_eta >= now() - INTERVAL {int(dias)} DAY
    """
    return dwh_query(sql)


@st.cache_data(ttl=300, show_spinner="⏳ Consultando qué responden los usuarios…")
def dwh_respuestas_hsm(poll_name: str, dias: int = 180):
    """Qué contestan los usuarios (botones/texto) dentro del flujo de un push específico,
    desglosado por hsm_name (para poder ver 'primer mensaje' vs 'segundo mensaje' por separado).
    fact_hsm_responses se filtra por poll_id, así que primero lo buscamos en fact_sessions.
    OJO: el LIMIT del lookup de poll_id estaba en 20 y cortaba instancias reales — se subió
    a 2000 para no perder datos (era la causa de que la Sección 2 no cuadrara con la 1)."""
    nombre_esc = poll_name.replace("'", "''")
    sql_ids = f"""
        SELECT DISTINCT poll_id FROM client_analytics.fact_sessions
        WHERE trim(poll_name) = '{nombre_esc}' AND created_at >= now() - INTERVAL {int(dias)} DAY
        LIMIT 2000
    """
    ids_df = dwh_query(sql_ids)
    if ids_df is None or ids_df.empty:
        return None, None
    ids = ",".join(str(int(i)) for i in ids_df["poll_id"])
    sql = f"""
        SELECT hsm_name, answer_text, count() AS respuestas
        FROM client_analytics.fact_hsm_responses
        WHERE poll_id IN ({ids}) AND response_date >= now() - INTERVAL {int(dias)} DAY
        GROUP BY hsm_name, answer_text ORDER BY hsm_name, respuestas DESC
    """
    detalle = dwh_query(sql)

    sql_total = f"""
        SELECT count(DISTINCT survey_user_id) AS usuarios_unicos, count() AS respuestas_totales
        FROM client_analytics.fact_hsm_responses
        WHERE poll_id IN ({ids}) AND response_date >= now() - INTERVAL {int(dias)} DAY
    """
    total = dwh_query(sql_total)
    return detalle, total


@st.cache_data(ttl=300, show_spinner="⏳ Consultando dónde termina la conversación…")
def dwh_estado_final_push(poll_name: str, dias: int = 180):
    """En qué estado termina el flujo disparado por este push (HumanHandover, Rating, etc.)."""
    nombre_esc = poll_name.replace("'", "''")
    sql = f"""
        SELECT status, count() AS n
        FROM client_analytics.fact_sessions
        WHERE trim(poll_name) = '{nombre_esc}' AND created_at >= now() - INTERVAL {int(dias)} DAY
        GROUP BY status ORDER BY n DESC
    """
    return dwh_query(sql)


@st.cache_data(ttl=300, show_spinner="⏳ Verificando actividad real en Treble…")
def dwh_actividad_reciente(poll_name: str):
    """¿Este push mandó algo de verdad, y cuándo fue la última vez? La mejor señal disponible
    de si está realmente activo en Treble ahora mismo — el DWH no tiene un flag 'activo/inactivo'
    explícito por poll, así que usamos la fecha del último envío real como proxy."""
    nombre_esc = poll_name.replace("'", "''")
    sql = f"""
        SELECT sum(sent) AS enviados_365d, max(day) AS ultimo_envio, min(day) AS primer_envio
        FROM client_analytics.fact_deployment_daily
        WHERE trim(poll_name) = '{nombre_esc}' AND day >= today() - 365
    """
    return dwh_query(sql)


@st.cache_data(ttl=300, show_spinner="⏳ Consultando motivos de no entrega…")
def dwh_motivos_no_entrega(poll_name: str, dias: int = 180):
    """Desglosa por qué un envío NO llegó, usando las columnas de motivo de falla reales
    de fact_deployment_daily (no inventadas — están documentadas en el esquema del DWH)."""
    nombre_esc = poll_name.replace("'", "''")
    sql = f"""
        SELECT
            sum(sent) AS enviados,
            sum(delivered) AS entregados,
            sum(failure_rate_limit) AS limite_de_tasa,
            sum(revoked) AS revocado,
            sum(invalid_phone) AS telefono_invalido,
            sum(missing_parameter) AS parametro_faltante,
            sum(failure_human_handover) AS fallo_transferencia_agente,
            sum(deactivated_poll_or_hsm) AS plantilla_desactivada,
            sum(failure_general) AS falla_general,
            sum(failure_unable_to_contact) AS no_se_pudo_contactar,
            sum(optout) AS optout_usuario,
            sum(meta_chose_not_deliver) AS meta_no_entrego
        FROM client_analytics.fact_deployment_daily
        WHERE trim(poll_name) = '{nombre_esc}' AND day >= today() - {int(dias)}
    """
    return dwh_query(sql)


@st.cache_data(ttl=300, show_spinner="⏳ Verificando actividad real de todos los pushes en Treble…")
def dwh_actividad_reciente_todos():
    """Última fecha de envío real y volumen, para TODAS las plantillas a la vez —
    una sola consulta en vez de una por fila, para no sobrecargar el DWH ni la app."""
    sql = """
        SELECT poll_name, max(day) AS ultimo_envio, min(day) AS primer_envio, sum(sent) AS enviados_365d
        FROM client_analytics.fact_deployment_daily
        WHERE day >= today() - 365 AND poll_name != '' AND poll_name IS NOT NULL
        GROUP BY poll_name
    """
    return dwh_query(sql)


# ══════════════════════════════════════════════════════════════
#  TARIFAS REALES DE TREBLE (auditadas contra export nativo "Inversión")
#  Fuente: reporte nativo de Treble de Opción Yo (captura jun-2026).
#  Estructura de tramos por volumen mensual de conversaciones, confirmada
#  y validada contra el gasto real reportado (ver pestaña Pushes → Auditoría).
# ══════════════════════════════════════════════════════════════
TREBLE_TRAMOS = [
    (0, 5000, 0.20),
    (5000, 10000, 0.18),
    (10000, 20000, 0.15),
    (20000, float("inf"), 0.12),
]

# Detalle real por plantilla, reportado por Treble (export nativo, línea de ATC/soporte —
# NO incluye ninguna campaña de Ventas/Marketing). Ventana: 1–11 jun 2026 aprox.
# Sirve para validar que la tarifa de $0.20/conversación (tramo de menor volumen) es exacta.
TREBLE_REAL_POR_PUSH = {
    # nombre tal como aparece en el catálogo/CSV: (conversaciones reales, inversión real USD)
    "Recordatorio Sesión en 28hs": (1627, 325),
    "Recordatorio 3hs antes": (637, 127),
    "Pago fallido": (224, 45),
    "Especialista esperando": (205, 41),
    "Soporte - Saludo": (158, 32),
    "Push sesión en 72hs": (146, 29),
    "Notificación Mensaje nuevo": (104, 21),
    "Inasistencia con AR": (102, 20),
    "Segunda Sesión - Sí asistió": (96, 19),
    "Tercera sesión sí asistió": (96, 19),
    "Primera sesión sí asistió": (79, 16),
    "Mensaje bienvenida a Opción Yo": (69, 14),
    "Inasistencia sin sesiones futuras": (69, 14),
    "Recordatorio consultoria 30 min antes": (65, 13),
}


def tarifa_por_tramo(volumen: float) -> float:
    """Tarifa por conversación según el tramo de volumen mensual (modelo real de Treble)."""
    for lo, hi, r in TREBLE_TRAMOS:
        if lo < volumen <= hi or (lo == 0 and volumen <= hi):
            return r
    return TREBLE_TRAMOS[-1][2]


# ══════════════════════════════════════════════════════════════
#  CARGA Y LIMPIEZA
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=300, show_spinner="⏳ Cargando reporte de pushes…")
def load_general_report():
    # Preferimos el DWH en vivo. Los dos motivos que antes nos hacían evitarlo ya están
    # resueltos en otras capas: (1) las filas con poll_name vacío se excluyen directo en
    # el SQL de dwh_general_report(), y (2) las campañas de Ventas/Marketing se filtran
    # más abajo con el filtro global ATC-only (_es_campana_atc). Si el DWH falla por
    # cualquier motivo, cae automáticamente al CSV de respaldo.
    df = dwh_general_report()
    fuente = "dwh"
    if df is None:
        fuente = "csv"
        path = find_data_file("general_report.csv")
        if not path:
            st.error("❌ No se encontró data/general_report.csv Y no hay conexión al Data Warehouse. "
                      "Necesito al menos una de las dos fuentes.")
            st.stop()
        try:
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        except Exception as e:
            st.error(f"No se pudo leer general_report.csv: {e}")
            st.stop()
    if "name_clean" not in df.columns:
        df["name_clean"] = (df["name"]
                             .str.replace("Copia de la conversación", "", regex=False)
                             .str.replace(r"\s+id:\d+", "", regex=True)
                             .str.strip())
    df["mes"] = df["date"].dt.to_period("M").apply(lambda p: p.start_time.date())
    df["fecha"] = df["date"].dt.date
    df["semana"] = df["date"].dt.to_period("W").apply(lambda p: p.start_time.date())
    for c in ["name", "name_clean"]:
        df[c] = df[c].astype("category")
    df.attrs["fuente"] = fuente
    return df


@st.cache_data(ttl=300, show_spinner="⏳ Cargando sesiones conversacionales…")
def load_sessions():
    df = dwh_sessions()
    fuente = "dwh"
    if df is None:
        fuente = "csv"
        path = find_data_file("sessions_report.csv")
        if not path:
            st.error("❌ No hay conexión al Data Warehouse Y no se encontró data/sessions_report.csv. "
                      "Necesito al menos una de las dos fuentes.")
            st.stop()
        try:
            df = pd.read_csv(path)
        except Exception as e:
            st.error(f"No se pudo leer sessions_report.csv: {e}")
            st.stop()

    for c in ["session_started_timestamp", "session_finished_timestamp",
              "first_message_timestamp", "last_message_timestamp"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")

    df["fecha"] = df["session_started_timestamp"].dt.date
    df["hora"] = df["session_started_timestamp"].dt.hour
    df["dia_nombre"] = df["session_started_timestamp"].dt.day_name()
    df["pais"] = df["user_country_code"].astype(str).str.replace("+", "", regex=False).map(REGION)
    df["pais"] = df["pais"].fillna("Otro / no identificado")
    df["dur_min"] = ((df["session_finished_timestamp"] - df["session_started_timestamp"])
                      .dt.total_seconds() / 60).clip(lower=0)

    for c in ["session_type", "session_status", "user_country_code", "pais",
              "whatsapp_link_campaign_name", "dia_nombre"]:
        df[c] = df[c].astype("category")
    df.attrs["fuente"] = fuente
    return df


@st.cache_data(ttl=300, show_spinner="⏳ Cargando catálogo de plantillas…")
def load_catalog():
    path = find_data_file("catalog.csv")
    if not path:
        st.error("❌ No se encontró data/catalog.csv. Verifica que el archivo esté en el repositorio.")
        st.stop()
    try:
        df = pd.read_csv(path)
    except Exception as e:
        st.error(f"No se pudo leer catalog.csv: {e}")
        st.stop()
    df["estado"] = df["estado"].fillna("Sin clasificar")

    # Compatibilidad: si el catálogo ya viene "completo" (auditado, con equipo_fuente,
    # nivel_documentacion, envios_historicos, etc.) usamos esas columnas tal cual.
    # Si no, calculamos los campos mínimos para que el dashboard no rompa.
    if "activo" not in df.columns:
        df["activo"] = df["estado"].isin(["Push Activo", "Manual activo", "Inbound"])
    else:
        df["activo"] = df["activo"].astype(str).map({"True": True, "False": False}).fillna(df["activo"])

    if "equipo" not in df.columns:
        df["equipo"] = "Sin asignar"
    df["equipo"] = df["equipo"].fillna("Sin asignar")

    if "tipo" not in df.columns:
        df["tipo"] = "Sin clasificar"
    df["tipo"] = df["tipo"].fillna("Sin clasificar")

    for c in ["equipo_fuente", "nivel_documentacion", "auditoria"]:
        if c not in df.columns:
            df[c] = "—"
    if "nota_interna" not in df.columns:
        df["nota_interna"] = ""
    df["nota_interna"] = df["nota_interna"].fillna("")
    if "en_uso_real" not in df.columns:
        df["en_uso_real"] = False
    else:
        df["en_uso_real"] = df["en_uso_real"].astype(str).map({"True": True, "False": False}).fillna(False)
    for c in ["envios_historicos", "entregados_historicos", "n_envios_batches"]:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    if "tasa_respuesta_hist" not in df.columns:
        df["tasa_respuesta_hist"] = np.nan

    return df


@st.cache_data(ttl=300, show_spinner="⏳ Cargando árbol de conversación…")
def load_arbol():
    path = find_data_file("arbol_conversacion.csv")
    if not path:
        return None  # pestaña opcional: si no está el archivo, la pestaña avisa y no rompe el resto
    try:
        df = pd.read_csv(path)
    except Exception:
        return None

    # Nodo interactivo real: el mismo nodo origen (Poll+Paso+Origen ID) tiene al
    # menos una arista que SÍ avanza (no es fuga) — así distinguimos una fuga real
    # (había opción de responder y no lo hicieron) de un push informativo de una
    # sola vía (donde "no avanzó" es 100% esperado porque no se pedía respuesta).
    grp_key = ["Poll ID", "Paso Origen", "Origen ID"]
    total_nodo = df.groupby(grp_key)["N Clientes"].transform("sum")
    alt_clientes = df[~df["Es Fuga"]].groupby(grp_key)["N Clientes"].sum()
    df = df.set_index(grp_key)
    df["alt_clientes"] = alt_clientes
    df = df.reset_index()
    df["alt_clientes"] = df["alt_clientes"].fillna(0)
    df["alt_share"] = df["alt_clientes"] / total_nodo.values
    df["fuga_real"] = df["Es Fuga"] & (df["alt_share"] >= 0.05)

    # Entrantes por plantilla (volumen del primer paso) — para dar contexto en % y no solo cifras sueltas
    entrantes = df[df["Paso Origen"] == 1].groupby("Plantilla")["N Clientes"].sum()
    df["entrantes_plantilla"] = df["Plantilla"].map(entrantes)
    return df


gr = load_general_report()
sr = load_sessions()
cat = load_catalog()
arbol = load_arbol()

# Filtro global de alcance: nos quedamos solo con campañas que están en el catálogo de
# plantillas ATC. El DWH trae TODAS las líneas de Treble (incluida Ventas/Marketing, que
# no es parte de este dashboard) — se filtra acá, una sola vez, para que Resumen, Pushes,
# Insights y el comparador de períodos ya trabajen limpios sin repetir el filtro en cada pestaña.
_cat_norm_set = [_norm_txt(k) for k in cat["conversacion"]]
def _es_campana_atc(nombre):
    n = _norm_txt(nombre)
    return any(k in n or n in k for k in _cat_norm_set)

_gr_campanas_antes = gr["name_clean"].nunique()
_fuente_gr = gr.attrs.get("fuente", "csv")
gr = gr[gr["name_clean"].apply(_es_campana_atc)].copy()
gr.attrs["fuente"] = _fuente_gr
for c in ["name", "name_clean"]:
    gr[c] = gr[c].astype("category")
_campanas_fuera_alcance = _gr_campanas_antes - gr["name_clean"].nunique()

# Mismo problema en sesiones cuando vienen del DWH: fact_sessions trae TODAS las líneas
# (868,055 filas totales confirmado en diagnóstico), no solo ATC. El CSV manual ya era
# ATC-only por naturaleza (export específico), así que este filtro solo aplica al DWH.
if sr.attrs.get("fuente") == "dwh":
    _sr_antes = len(sr)
    _fuente_sr = sr.attrs.get("fuente", "csv")
    sr = sr[sr["whatsapp_link_campaign_name"].astype(str).apply(_es_campana_atc)].copy()
    sr.attrs["fuente"] = _fuente_sr
    for c in ["session_type", "session_status", "user_country_code", "pais",
              "whatsapp_link_campaign_name", "dia_nombre"]:
        sr[c] = sr[c].astype("category")
    _sesiones_fuera_alcance = _sr_antes - len(sr)
else:
    _sesiones_fuera_alcance = 0

# Estado del Data Warehouse (silencioso — se usa en la pestaña Árbol, no hace falta mostrarlo aquí)
_dwh_ok, _dwh_msg, _dwh_tablas = dwh_status()

# ══════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DEL MODELO DE COSTO (panel plegable, sin sidebar)
# ══════════════════════════════════════════════════════════════
with st.expander("⚙️ Configuración del modelo de costo (tarifa real de Treble, auditada)", expanded=False):
    cc1, cc2 = st.columns(2)
    with cc1:
        st.caption(
            "Treble/WhatsApp cobra por **conversación** de 24h, en tramos según volumen mensual. "
            "Tramos reales de tu cuenta (auditados contra el export nativo 'Inversión' de Treble):\n\n"
            "- 0 – 5,000 conv. → $0.20\n"
            "- 5,001 – 10,000 conv. → $0.18\n"
            "- 10,001 – 20,000 conv. → $0.15\n"
            "- > 20,000 conv. → $0.12"
        )
        modo_costo = st.radio(
            "Fuente de la tarifa",
            ["Tramos reales de Treble (recomendado)", "Tarifa fija manual"],
            index=0,
            help="Los tramos reales se aplican automáticamente según el volumen mensual de cada mes."
        )
        if modo_costo == "Tarifa fija manual":
            tarifa_manual = st.number_input(
                "Tarifa manual por conversación (USD)", min_value=0.0, value=0.12, step=0.01, format="%.3f"
            )
        else:
            tarifa_manual = None
    with cc2:
        modelo_costo = st.radio(
            "¿Qué cuenta como conversación facturable?",
            ["Cada push entregado (conversación abierta)", "Solo cuando el cliente responde"],
            index=0,
            help="WhatsApp Business Platform factura por conversación de 24h iniciada por el negocio "
                 "al entregar la plantilla, independientemente de si el cliente responde."
        )
        st.caption(
            f"📅 Reporte de pushes: {gr['fecha'].min()} → {gr['fecha'].max()}\n\n"
            f"💬 Sesiones conversacionales: {sr['fecha'].min()} → {sr['fecha'].max()}\n\n"
            "**Fuentes:** reporte general Treble/WhatsApp, reporte de sesiones conversacionales, "
            "catálogo interno de plantillas (auditado y completado) y export nativo de Treble "
            "'Inversión' (tarifas reales).\n\n"
            "**Fuera de alcance (a propósito):** incidencias técnicas / HubSpot — dashboard aparte."
        )


# ══════════════════════════════════════════════════════════════
#  CÁLCULO DE COSTO (aplicado a Pushes) · modelo real de tramos de Treble
# ══════════════════════════════════════════════════════════════
# El tramo de tarifa se calcula sobre el volumen TOTAL de la cuenta ese mes
# (todos los pushes juntos), no por campaña individual — así es como Treble
# factura realmente. Se calcula siempre sobre gr completo (no un filtro),
# para que la tarifa de cada mes sea la real, independiente de qué filtre
# cada pestaña por separado.
_tarifa_mensual_real = (
    gr.groupby("mes", observed=True)["delivered"].sum().apply(tarifa_por_tramo).to_dict()
)


def con_costo(df):
    """Agrega columnas de conversaciones facturables y costo estimado a un df de pushes."""
    df = df.copy()
    if modelo_costo.startswith("Cada push"):
        df["conversaciones_facturables"] = df["delivered"]
    else:
        df["conversaciones_facturables"] = (df["delivered"] * df["response_rate"]).round()

    if tarifa_manual is not None:
        df["tarifa_aplicada"] = tarifa_manual
    else:
        df["tarifa_aplicada"] = df["mes"].map(_tarifa_mensual_real).fillna(TREBLE_TRAMOS[0][2])

    df["costo_estimado"] = df["conversaciones_facturables"] * df["tarifa_aplicada"]
    return df


def filtro_fechas(df, col_fecha, key_prefix, label="Rango de fechas"):
    """Widget de rango de fechas reutilizable, para usar dentro de cada pestaña."""
    min_d, max_d = df[col_fecha].min(), df[col_fecha].max()
    rango = st.date_input(label, value=(min_d, max_d), min_value=min_d, max_value=max_d,
                           key=f"{key_prefix}_fecha")
    if isinstance(rango, tuple) and len(rango) == 2:
        ini, fin = rango
    else:
        ini, fin = min_d, max_d
    return df[(df[col_fecha] >= ini) & (df[col_fecha] <= fin)]


# ══════════════════════════════════════════════════════════════
#  TABS
# ══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Resumen Ejecutivo", "📤 Pushes Automáticos & Costo",
    "💬 Conversaciones", "🗂️ Catálogo de Plantillas",
    "🎯 Insights & Recomendaciones", "🌳 Árbol de Conversación",
    "🔎 Push → Dónde se pierde la respuesta"
])

# ────────────────────────────────────────────────────────────────
# TAB 1 · RESUMEN EJECUTIVO
# ────────────────────────────────────────────────────────────────
with tab1:
    st.markdown('<span class="sec">Panorama general del período seleccionado</span>', unsafe_allow_html=True)
    _f_gr = "🟢 Data Warehouse en vivo" if gr.attrs.get("fuente") == "dwh" else "🟡 CSV (respaldo)"
    _f_sr = "🟢 Data Warehouse en vivo" if sr.attrs.get("fuente") == "dwh" else "🟡 CSV (respaldo)"
    st.caption(f"Fuente de datos — Pushes: {_f_gr} · Conversaciones: {_f_sr}")

    fc1, fc2 = st.columns([1, 3])
    with fc1:
        rango1 = st.date_input("📅 Rango de fechas (pushes y conversaciones)",
                                value=(min(gr["fecha"].min(), sr["fecha"].min()),
                                       max(gr["fecha"].max(), sr["fecha"].max())),
                                key="t1_fecha")
    if isinstance(rango1, tuple) and len(rango1) == 2:
        r1_ini, r1_fin = rango1
    else:
        r1_ini, r1_fin = gr["fecha"].min(), sr["fecha"].max()

    gr_f = gr[(gr["fecha"] >= r1_ini) & (gr["fecha"] <= r1_fin)]
    sr_f = sr[(sr["fecha"] >= r1_ini) & (sr["fecha"] <= r1_fin)]
    gr_costo = con_costo(gr_f)

    envios = int(gr_f["successful"].sum())
    entregados = int(gr_f["delivered"].sum())
    tasa_entrega = safe_pct(entregados, envios)
    resp_ponderada = safe_pct((gr_f["successful"] * gr_f["response_rate"]).sum(), envios)
    costo_total = gr_costo["costo_estimado"].sum()

    sesiones_total = len(sr_f)
    pct_outbound = safe_pct((sr_f["session_type"] == "OUTBOUND").sum(), sesiones_total)
    pct_inbound = safe_pct((sr_f["session_type"] == "INBOUND").sum(), sesiones_total)

    c = st.columns(6)
    kpis = [
        ("Pushes enviados", f"{envios:,}", "", ""),
        ("Tasa de entrega", f"{tasa_entrega}%", "", "ok" if tasa_entrega >= 90 else "warn"),
        ("Tasa de respuesta", f"{resp_ponderada}%", "ponderada por envíos", "alt"),
        ("💰 Costo estimado", fmt_usd(costo_total), "período seleccionado", "warn"),
        ("Sesiones (conversaciones)", f"{sesiones_total:,}", "", "dark"),
        ("% Push (outbound) / Entrante", f"{pct_outbound}% / {pct_inbound}%", "", "purple"),
    ]
    for col, (l, v, d, k) in zip(c, kpis):
        col.markdown(kpi(l, v, d, k), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns([1.4, 1])

    with col1:
        st.markdown('<span class="sec blue">Tendencia mensual de envíos y costo estimado</span>', unsafe_allow_html=True)
        m = gr_costo.groupby("mes", observed=True).agg(
            enviados=("successful", "sum"), costo=("costo_estimado", "sum")).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=m["mes"], y=m["enviados"], name="Enviados", marker_color=OY_TEAL, yaxis="y"))
        fig.add_trace(go.Scatter(x=m["mes"], y=m["costo"], name="Costo estimado (USD)",
                                  yaxis="y2", line=dict(color=OY_WARN, width=3)))
        fig.update_layout(
            yaxis=dict(title="Enviados"),
            yaxis2=dict(title="Costo USD", overlaying="y", side="right"),
            title="Envíos vs. costo estimado por mes"
        )
        st.plotly_chart(sfig(fig), use_container_width=True)

    with col2:
        st.markdown('<span class="sec amb">Distribución del costo por push</span>', unsafe_allow_html=True)
        cshare = gr_costo.groupby("name_clean", observed=True)["costo_estimado"].sum().nlargest(8).reset_index()
        fig = px.pie(cshare, names="name_clean", values="costo_estimado", hole=.5,
                     color_discrete_sequence=COLOR_SEQ)
        fig.update_traces(textinfo="percent")
        st.plotly_chart(sfig(fig, 340), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<span class="sec ok">Top 5 pushes por costo estimado</span>', unsafe_allow_html=True)
        top5 = gr_costo.groupby("name_clean", observed=True)["costo_estimado"].sum().nlargest(5).reset_index()
        fig = px.bar(top5.sort_values("costo_estimado"), x="costo_estimado", y="name_clean", orientation="h",
                     color_discrete_sequence=[OY_WARN], text_auto=".2s")
        fig.update_layout(yaxis_title="", xaxis_title="Costo estimado (USD)", showlegend=False)
        st.plotly_chart(sfig(fig, 300), use_container_width=True)

    with col4:
        st.markdown('<span class="sec">Volumen diario de conversaciones</span>', unsafe_allow_html=True)
        d = sr_f.groupby("fecha").size().reset_index(name="n")
        fig = px.area(d, x="fecha", y="n", color_discrete_sequence=[OY_TEAL])
        fig.update_layout(yaxis_title="Sesiones", xaxis_title="")
        st.plotly_chart(sfig(fig, 300), use_container_width=True)

    tarifas_activas = sorted(gr_costo["tarifa_aplicada"].unique()) if len(gr_costo) else []
    tarifas_txt = ", ".join(fmt_usd(t) for t in tarifas_activas) if tarifas_activas else "—"
    st.caption(f"💰 Tarifa aplicada: {tarifas_txt} · detalle completo en 📤 Pushes Automáticos & Costo")

    # ── Comparador de períodos (mes vs. mes, o semana vs. semana) ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<span class="sec purple">📆 Comparar períodos</span>', unsafe_allow_html=True)

    gr_comp = con_costo(gr)  # siempre sobre el histórico completo, independiente del filtro de arriba
    gr_comp["semana"] = pd.to_datetime(gr_comp["fecha"]).dt.to_period("W").apply(lambda p: p.start_time.date())
    sr_comp = sr.copy()
    sr_comp["semana"] = pd.to_datetime(sr_comp["fecha"]).dt.to_period("W").apply(lambda p: p.start_time.date())
    sr_comp["mes"] = pd.to_datetime(sr_comp["fecha"]).dt.to_period("M").apply(lambda p: p.start_time.date())

    granularidad = st.radio("Comparar por", ["Mes", "Semana"], horizontal=True, key="t1_gran")
    col_period = "mes" if granularidad == "Mes" else "semana"

    opciones_periodo = sorted(gr_comp[col_period].unique(), reverse=True)
    if len(opciones_periodo) < 2:
        st.info(f"No hay suficientes {granularidad.lower()}s distintos en los datos para comparar.")
    else:
        cp1, cp2 = st.columns(2)
        periodo_a = cp1.selectbox(f"{granularidad} A (más reciente)", opciones_periodo, index=0, key="t1_pa")
        periodo_b = cp2.selectbox(f"{granularidad} B (a comparar)", opciones_periodo, index=1, key="t1_pb")

        def _resumen_periodo(p):
            g = gr_comp[gr_comp[col_period] == p]
            s = sr_comp[sr_comp[col_period] == p]
            env = int(g["successful"].sum())
            ent = int(g["delivered"].sum())
            return {
                "Enviados": env,
                "Tasa de entrega %": safe_pct(ent, env),
                "Tasa de respuesta %": safe_pct((g["successful"] * g["response_rate"]).sum(), env),
                "Costo estimado (USD)": g["costo_estimado"].sum(),
                "Sesiones/conversaciones": len(s),
                "% Escalado a humano": safe_pct((s["session_status"] == "HumanHandover").sum(), len(s)) if len(s) else 0.0,
            }

        res_a = _resumen_periodo(periodo_a)
        res_b = _resumen_periodo(periodo_b)

        filas_cmp = []
        for metrica in res_a:
            va, vb = res_a[metrica], res_b[metrica]
            delta_pct = safe_pct(va - vb, vb) if vb else None
            filas_cmp.append({
                "Métrica": metrica,
                f"{periodo_a}": round(va, 2),
                f"{periodo_b}": round(vb, 2),
                "Variación": f"{'+' if (delta_pct or 0) >= 0 else ''}{delta_pct}%" if delta_pct is not None else "—",
            })
        cmp_df = pd.DataFrame(filas_cmp)
        st.dataframe(cmp_df, use_container_width=True, hide_index=True)
        boton_descarga(cmp_df, f"comparativa_{periodo_a}_vs_{periodo_b}.csv", "t1_dl_cmp")
        st.caption(
            f"Comparando {granularidad.lower()} del {periodo_a} contra el {periodo_b}. "
            "Cambia la granularidad o los períodos arriba para comparar cualquier combinación."
        )


# ────────────────────────────────────────────────────────────────
# TAB 2 · PUSHES AUTOMÁTICOS & COSTO
# ────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<span class="sec">Desempeño y costo por push</span>', unsafe_allow_html=True)

    # ── Toolbar único: fecha, búsqueda, filtros de alcance ──
    _fuente_gr_txt = "Data Warehouse en vivo" if gr.attrs.get("fuente") == "dwh" else "CSV de respaldo (no en vivo)"
    tc1, tc2, tc3, tc4 = st.columns([1, 1.6, 0.85, 0.85])
    with tc1:
        rango2 = st.date_input("📅 Fechas", value=(gr["fecha"].min(), gr["fecha"].max()),
                                min_value=gr["fecha"].min(), max_value=gr["fecha"].max(), key="t2_fecha",
                                help=f"Fuente de datos: {_fuente_gr_txt}. Rango disponible: "
                                     f"{gr['fecha'].min()} a {gr['fecha'].max()}.")
    with tc2:
        campanas_sel = st.multiselect("Push específico", sorted(gr["name_clean"].unique()),
                                       default=[], key="t2_campanas", placeholder="Todos los pushes")
    with tc3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        ocultar_inactivos = st.checkbox("Solo activos", value=False, key="t2_ocultar_inactivos")
    with tc4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        ocultar_sin_match = st.checkbox("Ocultar Ventas", value=True, key="t2_ocultar_sin_match",
                                         help="Oculta campañas fuera del catálogo ATC (típicamente Ventas/Marketing).")
    incluir_sin_envios = st.checkbox(
        "Incluir plantillas activas sin envíos en este período", value=False, key="t2_incluir_sin_envios",
        help="Muestra también las plantillas activas del catálogo que no enviaron nada en el rango elegido.")

    if isinstance(rango2, tuple) and len(rango2) == 2:
        r2_ini, r2_fin = rango2
    else:
        r2_ini, r2_fin = gr["fecha"].min(), gr["fecha"].max()

    gr_f = gr[(gr["fecha"] >= r2_ini) & (gr["fecha"] <= r2_fin)]
    if campanas_sel:
        gr_f = gr_f[gr_f["name_clean"].isin(campanas_sel)]
    gr_costo = con_costo(gr_f)

    if gr_f["successful"].sum() == 0:
        st.markdown(
            f'<div class="crit">🚨 Sin envíos entre {r2_ini} y {r2_fin}. Datos disponibles: '
            f'{gr["fecha"].min()} a {gr["fecha"].max()}.</div>', unsafe_allow_html=True
        )

    agg = gr_costo.groupby("name_clean", observed=True).agg(
        envios=("successful", "sum"),
        entregados=("delivered", "sum"),
        conversaciones_facturables=("conversaciones_facturables", "sum"),
        costo_estimado=("costo_estimado", "sum"),
        resp_pond=("successful", lambda s: (s * gr_costo.loc[s.index, "response_rate"]).sum()),
        n_batches=("date", "count"),
    ).reset_index()
    agg["tasa_entrega_%"] = (agg["entregados"] / agg["envios"] * 100).round(1)
    agg["tasa_respuesta_%"] = (agg["resp_pond"] / agg["envios"] * 100).round(1)
    agg = agg.drop(columns=["resp_pond"]).sort_values("costo_estimado", ascending=False)

    # Cruce con catálogo (matching normalizado sin tildes)
    cat_lookup = cat.set_index("conversacion")[["equipo", "estado", "activo"]]
    cat_norm_index = {_norm_txt(k): k for k in cat_lookup.index}
    def _cat_match(n):
        n_norm = _norm_txt(n)
        for k_norm, k in cat_norm_index.items():
            if k_norm in n_norm or n_norm in k_norm:
                return cat_lookup.loc[k, "equipo"], cat_lookup.loc[k, "estado"], cat_lookup.loc[k, "activo"]
        return "Sin match en catálogo", "Sin match", None
    _res = [_cat_match(n) for n in agg["name_clean"]]
    agg["equipo"] = [r[0] for r in _res]
    agg["estado_catalogo"] = [r[1] for r in _res]
    agg["activo"] = [r[2] for r in _res]
    agg["Activo"] = agg["activo"].map({True: "✅ Sí", False: "⛔ No"}).fillna("❓ Sin match")

    inactivos_con_envio = int((agg["activo"] == False).sum())
    sin_match_n = int((agg["estado_catalogo"] == "Sin match").sum())

    if incluir_sin_envios:
        _nombres_en_tabla = [_norm_txt(n) for n in agg["name_clean"]]
        def _ya_esta(nombre_catalogo):
            nn = _norm_txt(nombre_catalogo)
            return any(nn in en or en in nn for en in _nombres_en_tabla)
        cat_activas_faltantes = cat[cat["activo"] & ~cat["conversacion"].apply(_ya_esta)]
        if len(cat_activas_faltantes):
            filas_extra = pd.DataFrame({
                "name_clean": cat_activas_faltantes["conversacion"].values,
                "envios": 0, "entregados": 0, "conversaciones_facturables": 0, "costo_estimado": 0.0,
                "n_batches": 0, "tasa_entrega_%": 0.0, "tasa_respuesta_%": 0.0,
                "equipo": cat_activas_faltantes["equipo"].values,
                "estado_catalogo": cat_activas_faltantes["estado"].values,
                "activo": True, "Activo": "✅ Sí",
            })
            agg = pd.concat([agg, filas_extra], ignore_index=True)

    if ocultar_inactivos:
        agg = agg[agg["activo"] != False]
    if ocultar_sin_match:
        agg = agg[agg["estado_catalogo"] != "Sin match"]

    # ── Verificación en vivo contra Treble: última actividad real de TODOS los pushes ──
    agg["Último envío (DWH)"] = pd.NaT
    agg["¿Activo confirmado?"] = "❓ Sin dato DWH"
    _mismatches = 0
    if _dwh_ok:
        _activ = dwh_actividad_reciente_todos()
        if _activ is not None and not _activ.empty:
            _activ_lista = [(_norm_txt(r["poll_name"]), r["ultimo_envio"]) for _, r in _activ.iterrows()]

            def _buscar_ultimo_envio(nombre):
                nn = _norm_txt(nombre)
                for norm_p, ultimo in _activ_lista:
                    if norm_p in nn or nn in norm_p:
                        return ultimo
                return None

            agg["Último envío (DWH)"] = agg["name_clean"].apply(_buscar_ultimo_envio)
            agg["Último envío (DWH)"] = pd.to_datetime(agg["Último envío (DWH)"], errors="coerce").dt.date
            _hoy = pd.Timestamp.now().date()
            agg["_dias_desde_envio"] = agg["Último envío (DWH)"].apply(
                lambda d: (_hoy - d).days if pd.notna(d) else None)

            def _estado_confirmado(row):
                dias = row["_dias_desde_envio"]
                catalogo_activo = row["activo"] is True
                if pd.isna(dias):
                    return "❓ Sin dato DWH"
                dias = int(dias)
                real_activo = dias <= 30
                if real_activo != catalogo_activo:
                    return f"🚨 Revisar (últ. envío hace {dias}d)"
                return f"✅ Confirmado (hace {dias}d)" if real_activo else f"⏸️ Sin enviar hace {dias}d"

            agg["¿Activo confirmado?"] = agg.apply(_estado_confirmado, axis=1)
            _mismatches = agg["¿Activo confirmado?"].str.startswith("🚨").sum()
            agg = agg.drop(columns=["_dias_desde_envio"])

    # ── KPIs ──
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.markdown(kpi("Costo total", fmt_usd(agg["costo_estimado"].sum()), "período seleccionado", "warn"),
                unsafe_allow_html=True)
    c2.markdown(kpi("Pushes con envíos", f"{len(agg)}", "", ""), unsafe_allow_html=True)
    c3.markdown(kpi("Catálogo vs. realidad", f"{inactivos_con_envio + _mismatches}",
                    "discrepancias a revisar" if (inactivos_con_envio or _mismatches) else "todo consistente",
                    "warn" if (inactivos_con_envio or _mismatches) else "ok"), unsafe_allow_html=True)
    mas_caro = agg.iloc[0] if len(agg) else None
    if mas_caro is not None:
        c4.markdown(kpi("Push más costoso", fmt_usd(mas_caro["costo_estimado"]), mas_caro["name_clean"][:28], "amber"),
                    unsafe_allow_html=True)
    c5.markdown(kpi("Fuente de datos", "DWH en vivo" if gr.attrs.get("fuente") == "dwh" else "CSV (respaldo)", "",
                    "ok" if gr.attrs.get("fuente") == "dwh" else "warn"), unsafe_allow_html=True)

    # ── Tabla principal ──
    st.markdown("<br>", unsafe_allow_html=True)
    tabla = agg.rename(columns={
        "name_clean": "Push / Campaña", "envios": "Enviados", "entregados": "Entregados",
        "conversaciones_facturables": "Conversaciones facturables", "tasa_entrega_%": "Entrega %",
        "tasa_respuesta_%": "Respuesta %", "estado_catalogo": "Estado",
        "costo_estimado": "Costo (USD)", "n_batches": "Tandas de envío", "equipo": "Equipo"
    })
    cols_tabla = ["Push / Campaña", "Activo", "Estado", "Equipo",
                  "Enviados", "Entregados", "Conversaciones facturables", "Costo (USD)",
                  "Entrega %", "Respuesta %", "Tandas de envío"]
    tabla = tabla[cols_tabla]

    ft1, ft2, ft3, ft4, ft5 = st.columns([1.3, 1, 1, 1, 1])
    with ft1:
        f_nombre = st.text_input("Buscar", key="t2_f_nombre", placeholder="Nombre del push…")
    with ft2:
        f_equipo = st.multiselect("Equipo", sorted(tabla["Equipo"].dropna().unique()), key="t2_f_equipo")
    with ft3:
        f_activo = st.multiselect("Activo", sorted(tabla["Activo"].unique()), key="t2_f_activo")
    with ft4:
        f_entrega_min = st.number_input("Entrega % mín.", min_value=0, max_value=100, value=0, step=5, key="t2_f_entrega")
    with ft5:
        f_respuesta_min = st.number_input("Respuesta % mín.", min_value=0, max_value=100, value=0, step=5, key="t2_f_resp")

    if f_nombre:
        tabla = tabla[tabla["Push / Campaña"].str.contains(f_nombre, case=False, na=False)]
    if f_equipo:
        tabla = tabla[tabla["Equipo"].isin(f_equipo)]
    if f_activo:
        tabla = tabla[tabla["Activo"].isin(f_activo)]
    if f_entrega_min:
        tabla = tabla[tabla["Entrega %"] >= f_entrega_min]
    if f_respuesta_min:
        tabla = tabla[tabla["Respuesta %"] >= f_respuesta_min]

    st.dataframe(
        tabla, use_container_width=True, hide_index=True, height=460,
        column_config={
            "Costo (USD)": st.column_config.NumberColumn(format="$%.2f"),
            "Entrega %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
            "Respuesta %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
            "Tandas de envío": st.column_config.NumberColumn(
                help="Cantidad de envíos distintos registrados en el período."),
            "Activo": st.column_config.TextColumn(help="Estado documentado en el catálogo de plantillas."),
            "Conversaciones facturables": st.column_config.NumberColumn(
                help="Base de cálculo del costo, según el modelo elegido en ⚙️ Configuración."),
        }
    )
    boton_descarga(tabla, "costo_por_push.csv", "t2_dl_tabla")

    # ── Gráficos ──
    st.markdown("<br>", unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1:
        st.markdown('<span class="sec amb">Costo por push</span>', unsafe_allow_html=True)
        fig = px.bar(agg.sort_values("costo_estimado"), x="costo_estimado", y="name_clean", orientation="h",
                     color="costo_estimado", color_continuous_scale=[OY_TEAL, OY_AMBER, OY_WARN])
        fig.update_layout(yaxis_title="", xaxis_title="USD", coloraxis_showscale=False)
        st.plotly_chart(sfig(fig, 420), use_container_width=True)
    with g2:
        st.markdown('<span class="sec purple">Tasa de respuesta por push</span>', unsafe_allow_html=True)
        fig = px.bar(agg.sort_values("tasa_respuesta_%"), x="tasa_respuesta_%", y="name_clean", orientation="h",
                     color="tasa_respuesta_%", color_continuous_scale=[OY_WARN, OY_AMBER, OY_TEAL])
        fig.update_layout(yaxis_title="", xaxis_title="% respuesta", coloraxis_showscale=False)
        st.plotly_chart(sfig(fig, 420), use_container_width=True)

    st.markdown('<span class="sec">Evolución temporal</span>', unsafe_allow_html=True)
    camp_pick = st.selectbox("Push", sorted(gr_f["name_clean"].unique()), key="t2_serie_pick", label_visibility="collapsed")
    serie = gr_costo[gr_costo["name_clean"] == camp_pick].groupby("fecha").agg(
        enviados=("successful", "sum"), costo=("costo_estimado", "sum"),
        resp=("response_rate", "mean")).reset_index()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=serie["fecha"], y=serie["enviados"], name="Enviados", marker_color=OY_TEAL, yaxis="y"))
    fig.add_trace(go.Scatter(x=serie["fecha"], y=serie["costo"], name="Costo (USD)",
                              yaxis="y2", line=dict(color=OY_WARN, width=3)))
    fig.update_layout(yaxis=dict(title="Enviados"),
                       yaxis2=dict(title="Costo USD", overlaying="y", side="right"),
                       title=camp_pick)
    st.plotly_chart(sfig(fig, 380), use_container_width=True)

    # ── Herramientas avanzadas (colapsadas por defecto) ──
    with st.expander("🛠️ Herramientas avanzadas — auditoría de tarifa, verificación puntual, campañas nuevas"):
        sub1, sub2, sub3 = st.tabs(["Auditoría de tarifa", "Verificar una plantilla", "Campañas nuevas"])

        with sub1:
            st.caption("Compara el gasto real reportado por Treble contra el modelo de $0.20/conversación "
                       "para las plantillas ya auditadas.")
            filas_audit = []
            for nombre, (vol_real, usd_real) in TREBLE_REAL_POR_PUSH.items():
                modelo_usd = round(vol_real * 0.20, 2)
                filas_audit.append({
                    "Push": nombre, "Conversaciones reales": vol_real,
                    "Gasto real (Treble)": usd_real, "Gasto modelado": modelo_usd,
                    "Diferencia": round(modelo_usd - usd_real, 2),
                })
            audit_df = pd.DataFrame(filas_audit).sort_values("Conversaciones reales", ascending=False)
            st.dataframe(audit_df, use_container_width=True, hide_index=True,
                         column_config={
                             "Gasto real (Treble)": st.column_config.NumberColumn(format="$%.2f"),
                             "Gasto modelado": st.column_config.NumberColumn(format="$%.2f"),
                             "Diferencia": st.column_config.NumberColumn(format="$%.2f"),
                         })
            boton_descarga(audit_df, "auditoria_tarifa_real.csv", "t2_dl_audit")

        with sub2:
            st.caption("Pega uno o más nombres (uno por línea) y consulta directo contra el DWH.")
            if not _dwh_ok:
                st.info(f"Data Warehouse no conectado: {_dwh_msg}")
            else:
                nombres_verificar = st.text_area("Nombres a verificar", height=100, key="t2_verificar_nombres",
                                                   placeholder="Agendamiento exitoso\nPuntuación 1", label_visibility="collapsed")
                if st.button("Verificar", key="t2_verificar_btn"):
                    lineas = [l.strip() for l in nombres_verificar.split("\n") if l.strip()]
                    if not lineas:
                        st.warning("Pegá al menos un nombre.")
                    else:
                        resultados = []
                        for nombre in lineas:
                            nombre_esc = nombre.replace("'", "''")
                            sql = f"""
                                SELECT poll_name, sum(sent) AS enviados, sum(delivered) AS entregados,
                                       max(day) AS ultimo_envio, min(day) AS primer_envio
                                FROM client_analytics.fact_deployment_daily
                                WHERE positionCaseInsensitive(poll_name, '{nombre_esc}') > 0
                                GROUP BY poll_name ORDER BY enviados DESC LIMIT 5
                            """
                            r = dwh_query(sql)
                            if r is None or r.empty:
                                resultados.append({"Buscado": nombre, "poll_name real": "— no encontrado —",
                                                    "Enviados": 0, "Entregados": 0, "Primer envío": "—", "Último envío": "—"})
                            else:
                                for _, row in r.iterrows():
                                    resultados.append({
                                        "Buscado": nombre, "poll_name real": row["poll_name"],
                                        "Enviados": int(row["enviados"]), "Entregados": int(row["entregados"]),
                                        "Primer envío": str(row["primer_envio"]), "Último envío": str(row["ultimo_envio"]),
                                    })
                        res_df = pd.DataFrame(resultados)
                        st.dataframe(res_df, use_container_width=True, hide_index=True)
                        boton_descarga(res_df, "verificacion_plantillas_dwh.csv", "t2_dl_verificar")

        with sub3:
            st.caption("Detecta campañas con envíos reales que aún no están en el catálogo.")
            if not _dwh_ok:
                st.info(f"Data Warehouse no conectado: {_dwh_msg}")
            else:
                dias_nuevas = st.number_input("Días hacia atrás", min_value=1, value=7, step=1, key="t2_dias_nuevas")
                if st.button("Buscar", key="t2_buscar_nuevas_btn"):
                    sql_nuevas = f"""
                        SELECT poll_name, sum(sent) AS enviados, min(day) AS primera_fecha, max(day) AS ultima_fecha
                        FROM client_analytics.fact_deployment_daily
                        WHERE day >= today() - {int(dias_nuevas)} AND poll_name != '' AND poll_name IS NOT NULL
                        GROUP BY poll_name ORDER BY primera_fecha DESC
                    """
                    nuevas_df = dwh_query(sql_nuevas)
                    if nuevas_df is None or nuevas_df.empty:
                        st.info(f"Sin campañas en los últimos {dias_nuevas} días.")
                    else:
                        nuevas_df["¿En catálogo?"] = nuevas_df["poll_name"].apply(
                            lambda n: "✅ Sí" if _es_campana_atc(n) else "❓ Revisar")
                        nuevas_df = nuevas_df.rename(columns={
                            "poll_name": "Campaña", "enviados": "Enviados",
                            "primera_fecha": "Primer envío", "ultima_fecha": "Último envío"})
                        st.dataframe(nuevas_df, use_container_width=True, hide_index=True)
                        boton_descarga(nuevas_df, "campanas_nuevas_dwh.csv", "t2_dl_nuevas")


# ────────────────────────────────────────────────────────────────
# TAB 3 · CONVERSACIONES
# ────────────────────────────────────────────────────────────────
with tab3:
    st.markdown('<span class="sec">Análisis conversacional (sesiones de WhatsApp)</span>', unsafe_allow_html=True)

    fc1, fc2 = st.columns([1, 3])
    with fc1:
        rango3 = st.date_input("📅 Rango de fechas", value=(sr["fecha"].min(), sr["fecha"].max()),
                                min_value=sr["fecha"].min(), max_value=sr["fecha"].max(), key="t3_fecha")
    if isinstance(rango3, tuple) and len(rango3) == 2:
        r3_ini, r3_fin = rango3
    else:
        r3_ini, r3_fin = sr["fecha"].min(), sr["fecha"].max()
    sr_f = sr[(sr["fecha"] >= r3_ini) & (sr["fecha"] <= r3_fin)]

    st.markdown("<br>", unsafe_allow_html=True)
    c = st.columns(5)
    total_s = len(sr_f)
    ai_pct = safe_pct((sr_f["session_status"] == "AI").sum(), total_s)
    rating_pct = safe_pct((sr_f["session_status"] == "Rating").sum(), total_s)
    handover_n = int((sr_f["session_status"] == "HumanHandover").sum())
    paises_n = sr_f["pais"].nunique()

    kpis3 = [
        ("Total conversaciones", f"{total_s:,}", ""),
        ("Resueltas por IA", f"{ai_pct}%", "ok"),
        ("En calificación", f"{rating_pct}%", "alt"),
        ("Escaladas a agente humano", f"{handover_n}", "warn"),
        ("Países distintos", f"{paises_n}", "purple"),
    ]
    for col, (l, v, k) in zip(c, kpis3):
        col.markdown(kpi(l, v, "", k), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<span class="sec blue">Volumen diario por tipo de conversación</span>', unsafe_allow_html=True)
        d = sr_f.groupby(["fecha", "session_type"], observed=True).size().reset_index(name="n")
        fig = px.bar(d, x="fecha", y="n", color="session_type", color_discrete_sequence=COLOR_SEQ)
        fig.update_layout(yaxis_title="Sesiones", xaxis_title="", legend_title="")
        st.plotly_chart(sfig(fig, 360), use_container_width=True)
    with col2:
        st.markdown('<span class="sec red">Tasa de escalamiento a agente humano por día</span>', unsafe_allow_html=True)
        dh = sr_f.groupby("fecha").apply(
            lambda x: safe_pct((x["session_status"] == "HumanHandover").sum(), len(x)),
            include_groups=False
        ).reset_index(name="pct_handover")
        fig = px.line(dh, x="fecha", y="pct_handover", markers=True, color_discrete_sequence=[OY_WARN])
        fig.update_layout(yaxis_title="% escalado a humano", xaxis_title="")
        st.plotly_chart(sfig(fig, 360), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<span class="sec amb">Distribución horaria de conversaciones</span>', unsafe_allow_html=True)
        h = sr_f.groupby("hora").size().reset_index(name="n")
        fig = px.bar(h, x="hora", y="n", color_discrete_sequence=[OY_TEAL])
        fig.update_layout(xaxis_title="Hora del día (America/New_York)", yaxis_title="Sesiones")
        st.plotly_chart(sfig(fig, 320), use_container_width=True)
    with col4:
        st.markdown('<span class="sec">Top países de origen</span>', unsafe_allow_html=True)
        p = sr_f["pais"].value_counts().nlargest(10).reset_index()
        p.columns = ["pais", "n"]
        fig = px.bar(p.sort_values("n"), x="n", y="pais", orientation="h", color_discrete_sequence=[OY_BLUE])
        fig.update_layout(xaxis_title="Sesiones", yaxis_title="")
        st.plotly_chart(sfig(fig, 320), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<span class="sec purple">Sesiones por campaña / flujo de origen</span>', unsafe_allow_html=True)
    link_data = sr_f[sr_f["whatsapp_link_campaign_name"].notna()]
    if len(link_data):
        lk = link_data.groupby("whatsapp_link_campaign_name", observed=True).size().reset_index(name="n").sort_values("n", ascending=False)
        lk_tabla = lk.rename(columns={"whatsapp_link_campaign_name": "Campaña / flujo de origen", "n": "Sesiones"})
        st.dataframe(lk_tabla, use_container_width=True, hide_index=True)
        boton_descarga(lk_tabla, "sesiones_por_campana.csv", "t3_dl_link")
        if sr.attrs.get("fuente") == "dwh":
            st.caption("Fuente: `poll_name` del Data Warehouse (el flujo que disparó la sesión) — "
                       "no es un link de tracking con UTM, es la campaña/plantilla real de origen.")
    else:
        st.info("No hay sesiones con campaña de origen identificada en el rango seleccionado.")


# ────────────────────────────────────────────────────────────────
# TAB 4 · CATÁLOGO DE PLANTILLAS
# ────────────────────────────────────────────────────────────────
with tab4:
    st.markdown('<span class="sec">Inventario interno de plantillas HSM (los "pushes" que se envían)</span>', unsafe_allow_html=True)
    st.caption(f"📄 Catálogo cargado: **{len(cat)} plantillas** · si este número no coincide con tu Excel, "
               f"el archivo en tu repo no es el más reciente.")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi("Plantillas registradas", f"{len(cat)}", "", ""), unsafe_allow_html=True)
    c2.markdown(kpi("Activas", f"{int(cat['activo'].sum())}", "generan costo si se envían", "ok"), unsafe_allow_html=True)
    c3.markdown(kpi("Inactivas", f"{int((cat['estado']=='Inactivo').sum())}", "", "warn"), unsafe_allow_html=True)
    c4.markdown(kpi("Equipos dueños", f"{cat['equipo'].nunique()}", "", "purple"), unsafe_allow_html=True)

    inconsistentes = cat[cat["auditoria"].astype(str).str.startswith("⚠️", na=False)]
    if len(inconsistentes):
        st.markdown("<br>", unsafe_allow_html=True)
        detalle = ", ".join(inconsistentes["conversacion"].tolist())
        st.markdown(
            f'<div class="alrt">⚠️ <b>{len(inconsistentes)} plantilla(s) marcadas "Inactivo" con envíos reales '
            f'registrados:</b> {detalle}.</div>',
            unsafe_allow_html=True
        )

    _candidatas_eliminar = cat[cat["nota_interna"].astype(str).str.contains("eliminar", case=False, na=False)]
    if len(_candidatas_eliminar):
        st.markdown(
            f'<div class="info">🗑️ <b>{len(_candidatas_eliminar)} plantilla(s) marcadas por el equipo como '
            f'candidatas a eliminar</b> — filtra por "Notas" abajo para verlas.</div>', unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<span class="sec blue">Plantillas por equipo</span>', unsafe_allow_html=True)
        e = cat.groupby(["equipo", "activo"]).size().reset_index(name="n")
        e["estado_g"] = e["activo"].map({True: "Activa", False: "Inactiva"})
        fig = px.bar(e, x="equipo", y="n", color="estado_g", barmode="stack",
                     color_discrete_map={"Activa": OY_OK, "Inactiva": "#CBD5D9"})
        fig.update_layout(xaxis_title="", yaxis_title="N° plantillas", legend_title="")
        st.plotly_chart(sfig(fig, 340), use_container_width=True)
    with col2:
        st.markdown('<span class="sec amb">Nivel de documentación</span>', unsafe_allow_html=True)
        nd = cat["nivel_documentacion"].value_counts().reset_index()
        nd.columns = ["nivel", "n"]
        fig = px.pie(nd, names="nivel", values="n", hole=.5,
                     color="nivel", color_discrete_map={"Completa": OY_OK, "Parcial": OY_AMBER, "Sin documentar": OY_WARN})
        st.plotly_chart(sfig(fig, 340), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<span class="sec">Explorador del catálogo</span>', unsafe_allow_html=True)
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    equipo_f = fc1.multiselect("Equipo", sorted(cat["equipo"].unique()))
    estado_f = fc2.multiselect("Estado", sorted(cat["estado"].unique()))
    doc_f = fc3.multiselect("Documentación", sorted(cat["nivel_documentacion"].unique()))
    nota_f = fc4.multiselect("Notas", sorted(cat[cat["nota_interna"] != ""]["nota_interna"].unique()))
    buscar = fc5.text_input("Buscar", placeholder="Nombre del push…")

    cat_f = cat.copy()
    if equipo_f:
        cat_f = cat_f[cat_f["equipo"].isin(equipo_f)]
    if estado_f:
        cat_f = cat_f[cat_f["estado"].isin(estado_f)]
    if doc_f:
        cat_f = cat_f[cat_f["nivel_documentacion"].isin(doc_f)]
    if nota_f:
        cat_f = cat_f[cat_f["nota_interna"].isin(nota_f)]
    if buscar:
        cat_f = cat_f[cat_f["conversacion"].str.contains(buscar, case=False, na=False)]

    cat_f_tabla = cat_f[["conversacion", "plantilla", "tipo", "proposito", "estado", "equipo",
                         "envios_historicos", "entregados_historicos", "nota_interna", "auditoria"]].rename(columns={
        "conversacion": "Conversación / Campaña", "plantilla": "HSM / Plantilla",
        "tipo": "Tipo", "proposito": "Para qué se envía", "estado": "Estado", "equipo": "Equipo",
        "envios_historicos": "Envíos reales", "entregados_historicos": "Entregados reales",
        "nota_interna": "Nota del equipo", "auditoria": "Auditoría"
    })
    st.dataframe(cat_f_tabla, use_container_width=True, hide_index=True, height=420,
                 column_config={
                     "Envíos reales": st.column_config.NumberColumn(help="Cruce directo con Treble — no estimado."),
                 })
    boton_descarga(cat_f_tabla, "catalogo_plantillas.csv", "t4_dl_catalogo")


# ────────────────────────────────────────────────────────────────
# TAB 5 · INSIGHTS & RECOMENDACIONES
# ────────────────────────────────────────────────────────────────
with tab5:
    st.markdown('<span class="sec">Resumen por equipo</span>', unsafe_allow_html=True)

    gr_costo_full = con_costo(gr)

    # Equipo dueño por push, mismo criterio de matching que en Pushes Automáticos
    _cat_lookup5 = cat.set_index("conversacion")["equipo"]
    _cat_norm5 = {_norm_txt(k): v for k, v in _cat_lookup5.items()}
    def _equipo_de(nombre):
        nn = _norm_txt(nombre)
        for kn, v in _cat_norm5.items():
            if kn in nn or nn in kn:
                return v
        return "Sin match"
    gr_costo_full = gr_costo_full.copy()
    gr_costo_full["equipo"] = gr_costo_full["name_clean"].apply(_equipo_de)

    envios_equipo = gr_costo_full.groupby("equipo").agg(
        envios_totales=("successful", "sum"),
        costo_total=("costo_estimado", "sum"),
        resp_pond=("successful", lambda s: (s * gr_costo_full.loc[s.index, "response_rate"]).sum()),
    ).reset_index()
    envios_equipo["tasa_respuesta_%"] = (envios_equipo["resp_pond"] / envios_equipo["envios_totales"] * 100).round(1)
    envios_equipo = envios_equipo.drop(columns=["resp_pond"])

    resumen_equipo = cat.groupby("equipo").agg(
        total=("conversacion", "count"),
        activas=("activo", "sum"),
        con_envio_automatico=("en_uso_real", "sum"),
    ).reset_index()
    resumen_equipo["inactivas"] = resumen_equipo["total"] - resumen_equipo["activas"]
    resumen_equipo = resumen_equipo.merge(envios_equipo, on="equipo", how="left")
    for c in ["envios_totales", "costo_total", "tasa_respuesta_%"]:
        resumen_equipo[c] = resumen_equipo[c].fillna(0)

    resumen_equipo = resumen_equipo.rename(columns={
        "equipo": "Equipo", "total": "Total plantillas", "activas": "Activas",
        "inactivas": "Inactivas", "con_envio_automatico": "Con push automático real",
        "envios_totales": "Envíos reales", "costo_total": "Costo estimado (USD)",
        "tasa_respuesta_%": "Tasa respuesta %"
    })[["Equipo", "Total plantillas", "Activas", "Inactivas", "Con push automático real",
        "Envíos reales", "Costo estimado (USD)", "Tasa respuesta %"]]
    resumen_equipo = resumen_equipo.sort_values("Costo estimado (USD)", ascending=False)

    fe1, fe2 = st.columns([1, 3])
    with fe1:
        equipos_pick = st.multiselect("Filtrar equipo", sorted(cat["equipo"].unique()), key="t5_equipo_pick")
    resumen_f = resumen_equipo[resumen_equipo["Equipo"].isin(equipos_pick)] if equipos_pick else resumen_equipo

    st.dataframe(resumen_f, use_container_width=True, hide_index=True,
                 column_config={
                     "Costo estimado (USD)": st.column_config.NumberColumn(format="$%.2f"),
                     "Tasa respuesta %": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                     "Activas": st.column_config.ProgressColumn(
                         min_value=0, max_value=int(resumen_equipo["Total plantillas"].max()), format="%d"),
                 })
    boton_descarga(resumen_equipo, "resumen_por_equipo.csv", "t5_dl_equipo")

    g1, g2 = st.columns(2)
    with g1:
        fig = px.bar(resumen_equipo.melt(id_vars="Equipo", value_vars=["Activas", "Inactivas"],
                                           var_name="Estado", value_name="n"),
                     x="Equipo", y="n", color="Estado", barmode="stack",
                     color_discrete_map={"Activas": OY_OK, "Inactivas": "#CBD5D9"}, text="n")
        fig.update_layout(xaxis_title="", yaxis_title="N° plantillas", legend_title="")
        st.plotly_chart(sfig(fig, 320), use_container_width=True)
    with g2:
        fig = px.bar(resumen_equipo.sort_values("Costo estimado (USD)"), x="Costo estimado (USD)", y="Equipo",
                     orientation="h", color_discrete_sequence=[OY_WARN], text="Costo estimado (USD)")
        fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        fig.update_layout(xaxis_title="Costo estimado (USD)", yaxis_title="")
        st.plotly_chart(sfig(fig, 320), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<span class="sec">Hallazgos automáticos para toma de decisiones</span>', unsafe_allow_html=True)

    insights = []

    # 1) Tendencia de escalamiento a humano
    dh_full = sr.groupby("fecha").apply(
        lambda x: safe_pct((x["session_status"] == "HumanHandover").sum(), len(x)), include_groups=False
    ).reset_index(name="pct")
    dh_full = dh_full.sort_values("fecha")
    if len(dh_full) >= 5:
        ult3 = dh_full.tail(3)["pct"].mean()
        prev3 = dh_full.iloc[-6:-3]["pct"].mean() if len(dh_full) >= 6 else dh_full.head(3)["pct"].mean()
        if ult3 > prev3 + 1:
            insights.append(("crit", "⚠️ Escalamiento a humano en ascenso",
                              f"La tasa de conversaciones escaladas a agente pasó de un promedio de "
                              f"{prev3:.1f}% a {ult3:.1f}% en los últimos días. Cada escalamiento implica "
                              f"tiempo de agente además del costo del push — vale la pena revisar con "
                              f"el equipo si hay un cambio en el flujo de IA o un pico de casos complejos."))

    # 2) Pushes con baja tasa de entrega (dinero gastado sin llegar)
    agg_full = gr_costo_full.groupby("name_clean", observed=True).agg(
        envios=("successful", "sum"), entregados=("delivered", "sum"),
        costo=("costo_estimado", "sum")).reset_index()
    agg_full["tasa"] = agg_full["entregados"] / agg_full["envios"] * 100
    bajas = agg_full[(agg_full["tasa"] < 90) & (agg_full["envios"] >= 50)].sort_values("tasa")
    if len(bajas):
        top3 = ", ".join([f"{r.name_clean} ({r.tasa:.0f}%)" for r in bajas.head(3).itertuples()])
        resto = len(bajas) - 3
        resumen = top3 + (f", y {resto} más" if resto > 0 else "")
        insights.append(("alrt", "📉 Pushes con tasa de entrega por debajo del 90%",
                          f"{len(bajas)} push(es), empezando por {resumen}. Si el modelo de costeo activo "
                          f"factura por envío/entrega, esto es dinero pagado por mensajes que no llegaron — "
                          f"revisar calidad de la lista de contactos o estado de la plantilla en Meta.",
                          bajas.rename(columns={"name_clean": "Push", "envios": "Enviados",
                                                 "entregados": "Entregados", "tasa": "Tasa entrega %",
                                                 "costo": "Costo (USD)"})[["Push", "Enviados", "Entregados",
                                                                            "Tasa entrega %", "Costo (USD)"]]))

    # 3) Concentración de costo
    top_share = agg_full.nlargest(1, "costo")
    if len(top_share) and agg_full["costo"].sum() > 0:
        share_pct = safe_pct(top_share["costo"].iloc[0], agg_full["costo"].sum())
        if share_pct > 40:
            insights.append(("info", "📊 Alta concentración de costo en un solo push",
                              f"'{top_share['name_clean'].iloc[0]}' representa {share_pct}% del costo "
                              f"estimado total histórico ({fmt_usd(top_share['costo'].iloc[0])}). "
                              f"Cualquier optimización de segmentación o frecuencia en este push tiene "
                              f"el mayor impacto posible en el gasto total.", None))

    # 4) Respuesta baja en pushes de alto volumen (costo sin interacción)
    resp_full = gr_costo_full.groupby("name_clean", observed=True).apply(
        lambda d: safe_pct((d["successful"] * d["response_rate"]).sum(), d["successful"].sum()),
        include_groups=False
    ).reset_index(name="tasa_resp")
    resp_full = resp_full.merge(agg_full[["name_clean", "envios", "costo"]], on="name_clean")
    bajas_resp = resp_full[(resp_full["tasa_resp"] < 10) & (resp_full["envios"] >= 500)].sort_values("costo", ascending=False)
    if len(bajas_resp):
        top3 = ", ".join([f"{r.name_clean} ({r.tasa_resp:.1f}%)" for r in bajas_resp.head(3).itertuples()])
        resto = len(bajas_resp) - 3
        resumen = top3 + (f", y {resto} más" if resto > 0 else "")
        insights.append(("alrt", "💬 Pushes de alto volumen con baja tasa de respuesta",
                          f"{len(bajas_resp)} push(es), empezando por {resumen}. Son recordatorios "
                          f"informativos (respuesta baja es esperable), pero si el modelo de costeo activo "
                          f"factura por conversación entregada (no por respuesta), estos son el gasto fijo "
                          f"recurrente más alto — los que más conviene auditar primero si se busca reducir costo.",
                          bajas_resp.rename(columns={"name_clean": "Push", "envios": "Enviados",
                                                      "tasa_resp": "Tasa respuesta %", "costo": "Costo (USD)"})
                          [["Push", "Enviados", "Tasa respuesta %", "Costo (USD)"]]))

    if not insights:
        st.markdown('<div class="good">✅ No se detectaron anomalías relevantes en el período analizado.</div>',
                     unsafe_allow_html=True)
    else:
        for item in insights:
            kind, titulo, texto = item[0], item[1], item[2]
            tabla_detalle = item[3] if len(item) > 3 else None
            st.markdown(f'<div class="{kind}"><b>{titulo}</b><br>{texto}</div>', unsafe_allow_html=True)
            if tabla_detalle is not None:
                with st.expander(f"Ver el detalle completo ({len(tabla_detalle)} filas)"):
                    st.dataframe(tabla_detalle, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<span class="sec">Próximos pasos sugeridos</span>', unsafe_allow_html=True)
    st.markdown("""
- **Confirmar la tarifa real de costo por conversación** con Treble/Meta si llegara a cambiar —
  hoy ya usamos la tarifa real auditada, no un supuesto, pero conviene re-auditar periódicamente.
- **Confirmar el modelo de costeo real** (¿se cobra por conversación entregada o solo cuando el
  cliente responde?) — cambia significativamente qué pushes son realmente los más caros.
- **Revisar con Iva** los pushes con baja tasa de entrega, ya que representan gasto sin llegar al
  cliente bajo el modelo "por entrega".
- **Alertas automáticas**: configurar un umbral de costo mensual o de tasa de entrega que dispare
  notificación sin depender de revisión manual del dashboard.
""")


# ────────────────────────────────────────────────────────────────
# TAB 6 · ÁRBOL DE CONVERSACIÓN (dónde se rompe / dónde queda en silencio)
# ────────────────────────────────────────────────────────────────
with tab6:
    st.markdown('<span class="sec">🌳 Dónde se rompe la conversación</span>', unsafe_allow_html=True)

    # ── Sección en vivo: lo que SÍ se puede sacar del DWH directamente ──
    st.markdown('<span class="sec blue">🟢 En vivo — respuesta a plantillas HSM</span>', unsafe_allow_html=True)
    if not _dwh_ok:
        st.caption(f"Data Warehouse no conectado: {_dwh_msg}")
    else:
        sql_hsm = """
            SELECT hsm_name, count() AS respuestas, count(DISTINCT survey_user_id) AS usuarios_unicos
            FROM client_analytics.fact_hsm_responses
            WHERE response_date >= now() - INTERVAL 30 DAY
            GROUP BY hsm_name ORDER BY respuestas DESC LIMIT 20
        """
        df_hsm = dwh_query(sql_hsm)
        if df_hsm is None or df_hsm.empty:
            st.caption("Sin datos de respuestas HSM en los últimos 30 días.")
        else:
            fig = px.bar(df_hsm.sort_values("respuestas"), x="respuestas", y="hsm_name", orientation="h",
                         color_discrete_sequence=[OY_BLUE])
            fig.update_layout(xaxis_title="Respuestas de usuarios (30 días)", yaxis_title="")
            st.plotly_chart(sfig(fig, 360), use_container_width=True)
            st.caption("Solo respuestas registradas — el detalle completo de silencios está abajo.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<span class="sec">📄 Análisis completo — export de árbol de Treble</span>', unsafe_allow_html=True)

    if arbol is None:
        st.markdown(
            '<div class="alrt">⚠️ Falta <code>data/arbol_conversacion.csv</code> en el repositorio.</div>',
            unsafe_allow_html=True
        )
    else:
        fuga_real_df = arbol[arbol["fuga_real"]]
        total_fuga_real = int(fuga_real_df["N Clientes"].sum())
        n_puntos = fuga_real_df["Origen ID"].nunique()
        rank_global = fuga_real_df.groupby("Plantilla").agg(
            fuga_real=("N Clientes", "sum"), puntos_de_quiebre=("Origen ID", "nunique"),
            entrantes=("entrantes_plantilla", "first"),
        ).reset_index().sort_values("fuga_real", ascending=False)
        rank_global["pct_entrantes"] = (rank_global["fuga_real"] / rank_global["entrantes"] * 100).round(1)

        c1, c2, c3 = st.columns(3)
        c1.markdown(kpi("Clientes en fuga real", f"{total_fuga_real:,}", "con alternativa real de responder", "warn"),
                    unsafe_allow_html=True)
        c2.markdown(kpi("Puntos de quiebre distintos", f"{n_puntos}", "en todos los flujos", "amber"),
                    unsafe_allow_html=True)
        if len(rank_global):
            top_row = rank_global.iloc[0]
            c3.markdown(kpi("Plantilla con más fuga", f"{int(top_row['fuga_real']):,}",
                            top_row["Plantilla"][:30], "dark"), unsafe_allow_html=True)
        st.caption("Fuga real = cliente tenía una opción para responder y no lo hizo (excluye avisos de una sola vía).")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="sec red">📊 Ranking de plantillas por volumen de fuga real</span>', unsafe_allow_html=True)
        st.caption(
            "Cada barra = cuántos clientes recibieron esa plantilla, tenían una opción real para "
            "responder, y aun así no respondieron. El % es sobre el total de gente que entró a esa "
            "plantilla (no sobre el total general)."
        )
        rank_global["etiqueta"] = rank_global.apply(
            lambda r: f"{int(r['fuga_real']):,} ({r['pct_entrantes']:.0f}% de {int(r['entrantes']):,} entrantes)", axis=1)
        top15 = rank_global.head(15).sort_values("fuga_real")
        fig = px.bar(top15, x="fuga_real", y="Plantilla", orientation="h",
                     color_discrete_sequence=[OY_WARN], text="etiqueta")
        fig.update_traces(textposition="outside", textfont=dict(size=11))
        fig.update_layout(xaxis_title="Clientes en fuga real", yaxis_title="",
                           margin=dict(r=220))  # espacio para que la etiqueta no se corte
        st.plotly_chart(sfig(fig, 460), use_container_width=True)
        boton_descarga(
            rank_global.rename(columns={"fuga_real": "Clientes en fuga real", "puntos_de_quiebre": "Puntos de quiebre",
                                         "entrantes": "Entrantes", "pct_entrantes": "% de entrantes"})
            [["Plantilla", "Clientes en fuga real", "% de entrantes", "Puntos de quiebre", "Entrantes"]],
            "ranking_fuga_real.csv", "t6_dl_ranking"
        )

        # ── 🔎 Hallazgos automáticos — 100% calculados desde los datos actuales, nunca escritos a mano ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="sec">🔎 Hallazgos automáticos</span>', unsafe_allow_html=True)

        def _extracto(texto, largo=140):
            texto = str(texto).strip()
            return (texto[:largo] + "…") if len(texto) > largo else texto

        if len(rank_global):
            # Hallazgo 1: el quiebre más concentrado (mayor volumen en un solo punto de un solo mensaje)
            fila_max = fuga_real_df.loc[fuga_real_df["N Clientes"].idxmax()]
            plantilla_concentrada = fila_max["Plantilla"]
            filas_msg = fuga_real_df[(fuga_real_df["Plantilla"] == plantilla_concentrada) &
                                      (fuga_real_df["Origen ID"] == fila_max["Origen ID"])]
            pct_lo, pct_hi = filas_msg["Pct Del Nodo"].min(), filas_msg["Pct Del Nodo"].max()
            vol_msg = int(filas_msg["N Clientes"].sum())
            rango_pct = f"{pct_lo:.0f}%" if pct_lo == pct_hi else f"{pct_lo:.0f}–{pct_hi:.0f}%"
            st.markdown(
                f'<div class="crit">⚠️ <b>"{plantilla_concentrada}"</b>: <i>"{_extracto(fila_max["Nodo Origen"], 90)}"</i> '
                f'sin respuesta en <b>{rango_pct}</b> de los casos ({vol_msg:,} clientes).</div>', unsafe_allow_html=True
            )

            # Hallazgo 2: el flujo con fricción más repartida (más puntos de quiebre distintos)
            candidatos = rank_global[rank_global["Plantilla"] != plantilla_concentrada]
            if len(candidatos):
                fila_disperso = candidatos.sort_values("puntos_de_quiebre", ascending=False).iloc[0]
                if fila_disperso["puntos_de_quiebre"] >= 5:
                    plantilla_disperso = fila_disperso["Plantilla"]
                    st.markdown(
                        f'<div class="alrt">📊 <b>"{plantilla_disperso}"</b>: fricción repartida en '
                        f'<b>{int(fila_disperso["puntos_de_quiebre"])} puntos</b> '
                        f'({int(fila_disperso["fuga_real"]):,} clientes) — no un quiebre único, sino '
                        f'varios pasos con fuga.</div>', unsafe_allow_html=True
                    )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="sec purple">🔬 Inspeccionar un flujo específico</span>',
                    unsafe_allow_html=True)
        # Todas las plantillas del archivo, no solo las que ya tienen fuga real detectada —
        # con el número de instancias (Poll ID) entre paréntesis, igual que el selector de Diosnel.
        _instancias_por_plantilla = arbol.groupby("Plantilla")["Poll ID"].nunique()
        _plantillas_todas = sorted(arbol["Plantilla"].unique(),
                                    key=lambda p: -_instancias_por_plantilla[p])
        _opciones_flujo = {f"{p} ({_instancias_por_plantilla[p]})": p for p in _plantillas_todas}

        fc1, fc2 = st.columns([2, 1])
        with fc1:
            _flujo_label = st.selectbox("Flujo", list(_opciones_flujo.keys()), key="t6_plantilla")
            plantilla_pick = _opciones_flujo[_flujo_label]
        with fc2:
            min_clientes = st.number_input("Mínimo de clientes por rama", min_value=0, value=50, step=10,
                                            key="t6_min_clientes",
                                            help="Ramas con menos clientes que este número no se muestran, "
                                                 "para que el árbol se pueda leer.")

        sub_full = arbol[arbol["Plantilla"] == plantilla_pick].copy()
        # Nos quedamos con un Poll ID representativo (el de mayor volumen) para que el
        # diagrama no mezcle instancias distintas del mismo flujo
        poll_top = sub_full.groupby("Poll ID")["N Clientes"].sum().idxmax()
        sub_full = sub_full[sub_full["Poll ID"] == poll_top].copy()
        total_flujo = sub_full["N Clientes"].sum()

        sub = sub_full[sub_full["N Clientes"] >= min_clientes].copy()
        n_ocultas = len(sub_full) - len(sub)
        vol_oculto = int(sub_full[sub_full["N Clientes"] < min_clientes]["N Clientes"].sum())

        st.markdown('<span class="sec blue">Mapa del flujo</span>', unsafe_allow_html=True)
        aviso_ocultas = (f" **{n_ocultas} rama(s)** con menos de {min_clientes} clientes están ocultas "
                          f"({vol_oculto:,} clientes, {safe_pct(vol_oculto, total_flujo)}% del flujo) — "
                          f"bajá el mínimo de arriba si querés verlas." if n_ocultas else "")
        st.caption(
            "Se lee de izquierda a derecha: cada barra es un mensaje, cada franja es cuánta gente "
            "pasó de un mensaje al siguiente. Los nodos van con un código corto (P1-a, P2-b…) — el "
            "texto completo de cada uno está en la leyenda de abajo. 🔴 rojo = terminó en silencio."
            + aviso_ocultas
        )

        if sub.empty:
            st.info("No quedan ramas con ese mínimo de clientes. Bajá el número de 'Mínimo de clientes "
                    "por rama' para ver el árbol.")
        else:
            # Códigos cortos por nodo (P1-a, P1-b, P2-a...) + tabla de leyenda con el texto completo —
            # esto es lo que la herramienta de Diosnel NO resuelve (sus etiquetas también se cortan).
            nodos_orden = list(pd.unique(sub[["Nodo Origen Key", "Nodo Destino Key"]].values.ravel()))

            def _paso_de(n):
                n = str(n)
                if " · " in n:
                    return n.split(" · ", 1)[0].strip()
                if "No avanzó" in n or "✖" in n:
                    return "FIN"
                return "?"

            codigo_por_nodo, texto_por_nodo, contador_paso = {}, {}, {}
            for n in nodos_orden:
                paso = _paso_de(n)
                if paso == "FIN":
                    codigo_por_nodo[n] = "✖ " + n.replace("✖ No avanzó ", "").strip()
                    texto_por_nodo[n] = "Cliente no respondió / no avanzó"
                else:
                    contador_paso[paso] = contador_paso.get(paso, 0) + 1
                    letra = chr(ord("a") + contador_paso[paso] - 1)
                    codigo_por_nodo[n] = f"{paso}-{letra}"
                    texto_por_nodo[n] = n.split(" · ", 1)[1] if " · " in n else n

            nodo_idx = {n: i for i, n in enumerate(nodos_orden)}
            pasos_unicos = sorted({_paso_de(n) for n in nodos_orden if _paso_de(n) != "FIN"})
            paso_color = {p: COLOR_SEQ[i % len(COLOR_SEQ)] for i, p in enumerate(pasos_unicos)}
            colores_nodo = [OY_WARN if _paso_de(n) == "FIN" else paso_color[_paso_de(n)] for n in nodos_orden]
            link_colores = ["rgba(229,72,77,.55)" if f else "rgba(120,120,120,.28)" for f in sub["Es Fuga"]]
            pct_total = (sub["N Clientes"] / total_flujo * 100).round(1)

            sankey = go.Figure(go.Sankey(
                arrangement="snap",
                node=dict(label=[codigo_por_nodo[n] for n in nodos_orden], pad=22, thickness=26,
                          color=colores_nodo, line=dict(color="rgba(0,0,0,.2)", width=.6),
                          hovertemplate="%{label}<extra></extra>"),
                link=dict(source=sub["Nodo Origen Key"].map(nodo_idx),
                          target=sub["Nodo Destino Key"].map(nodo_idx),
                          value=sub["N Clientes"], color=link_colores,
                          customdata=pct_total,
                          hovertemplate="%{value:,} clientes (%{customdata}% del flujo)<extra></extra>")
            ))
            sankey.update_traces(textfont=dict(size=13, color=OY_CHART_TEXT))
            st.plotly_chart(sfig(sankey, 620), use_container_width=True)

            col1, col2 = st.columns([1.1, 1])
            with col1:
                st.markdown('<span class="sec amb">Leyenda — qué dice cada mensaje</span>', unsafe_allow_html=True)
                leyenda_df = pd.DataFrame([
                    {"Código": codigo_por_nodo[n], "Mensaje completo": texto_por_nodo[n]}
                    for n in nodos_orden
                ]).drop_duplicates("Código").sort_values("Código")
                st.dataframe(leyenda_df, use_container_width=True, hide_index=True, height=380)
                boton_descarga(leyenda_df, f"leyenda_{plantilla_pick}.csv", "t6_dl_leyenda")
            with col2:
                st.markdown('<span class="sec red">Puntos de quiebre de este flujo</span>', unsafe_allow_html=True)
                puntos = sub_full[sub_full["N Clientes"] >= min_clientes]
                puntos = puntos[puntos["fuga_real"]][["Paso Origen", "Nodo Origen", "N Clientes", "Pct Del Nodo"]]
                puntos = puntos.sort_values("N Clientes", ascending=False)
                if len(puntos):
                    puntos_tabla = puntos.rename(columns={"Paso Origen": "Paso", "Nodo Origen": "Mensaje",
                                                            "N Clientes": "Clientes en silencio", "Pct Del Nodo": "% del nodo"})
                    st.dataframe(puntos_tabla, use_container_width=True, hide_index=True, height=380)
                    boton_descarga(puntos_tabla, f"puntos_quiebre_{plantilla_pick}.csv", "t6_dl_puntos")
                else:
                    st.info("Este flujo no tiene puntos de fuga real detectados (es informativo de una sola "
                            "vía, o casi todos los que llegan responden).")

        # ── Tabla resumen histórica — TODAS las plantillas, no solo el top 15 del ranking ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="sec">📋 Resumen histórico completo — todas las plantillas</span>',
                    unsafe_allow_html=True)
        st.caption("Foto fija del export de Treble — sin fecha por fila, no filtrable por período.")

        resumen_completo = arbol.groupby("Plantilla").agg(
            instancias=("Poll ID", "nunique"),
            entrantes=("entrantes_plantilla", "first"),
            puntos_totales=("Origen ID", "nunique"),
        ).reset_index()
        fuga_por_plantilla_total = fuga_real_df.groupby("Plantilla").agg(
            fuga_real=("N Clientes", "sum"), puntos_de_quiebre=("Origen ID", "nunique")).reset_index()
        resumen_completo = resumen_completo.merge(fuga_por_plantilla_total, on="Plantilla", how="left")
        resumen_completo["fuga_real"] = resumen_completo["fuga_real"].fillna(0).astype(int)
        resumen_completo["puntos_de_quiebre"] = resumen_completo["puntos_de_quiebre"].fillna(0).astype(int)
        resumen_completo["pct_fuga"] = (resumen_completo["fuga_real"] / resumen_completo["entrantes"] * 100).round(1)

        # Cruce con catálogo para saber equipo dueño y si está activa (mismo criterio que el resto del dashboard)
        _cat_lookup6 = cat.set_index("conversacion")[["equipo", "activo"]]
        def _match6(n):
            nn = _norm_txt(n)
            for k in _cat_lookup6.index:
                kn = _norm_txt(k)
                if kn in nn or nn in kn:
                    return _cat_lookup6.loc[k, "equipo"]
            return "Sin match en catálogo"
        resumen_completo["equipo"] = resumen_completo["Plantilla"].apply(_match6)

        buscar6 = st.text_input("🔍 Buscar plantilla por nombre", key="t6_buscar")
        resumen_f = resumen_completo.copy()
        if buscar6:
            resumen_f = resumen_f[resumen_f["Plantilla"].str.contains(buscar6, case=False, na=False)]
        resumen_f = resumen_f.sort_values("fuga_real", ascending=False)

        resumen_tabla = resumen_f.rename(columns={
            "Plantilla": "Plantilla", "instancias": "Instancias (Poll ID)", "entrantes": "Entrantes",
            "fuga_real": "Clientes en fuga real", "pct_fuga": "% fuga", "puntos_de_quiebre": "Puntos de quiebre",
            "equipo": "Equipo dueño"
        })[["Plantilla", "Equipo dueño", "Instancias (Poll ID)", "Entrantes", "Clientes en fuga real",
            "% fuga", "Puntos de quiebre"]]
        st.dataframe(resumen_tabla, use_container_width=True, hide_index=True, height=420,
                     column_config={"% fuga": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%")})
        boton_descarga(resumen_tabla, "resumen_arbol_todas_plantillas.csv", "t6_dl_resumen")
        st.caption(f"{len(resumen_completo)} plantillas totales en el export · {buscar6 and f'{len(resumen_f)} tras el filtro de búsqueda'}")


# ────────────────────────────────────────────────────────────────
# TAB 7 · PUSH → DÓNDE SE PIERDE LA RESPUESTA
# ────────────────────────────────────────────────────────────────
with tab7:
    st.markdown('<span class="sec">🔎 Push → Dónde se pierde la respuesta</span>', unsafe_allow_html=True)
    st.caption("Cruza 3 fuentes en vivo: respuesta real, qué contestan, y en qué termina la conversación.")

    if not _dwh_ok:
        st.markdown(f'<div class="alrt">Data Warehouse no conectado: {_dwh_msg}</div>', unsafe_allow_html=True)
    else:
        push_opciones = sorted(cat[cat["activo"]]["conversacion"].unique())
        push_pick = st.selectbox("Elegí un push para analizar", push_opciones, key="t7_push")

        # ── 1) Tasa de respuesta real, granular (fact_deployment_status) ──
        st.markdown('<span class="sec blue">1️⃣ Respuesta real</span>', unsafe_allow_html=True)
        resp_df = dwh_respuesta_push(push_pick)
        if resp_df is None or resp_df.empty or resp_df["enviados"].iloc[0] == 0:
            st.caption(f"Sin envíos de \"{push_pick}\" en los últimos 180 días.")
        else:
            enviados = int(resp_df["enviados"].iloc[0])
            entregados = int(resp_df["entregados"].iloc[0])
            respondidos = int(resp_df["respondidos"].iloc[0])
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(kpi("Enviados", f"{enviados:,}", "últimos 180 días", ""), unsafe_allow_html=True)
            c2.markdown(kpi("Entregados", f"{entregados:,}", f"{safe_pct(entregados, enviados)}%", "ok"),
                        unsafe_allow_html=True)
            c3.markdown(kpi("Respondidos", f"{respondidos:,}", f"{safe_pct(respondidos, entregados)}% de entregados",
                            "warn" if safe_pct(respondidos, entregados) < 30 else "alt"), unsafe_allow_html=True)
            c4.markdown(kpi("No respondieron", f"{entregados - respondidos:,}",
                            f"{safe_pct(entregados - respondidos, entregados)}% de entregados", "dark"),
                        unsafe_allow_html=True)

            # ── ¿Por qué no llegó el mensaje? Motivos reales de no entrega ──
            no_entregados = enviados - entregados
            if no_entregados > 0:
                motivos_df = dwh_motivos_no_entrega(push_pick)
                if motivos_df is not None and not motivos_df.empty:
                    m = motivos_df.iloc[0]
                    etiquetas = {
                        "limite_de_tasa": "Límite de tasa (rate limit)",
                        "revocado": "Revocado",
                        "telefono_invalido": "Teléfono inválido",
                        "parametro_faltante": "Parámetro faltante",
                        "fallo_transferencia_agente": "Falla al transferir a agente",
                        "plantilla_desactivada": "Plantilla desactivada",
                        "falla_general": "Falla general",
                        "no_se_pudo_contactar": "No se pudo contactar",
                        "optout_usuario": "Usuario dio opt-out",
                        "meta_no_entrego": "Meta no entregó",
                    }
                    motivos_vals = {etiquetas[k]: int(m[k]) for k in etiquetas if pd.notna(m[k]) and int(m[k]) > 0}
                    st.markdown('<span class="sec red">¿Por qué no llegó?</span>', unsafe_allow_html=True)
                    if motivos_vals:
                        motivos_serie = pd.Series(motivos_vals).sort_values(ascending=False)
                        clasificados = int(motivos_serie.sum())
                        sin_clasificar = max(0, no_entregados - clasificados)
                        if sin_clasificar > 0:
                            motivos_serie["Sin motivo específico registrado"] = sin_clasificar
                        motivos_df_show = motivos_serie.reset_index()
                        motivos_df_show.columns = ["Motivo", "Cantidad"]
                        motivos_df_show["% del total no entregado"] = (motivos_df_show["Cantidad"] / no_entregados * 100).round(1)
                        fig = px.bar(motivos_df_show.sort_values("Cantidad"), x="Cantidad", y="Motivo",
                                     orientation="h", color_discrete_sequence=[OY_WARN], text="Cantidad")
                        fig.update_traces(texttemplate="%{text:,}", textposition="outside")
                        fig.update_layout(xaxis_title=f"De {no_entregados:,} no entregados", yaxis_title="")
                        st.plotly_chart(sfig(fig, 280), use_container_width=True)
                        boton_descarga(motivos_df_show, f"motivos_no_entrega_{push_pick}.csv", "t7_dl_motivos")
                    else:
                        st.caption(f"{no_entregados:,} no entregados, pero Treble no registró un motivo "
                                   f"específico para ninguno (columnas de falla en cero).")

            # ── ¿El catálogo dice lo mismo que Treble? ──
            estado_catalogo_push = cat[cat["conversacion"] == push_pick]
            estado_catalogo_txt = estado_catalogo_push.iloc[0]["estado"] if len(estado_catalogo_push) else "?"
            act_df = dwh_actividad_reciente(push_pick)
            if act_df is not None and not act_df.empty and pd.notna(act_df["ultimo_envio"].iloc[0]):
                ultimo_envio = pd.to_datetime(act_df["ultimo_envio"].iloc[0]).date()
                dias_desde_ultimo = (pd.Timestamp.now().date() - ultimo_envio).days
                esta_activo_real = dias_desde_ultimo <= 30
                catalogo_dice_activo = estado_catalogo_txt in ("Push Activo", "Manual activo")
                if esta_activo_real != catalogo_dice_activo:
                    st.markdown(
                        f'<div class="crit">🚨 Catálogo dice "{estado_catalogo_txt}" — último envío real: '
                        f'{ultimo_envio} ({dias_desde_ultimo}d atrás). Actualizar catálogo.</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.caption(f"✅ Consistente — último envío: {ultimo_envio} ({dias_desde_ultimo}d atrás).")

            # ── 2) Qué contestan (fact_hsm_responses) — desglosado por paso, y reconciliado ──
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<span class="sec amb">2️⃣ Qué contestan (por paso)</span>', unsafe_allow_html=True)
            hsm_df, hsm_total = dwh_respuestas_hsm(push_pick)
            if hsm_df is None or hsm_df.empty:
                st.caption("Sin respuestas estructuradas (aviso de una sola vía, o texto libre sin clasificar).")
            else:
                # Reconciliación explícita contra la Sección 1 — si no cuadra, lo decimos, no lo escondemos.
                usuarios_unicos_hsm = int(hsm_total["usuarios_unicos"].iloc[0]) if hsm_total is not None and not hsm_total.empty else None
                if usuarios_unicos_hsm is not None:
                    diff = usuarios_unicos_hsm - respondidos
                    if abs(diff) <= max(1, round(respondidos * 0.02)):
                        st.caption(f"✅ Cuadra: {usuarios_unicos_hsm:,} vs. {respondidos:,} respondidos (diferencia {diff:+,}).")
                    else:
                        st.markdown(
                            f'<div class="alrt">⚠️ {usuarios_unicos_hsm:,} usuarios únicos vs. {respondidos:,} '
                            f'"respondidos" (diferencia {diff:+,}) — fact_deployment_status cuenta cualquier '
                            f'respuesta, fact_hsm_responses solo las que calzan con un botón.</div>',
                            unsafe_allow_html=True
                        )

                # Resumen de % por categoría (Confirmar / Reagendar / Otros) — pedido por gerencia
                total_resp_hsm = int(hsm_df["respuestas"].sum())
                top_categorias = hsm_df.groupby("answer_text")["respuestas"].sum().sort_values(ascending=False)
                top3 = top_categorias.head(3)
                otros_n = total_resp_hsm - int(top3.sum())
                resumen_pct = list(top3.items())
                if otros_n > 0:
                    resumen_pct.append(("Otros", otros_n))
                cols_pct = st.columns(len(resumen_pct))
                for col, (etiqueta, n) in zip(cols_pct, resumen_pct):
                    col.markdown(kpi(etiqueta[:22], f"{safe_pct(n, total_resp_hsm)}%", f"{n:,} respuestas", "alt"),
                                 unsafe_allow_html=True)

                pasos_disponibles = sorted(hsm_df["hsm_name"].unique())
                if len(pasos_disponibles) > 1:
                    paso_pick = st.selectbox(f"{len(pasos_disponibles)} pasos con respuesta — ver:",
                                              ["Todos los pasos"] + pasos_disponibles, key="t7_paso")
                else:
                    paso_pick = "Todos los pasos"

                hsm_mostrar = hsm_df if paso_pick == "Todos los pasos" else hsm_df[hsm_df["hsm_name"] == paso_pick]
                resumen_paso = hsm_mostrar.groupby("answer_text")["respuestas"].sum().reset_index().sort_values("respuestas")
                fig = px.bar(resumen_paso.tail(15), x="respuestas", y="answer_text",
                             orientation="h", color_discrete_sequence=[OY_AMBER], text="respuestas")
                fig.update_traces(texttemplate="%{text:,}", textposition="outside")
                layout_kwargs = dict(xaxis_title="Respuestas", yaxis_title="")
                if paso_pick != "Todos los pasos":
                    layout_kwargs["title"] = paso_pick
                fig.update_layout(**layout_kwargs)
                st.plotly_chart(sfig(fig, 380), use_container_width=True)
                st.caption(f"Total de respuestas en este gráfico: {int(resumen_paso['respuestas'].sum()):,}")
                boton_descarga(hsm_df, f"respuestas_{push_pick}.csv", "t7_dl_hsm")

            # ── 3) Dónde termina (fact_sessions status) ──
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<span class="sec purple">3️⃣ Dónde termina la conversación</span>', unsafe_allow_html=True)
            estado_df = dwh_estado_final_push(push_pick)
            if estado_df is None or estado_df.empty:
                st.caption("Sin datos de estado final.")
            else:
                fig = px.pie(estado_df, names="status", values="n", hole=.5, color_discrete_sequence=COLOR_SEQ)
                st.plotly_chart(sfig(fig, 340), use_container_width=True)
                boton_descarga(estado_df, f"estado_final_{push_pick}.csv", "t7_dl_estado")
                if "HumanHandover" in estado_df["status"].values:
                    pct_agente = safe_pct(estado_df[estado_df["status"] == "HumanHandover"]["n"].iloc[0],
                                           estado_df["n"].sum())
                    st.caption(f"{pct_agente}% escala a agente humano.")

        # ── 4) Árbol completo, si este push está en el export de Treble ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<span class="sec red">4️⃣ Mapa completo paso a paso</span>', unsafe_allow_html=True)
        if arbol is None:
            st.caption("Sin export de árbol de conversación cargado.")
        else:
            fila_cat = cat[cat["conversacion"] == push_pick]
            plantilla_hsm = fila_cat.iloc[0]["plantilla"] if len(fila_cat) else None
            candidatos = [push_pick] + ([plantilla_hsm] if plantilla_hsm and plantilla_hsm != "Sin documentar" else [])
            arbol_plantillas = arbol["Plantilla"].unique()
            match_arbol = None
            for cand in candidatos:
                cn = _norm_txt(cand)
                for p in arbol_plantillas:
                    pn = _norm_txt(p)
                    if pn in cn or cn in pn:
                        match_arbol = p
                        break
                if match_arbol:
                    break

            if not match_arbol:
                st.caption("Este push no está en el export del árbol bajo un nombre reconocible.")
            else:
                st.caption(f"✅ Encontrado como: **{match_arbol}**")
                sub_full7 = arbol[arbol["Plantilla"] == match_arbol].copy()
                poll_top7 = sub_full7.groupby("Poll ID")["N Clientes"].sum().idxmax()
                sub_full7 = sub_full7[sub_full7["Poll ID"] == poll_top7].copy()
                total_flujo7 = sub_full7["N Clientes"].sum()
                sub7 = sub_full7[sub_full7["N Clientes"] >= 20].copy()

                if not sub7.empty:
                    nodos7 = list(pd.unique(sub7[["Nodo Origen Key", "Nodo Destino Key"]].values.ravel()))

                    def _paso_de7(n):
                        n = str(n)
                        if " · " in n:
                            return n.split(" · ", 1)[0].strip()
                        return "FIN"

                    codigo7, texto7, contador7 = {}, {}, {}
                    for n in nodos7:
                        paso = _paso_de7(n)
                        if paso == "FIN":
                            codigo7[n] = "✖ " + n.replace("✖ No avanzó ", "").strip()
                            texto7[n] = "Cliente no respondió / no avanzó"
                        else:
                            contador7[paso] = contador7.get(paso, 0) + 1
                            codigo7[n] = f"{paso}-{chr(ord('a') + contador7[paso] - 1)}"
                            texto7[n] = n.split(" · ", 1)[1] if " · " in n else n

                    idx7 = {n: i for i, n in enumerate(nodos7)}
                    pasos_u7 = sorted({_paso_de7(n) for n in nodos7 if _paso_de7(n) != "FIN"})
                    color_p7 = {p: COLOR_SEQ[i % len(COLOR_SEQ)] for i, p in enumerate(pasos_u7)}
                    colores7 = [OY_WARN if _paso_de7(n) == "FIN" else color_p7[_paso_de7(n)] for n in nodos7]
                    linkcol7 = ["rgba(229,72,77,.55)" if f else "rgba(120,120,120,.28)" for f in sub7["Es Fuga"]]
                    sankey7 = go.Figure(go.Sankey(
                        arrangement="snap",
                        node=dict(label=[codigo7[n] for n in nodos7], pad=20, thickness=24,
                                  color=colores7, line=dict(color="rgba(0,0,0,.2)", width=.6)),
                        link=dict(source=sub7["Nodo Origen Key"].map(idx7), target=sub7["Nodo Destino Key"].map(idx7),
                                  value=sub7["N Clientes"], color=linkcol7,
                                  hovertemplate="%{value:,} clientes<extra></extra>")
                    ))
                    st.plotly_chart(sfig(sankey7, 500), use_container_width=True)
                    leyenda7 = pd.DataFrame([{"Código": codigo7[n], "Mensaje completo": texto7[n]} for n in nodos7]).drop_duplicates("Código")
                    st.dataframe(leyenda7, use_container_width=True, hide_index=True, height=260)
                    st.caption("Detalle completo de puntos de quiebre en 🌳 Árbol de Conversación.")


st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption("Dashboard Conversaciones y Pushes Automáticos · Opción Yo — generado con NOVA. "
           "Datos: Data Warehouse de Treble en vivo (con respaldo automático a CSV si no hay conexión), "
           "catálogo interno de plantillas y export de árbol de conversación. "
           "No incluye incidencias técnicas (dashboard aparte).")
