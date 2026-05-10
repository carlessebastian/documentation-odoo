# Cheatsheet de modelos Odoo 19 - contabilidad

Referencia compacta de los modelos que el skill manipula. Para profundidad
de workflow, ver `workflows.md`.

## `account.move` (asientos contables, facturas, abonos)

Desde Odoo 13, `account.invoice` se fusiono en `account.move`. Cualquier
codigo legado que mencione `account.invoice`, `account.invoice.line` o
`action_invoice_open` es obsoleto. En Odoo 17/18/19 se usa `account.move`
+ `action_post`.

### Campos clave

| Campo | Tipo | Notas |
|-------|------|-------|
| `move_type` | selection | `entry`, `out_invoice`, `out_refund`, `in_invoice`, `in_refund`, `out_receipt`, `in_receipt` |
| `state` | selection | `draft`, `posted`, `cancel` |
| `payment_state` | selection | `not_paid`, `in_payment`, `paid`, `partial`, `reversed`, `invoicing_legacy`, `blocked` |
| `partner_id` | Many2one `res.partner` | Cliente o proveedor |
| `partner_shipping_id`, `partner_bank_id` | Many2one | Direccion envio, banco |
| `journal_id` | Many2one `account.journal` | Diario |
| `invoice_date` | Date | Fecha factura |
| `invoice_date_due` | Date | Vencimiento |
| `name` | Char | Numero asignado al postear |
| `ref` | Char | Referencia interna libre (clave para idempotencia) |
| `currency_id` | Many2one `res.currency` | Divisa |
| `company_id` | Many2one `res.company` | Compania |
| `fiscal_position_id` | Many2one `account.fiscal.position` | Mapeo fiscal |
| `invoice_line_ids` | One2many `account.move.line` | Lineas visibles de factura |
| `line_ids` | One2many `account.move.line` | Todas las lineas (incl. contrapartidas) |
| `amount_untaxed`, `amount_tax`, `amount_total`, `amount_residual` | Monetary | Totales |
| `invoice_origin` | Char | Documento origen |
| `reversed_entry_id` | Many2one `account.move` | Si es abono creado por reversal |

### Campos especificos ES (con `l10n_es_edi_*` instalado)

| Campo | Origen |
|-------|--------|
| `l10n_es_edi_sii_state` | `l10n_es_edi_sii` |
| `l10n_es_edi_verifactu_state` | `l10n_es_edi_verifactu` |
| `l10n_es_edi_verifactu_chain_index` | encadenamiento Veri*Factu |
| `l10n_es_edi_verifactu_qr_code` | QR para impresion |
| `l10n_es_edi_facturae_xml_id` | XML FacturaE generado |

### Metodos publicos relevantes

- `action_post()` - postea (asigna numero, dispara EDI).
- `button_cancel()` - cancela.
- `button_draft()` - vuelve a borrador (si lo permite la config).
- `js_assign_outstanding_line(line_id)` - reconciliacion manual.

## `account.move.line`

| Campo | Notas |
|-------|-------|
| `account_id` | Cuenta contable |
| `partner_id`, `journal_id`, `date`, `name` | Comunes |
| `debit`, `credit`, `balance` | Importes |
| `tax_ids` | Many2many `account.tax` aplicados a la linea |
| `tax_line_id` | Si la linea ES un impuesto, apunta al `account.tax` |
| `product_id`, `quantity`, `price_unit`, `discount` | Para lineas de factura |
| `price_subtotal`, `price_total` | Computados |
| `analytic_distribution` | dict `{plan_id: percentage}` (Odoo 17+) |
| `display_type` | `product`, `tax`, `payment_term`, `line_section`, `line_note` |
| `reconciled`, `full_reconcile_id`, `matched_debit_ids`, `matched_credit_ids` | Reconciliacion |
| `move_id` | Asiento padre |

Truco: `context = {'check_move_validity': False}` permite crear lineas
desbalanceadas temporalmente (uso interno, evitar en produccion).

## `account.payment` y `account.payment.register`

`account.payment` es el pago real (con su propio `account.move`
contrapartida).

`account.payment.register` es un **wizard transient**. Patron correcto:

```python
ctx = {"active_model": "account.move", "active_ids": [invoice_id]}
reg_id = client.call("account.payment.register", "create",
    [{"payment_date": "2026-05-12", "journal_id": bank_journal_id}],
    {"context": ctx})
client.call("account.payment.register", "action_create_payments",
    [[reg_id]], {"context": ctx})
```

Campos del wizard:
- `payment_date`, `journal_id`, `payment_method_line_id`, `amount`,
  `currency_id`, `communication`, `group_payment` (boolean).

## `account.move.reversal` (factura rectificativa)

Wizard transient. En Odoo 17+ el campo `refund_method` fue eliminado; ahora
se decide por metodo:

- `reverse_moves()` - rectificativa por diferencias (credito puro).
- `modify_moves()` - cancelar la original y crear nueva (sustitucion).

Campos: `date`, `reason`, `journal_id`.

## `account.journal`

| Campo | Notas |
|-------|-------|
| `type` | `sale`, `purchase`, `bank`, `cash`, `general` |
| `default_account_id` | Cuenta por defecto |
| `currency_id` | Divisa del diario |
| `bank_account_id` | Si es bancario |
| `code` | Codigo corto |
| Especificos ES con Veri*Factu | `l10n_es_verifactu_enabled`, `l10n_es_verifactu_certificate_id` |

## `account.tax`

| Campo | Notas |
|-------|-------|
| `amount_type` | `percent`, `fixed`, `group`, `division` |
| `amount` | Tipo (21.0 para IVA 21%) |
| `type_tax_use` | `sale`, `purchase`, `none` |
| `tax_group_id` | Many2one `account.tax.group` |
| `invoice_repartition_line_ids`, `refund_repartition_line_ids` | Distribucion contable |
| `country_id` | Pais (ES para los `l10n_es`) |

XML-IDs tipicos del modulo `l10n_es`:
- `S_IVA21B`, `S_IVA10B`, `S_IVA4B`, `S_IVA0_E` (sale)
- `P_IVA21_BC`, `P_IVA10_BC`, `P_IVA4_BC` (purchase)
- `P_IRPF15`, `P_IRPF7`, `P_IRPF19`, `P_IRPF24` (retenciones)
- `S_REQ52`, `S_REQ14`, `S_REQ05` (Recargo de Equivalencia)

## `account.tax.group`

Solo agrupacion para presentacion: IVA, IRPF, RE.

## `account.fiscal.position`

Mapea automaticamente impuestos y cuentas segun pais/region/grupo del
partner. Ejemplos en `l10n_es`:

- Regimen Nacional
- Operaciones intracomunitarias (UE)
- Exportacion (resto del mundo)
- Recargo de Equivalencia
- Criterio de Caja
- REAGYP (agricultura, ganaderia y pesca)
- Inversion del Sujeto Pasivo (ISP)

## `account.account` (PGCE)

| Campo | Notas |
|-------|-------|
| `code` | Codigo PGCE (4-7 digitos en ES) |
| `name` | Nombre |
| `account_type` | `asset_*`, `liability_*`, `income`, `expense`, etc. |
| `tag_ids` | `account.account.tag` para casillas modelos AEAT |

## `res.partner`

| Campo | Notas |
|-------|-------|
| `vat` | NIF/CIF/NIE con prefijo pais (`ES12345678Z`) |
| `country_id`, `state_id` | Pais y provincia |
| `lang` | `es_ES`, `ca_ES`, `en_US`, etc. |
| `property_account_receivable_id`, `property_account_payable_id` | Cuentas asociadas |
| `property_payment_term_id` | Terminos de pago default |
| `customer_rank`, `supplier_rank` | > 0 marca como cliente/proveedor |
| Especificos ES | `l10n_es_type` (`empresa`, `autonomo`, `particular`) |
| EDI ES | `l10n_es_edi_sii_*`, `l10n_es_edi_facturae_*` (si modulos instalados) |

## `res.currency` y `res.currency.rate`

`res.currency.rate.rate` es el tipo de cambio para una `name` (fecha) y
`currency_id`. Para multi-divisa, `res.currency.rate` debe existir para la
fecha de la factura (o se usa el ultimo disponible).

## `product.product` y `product.template`

| Campo | Notas |
|-------|-------|
| `default_code` | SKU |
| `taxes_id` | Impuestos venta (Many2many a `account.tax`) |
| `supplier_taxes_id` | Impuestos compra |
| `property_account_income_id`, `property_account_expense_id` | Cuentas propias |

## Otros modelos relevantes

| Modelo | Uso |
|--------|-----|
| `account.bank.statement` / `account.bank.statement.line` | Extractos |
| `account.reconcile.model` | Reglas reconciliacion automatica |
| `account.partial.reconcile` / `account.full.reconcile` | Tablas de reconciliacion |
| `account.analytic.account` / `.line` / `.plan` | Analitica (planes desde 17+) |
| `ir.actions.report` | Generacion de PDFs (`_render_qweb_pdf`) |
| `ir.attachment` | Adjuntos (incluye PDFs ya generados) |

## Comandos ORM (campos `*2many`)

| Comando | Significado |
|---------|-------------|
| `(0, 0, vals)` | Crear nuevo |
| `(1, id, vals)` | Actualizar existente |
| `(2, id, 0)` | Borrar y eliminar |
| `(3, id, 0)` | Quitar (sin borrar) |
| `(4, id, 0)` | Anadir referencia |
| `(5, 0, 0)` | Limpiar todos |
| `(6, 0, [ids])` | Reemplazar por esta lista (para Many2many) |
