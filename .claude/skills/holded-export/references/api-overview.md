# Holded API — overview

## Domains

Holded particiona la API en cinco dominios, todos bajo
`https://api.holded.com/api/<domain>/v1/...`:

| Domain | Cobertura | Cubierto por esta skill |
|---|---|---|
| `invoicing` | contactos, documentos, productos, servicios, almacenes, tesoreria, impuestos, series de numeracion, pagos, remesas, canales de venta | si |
| `accounting` | `dailyledger` (asientos contables) | si |
| `projects` | proyectos, tareas, time tracking | parcial (proyectos + tareas) |
| `crm` | funnels, leads | no (doc parca, sin endpoints estables) |
| `team` | empleados, nominas | minimo (`update-employee` solo) |

## Autenticacion

- Header: `key: <HOLDED_API_KEY>`. No es Bearer.
- Generada en la UI de Holded en **Settings -> Developers**.
- El cliente la lee de la env var `HOLDED_API_KEY`.

## Paginacion

Tres patrones distintos en la misma API:

1. **`page=N`** (numerico, max 500/pagina). Usado por:
   - `GET /accounting/v1/dailyledger`
2. **`page=N` en la practica** aunque la spec no lo declare. Usado por:
   - `GET /invoicing/v1/documents/{docType}` (filtros `starttmp`, `endtmp`,
     `contactid`, `paid`, `billed`, `sort`)
3. **Sin paginacion**: el endpoint devuelve toda la lista de golpe.
   Lo usan `contacts`, `products`, `services`, `treasury`, `taxes`,
   `expensesaccount`, `payments`, `saleschannels`, `remittances`,
   `warehouse`.

El cliente abstrae las 3 modalidades en `HoldedClient.paginate(...)`:

- Si pasas `page_size=N` -> asume paginacion `page=` numerica e
  itera hasta que la pagina devuelva `< N` items.
- Si no pasas `page_size` -> espera una unica lista; itera todos los
  items y para.

## Rate limits

No documentados oficialmente. La comunidad reporta **429
esporadicos**. El cliente:

- Reintenta sobre 429 y 5xx con backoff exponencial (1s, 2s, 4s).
- Respeta `Retry-After` si viene numerico.
- Max 3 intentos por defecto; despues lanza
  `HoldedRateLimited` / `HoldedServerError`.

Para dumps largos preferimos **serie secuencial** (no paralelismo)
para no disparar 429.

## Formato de fechas

Holded usa **timestamps UNIX en segundos** (UTC) en los filtros
`starttmp` / `endtmp` para documents y dailyledger. El script
`holded_export.py` convierte `--start-date YYYY-MM-DD` con
`datetime.datetime.strptime(...).timestamp()`.

## DocTypes validos

```python
DOC_TYPES = (
    "invoice",          # factura emitida
    "salesreceipt",     # ticket de venta
    "creditnote",       # nota de credito (abono)
    "salesorder",       # pedido de venta
    "proform",          # proforma
    "waybill",          # albaran
    "estimate",         # presupuesto
    "purchase",         # factura recibida
    "purchaseorder",    # pedido de compra
    "purchaserefund",   # abono de proveedor
)
```

Estan en `holded_client.DOC_TYPES`. El cliente rechaza cualquier otro
valor.

## Read-only

El cliente solo expone metodos GET. Ver `pdf-attachments.md` para los
detalles del workaround de PDFs y `endpoint-coverage.md` para la
lista exacta de endpoints en la whitelist.
