# Carga idempotente de datos via `ir.model.data`

## Por que `ir.model.data`

El modelo `ir.model.data` mapea registros DB a XML-IDs (claves
externas legibles tipo `module.name`). Crear via XML-ID es la forma
canonica de hacer **upserts idempotentes**: si el ext-ID existe, hace
`write()`; si no, hace `create()` y registra el nuevo XML-ID.

Es el mismo mecanismo que usan los modulos al instalarse.

## Convencion de XML-IDs

```
<modulo>.<nombre_unico>
```

- `<modulo>`: para datos custom administrativos, usar `__custom__` (no
  colisiona con modulos reales) o un namespace propio tipo
  `<tenant_slug>_admin`.
- `<nombre_unico>`: snake_case, descriptivo.

Ejemplos:
- `__custom__.company_acme_iberia`
- `__custom__.user_maria_pons`
- `__custom__.journal_acme_sale`
- `acme_admin.fp_intra_eu_iberia`

## Patron canonico via JSON-2 / XML-RPC

```python
def upsert(client, xmlid, model, vals):
    module, name = xmlid.split('.')
    existing = client.call('ir.model.data', 'search_read',
                           [[('module', '=', module), ('name', '=', name)]],
                           {'fields': ['res_id', 'model'], 'limit': 1})
    if existing:
        rec_id = existing[0]['res_id']
        client.call(model, 'write', [[rec_id], vals])
        return rec_id
    rec_id = client.call(model, 'create', [vals])
    client.call('ir.model.data', 'create', [{
        'module': module,
        'name': name,
        'model': model,
        'res_id': rec_id,
        'noupdate': False,
    }])
    return rec_id
```

`scripts/ext_id_upsert.py` implementa esto como CLI.

## CLI

```bash
python3 scripts/ext_id_upsert.py \
    --xmlid __custom__.company_acme_iberia \
    --model res.company \
    --vals '{"name": "Acme Iberia S.L.", "vat": "ESB99999999",
             "country_id": 69, "currency_id": 1}'
```

Imprime `id_resultante`. Reejecutarlo con `--vals` distinto hace `write`.

## `noupdate`

Campo en `ir.model.data`. Si `noupdate=True`:

- Una reinstalacion del modulo NO sobrescribe los valores escritos por
  el usuario en la UI.
- Util para datos "semilla" que el usuario debe poder personalizar.

Para upserts administrativos via Claude, dejar `noupdate=False` para que
nuestras llamadas si actualicen siempre.

## `base_import.import` via JSON-2 (carga masiva CSV)

```python
import_id = client.call('base_import.import', 'create', [{
    'res_model': 'res.partner',
    'file_name': 'partners.csv',
    'file': base64.b64encode(csv_bytes).decode('ascii'),
    'file_type': 'text/csv',
}])

result = client.call('base_import.import', 'execute_import', [
    [import_id],
    ['name', 'vat', 'email', 'country_id/id'],  # campos
    ['Name', 'NIF', 'Email', 'Country'],         # headers CSV
    {'has_headers': True, 'separator': ',', 'quoting': '"',
     'encoding': 'utf-8', 'date_format': '%Y-%m-%d'},
])
```

Notas:
- Sufijo `/id` en una columna fuerza lookup por `ir.model.data` XML-ID.
- Sufijo `.id` (vs `/id`): lookup por DB id numerico.
- Para Many2one por nombre legible, usar el campo sin sufijo (Odoo hace
  `name_search`); arriesgado si hay duplicados.

## Patron Many2many en CSV

```
groups_id/id
base.group_user,account.group_account_invoice
```

Comas separan los XML-IDs. Equivale a `(6, 0, [...])`.

## Patron One2many en CSV (lineas hijas)

Repetir la fila padre con valores vacios para padre y rellenos para
hijos:

```
name,line_ids/sequence,line_ids/name
Header A,1,Hijo 1
,2,Hijo 2
,3,Hijo 3
```

Frecuente en `account.move` con sus `invoice_line_ids` o
`account.move.line`.

## Cuando NO usar `base_import.import`

- Volumenes >50k filas: usar SQL directo (fuera del alcance de este
  skill) o batches en script Python via `create()`.
- Datos relacionales complejos: preferir scripts Python con upsert por
  XML-ID.
- Atomicidad: `base_import` no garantiza all-or-nothing; usa savepoints
  manuales si es critico.
