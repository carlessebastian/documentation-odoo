# Automatizacion - importacion masiva, recurrencia, lotes

Patrones para operar en lote (decenas o miles de registros) con seguridad
e idempotencia.

## Importacion masiva de facturas (CSV/Excel)

### Formato CSV recomendado

Una fila por linea de factura. Las cabeceras de factura se duplican en
cada linea (la importacion las agrupa por `ref`):

```csv
ref,move_type,partner_vat,invoice_date,invoice_date_due,line_name,line_qty,line_price,line_tax_codes
WEB-2026-0001,out_invoice,ESB12345678,2026-05-01,2026-05-31,Servicio enero,1,1000.00,S_IVA21B
WEB-2026-0001,out_invoice,ESB12345678,2026-05-01,2026-05-31,Material,5,20.00,S_IVA21B
WEB-2026-0002,out_invoice,ESA28015865,2026-05-02,2026-06-01,Consultoria,8,75.00,S_IVA21B
```

El script `bulk_invoice_import.py` lo procesa: agrupa por `ref`, resuelve
partners por VAT, resuelve impuestos por nombre, llama a
`create_invoice.py::create_or_update_invoice` (idempotente).

### Excel (XLSX)

`bulk_invoice_import.py --format xlsx` requiere `openpyxl`. El script
hace fallback a `pip install openpyxl` solo si esta presente; si no,
recomienda exportar a CSV.

### Manejo de errores en lote

- **Continue on error**: por defecto, una fila fallida NO interrumpe el
  resto. El script devuelve un JSON con `created`, `updated`, `errors[]`.
- **Atomic mode**: con `--atomic`, todas las facturas se procesan en
  borrador primero; si todas pasan validacion, se postean. Si alguna
  falla, ninguna se postea.
- **Tamano de batch**: por defecto 50 facturas por commit; ajustable con
  `--batch-size`.

## Facturacion recurrente / suscripciones

### Modulos relevantes

| Modulo | Origen | Uso |
|--------|--------|-----|
| `sale_subscription` | Enterprise | Suscripciones nativas |
| `account_invoice_recurring` | OCA | Facturacion recurrente sin sale_subscription |
| `subscription_oca` | OCA | Suscripciones avanzadas |
| `contract` | OCA | Contratos con facturacion recurrente |

### Patron generico (sin modulo de suscripciones)

Mantener una "plantilla maestra" como factura draft que NO se postea.
Cada periodo:

1. Duplicar la plantilla con `copy()`.
2. Setear `invoice_date` y `ref` con el periodo nuevo.
3. Postear la copia.

```python
new_id = client.call("account.move", "copy",
    [[template_id]], {"default": {
        "invoice_date": "2026-06-01",
        "invoice_date_due": "2026-06-30",
        "ref": f"SUBS-{partner_id}-2026-06",
    }})
client.action("account.move", [new_id], "action_post")
```

El script `recurring_invoice.py` automatiza esto para una lista de
plantillas + frecuencia (mensual, trimestral, anual).

### Con `sale_subscription` (Enterprise)

```python
# Forzar generacion de facturas pendientes
subs = client.search_read("sale.subscription",
    [("stage_id.category", "=", "progress"),
     ("recurring_next_date", "<=", today)],
    ["id"])
client.action("sale.subscription",
    [s["id"] for s in subs], "_recurring_create_invoice")
```

## Operaciones en lote (post / payment / send)

### Bulk post

```python
draft_ids = client.search_read("account.move",
    [("state", "=", "draft"), ("move_type", "in",
        ["out_invoice", "out_refund"])],
    ["id"], limit=200)["ids"]
# Validar pre-post con verify_es_compliance.py
client.action("account.move", draft_ids, "action_post")
```

**Ojo**: si una factura en el lote falla la validacion espanola (NIF,
fiscal_position), la transaccion se aborta y NINGUNA se postea.
Recomendable validar individualmente y postear solo las que pasan.

### Bulk payment registration

`account.payment.register` acepta multiples `active_ids`. Con
`group_payment=True` agrupa todas las facturas del mismo partner+banco
en un solo `account.payment`.

```python
ctx = {"active_model": "account.move", "active_ids": invoice_ids}
reg_id = client.call("account.payment.register", "create",
    [{"journal_id": bank_id, "group_payment": True}],
    {"context": ctx})
client.call("account.payment.register", "action_create_payments",
    [[reg_id]], {"context": ctx})
```

### Bulk send (email + EDI + PDF)

En Enterprise, `account.move.send` (wizard) hace todo de una pasada:
genera PDF, adjunta XML EDI (FacturaE/Verifactu/SII), envia email.

```python
ctx = {"active_model": "account.move", "active_ids": invoice_ids}
wiz_id = client.call("account.move.send", "create",
    [{"checkbox_send_mail": True, "checkbox_download": False}],
    {"context": ctx})
client.call("account.move.send", "action_send_and_print",
    [[wiz_id]], {"context": ctx})
```

En Community sin el wizard, llamar `message_post_with_template` por
factura.

## Performance y limites

| Operacion | Throughput tipico (self-hosted, hardware medio) |
|-----------|---------------------------------------------------|
| `create` factura simple (1-3 lineas) | 10-30/seg |
| `action_post` factura (sin EDI) | 5-15/seg |
| `action_post` con SII/Verifactu sincrono | 1-3/seg |
| `_render_qweb_pdf` factura | 0.5-2/seg |
| Bulk `read_group` 100k lineas | 1-5 seg total |

### Optimizaciones recomendadas

1. **Disable EDI durante import masivo**: setear
   `journal.l10n_es_verifactu_enabled=False` temporalmente, importar,
   reactivar y enviar manualmente.
2. **Pre-cachear**: resolver partners e impuestos una sola vez al
   inicio, mantener en dict local.
3. **Batch en commits de 50-100**: balance entre overhead de transaccion
   y riesgo de rollback de mucho trabajo.
4. **Workers**: aumentar `workers` en `odoo.conf` para paralelizar
   peticiones HTTP (no ayuda dentro de una misma request).
5. **No hacer `search` con dominio vacio** en `account.move.line` en
   empresas grandes; siempre filtrar por `company_id` y rango de fechas.

## Idempotencia en lotes

Cada script de lote del skill busca por `ref` antes de crear:

```python
existing = client.search_read("account.move",
    [("ref", "=", row["ref"]),
     ("partner_id", "=", partner_id),
     ("move_type", "=", row["move_type"])],
    ["id", "state"], limit=1)
if existing and existing[0]["state"] == "posted":
    return "already_posted"
```

Esto permite **reintentar el mismo CSV** sin duplicar facturas. Si el
batch fallo en la fila 47 de 100, basta volver a ejecutarlo: las
primeras 46 se detectaran como `already_posted`.

## Logging y auditoria

Cada script de lote produce JSON estructurado al stdout. Para auditoria
permanente:

```bash
python3 bulk_invoice_import.py --file ventas-mayo.csv --post \
  | tee logs/import-$(date +%F).json
```

Y en Odoo, cada operacion del usuario bot queda en su `mail.message`
historico (visible en el chatter del registro afectado).
