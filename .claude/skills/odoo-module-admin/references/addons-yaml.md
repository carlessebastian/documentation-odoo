# `addons.yaml` (doodba)

## Que es

`addons.yaml` declara que addons activar en `auto/addons` (la ruta
real montada en el contenedor Odoo via `addons_path`). doodba lee
este YAML al hacer `invoke img-build` o `invoke addons` y crea
symlinks selectivos.

Path canonico: `custom/src/addons.yaml`.

## Sintaxis basica

Cada clave de primer nivel es el nombre de un repo (subcarpeta de
`custom/src/`). Su valor es una lista de modulos a activar, **o**
`"*"` para activar todos los modulos del repo.

```yaml
private:
  - "*"        # todos los addons en custom/src/private/

l10n-spain:
  - "*"

account-financial-tools:
  - account_lock_date_update
  - account_move_line_purchase_info
  - account_chart_update

server-tools:
  - auditlog
  - base_technical_user
  - mail_environment

queue:
  - queue_job
  - queue_job_cron
```

## Directivas `ONLY` y `EXCEPT`

Permiten condicionar la inclusion segun env vars:

```yaml
ONLY:
  ODOO_VERSION: ["19.0"]
  CI: ["1"]
EXCEPT:
  CI: ["1"]
```

Uso tipico: distintos sets de modulos por entorno (devel cargado de
testing tools, prod minimo).

```yaml
account-financial-reporting:
  - account_financial_report
  - mis_builder
  - mis_builder_budget

ONLY:
  ENVIRONMENT: ["devel"]
EXCEPT:
  ENVIRONMENT: ["prod"]
server-tools:
  - dev_tools
  - debug_console
```

## Reglas

1. Si `private` aparece, suele llevar `"*"` para activar todos los
   modulos privados sin enumerarlos.
2. **Orden importa para `addons_path`**: cuanto mas arriba, mas
   prioridad si dos repos tienen un modulo con el mismo nombre. doodba
   genera el orden segun el orden del YAML.
3. **Modulos no listados** no se activan aunque esten clonados. Util
   para mantener repos completos pero activar solo lo necesario.
4. La activacion se materializa via symlinks en `auto/addons`. Si
   editas el YAML pero no regeneras, los cambios no se ven.

## Regeneracion de `auto/addons`

```bash
# Via doodba invoke
ssh "$DOODBA_SSH_HOST" "cd $DOODBA_PROJECT_DIR && invoke img-build"

# Via docker compose directo
ssh "$DOODBA_SSH_HOST" \
  "cd $DOODBA_PROJECT_DIR && \
   docker compose run --rm -T odoo --addons --git-aggregate"
```

Tras regenerar, **siempre `update_list()` via RPC** o reinicio del
contenedor para que Odoo descubra los nuevos addons.

## Verificar que un addon esta activo

```bash
ssh "$DOODBA_SSH_HOST" \
  "ls -la $DOODBA_PROJECT_DIR/odoo/auto/addons/ | grep <module_name>"
```

Si aparece como symlink a `custom/src/<repo>/<module_name>` -> activo.
Si no aparece pero el modulo si esta en `custom/src/<repo>/`, el
`addons.yaml` no lo lista o el regen no se hizo.

## Errores frecuentes

- **Symlink roto**: el modulo se removio del repo OCA pero sigue en
  `addons.yaml`. `auto/addons/<modulo>` existe pero apunta a vacio.
  Solucion: quitarlo del YAML y regenerar.
- **Modulo aparece dos veces**: dos repos contienen un modulo con el
  mismo nombre tecnico (e.g. `partner_firstname` en server-tools y
  partner-contact). El primero del YAML gana. Para resolver, mover el
  preferido arriba o quitar uno.
- **Modulo activo en YAML pero `update_list()` no lo ve**: olvido del
  regen. Re-ejecutar `invoke img-build` o equivalente.

## Patron canonico para addons OCA-ES

```yaml
private: ["*"]

l10n-spain:
  - l10n_es
  - l10n_es_aeat
  - l10n_es_aeat_mod303
  - l10n_es_aeat_mod347
  - l10n_es_aeat_mod349
  - l10n_es_aeat_mod390
  - l10n_es_aeat_sii_oca
  - l10n_es_facturae
  # Anyadir l10n_es_verifactu_oca cuando este disponible en 19.0

account-financial-reporting:
  - mis_builder
  - mis_builder_budget
  - account_financial_report

account-financial-tools:
  - account_lock_date_update
  - account_chart_update

bank-payment:
  - account_payment_partner
  - account_payment_mode
  - account_banking_sepa_direct_debit

server-tools:
  - auditlog
  - base_technical_user
  - module_auto_update

queue:
  - queue_job

web:
  - web_responsive
```

## Sincronizar `addons.yaml` con `repos.yaml`

Regla: **cada repo de primer nivel en `addons.yaml` debe existir como
clave en `repos.yaml`**. Si activas `bank-payment` pero olvidas anyadirlo
a `repos.yaml`, el clone no existe y los symlinks fallan.

`scripts/manifest_lint.py` puede usarse para validar manifests despues
de un regen; para validar que todos los repos referenciados existen,
hacer:

```bash
ssh "$DOODBA_SSH_HOST" \
  "cd $DOODBA_PROJECT_DIR/custom/src && \
   for d in \$(yq -r 'keys[]' addons.yaml); do \
     [ -d \$d ] || echo MISSING: \$d; \
   done"
```
