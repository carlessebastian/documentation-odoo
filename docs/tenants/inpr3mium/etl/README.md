# ETL Holded → Odoo (tenant inpr3mium)

Scripts ad-hoc para migrar el histórico de Holded (dump
`docs/tenants/inpr3mium/holded-export/<YYYY-MM-DD>/`) a la instancia
Odoo 19 destino. Diseño completo en
[`../migration-from-holded.md`](../migration-from-holded.md) sección
**"ETL Fase 5.1 — Diseño detallado"**.

> No es una skill nueva. Justificación en 5.1: fedefarma migra desde
> Axional y los loaders dependen de decisiones concretas inpr3mium
> (catch-all `p_iva_exento`, sales channels). Si en 5.4 los scripts
> resultan limpios y aparece otro tenant Holded, se promueve a skill
> `holded-to-odoo`.

## Estado de implementación

| # | Loader | Volumen | Estado |
|---|---|---:|---|
|   | `holded_resolvers.py` | — | **scaffold** (Fase 5.1) |
|   | `tax_reclassification.yaml` | — | **schema vacío** — operador rellena en 5.3 |
| 0a | `loader_expenseaccounts.py` | 148 | TODO |
| 0b | `loader_saleschannels.py` | 38 | TODO |
| 1 | `loader_partners.py` | 3.363 + 1 unknown | TODO |
| 2 | `loader_products.py` | 2.009 | TODO |
| 3 | `loader_invoices.py` | 3.430 | TODO |
| 4 | `loader_purchases.py` | 7.998 | TODO |
| 5 | `loader_creditnotes.py` | 678 | TODO |
| 6 | `loader_purchaserefunds.py` | 69 | TODO |
| 7 | `loader_payments.py` | 701 | TODO |
| 8 | `loader_dailyledger.py` | ~800–1.500 (filtrado) | TODO |
| 9 | `loader_attachments.py` | 7.489 | TODO |
| 10 | `validate_etl.py` | — | TODO |

## Variables de entorno

Reusa la config Odoo del repo (`.env`):

| Variable | Uso |
|---|---|
| `ODOO_AGENT_TENANT=inpr3mium` | selecciona tenant activo |
| `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` | RPC destino |
| `HOLDED_DUMP_DIR` | path al dump (default: último `holded-export/<YYYY-MM-DD>/`) |

## Estructura

```
etl/
├── README.md                     # este archivo
├── holded_resolvers.py           # 4 resolvers + helpers puros + cache
├── tax_reclassification.yaml     # heurísticas catch-all (rellena operador en 5.3)
├── loader_*.py                   # 11 loaders + validate (TODO)
└── tests/
    ├── conftest.py
    └── test_holded_resolvers.py
```

## Convenciones

- **Idempotencia por ext_id**: cada record Holded importado se persiste
  en `ir.model.data` con XML-ID `__holded__.<resource>_<holdedId>` vía
  `ext_id_upsert.py` del skill `odoo-functional-admin`. Esquema en
  `migration-from-holded.md` sección 5.1 "Estrategia general".
- **CLI uniforme** en cada loader:
  ```
  --dump-dir PATH        path al dump (default: $HOLDED_DUMP_DIR)
  --dry-run              valida resolución sin escribir; emite report CSV
  --limit N              procesa solo N records (debug)
  --resume               continúa desde etl-state/<run-id>/cursor.json
  --batch-size N         default 100
  ```
- **Estado y reanudación**: `etl-state/<run-id>/cursor.json` con
  `{loader, last_id_processed, batch_n}`. Failed batches en
  `etl-state/<run-id>/failed_<loader>.jsonl` para revisión.
- **Reuse de infra**: `holded_resolvers.py` importa `OdooClient` y
  `ext_id_upsert.upsert` del skill `odoo-functional-admin`. Los
  loaders harán lo mismo. No duplicamos `_common.py`/`odoo_client.py`
  aquí porque el directorio `etl/` no es portable (es del tenant).

## Cómo ejecutar

Pre-vuelo (siempre antes de un loader nuevo):

```bash
# 1. activar el venv del repo
source .venv/bin/activate

# 2. asegurar que el .env del repo tiene ODOO_* + ODOO_AGENT_TENANT=inpr3mium
export $(grep -v '^#' .env | xargs)

# 3. dry-run del loader objetivo
PYTHONPATH=".claude/skills/odoo-functional-admin/scripts:docs/tenants/inpr3mium/etl" \
  python3 docs/tenants/inpr3mium/etl/loader_<X>.py --dry-run --limit 10
```

Run real:

```bash
PYTHONPATH=".claude/skills/odoo-functional-admin/scripts:docs/tenants/inpr3mium/etl" \
  python3 docs/tenants/inpr3mium/etl/loader_<X>.py
```

## Tests

```bash
cd docs/tenants/inpr3mium/etl
python3 -m pytest tests/ -q
```

Tests offline: validan helpers puros de `holded_resolvers.py`
(VAT normalize, journal prefix parse, PGCE parent derivation,
unix→ISO, partner activeness). No tocan red ni Odoo.

## Orden de ejecución para Fase 5.3 (validación subset 2024+2025)

1. Pre-load subcuentas: `loader_expenseaccounts.py` → `loader_saleschannels.py`
   (dry-run primero, real después).
2. Partners + products: `loader_partners.py` → `loader_products.py`.
3. Docs subset 2024+2025: invoices → purchases → creditnotes →
   purchaserefunds. Sin PDFs (paso 9 diferido a 5.4).
4. Payments del subset.
5. dailyledger filtrado del subset → revisión manual del
   `dailyledger_classification.csv` antes de cargar.
6. `validate_etl.py` con queries de cuadre.
7. Limpiar moves de validación antes de 5.4: ver Riesgo #5 en 5.1.
