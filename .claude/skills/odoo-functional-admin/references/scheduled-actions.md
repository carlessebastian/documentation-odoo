# Acciones programadas (`ir.cron`)

## Modelo

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | Char | Etiqueta. |
| `model_id` | Many2one(ir.model) | Modelo sobre el que se ejecuta. |
| `state` | Selection | `code` (Python inline) o `object_method` (recomendado). |
| `code` | Text | Codigo Python si `state='code'`. |
| `cron_name` (alias `name`) / `function` | Char | Nombre del metodo si `state='object_method'`. |
| `interval_number` / `interval_type` | Int / Selection | `minutes`, `hours`, `days`, `weeks`, `months`. |
| `numbercall` | Int | Numero maximo de ejecuciones (-1 = infinito). |
| `nextcall` | Datetime | Proxima ejecucion. |
| `priority` | Int | Default 5; menor numero = mas prioritario. |
| `active` | Boolean | Pause/resume. |
| `user_id` | Many2one(res.users) | Suele ser `base.user_root`. |
| `lastcall` | Datetime | Ultima ejecucion. |

## Patrones canonicos

### Crear un cron que ejecuta un metodo

```python
client.call('ir.cron', 'create', [{
    'name': 'Recompute partner credits',
    'model_id': model_id_of('res.partner'),
    'state': 'code',
    'code': "model._compute_credit_debit()",
    'interval_number': 1,
    'interval_type': 'days',
    'numbercall': -1,
    'active': True,
    'user_id': uid_of('base.user_root'),
}])
```

### Ejecutar un cron AHORA (`method_direct_trigger`)

```python
client.call('ir.cron', 'method_direct_trigger', [[cron_id]])
```

Se salta `nextcall` y ejecuta inmediatamente. Util para debug. **No**
modifica `nextcall`; el cron sigue su ciclo normal despues.

### Pausar / reanudar

```python
client.call('ir.cron', 'write', [[cron_id], {'active': False}])  # pause
client.call('ir.cron', 'write', [[cron_id], {'active': True}])   # resume
```

## `scripts/cron_manage.py` (uso)

```bash
python3 scripts/cron_manage.py list
python3 scripts/cron_manage.py pause --id 42
python3 scripts/cron_manage.py resume --id 42
python3 scripts/cron_manage.py run --id 42
```

`list` devuelve JSON con todos los crons activos: id, name, model,
interval, nextcall, lastcall, active.

## Crons criticos en una instalacion ES tipica

| Nombre | Frecuencia | Que hace |
|--------|-----------|----------|
| `Mail: Fetchmail Service` | 5 min | IMAP/POP. |
| `Mail: Send Email Queue` | 1 min | Envia mails encolados. |
| `Bank Synchronization: refresh transactions` | 4 horas | Si OdooFin/OCA. |
| `Currency Rate Update` | 1 dia | Tipos de cambio. |
| `Account: Auto-validate accounting locks` | 1 dia | Lock dates auto. |
| `Account Move Auto-Post` | 1 hora | Posteo de moves recurrentes. |
| `Verifactu: Send pending` | 5 min | Modulos OCA Verifactu. |
| `SII: Send pending invoices` | 30 min | Si SII activo. |

## Politica de errores

Un cron que lanza una excepcion **NO** se desactiva automaticamente; se
reintenta en el siguiente `nextcall`. Esto puede llenar logs si el error
es persistente. Politica recomendada:

1. Mirar `Settings -> Technical -> Logging` o `ir.logging` para ver
   ultimas trazas.
2. Si el error es de configuracion (falta cuenta, falta cert), **pausar
   el cron** mientras se resuelve.
3. No tocar `nextcall` directamente para "reintentar antes"; usar
   `method_direct_trigger`.

## Multi-worker y locks

Si hay >1 worker Odoo, el cron loop usa locks PostgreSQL advisory para
no ejecutar el mismo cron en dos workers simultaneamente. Implicacion:
**no escribas crons no-idempotentes**.

## Que NO hacer

- **No** hardcodees fechas en `nextcall` para "saltar" un cron; usa
  `active=False` y restaura cuando toque.
- **No** crees crons con `interval_number=0`; cuelgan el loop.
- **No** uses `state='code'` con codigo largo; mete la logica en un
  metodo del modelo y usa `state='object_method'`.
