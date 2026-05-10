# Reportes contables y fiscales

Cubre el motor `account.report` (Odoo 16+), modelos AEAT, generacion de
PDFs de factura y exportes BOE.

## Motor `account.report` (Odoo 16+)

Desde Odoo 16, los reportes contables se unificaron en un sistema
declarativo:

- `account.report` - definicion del informe (lineas, columnas).
- `account.report.line` - cada linea con su `expression_label`.
- `account.report.expression` - formula (`engine`: `domain`, `tax_tags`,
  `account_codes`, `aggregation`, `external`).
- `account.report.column` - columnas (periodo actual, comparativo, etc.).

En Odoo 19 se unifico ademas Balance + P&L + trial balance en un unico
informe anual con vistas configurables.

### Listar reportes disponibles

```python
reports = client.search_read("account.report",
    [("country_id.code", "=", "ES")],
    ["id", "name", "country_id"])
```

### Ejecutar un reporte

```python
report_id = client.search_read("account.report",
    [("name", "=", "Balance Sheet")], ["id"], limit=1)[0]["id"]

options = client.call("account.report", "_get_options",
    [report_id, {"date": {"date_from": "2026-01-01",
                          "date_to":   "2026-03-31",
                          "filter":    "custom",
                          "mode":      "range"}}])

lines = client.call("account.report", "_get_lines", [report_id, options])
```

## Modelos AEAT espanoles

| Modelo | Periodicidad | Concepto |
|--------|--------------|----------|
| 111 | Trimestral | Retenciones e ingresos a cuenta - rendimientos del trabajo y profesionales |
| 115 | Trimestral | Retenciones IRPF arrendamientos urbanos |
| 130 | Trimestral | Pago fraccionado IRPF (estimacion directa) |
| 303 | Trimestral o mensual (REDEME) | Autoliquidacion IVA |
| 347 | Anual (febrero) | Operaciones con terceros > 3.005,06 EUR |
| 349 | Mensual o trimestral | Operaciones intracomunitarias |
| 369 | Trimestral | Ventanilla unica (OSS/IOSS) |
| 390 | Anual (enero) | Resumen anual IVA |

### Modulos

Enterprise: `l10n_es_reports` cubre todos.

Community/OCA:
- `l10n_es_aeat` (motor base)
- `l10n_es_aeat_mod111`, `mod115`, `mod130`, `mod303`, `mod347`, `mod349`,
  `mod369`, `mod390`.
- `l10n_es_vat_book` (libro IVA emitido/recibido).
- `l10n_es_vat_prorate` (prorrata).

### Casillas clave del 303 (resumen)

| Casilla | Concepto |
|---------|----------|
| 01-09 | IVA devengado regimen general (base, tipo, cuota) por tipo |
| 10-11 | Adquisiciones intracomunitarias (base + cuota) |
| 12-13 | Otras operaciones con ISP (base + cuota) |
| 14-15 | Modificacion bases y cuotas |
| 28-39 | IVA deducible operaciones interiores corrientes |
| 40-41 | IVA deducible importaciones |
| 46 | Cuota a compensar de periodos anteriores |
| 47 | Cuota a deducir |
| 65-66 | Atribuible al Estado / a las Diputaciones Forales |
| 69 | Resultado |
| 71 | A devolver / A compensar / A ingresar |

Mapeo Odoo: `account.account.tag` con prefijo `+303.<casilla>` o `-303.<casilla>`
sumando o restando las contrapartidas. La asignacion correcta de tags es
critica - el skill debe verificar que las cuentas usadas tienen los tags
adecuados antes de ejecutar el modelo.

### Generar el modelo y exportar BOE

Patron Enterprise (`l10n_es_reports`):

```python
report_id = client.search_read("account.report",
    [("name", "=", "Tax Report (Modelo 303)")], ["id"], limit=1)[0]["id"]

options = client.call("account.report", "_get_options",
    [report_id, {"date": {"date_from": "2026-01-01",
                          "date_to":   "2026-03-31",
                          "mode":      "range",
                          "filter":    "custom"}}])

# Exporta segun handler especifico ES:
boe_export = client.call("account.report", "l10n_es_reports_export_boe",
    [report_id, options])
```

Patron OCA (`l10n_es_aeat_mod303`):

```python
mod303_id = client.create("l10n.es.aeat.mod303.report", {
    "name": "303-2026Q1",
    "company_id": 1,
    "year": 2026,
    "period_type": "1T",
    "tipo_declaracion": "I",  # I=Ingreso, U=Domiciliacion, etc.
})
client.action("l10n.es.aeat.mod303.report", [mod303_id], "calculate")
client.action("l10n.es.aeat.mod303.report", [mod303_id], "confirm")

# Exportar BOE:
boe_txt = client.call("l10n.es.aeat.mod303.report",
    "export_boe", [[mod303_id]])
```

El formato BOE son ficheros TXT de longitud fija con codificacion
ISO-8859-1, listos para subir al portal AEAT (o presentar via certificado
con `l10n_es_aeat_certificate_*`).

## PDF de factura

### Reporte estandar

```python
report_id = client.search_read("ir.actions.report",
    [("report_name", "=", "account.report_invoice")],
    ["id"], limit=1)[0]["id"]

pdf_b64, _ext = client.call("ir.actions.report",
    "_render_qweb_pdf", [report_id, [invoice_id]])
```

### Variantes con datos EDI

- `account.report_invoice_with_payments` - incluye historico de cobros.
- `l10n_es_edi_verifactu.report_invoice_verifactu` - incluye QR Veri*Factu.
- `l10n_es_edi_TBAI.report_invoice_tbai` - incluye QR TicketBAI.

Escoger el correcto segun lo instalado.

### Adjuntar PDF al `mail.message`

Si se quiere enviar la factura por email, el patron es:

```python
template_id = client.search_read("mail.template",
    [("model", "=", "account.move"),
     ("name", "ilike", "Customer Invoice")],
    ["id"], limit=1)[0]["id"]

client.action("account.move", [invoice_id], "message_post_with_template",
    ctx={"template_id": template_id})
```

(En la practica, el wizard `account.move.send` automatiza envio + EDI +
PDF en una sola pasada en Enterprise.)

## Libros de IVA

Modulos OCA:
- `l10n_es_vat_book` - libro IVA emitido y recibido por trimestre.
- `l10n_es_aeat_sii` - registros SII (sirven tambien como libro IVA).

Exportable a XLSX y a PDF.

## Reportes "ad-hoc" via `read_group`

Para preguntas tipo "facturas pendientes de cobro de clientes ES > 5.000 EUR":

```python
client.call("account.move", "read_group",
    [
        [("move_type", "=", "out_invoice"),
         ("state", "=", "posted"),
         ("payment_state", "in", ["not_paid", "partial"]),
         ("partner_id.country_id.code", "=", "ES"),
         ("amount_residual", ">", 5000)],
        ["amount_residual", "partner_id"],
        ["partner_id"]
    ],
    {"orderby": "amount_residual desc"})
```

En Odoo 19+ existe `formatted_read_group` que devuelve los valores ya
formateados (Monetary con simbolo, fechas locale, etc.).

## Limitaciones conocidas

1. Los **MCP servers genericos no exponen `ir.actions.report`** (solo CRUD).
   Para PDFs siempre usar `scripts/report_invoice_pdf.py`.
2. La generacion de PDFs es lenta (~1-3 segundos por factura) por wkhtmltopdf;
   para batch, usar `_render_qweb_pdf` con varios IDs en una sola llamada.
3. Los exportes BOE de OCA cambian de formato segun ano fiscal; verificar
   que la version del modulo coincide con el ano del modelo.
4. `account.report._get_lines` puede ser muy pesado en empresas con
   millones de `account.move.line`; usar `tax_lock_date` para acelerar
   recalculos.
