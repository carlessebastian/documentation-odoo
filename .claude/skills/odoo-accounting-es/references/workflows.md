# Workflows contables - recetas paso a paso

Recetas listas para ejecutar via `scripts/odoo_client.py` o equivalentes.
Todos los ejemplos asumen `from scripts.odoo_client import OdooClient;
client = OdooClient()`.

## Crear factura cliente y postear

```python
partner_id = client.search_read("res.partner",
    [("vat", "=", "ESB12345678")], ["id"], limit=1)[0]["id"]

journal_id = client.search_read("account.journal",
    [("type", "=", "sale"), ("company_id", "=", 1)], ["id"], limit=1)[0]["id"]

iva21_id = client.search_read("account.tax",
    [("name", "=", "S_IVA21B"), ("type_tax_use", "=", "sale")],
    ["id"], limit=1)[0]["id"]

invoice_id = client.create("account.move", {
    "move_type": "out_invoice",
    "partner_id": partner_id,
    "invoice_date": "2026-05-10",
    "invoice_date_due": "2026-06-09",
    "journal_id": journal_id,
    "ref": "WEB-2026-0042",
    "invoice_line_ids": [
        (0, 0, {
            "name": "Consultoria mayo 2026",
            "quantity": 10,
            "price_unit": 75.00,
            "tax_ids": [(6, 0, [iva21_id])],
        }),
    ],
})

client.action("account.move", [invoice_id], "action_post")
```

Para el patron idempotente (busca por `ref`+partner antes de crear), usa
`scripts/create_invoice.py`.

## Crear factura proveedor (vendor bill)

Identico al anterior cambiando `move_type='in_invoice'` y usando un diario
`type='purchase'`. Las cuentas analiticas, retenciones IRPF y la fecha de
recepcion (`invoice_date`) deben validarse contra las del proveedor.

## Registrar cobro o pago

`account.payment.register` es un wizard transient. NO crear directamente
`account.payment` (rompe la conciliacion automatica con la factura).

```python
ctx = {"active_model": "account.move", "active_ids": [invoice_id]}

bank_journal_id = client.search_read("account.journal",
    [("type", "in", ["bank", "cash"])], ["id"], limit=1)[0]["id"]

reg_id = client.call("account.payment.register", "create",
    [{
        "payment_date": "2026-05-12",
        "journal_id": bank_journal_id,
    }],
    {"context": ctx})

client.call("account.payment.register", "action_create_payments",
    [[reg_id]], {"context": ctx})
```

Para pagos parciales: anadir `"amount": 100.0` al dict del wizard.

Para pagar varias facturas con un unico `account.payment`: pasar varios
`active_ids` y anadir `"group_payment": True`.

Comprobacion posterior: `payment_state` de la factura debe pasar a `paid`,
`partial` o `in_payment`.

## Crear factura rectificativa (nota de credito)

NO modifiques una factura posteada. Usa `account.move.reversal`:

```python
ctx = {"active_model": "account.move", "active_ids": [invoice_id]}

rev_id = client.call("account.move.reversal", "create",
    [{
        "date": "2026-05-15",
        "reason": "Devolucion parcial",
        "journal_id": journal_id,
    }],
    {"context": ctx})

# Opcion A: solo crear la rectificativa por diferencias
client.call("account.move.reversal", "reverse_moves", [[rev_id]],
    {"context": ctx})

# Opcion B: cancelar la original y crear una nueva
# client.call("account.move.reversal", "modify_moves", [[rev_id]],
#     {"context": ctx})
```

En Odoo 17+ se elimino el campo `refund_method`. La eleccion la haces
llamando a `reverse_moves` (rectificativa por diferencias) o
`modify_moves` (cancelar y crear nueva).

Si Veri*Factu esta activo, ambas operaciones encadenan registros AEAT y la
numeracion debe permanecer secuencial.

## Conciliacion bancaria

Flujo recomendado:

1. Importar extracto en `account.bank.statement` (manual, OFX, CSV, CAMT
   o conector bancario).
2. Para cada `account.bank.statement.line`, ejecutar
   `js_assign_outstanding_line` o usar `account.reconcile.model` con regla
   automatica.
3. Verificar que el `payment_state` de las facturas pasa a `paid`.

```python
sl_id = client.create("account.bank.statement.line", {
    "statement_id": statement_id,
    "date": "2026-05-12",
    "payment_ref": "TRF FRA WEB-2026-0042",
    "amount": 907.50,
    "partner_id": partner_id,
})
```

La reconciliacion programatica suele requerir un metodo helper o un modulo
custom; para casos simples se hace via UI. Los scripts del skill no la
incluyen por defecto.

## Multi-divisa

Setear `currency_id` distinto a `company_id.currency_id` activa el
calculo automatico de `amount_currency` y `balance` siempre que exista
`res.currency.rate` para `invoice_date`.

```python
usd = client.search_read("res.currency", [("name", "=", "USD")],
    ["id"], limit=1)[0]["id"]

client.create("res.currency.rate", {
    "currency_id": usd,
    "name": "2026-05-10",
    "rate": 0.92,  # USD por EUR (Odoo: rate = monto en moneda extranjera por 1 unidad de la base)
    "company_id": 1,
})
```

Si la tasa para la fecha no existe, Odoo usa la ultima disponible y emite
warning silencioso. Validar antes de crear facturas en divisas raras.

## Lock dates

Configuradas en `res.company`:

- `fiscalyear_lock_date` - bloquea TODOS los asientos hasta esa fecha.
- `tax_lock_date` - bloquea solo movimientos con impuestos.
- `purchase_lock_date`, `sale_lock_date` - especificos.

Postear sobre fechas bloqueadas lanza `UserError`. El skill debe verificar
antes de crear:

```python
company = client.search_read("res.company", [("id", "=", 1)],
    ["fiscalyear_lock_date", "tax_lock_date"], limit=1)[0]
if company["fiscalyear_lock_date"] and invoice_date <= company["fiscalyear_lock_date"]:
    raise OdooError(f"Periodo bloqueado hasta {company['fiscalyear_lock_date']}")
```

## Generar PDF de factura

```python
report_id = client.search_read("ir.actions.report",
    [("report_name", "=", "account.report_invoice")],
    ["id"], limit=1)[0]["id"]

pdf_b64, content_type = client.call("ir.actions.report",
    "_render_qweb_pdf", [report_id, [invoice_id]])
```

Devuelve `(bytes_base64, "pdf")`. El skill `report_invoice_pdf.py` lo
guarda en disco o stdout.

Limitacion: muchos MCP servers genericos no exponen `ir.actions.report`.
Usar siempre el script del skill para generar PDFs.

## Errores frecuentes

| Error | Causa probable | Solucion |
|-------|----------------|----------|
| `UserError: Cannot create moves for different companies` | partner y diario en companias distintas | Filtrar `journal_id` por `company_id` correcto |
| `ValidationError: The journal entry is not balanced` | Lineas de contrapartida mal configuradas | Revisar `account.move.line.debit/credit`; usar `check_move_validity=False` solo en codigo intermedio |
| `UserError: You cannot post an entry which has no debit/credit` | Lineas vacias | Eliminar lineas con `quantity=0` o `price_unit=0` |
| `MissingError: Record does not exist` | ID incorrecto, eliminado o sin permisos | Re-buscar; verificar `access` |
| `UserError: ... has been locked.` | Periodo bloqueado | Revisar lock dates; pedir desbloqueo al admin |
| `UserError: Veri*Factu certificate not configured` | Falta certificado AEAT | Settings > Veri*Factu > Manage certificates |
| `[1103] FacturaSinDestinatario` (Veri*Factu) | Partner sin VAT VIES intracomunitario | Mapear `IDType` 02-07 segun caso (pasaporte, NIF-IVA no VIES) |
| `[3000] Duplicate billing record` (Veri*Factu) | Reenvio de la misma factura | Tratar como "ya enviado" (no es error real) |

## Atomicidad cross-request

**Cada llamada XML-RPC / JSON-2 = una transaccion Postgres.** Si necesitas
"crear factura + registrar pago + reconciliar" como una sola unidad
atomica, escribe un metodo Python en un modulo Odoo custom (server-side) y
exponlo via `execute_kw`. El skill no garantiza atomicidad encadenando
llamadas desde el cliente.
