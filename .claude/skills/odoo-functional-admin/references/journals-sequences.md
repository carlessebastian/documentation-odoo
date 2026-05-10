# Diarios y secuencias en Odoo 19

## `account.journal`

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | Char | Etiqueta humana ("Customer Invoices"). |
| `code` | Char(5) | Maximo 5 caracteres ("VENT", "INV", "BANK"). |
| `type` | Selection | `sale`, `purchase`, `bank`, `cash`, `general`. |
| `sequence_id` | Many2one(ir.sequence) | Si vacio en create, Odoo crea uno auto. |
| `default_account_id` | Many2one(account.account) | Cuenta por defecto. |
| `currency_id` | Many2one(res.currency) | Vacio = compania. |
| `suspense_account_id` | Many2one(account.account) | Para tipo `bank/cash`. |
| `bank_account_id` | Many2one(res.partner.bank) | Para tipo `bank`. |
| `payment_method_line_ids` | One2many | Metodos de pago habilitados. |
| `restrict_mode_hash_table` | Boolean | Hash chain legal (one-way lock). |
| `company_id` | Many2one(res.company) | Obligatorio. |

### Hash chain (`restrict_mode_hash_table`)

Una vez activo, las facturas posteadas en ese diario llevan un hash
encadenado y **no se pueden cancelar/borrar** ni siquiera con admin. Es
irreversible para los registros ya creados con ese flag.

- En Espana, si Veri*Factu / SII estan activos, la responsabilidad de
  no-repudio recae en los modulos EDI; el hash chain interno suele
  dejarse desactivado para no duplicar la inmutabilidad.
- En diarios de tipo `bank`, normalmente OFF (los extractos se importan
  y modifican en la fase de conciliacion).
- En diarios `general` para asientos manuales: opcional segun politica.

## `ir.sequence`

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | Char | Etiqueta. |
| `code` | Char | Identificador tecnico (`account.move.kt`). |
| `prefix` | Char | Soporta tokens (ver abajo). |
| `suffix` | Char | Tokens igual que prefix. |
| `padding` | Int | Numero de digitos rellenados con ceros. |
| `number_next` | Int | Proximo numero. |
| `number_increment` | Int | Default 1. |
| `implementation` | Selection | `standard` (con saltos posibles) o `no_gap`. |
| `use_date_range` | Boolean | True para reset por anyo/periodo. |
| `date_range_ids` | One2many(ir.sequence.date_range) | Rangos por ejercicio. |
| `company_id` | Many2one(res.company) | Multi-company. |

### Tokens del `prefix` / `suffix`

| Token | Significado |
|-------|-------------|
| `%(year)s` | Anyo de la fecha de creacion. |
| `%(month)s` | Mes 01-12. |
| `%(day)s` | Dia 01-31. |
| `%(doy)s` | Dia del anyo. |
| `%(woy)s` | Semana del anyo. |
| `%(weekday)s` | 0=Lunes. |
| `%(h24)s` / `%(h12)s` / `%(min)s` / `%(sec)s` | Hora. |
| `%(range_year)s` | Anyo del **range** (con `use_date_range=True`). |
| `%(range_month)s` | Mes del range. |

**Para facturas espanolas se usa casi siempre `%(range_year)s`**, no
`%(year)s`, porque la numeracion debe reiniciarse cada ejercicio fiscal
y los rangos en `date_range_ids` representan los ejercicios.

### `no_gap` y la ley espanola

La numeracion de **facturas emitidas** (`out_invoice`, `out_refund`) en
Espana debe ser correlativa **sin saltos**. Implicacion practica:

```python
{'implementation': 'no_gap'}
```

- `standard`: usa `nextval()` de PostgreSQL; rapido pero puede dejar
  huecos si una transaccion hace rollback.
- `no_gap`: lock pesimista; la siguiente factura espera a que la actual
  termine. Mas lento bajo carga, pero garantizado sin saltos.

Para `in_invoice` (facturas recibidas) NO se requiere correlativa porque
no es un documento emitido por la sociedad.

## Patron canonico: diario con secuencia anual

```python
seq_id = client.call('ir.sequence', 'create', [{
    'name': 'KT Customer Invoices',
    'code': 'account.move.kt',
    'prefix': 'KT/%(range_year)s/',
    'padding': 5,
    'use_date_range': True,
    'implementation': 'no_gap',
    'company_id': kura_id,
}])

journal_id = client.call('account.journal', 'create', [{
    'name': 'Customer Invoices',
    'type': 'sale',
    'code': 'KTINV',
    'sequence_id': seq_id,
    'company_id': kura_id,
}])
```

Resultado: las facturas posteadas el 2026-03-15 reciben numeros
`KT/2026/00001`, `KT/2026/00002`, ... y al pasar al 2027 reinician en
`KT/2027/00001` (siempre que se haya creado el `ir.sequence.date_range`
para 2027 antes; si `date_range_ids` esta vacio, Odoo crea el rango
automaticamente al postear la primera factura de un anyo nuevo).

## `ir.sequence.date_range`

Hijo de `ir.sequence`. Permite numeracion independiente por rango de
fechas:

| Campo | Notas |
|-------|-------|
| `date_from` / `date_to` | Limites. |
| `number_next` | Suele ser 1 al crear el rango. |
| `sequence_id` | Padre. |

Crear rangos manualmente para 2026/2027/2028 evita la sorpresa de "no se
crea solo a las 23:59 del 31/12":

```python
for y in (2026, 2027, 2028):
    client.call('ir.sequence.date_range', 'create', [{
        'sequence_id': seq_id,
        'date_from': f'{y}-01-01',
        'date_to':   f'{y}-12-31',
        'number_next': 1,
    }])
```

## Diarios estandar para una company ES

| Code | Type | Nombre | Notas |
|------|------|--------|-------|
| VENT | sale | Customer Invoices | `no_gap`, prefix `<CODE>/%(range_year)s/`. |
| COMP | purchase | Vendor Bills | `standard` OK. |
| BANC | bank | Banco Principal | Por banco; `bank_account_id` requerido. |
| CAJA | cash | Caja | `default_account_id` = 570. |
| NOMI | general | Nominas | Para asientos de payroll. |
| CIERRE | general | Cierre | Asientos de cierre 6/7 -> 129. |

Ver `assets/journal_templates_es.csv` para los datos exactos.

## `scripts/journal_setup.py` (uso)

```bash
python3 scripts/journal_setup.py \
    --type sale --code VENT --company 2 \
    --name "Customer Invoices" \
    --prefix "VENT/%(range_year)s/" --no-gap
```

Idempotente sobre `(company_id, code)`: si ya existe, hace `write()` con
los nuevos valores en lugar de crear duplicados.

## Errores frecuentes

- `ValidationError: Code must be unique per company` -> intenta crear
  un diario con `code='VENT'` cuando ya existe en esa company. Usa
  `--update` si quieres modificar el existente.
- Numeracion repite tras un downgrade de Odoo -> `number_next` quedo
  desincronizado del MAX(name). Reasignar manualmente.
- `Sequence date range overlaps another` -> dos `date_range` con fechas
  superpuestas. Borrar uno antes de crear el otro.
