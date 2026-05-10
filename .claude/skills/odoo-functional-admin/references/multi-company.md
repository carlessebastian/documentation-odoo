# Multi-empresa en Odoo 19

## Modelo `res.company`

Campos relevantes:

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | Char | Razon social. |
| `partner_id` | Many2one(res.partner) | Generado en create; lleva direccion, NIF. |
| `parent_id` / `child_ids` | Many2one self / One2many | Jerarquia. Branches = mismo pais y CoA que el padre. |
| `currency_id` | Many2one(res.currency) | Moneda funcional. |
| `country_id` | Many2one(res.country) | Branches deben coincidir con el padre. |
| `vat` | Char | NIF/CIF; clave natural para idempotencia. |
| `chart_template` | Selection | `es_pymes`, `es_assoc`, `es_full` para Espana. |
| `fiscalyear_lock_date` / `tax_lock_date` | Date | Cierres legales. |
| `fiscalyear_last_day` / `fiscalyear_last_month` | Int / Selection | Default 31/12. |

## Branch vs company independiente

| Criterio | Branch | Company independiente |
|----------|--------|------------------------|
| CIF / NIF distinto | No | Si |
| Plan contable distinto | No | Si |
| Pais distinto | No | Si |
| Libros legales propios | No | Si |
| Multi-divisa funcional | No | Si |
| Permite consolidacion automatica | Si (mismo CoA) | Manual (intercompany) |

**Regla mental**: si la AEAT ve dos NIFs distintos, son dos `res.company`.
Si es un mismo NIF con varios establecimientos -> branch.

## Holding "Ikigai Magi" - estructura tipica

```
Ikigai Magi S.L. (parent_id=False, ES, EUR)
  |
  +-- Camomilla Blu S.L. (parent_id=ikigai, ES, EUR, CIF distinto)
  |
  +-- Kura Terra S.L. (parent_id=ikigai, ES, EUR, CIF distinto)
  |
  (Omotenashi Hama puede quedar fuera del arbol o en parent_id=ikigai)
```

Las tres SLs son **companies independientes** con `parent_id=ikigai_id`
(no branches, porque cada una es persona juridica con su propio CIF y
libros). Esta estructura permite ejecutar consolidacion via OCA
`account_consolidation` o reporting agrupado por `parent_id`.

## `allowed_company_ids` y `self.env.company`

- `res.users.company_id` -> compania por defecto del usuario.
- `res.users.company_ids` -> Many2many de companias permitidas.
- `self.env.companies` -> set de compania activa segun el switcher.
- `self.env.company` -> "lead" actual (la que aparece arriba a la izquierda).

Nunca asumas que `self.env.company == self.env.user.company_id`. El
usuario puede haber cambiado el switcher.

## Reglas de registro multi-empresa (canonicas)

Records compartidos (visibles si `company_id` es False o esta en allowed):

```python
domain_force = "['|', ('company_id','=',False), ('company_id','in',company_ids)]"
```

Records restringidos (solo visibles para sus companies):

```python
domain_force = "[('company_id','in',company_ids)]"
```

Ambas suelen ser **globales** (`groups=[]`), no by-passable, y se aplican
en modelos como `account.move`, `account.journal`, `res.partner` (cuando
tienen `company_id`), `crm.lead`, `sale.order`, `purchase.order`.

## `_check_company_auto = True`

Modelos que lo declaran (la mayoria de account/sale/purchase) verifican
en `create()` y `write()` que cada Many2one con `check_company=True`
apunte a un registro cuya `company_id` sea compatible. Una `sale.order`
en compania A con productos solo accesibles en compania B fallara con
`UserError`.

Implicacion practica: cuando crees registros multi-compania via RPC,
**fija primero el `company_id` y luego los Many2ones dependientes**, no
al reves.

## `parent_id` semi-irreversible

- Crear una company sin `parent_id` y luego ponerselo: **OK**.
- Crear una company con `parent_id=A` y cambiarlo a `parent_id=B`: **OK**
  pero requiere recalcular reglas y cuentas; pide confirmacion.
- Tener una company con `child_ids` y querer convertirla en hija de
  otra: **NO recomendado**, Odoo mete checks que pueden fallar; en
  v19 da error si hay datos contables en las hijas.

## Activacion del switcher multi-company

```python
mc_grp = client.call('ir.model.data', 'check_object_reference',
                     ['base', 'group_multi_company'])[1]
client.call('res.users', 'write', [[uid], {'groups_id': [(4, mc_grp)]}])
```

El grupo solo activa el widget; **no** concede acceso a companies. Hay
que poblar `company_ids` explicitamente.

## Snapshot del arbol

```bash
python3 scripts/audit_admin_state.py --section companies
```

Devuelve JSON con `id`, `name`, `parent_id`, `vat`, `currency`, lista de
`child_ids` y users con esa company en su `company_ids`.

## Errores frecuentes

- `Configuration error: company X has a parent in country Y but operates
  in country Z` -> branch con `country_id` distinto del padre. Usa
  company independiente.
- `Cannot delete a record from "res.company" because it has accounting
  entries` -> hay `account.move` apuntando. Archivar en lugar de borrar.
- `You cannot remove the company X from your allowed companies because
  you have records in it` -> hay registros propiedad de esa company
  asignados al user. Reasignar antes de quitarla del `company_ids`.
