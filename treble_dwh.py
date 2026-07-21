"""
treble_dwh.py — Módulo de conexión al Data Warehouse de Treble (ClickHouse Cloud).

Diseño defensivo: si el DWH está disponible (IP autorizada + credenciales válidas),
las funciones devuelven datos frescos. Si no, devuelven None y el dashboard cae
limpiamente a los CSV del repo. Nunca lanza una excepción que rompa la app.

Requisitos: clickhouse-connect  (agregar a requirements.txt)
Credenciales: se leen de st.secrets, NUNCA hardcodeadas.

Configuración esperada en Streamlit Secrets:
    [treble_dwh]
    host = "eaoxkoa7g7.us-east-1.aws.clickhouse.cloud"
    port = 8443
    username = "opcionyo_readonly"
    password = "········"
    database = "client_analytics"
"""
from __future__ import annotations
import pandas as pd

try:
    import streamlit as st
except Exception:  # permite usar el módulo fuera de Streamlit
    st = None

# ------------------------------------------------------------------
# CONEXIÓN
# ------------------------------------------------------------------
def _get_secrets():
    """Lee credenciales de Streamlit Secrets. Devuelve dict o None si no existen."""
    if st is None:
        return None
    try:
        s = st.secrets["treble_dwh"]
        return {
            "host": s["host"],
            "port": int(s.get("port", 8443)),
            "username": s["username"],
            "password": s["password"],
            "database": s.get("database", "client_analytics"),
        }
    except Exception:
        return None


def dwh_disponible() -> bool:
    """True si hay credenciales configuradas (no garantiza que la IP esté autorizada)."""
    return _get_secrets() is not None


def _conectar(timeout: int = 15):
    """Devuelve un cliente ClickHouse o None si falla (credenciales, red o whitelist)."""
    cfg = _get_secrets()
    if cfg is None:
        return None
    try:
        import clickhouse_connect
        return clickhouse_connect.get_client(
            host=cfg["host"], port=cfg["port"],
            username=cfg["username"], password=cfg["password"],
            database=cfg["database"], secure=True,
            connect_timeout=timeout, send_receive_timeout=30,
        )
    except Exception:
        return None


# ------------------------------------------------------------------
# CONSULTAS (cacheadas 1h). Todas devuelven DataFrame o None.
# ------------------------------------------------------------------
def _query(sql: str):
    client = _conectar()
    if client is None:
        return None
    try:
        return client.query_df(sql)
    except Exception:
        return None
    finally:
        try:
            client.close()
        except Exception:
            pass


# Envoltura con caché sólo si Streamlit está presente
if st is not None:
    _query = st.cache_data(ttl=3600, show_spinner=False)(_query)  # type: ignore


def test_conexion() -> tuple[bool, str]:
    """Prueba la conexión y devuelve (ok, mensaje) para mostrar en la UI."""
    cfg = _get_secrets()
    if cfg is None:
        return False, "No hay credenciales configuradas en Secrets ([treble_dwh])."
    df = _query("SELECT 1 AS ok")
    if df is None:
        return False, ("Credenciales presentes pero no se pudo conectar. "
                       "Causa más probable: la IP del servidor no está en la lista blanca de ClickHouse Cloud. "
                       "Solicita a Treble/Diosnel autorizar las IPs de salida de Streamlit.")
    return True, "Conexión al Data Warehouse de Treble activa."


def listar_tablas():
    """Lista las tablas disponibles en client_analytics."""
    return _query("SHOW TABLES FROM client_analytics")


# ------------------------------------------------------------------
# CONSULTAS DE NEGOCIO (ajustar nombres de columna al confirmar el esquema real)
# ------------------------------------------------------------------
def conversaciones_por_dia(dias: int = 90):
    """Volumen de conversaciones atendidas por día en los últimos N días."""
    return _query(f"""
        SELECT toDate(created_at) AS fecha, count() AS conversaciones
        FROM client_analytics.fact_conversations
        WHERE created_at >= now() - INTERVAL {int(dias)} DAY
        GROUP BY fecha ORDER BY fecha
    """)


def conversaciones_por_agente(dias: int = 30):
    """Conversaciones atendidas por agente en los últimos N días."""
    return _query(f"""
        SELECT agent_name AS agente, count() AS conversaciones
        FROM client_analytics.fact_conversations
        WHERE created_at >= now() - INTERVAL {int(dias)} DAY
          AND agent_name != ''
        GROUP BY agente ORDER BY conversaciones DESC
    """)


def campanias_resumen(dias: int = 30):
    """Resumen de envíos outbound por campaña: entregados y respuestas."""
    return _query(f"""
        SELECT
            toDate(date) AS fecha,
            count() AS envios
        FROM client_analytics.fact_deployment_daily
        WHERE date >= today() - {int(dias)}
        GROUP BY fecha ORDER BY fecha
    """)


def query_libre(sql: str):
    """Ejecuta un SELECT arbitrario (para exploración). Sólo lectura."""
    limpio = sql.strip().rstrip(";").lower()
    if not limpio.startswith(("select", "show", "describe", "with")):
        return None  # sólo consultas de lectura
    return _query(sql)
