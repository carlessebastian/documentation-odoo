# Sintaxis de dominios Odoo y patrones de lectura eficiente

## Estructura basica de un dominio

Un dominio es una lista de tuplas `(field, operator, value)` combinadas
implicitamente con AND.

```python
domain = [
    ("move_type", "=", "out_invoice"),
    ("state", "=", "posted"),
    ("amount_residual", ">", 0),
]
```

Equivale a `move_type='out_invoice' AND state='posted' AND amount_residual>0`.

## Notacion polaca prefija para OR / NOT

| Operador | Aridad | Significado |
|----------|--------|-------------|
| `&` | binario (default) | AND |
| `\|` | binario | OR |
| `!` | unario | NOT |

El operador se pone **antes** de los argumentos. Ejemplos:

```python
# state='posted' AND (move_type='out_invoice' OR move_type='out_refund')
[
    ("state", "=", "posted"),
    "|",
    ("move_type", "=", "out_invoice"),
    ("move_type", "=", "out_refund"),
]

# NOT (state='draft')
["!", ("state", "=", "draft")]

# Multi-OR: tres alternativas requieren dos `|`
[
    "|", "|",
    ("state", "=", "draft"),
    ("state", "=", "cancel"),
    ("state", "=", "posted"),
]
```

Regla mnemotecnica: para combinar N tuplas con OR se necesitan **N-1
operadores `|`** al inicio.

## Operadores de comparacion

| Operador | Significado |
|----------|-------------|
| `=`, `!=` | igualdad |
| `>`, `>=`, `<`, `<=` | comparacion numerica/fecha |
| `=?` | igualdad o NULL (devuelve True si el campo es False) |
| `in`, `not in` | pertenencia a lista |
| `like`, `not like` | LIKE SQL (`%` y `_` literales) |
| `ilike`, `not ilike` | ILIKE (case-insensitive) |
| `=like`, `=ilike` | LIKE sin escape automatico |
| `child_of` | jerarquia: incluye descendientes |
| `parent_of` | jerarquia: incluye ascendientes |
| `any`, `not any` | sub-dominio sobre Many2one/One2many (Odoo 17+) |

## Dot-notation (cross-modelo)

Atravesar Many2one con punto:

```python
# Facturas de partners cuyo pais es Espana
[("partner_id.country_id.code", "=", "ES")]

# Facturas con linea cuyo producto tiene categoria 'Servicios'
[("invoice_line_ids.product_id.categ_id.name", "=", "Servicios")]
```

Para One2many/Many2many con dot-notation, Odoo aplica EXISTS implicito.
Para subqueries explicitas usar `any` (17+):

```python
[("invoice_line_ids", "any", [
    ("product_id.default_code", "=", "SERV-001"),
    ("quantity", ">", 5)
])]
```

## Lectura: `search_read` vs `search` + `read`

`search_read` hace ambos en una sola llamada (mas eficiente):

```python
client.search_read("account.move",
    [("state", "=", "posted")],
    fields=["id", "name", "amount_total"],
    limit=50,
    offset=0,
    order="invoice_date desc")
```

**Limit por defecto 100** si no se especifica. Pasar siempre `limit`
explicito para evitar timeouts en tablas grandes.

## Agregaciones: `read_group`

Equivalente a SQL GROUP BY:

```python
client.call("account.move", "read_group",
    [
        [("move_type", "=", "out_invoice"), ("state", "=", "posted")],
        ["amount_total:sum", "id:count"],  # campos a agregar
        ["partner_id", "invoice_date:month"],  # group by
    ],
    {"orderby": "amount_total desc", "limit": 20})
```

Modificadores en `groupby`:
- `:day`, `:month`, `:quarter`, `:year` - granularidad temporal.
- En Odoo 19+: `formatted_read_group` devuelve valores presentables
  directamente (Monetary con simbolo, fechas locale).

## Paginacion

Para datasets grandes:

```python
batch_size = 200
offset = 0
while True:
    rows = client.search_read("account.move.line",
        [("date", ">=", "2026-01-01")],
        ["id", "debit", "credit"],
        limit=batch_size, offset=offset, order="id")
    if not rows:
        break
    process(rows)
    offset += batch_size
```

Mejor aun: paginar por `id` (cursor-based) para evitar duplicados si se
crean registros nuevos durante la iteracion:

```python
last_id = 0
while True:
    rows = client.search_read("account.move.line",
        [("date", ">=", "2026-01-01"), ("id", ">", last_id)],
        ["id", "debit", "credit"],
        limit=batch_size, order="id")
    if not rows: break
    process(rows)
    last_id = rows[-1]["id"]
```

## Optimistic locking con `write_date`

Patron para detectar modificaciones concurrentes:

```python
record = client.search_read("account.move", [("id", "=", invoice_id)],
    ["write_date", "amount_total"], limit=1)[0]
saved_write_date = record["write_date"]

# ...calcular cambios fuera de Odoo...

current = client.search_read("account.move", [("id", "=", invoice_id)],
    ["write_date"], limit=1)[0]
if current["write_date"] != saved_write_date:
    raise OdooError("Registro modificado por otro proceso, reintentar")

client.write("account.move", [invoice_id], {...})
```

## Filtros tipicos para contabilidad ES

```python
# Facturas pendientes de cobro de clientes espanoles
[
    ("move_type", "=", "out_invoice"),
    ("state", "=", "posted"),
    ("payment_state", "in", ["not_paid", "partial"]),
    ("partner_id.country_id.code", "=", "ES"),
]

# Facturas posteadas en Q1 2026
[
    ("move_type", "in", ["out_invoice", "out_refund"]),
    ("state", "=", "posted"),
    ("invoice_date", ">=", "2026-01-01"),
    ("invoice_date", "<=", "2026-03-31"),
]

# Asientos sin enviar a Veri*Factu (Enterprise)
[
    ("move_type", "in", ["out_invoice", "out_refund"]),
    ("state", "=", "posted"),
    ("l10n_es_edi_verifactu_state", "in", [False, "rejected"]),
]

# Partners morosos (saldo > 5.000 EUR vencido)
# Nota: 'credit' en res.partner es el saldo deudor (lo que nos deben)
[
    ("customer_rank", ">", 0),
    ("country_id.code", "=", "ES"),
    ("credit", ">", 5000),
]
```

## Performance - reglas practicas

1. **Siempre indicar `fields`** en `search_read`: omitir trae todos los
   campos calculados, lo cual puede triplicar el tiempo de respuesta.
2. **Filtrar por fecha primero**: las tablas `account.move` y
   `account.move.line` suelen ser las mas grandes.
3. **Evitar `order` sobre campos calculados** (`amount_total`,
   `payment_state`): no usan indice y fuerzan full-scan.
4. **Para conteos**: `search_count` es mas barato que `search_read` +
   `len()`.
5. **Prefetching**: Odoo cachea Many2one en el lado servidor; pedir varios
   campos relacionados en una sola lectura es mas eficiente que varias.
6. **No abusar de dot-notation profunda** (`a.b.c.d.e`): cada salto es un
   JOIN; mejor `read_group` o queries separadas.

## Limites Odoo

- SaaS: ~60 req/min por API key, sin paralelismo.
- Self-hosted: gobernado por `workers` (recomendado `2 * CPU + 1`),
  `limit_time_cpu`, `limit_time_real`, `limit_request`, `limit_memory_hard`
  en `odoo.conf`.
- Cada llamada XML-RPC / JSON-2 = una transaccion: para flujos
  multi-paso, encadenar en un metodo server-side custom o aceptar la
  no-atomicidad.
