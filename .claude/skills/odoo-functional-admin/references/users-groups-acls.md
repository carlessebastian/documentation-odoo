# Usuarios, grupos, ACLs y reglas de registro

## `res.users`

Campos relevantes para crear/actualizar via RPC:

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | Char | Nombre completo. |
| `login` | Char | Email recomendado; clave natural. |
| `password` | Char | Solo para reset directo; preferible `action_reset_password`. |
| `email` | Char | Suele coincidir con `login`. |
| `partner_id` | Many2one(res.partner) | Generado en create; no escribirlo. |
| `groups_id` | Many2many(res.groups) | Sintaxis `(6,0,[ids])` o `(4,id)`. |
| `company_id` | Many2one(res.company) | Compania por defecto. |
| `company_ids` | Many2many(res.company) | Companias permitidas. |
| `lang` | Selection | `es_ES`, `ca_ES`, `it_IT`, `en_US`. Idioma debe estar instalado. |
| `tz` | Selection | `Europe/Madrid` por defecto. |
| `share` | Boolean | True = portal/external; False = internal. |
| `active` | Boolean | Soft delete. |
| `notification_type` | Selection | `email` o `inbox`. |
| `api_key_ids` | One2many(res.users.apikeys) | API keys. No se setean en create. |

## Sintaxis Many2many (CRITICA)

Cuando escribas `groups_id` o `company_ids`:

| Tupla | Significado |
|-------|-------------|
| `(0, 0, vals)` | Crea un nuevo registro en linea con `vals`. |
| `(1, id, vals)` | Update del registro `id` con `vals`. |
| `(2, id)` | Borra el registro `id` (unlink). |
| `(3, id)` | Quita la relacion (sin borrar). |
| `(4, id)` | Anyade la relacion. |
| `(5,)` | Quita todas las relaciones. |
| `(6, 0, [ids])` | Reemplaza por la lista `ids`. |

**Patron canonico para crear un usuario con grupos cerrados**:

```python
{'groups_id': [(6, 0, [g_user, g_account_inv, g_multi_company])]}
```

**Patron canonico para anyadir un grupo a un usuario existente**:

```python
{'groups_id': [(4, g_account_inv)]}
```

**Patron canonico para quitar un grupo**:

```python
{'groups_id': [(3, g_account_inv)]}
```

## XML-IDs de grupo frecuentes

| XML-ID | Significado |
|--------|-------------|
| `base.group_user` | Internal user (acceso minimo a Odoo). |
| `base.group_portal` | Portal user (clientes externos). |
| `base.public_user` | Visitante anonimo. |
| `base.group_system` | Settings - Administrator. **Equivale a sudo()**, evitar. |
| `base.group_no_one` | Developer mode (debug). |
| `base.group_multi_company` | Activa el switcher de companias. |
| `base.group_partner_manager` | Contacts - Edit contacts. |
| `account.group_account_invoice` | Accounting - Billing. |
| `account.group_account_user` | Accounting - Accountant. |
| `account.group_account_manager` | Accounting - Adviser (full). |
| `account.group_account_readonly` | Solo lectura. |
| `sales_team.group_sale_salesman` | Sales - User: Own Documents Only. |
| `sales_team.group_sale_salesman_all_leads` | Sales - User: All Documents. |
| `sales_team.group_sale_manager` | Sales - Administrator. |
| `purchase.group_purchase_user` | Purchase - User. |
| `purchase.group_purchase_manager` | Purchase - Manager. |
| `stock.group_stock_user` / `stock.group_stock_manager` | Inventory. |
| `hr.group_hr_user` / `hr.group_hr_manager` | HR. |

Resolver XML-ID a `res.id`:

```python
res = client.call('ir.model.data', 'check_object_reference',
                  ['account', 'group_account_invoice'])
group_id = res[1]
```

O via `search_read` sobre `ir.model.data`:

```python
client.call('ir.model.data', 'search_read',
            [[('module', '=', 'account'),
              ('name', '=', 'group_account_invoice')]],
            {'fields': ['res_id'], 'limit': 1})[0]['res_id']
```

## `res.groups` - herencia (`implied_ids`)

Los grupos se implican entre si: pertenecer a `account.group_account_manager`
implica automaticamente `account.group_account_user` que implica
`account.group_account_invoice` que implica `base.group_user`.

Implicacion: **no asignes manualmente todos los grupos de la cadena**;
asigna solo el "lider" y Odoo propaga via `implied_ids`.

## `ir.model.access` (CSV)

Define permisos *a nivel de modelo* por grupo. Encabezados estandar:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_my_model_user,my.model.user,model_my_model,base.group_user,1,1,1,0
```

- El nombre del modelo se referencia como `model_<nombre_con_underscore>`
  (p.ej. `res.partner` -> `model_res_partner`).
- Si `group_id:id` queda vacio, aplica a todos.
- Los flags son 0/1.

Para auditar accesos via RPC:

```python
client.call('ir.model.access', 'search_read',
            [[('model_id.model', '=', 'res.partner')]],
            {'fields': ['name', 'group_id', 'perm_read', 'perm_write',
                        'perm_create', 'perm_unlink']})
```

## `ir.rule` (record rules)

Define filtros *a nivel de fila*. Campos:

| Campo | Notas |
|-------|-------|
| `name` | Etiqueta humana. |
| `model_id` | Many2one(ir.model). |
| `domain_force` | String evaluable como dominio Python. |
| `groups` | Many2many(res.groups). **Vacio = global rule, no by-passable.** |
| `perm_read` / `perm_write` / `perm_create` / `perm_unlink` | Flags. |
| `active` | Boolean. |

### Variables disponibles en `domain_force`

| Variable | Tipo |
|----------|------|
| `user.id` | int |
| `user.partner_id.id` | int |
| `user.company_id.id` | int |
| `company_ids` | list[int] (companias activas en el switcher) |
| `time` | modulo `time` |

### Ejemplo: comerciales solo ven sus oportunidades

```python
client.call('ir.rule', 'create', [{
    'name': 'Salesperson sees only own leads',
    'model_id': model_id_of('crm.lead'),
    'groups': [(6, 0, [group_id_of('sales_team.group_sale_salesman')])],
    'domain_force': "[('user_id','=',user.id)]",
    'perm_read': True, 'perm_write': True,
    'perm_create': True, 'perm_unlink': False,
}])
```

### Reglas globales (sin grupos)

Vacio en `groups` = aplica a TODOS los usuarios y NO se puede saltar
con `sudo()`. Usa esto para multi-company:

```python
{'groups': [(6, 0, [])],
 'domain_force':
    "['|', ('company_id','=',False), ('company_id','in',company_ids)]"}
```

### Logica de combinacion

- Reglas dentro del MISMO grupo se combinan con **OR**.
- Reglas entre grupos distintos se combinan con **AND** con la
  interseccion de los grupos del usuario.
- Reglas globales se aplican siempre con **AND** sobre todo lo demas.

Mal entendido frecuente: si un usuario pertenece a dos grupos con reglas
distintas en el mismo modelo, ve la **interseccion** de ambas reglas
(AND), no la union.

## `sudo()` y bypass

`record.sudo()` saltea **`ir.model.access`** y **`ir.rule` no globales**.
**No** saltea reglas globales. Implicacion: para garantizar
multi-company, usa siempre reglas globales.

## Auditoria via script

```bash
python3 scripts/access_rule_audit.py --model crm.lead
```

Devuelve, para el modelo dado, todas las `ir.model.access` y `ir.rule`
activas, con sus grupos y dominios. Util antes de crear nuevas para
detectar conflictos.
