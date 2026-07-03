# 💳 Opción Yo — Dashboard de Reembolsos y Disputas

Dashboard ejecutivo en Streamlit para monitorear reembolsos y disputas de pagos (Stripe), con foco en detectar disputas próximas a vencer antes de que se pierdan por default.

**App en vivo:** _(pega aquí la URL una vez desplegada, ej. `opcionyo-reembolsos.streamlit.app`)_

---

## ¿Qué resuelve?

- Reconcilia reembolsos y disputas del mes, separando **pago del mismo mes** vs. **pago de meses anteriores** (métrica pedida por Roberto/gerencia).
- Calcula el monto total en riesgo por mes: `reembolsos + (monto disputado + fee de disputa Stripe)`.
- **Alerta de disputas urgentes**: lista las disputas en `needs_response` / `under_review` ordenadas por fecha límite de evidencia (`Dispute Evidence Due`), marcando en rojo las ya vencidas.
- Desglose por motivo de disputa, tipo de cargo, y clientes con reembolsos recurrentes.

## Fuente de datos

Exportación **unified_payments** (Stripe), CSV. Columnas clave usadas:

| Columna | Uso |
|---|---|
| `Refunded date (UTC)` | Asigna el reembolso a su mes de ocurrencia |
| `Dispute Date (UTC)` | Asigna la disputa a su mes de ocurrencia |
| `Created date (UTC)` | Determina si el pago original fue del mismo mes o anterior |
| `Amount Refunded` | Monto reembolsado |
| `Disputed Amount` + `Fee` | Monto en disputa + fee fijo de Stripe ($15/caso) |
| `Dispute Evidence Due (UTC)` | Fecha límite para responder — base de la pestaña de urgentes |
| `Customer Email` | ⚠️ Dato sensible — ver sección Privacidad |

## Estructura del repo

```
dashboard_reembolsos_disputas.py   # App Streamlit (single-file)
requirements.txt                    # streamlit, pandas, plotly
runtime.txt                         # Fuerza Python 3.12 en Streamlit Cloud
```

## Deploy

1. Repo debe ser **privado** (contiene emails de clientes).
2. [share.streamlit.io](https://share.streamlit.io) → New app → seleccionar este repo, branch `main`, main file `dashboard_reembolsos_disputas.py`.
3. Al abrir la app, subir el CSV `unified_payments.csv` cuando se solicite.

## ⚠️ Privacidad

Este repo contiene `Customer Email` en el CSV de datos si se llega a subir un archivo de ejemplo al repo. **Mantener el repo en modo Private siempre.** No subir CSVs de datos reales a `data/` del repo sin verificar visibilidad antes de cada commit.

## Limitaciones conocidas (roadmap)

- [ ] **Sin persistencia**: cada sesión requiere resubir el CSV manualmente. Pendiente decidir entre:
  - Persistencia vía GitHub (patrón `gh_load_df()`/`gh_save_df()` ya usado en `opcionyo-dashboard-atc`)
  - Conexión directa a Stripe API (recomendado — data en vivo, crítico para la pestaña de disputas urgentes)
- [ ] Sin cruce automático con tickets de HubSpot (`FID- Rescate de reembolsos`, `ADMIN- Disputa`) — hoy es análisis manual puntual.

## Mantenido por

Roberto Ortega (Data/CRM/Operaciones) — Opción Yo
