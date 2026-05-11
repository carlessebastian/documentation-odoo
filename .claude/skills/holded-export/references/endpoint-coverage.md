# Endpoints implementados

Listado generado a partir de `holded_client.ALLOWED_ENDPOINTS`.

## Invoicing (`https://api.holded.com/api/invoicing/v1`)

| Method | Path | Helper Python | Mapeo Odoo previsto |
|---|---|---|---|
| GET | `/contacts` | `iter_contacts(client)` | `res.partner` |
| GET | `/contacts/{contactId}` | `client.get("invoicing", f"/contacts/{id}")` | — |
| GET | `/contacts/groups` | `get_contact_groups(client)` | tags / categorias de partner |
| GET | `/products` | `iter_products(client)` | `product.template` |
| GET | `/products/{productId}` | `client.get(...)` | — |
| GET | `/services` | `iter_services(client)` | `product.template` (type=service) |
| GET | `/services/{serviceId}` | `client.get(...)` | — |
| GET | `/warehouse` | `iter_warehouses(client)` | `stock.warehouse` |
| GET | `/warehouse/{warehouseId}` | `client.get(...)` | — |
| GET | `/treasury` | `iter_treasuries(client)` | `account.journal` (cash/bank) |
| GET | `/treasury/{treasuryId}` | `client.get(...)` | — |
| GET | `/expensesaccount` | `iter_expensesaccount(client)` | `account.account` (gasto) |
| GET | `/numberingseries/{type}` | `get_numbering_series(client, type)` | `ir.sequence` (clave para Fase 4.3) |
| GET | `/saleschannels` | `iter_saleschannels(client)` | analitica / tag |
| GET | `/saleschannels/{salesChannelId}` | `client.get(...)` | — |
| GET | `/payments` | `iter_payments(client)` | `account.payment` |
| GET | `/payments/{paymentId}` | `client.get(...)` | — |
| GET | `/remittances` | `iter_remittances(client)` | `account.payment` (en lote SEPA) |
| GET | `/remittances/{remittanceId}` | `client.get(...)` | — |
| GET | `/taxes` | `iter_taxes(client)` | `account.tax` (mapeado a `l10n_es`) |
| GET | `/documents/{docType}` | `iter_documents(client, docType, **filters)` | `account.move` (emitidas/recibidas) |
| GET | `/documents/{docType}/{documentId}` | `client.get(...)` | — |
| GET | `/documents/{docType}/{documentId}/pdf` | `client.download_pdf(docType, id)` | `ir.attachment` adjunto a `account.move` |

## Accounting (`https://api.holded.com/api/accounting/v1`)

| Method | Path | Helper Python | Mapeo Odoo previsto |
|---|---|---|---|
| GET | `/dailyledger` | `iter_dailyledger(client, **filters)` | `account.move` + `account.move.line` |

Holded NO expone GET para el plan de cuentas como tal; las cuentas
asociadas a movimientos aparecen embebidas en cada linea del
`dailyledger` y en `expensesaccount`.

## Projects (`https://api.holded.com/api/projects/v1`)

| Method | Path | Mapeo Odoo |
|---|---|---|
| GET | `/projects` | `project.project` |
| GET | `/projects/{projectId}` | — |
| GET | `/projects/{projectId}/tasks` | `project.task` |
| GET | `/projects/{projectId}/tasks/{taskId}` | — |

## Filtros utiles para documents

Confirmados via `references/holded-api/list-documents-1.md`:

| Param | Tipo | Significado |
|---|---|---|
| `starttmp` | UNIX seconds | limite inferior (inclusive) de fecha |
| `endtmp` | UNIX seconds | limite superior (inclusive) |
| `contactid` | string | filtra por contacto |
| `paid` | `all|yes|no` | estado de cobro |
| `billed` | `all|yes|no` | estado de facturacion |
| `sort` | `created-desc|created-asc|updated-desc|updated-asc` | orden |

## Cambios a la whitelist

Si Holded anyade un endpoint nuevo o cambia un path:

1. Vendoriza la doc actualizada con `scripts/scrape_holded_docs.py`.
2. Edita `holded_client.ALLOWED_ENDPOINTS` con el patron nuevo.
3. Anyade un test en `tests/test_holded_client.py`
   (`TestAllowedEndpoints`) que cubra el nuevo path.
4. Si tiene CRUD-write, **NO lo anyadas a esta skill** — esta skill es
   read-only.
