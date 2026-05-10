# Tesoreria - cuentas por cobrar/pagar, conciliacion, dunning, KPIs

Workflows de tesoreria diaria. Para mecanica basica de pagos, ver
`workflows.md`.

## Aged receivables / payables (antiguedad de saldos)

Concepto: agrupar facturas no cobradas/pagadas por antiguedad (buckets:
no vencido, 1-30, 31-60, 61-90, >90 dias).

### Datos fuente

- `account.move.line` con `account_id.account_type` in
  (`asset_receivable`, `liability_payable`).
- `parent_state='posted'`, `reconciled=False`, `amount_residual != 0`.
- `date_maturity` define el vencimiento; si no esta, usar `date`.

### Calculo de bucket

```python
from datetime import date, timedelta

def bucket(due: str, today: date) -> str:
    d = date.fromisoformat(due) if due else today
    delta = (today - d).days
    if delta < 0: return "not_due"
    if delta <= 30: return "1-30"
    if delta <= 60: return "31-60"
    if delta <= 90: return "61-90"
    return "+90"
```

### Reporte estandar

Odoo Enterprise tiene `Aged Receivable` y `Aged Payable` en
`account.aged.partner.balance.report` (o `account.report` con name
"Aged Receivable"). OCA equivalente: `account_financial_report`.

El script `aged_balance.py` reimplementa el calculo via `read_group` para
no depender del modulo de reporte.

## Conciliacion bancaria

### Importacion de extractos

Formatos soportados nativamente en Odoo:

| Formato | Modulo |
|---------|--------|
| CAMT.053 (ISO 20022, EU bank standard) | `account_bank_statement_import_camt` (Enterprise/OCA) |
| OFX (Open Financial Exchange) | `account_bank_statement_import_ofx` |
| QIF (Quicken) | `account_bank_statement_import_qif` |
| CSV | `account_bank_statement_import_csv` (OCA) |
| Norma 43 (BBVA / banca espanola) | `account_bank_statement_import_n43` (OCA) |

Patron generico via wizard:

```python
ctx = {"journal_id": bank_journal_id}
wiz_id = client.call("account.statement.import", "create",
    [{"attachment_ids": [(0, 0, {
        "name": "extract.csv",
        "datas": base64_content,
    })]}],
    {"context": ctx})
result = client.call("account.statement.import", "import_file_button",
    [[wiz_id]], {"context": ctx})
```

El wizard crea uno o varios `account.bank.statement` con sus
`account.bank.statement.line`.

### Reconciliacion automatica

Odoo aplica `account.reconcile.model` (reglas) automaticamente al subir el
extracto. Tipos de regla:

| Type | Comportamiento |
|------|----------------|
| `invoice_matching` | Empareja con factura por importe/referencia/partner |
| `writeoff_button` | Permite write-off manual |
| `writeoff_suggestion` | Sugiere contrapartida con cuenta + impuesto fijo |

Sin reglas activas, las lineas quedan en estado `not_reconciled` y deben
emparejarse via UI o programaticamente:

```python
# Emparejar linea de extracto con factura especifica
client.call("account.bank.statement.line", "set_line_bank_statement_line",
    [[stmt_line_id]], {"counterpart_aml_dicts": [{"id": aml_id}]})
```

En Odoo 17+ el metodo cambio. Patron transversal: usar
`account.bank.statement.line.action_post()` tras setear contrapartidas en
`line_ids`.

### Heuristicas de matching para Espana

1. **Concepto bancario**: contiene `name` o `ref` de la factura. Buscar
   coincidencias de >= 6 caracteres del `ref` en `payment_ref`.
2. **Importe exacto**: `abs(stmt.amount) == invoice.amount_residual`.
3. **Partner via cuenta IBAN**: si el extracto tiene `account_number`,
   buscar en `res.partner.bank.acc_number`.
4. **Tolerancia centimos**: aceptar diferencia <= 0.05 EUR.

## Dunning (recordatorios de cobro)

Odoo Enterprise tiene `account.followup` con niveles configurables (5, 15,
30, 60 dias post-vencimiento). En Community usar OCA
`account_followup` o invocar plantilla `mail.template` manualmente.

### Niveles tipicos en Espana

| Nivel | Dias post-venc. | Tono | Accion adicional |
|-------|-----------------|------|------------------|
| 1 | 7-15 | Recordatorio amistoso | Solo email |
| 2 | 30 | Insistente | Email + llamada |
| 3 | 60 | Reclamacion formal | Email + carta certificada |
| 4 | 90+ | Pre-juridico | Cesion a recuperacion |

### Patron de envio masivo

```python
overdue = client.search_read("account.move",
    [("move_type", "=", "out_invoice"),
     ("state", "=", "posted"),
     ("payment_state", "in", ["not_paid", "partial"]),
     ("invoice_date_due", "<=", today_iso)],
    ["id", "partner_id", "amount_residual", "invoice_date_due"])

template_id = ...  # mail.template para "Recordatorio cobro nivel 1"

for inv in overdue:
    client.action("account.move", [inv["id"]],
        "message_post_with_template",
        ctx={"template_id": template_id})
```

Para evitar spam (no enviar mismo nivel dos veces en 7 dias), guardar
ultimo envio en `account.move.x_last_followup_date` (campo custom) o
inferirlo del `mail.message` historico.

## Dashboard de KPIs

### KPIs estandar de tesoreria

| KPI | Formula |
|-----|---------|
| **DSO** (Days Sales Outstanding) | (Cuentas por cobrar / Ventas periodo) * dias periodo |
| **DPO** (Days Payable Outstanding) | (Cuentas por pagar / Compras periodo) * dias periodo |
| **DIO** (Days Inventory Outstanding) | (Inventario medio / COGS periodo) * dias periodo |
| **CCC** (Cash Conversion Cycle) | DSO + DIO - DPO |
| **Working Capital** | Activo corriente - Pasivo corriente |
| **Quick Ratio** | (Activo corriente - Inventario) / Pasivo corriente |
| **Current Ratio** | Activo corriente / Pasivo corriente |

### Datos para los calculos

```python
# Cuentas por cobrar (saldo)
ar = client.call("account.move.line", "read_group",
    [[("account_id.account_type", "=", "asset_receivable"),
      ("parent_state", "=", "posted"),
      ("reconciled", "=", False)],
     ["amount_residual:sum"], []])

# Ventas del periodo (sin impuestos, sin abonos)
sales = client.call("account.move.line", "read_group",
    [[("account_id.account_type", "=", "income"),
      ("parent_state", "=", "posted"),
      ("date", ">=", date_from), ("date", "<=", date_to)],
     ["balance:sum"], []])
# Notar: balance en cuentas de ingreso es NEGATIVO (credito > debito)
```

### Cash flow forecast (12 semanas)

Proyectar:
1. Ingresos: facturas posted con `invoice_date_due` futuro + recurrentes.
2. Egresos: facturas proveedor pendientes + nominas + impuestos previstos.
3. Saldo bancario inicial (de `account.account` cuenta tesoreria).

Output tipico: tabla semana x (ingreso, egreso, saldo).

## Combinando con otros modulos

- **Multi-divisa**: el script `dashboard_kpis.py` debe consolidar al
  `company_id.currency_id` usando `currency_id.compute()`.
- **Inter-company**: filtrar por `company_id` o consolidar varias.
- **Analitica**: agrupar KPIs por `analytic_distribution` (proyecto,
  centro de coste).

## Limitaciones y caveats

1. **Tasas de cambio historicas**: Odoo usa la tasa de la fecha del
   movimiento, no la spot actual. Para revaluacion al cierre, ver
   `cierre-periodico.md`.
2. **Notas de credito**: restan del saldo del partner pero **siguen
   apareciendo** en aged si no se reconcilian con la factura original.
   Idealmente reconciliar abono <-> factura para limpiar el report.
3. **Conciliacion parcial**: una factura puede tener varios pagos; usar
   `amount_residual` (no `amount_total`) en aged.
4. **Lock dates**: postear nuevos `account.move` para reconciliar puede
   fallar si la fecha cae en periodo bloqueado.
