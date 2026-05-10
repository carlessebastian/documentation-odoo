# Ciclo de vida de modulos en Odoo 19

## Modelo `ir.module.module`

| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | Char | Nombre tecnico (`l10n_es`, `account`). |
| `shortdesc` | Char | Nombre legible. |
| `state` | Selection | uninstalled / to install / installed / to upgrade / to remove / uninstallable. |
| `latest_version` | Char | Version del manifest del codigo en disco. |
| `installed_version` | Char | Version actualmente registrada en DB. |
| `author` | Char | Indicador de origen (Odoo S.A., OCA, custom). |
| `license` | Selection | LGPL-3, AGPL-3, OEEL-1, etc. |
| `dependencies_id` | One2many | Dependencias declaradas. |
| `application` | Boolean | True para Apps "principales" (visibles en home). |
| `auto_install` | Boolean | Se instala solo si todas las deps estan instaladas. |
| `category_id` | Many2one | Categoria (Accounting, Sales). |
| `summary` | Char | One-liner descriptivo. |

## Estados y transiciones

```
uninstalled  ──install──►  to install  ──[apply]──►  installed
installed    ──upgrade──►  to upgrade  ──[apply]──►  installed
installed    ──uninstall──►  to remove ──[apply]──►  uninstalled
uninstalled  ──(error)────►  uninstallable  (manifest invalido)
```

Estados transitorios (`to install`, `to upgrade`, `to remove`) se
materializan con un restart de Odoo en modo `--update` o llamando
explicitamente al loader.

## Metodos clave

| Metodo | Que hace |
|--------|----------|
| `update_list()` | Refresca la lista escaneando carpetas en `addons_path`. |
| `button_install` | Marca el modulo como `to install` (sin aplicar). |
| `button_immediate_install` | Marca + recarga registry inmediatamente. **Rompe la conexion RPC.** |
| `button_upgrade` | Marca como `to upgrade`. |
| `button_immediate_upgrade` | Marca + aplica. Mismo caveat de conexion. |
| `button_uninstall` | Marca como `to remove`. |
| `button_immediate_uninstall` | Marca + aplica. Mismo caveat. |
| `module_uninstall` | Variante interna; no usar directamente. |
| `_button_immediate_function` | Helper interno para los `_immediate_*`. |

## RPC vs CLI: cuando cada uno

| Caso | Recomendado |
|------|-------------|
| Instalar 1 modulo en dev/test | RPC OK (rompe conexion, reconectar). |
| Instalar/upgrade en produccion | **CLI** (`odoo-bin -i/-u --stop-after-init`). |
| Upgrade `-u all` despues de pull | **CLI** o `click-odoo-update`. |
| Uninstall | **CLI** preferible (registry reload garantizado). |
| Ver estado / inspeccionar | **RPC** (no muta nada). |
| Cuando hay >1 worker | **CLI** (evita conflictos de cache cross-worker). |

## CLI `odoo-bin`

Flags relevantes:

| Flag | Significado |
|------|-------------|
| `-d <db>` | Base de datos. |
| `-i <names>` | Install (CSV de modulos, `all` para todos disponibles). |
| `-u <names>` | Update/upgrade. `all` actualiza todo lo instalado. |
| `--stop-after-init` | Sale tras la operacion. **Critico** para que no levante HTTP. |
| `--no-http` | No abre puerto. Util en one-shot junto con `--stop-after-init`. |
| `--logfile <path>` | Log a fichero (preferido para auditoria). |
| `--upgrade-path <dir>` | Para OpenUpgrade scripts. |
| `--load <modules>` | Modulos cargados al boot (default `web,base`). |

Ejemplo canonico via SSH + Docker:

```bash
ssh "$DOODBA_SSH_HOST" \
  "cd $DOODBA_PROJECT_DIR && \
   docker compose run --rm -T odoo \
     odoo --stop-after-init --no-http \
     -d $DOODBA_DB_NAME -i l10n_es_aeat_mod303 \
     --logfile /var/log/odoo/install.log"
```

`docker compose run --rm` levanta un contenedor efimero del servicio
`odoo` (mismo image y mounts) que se elimina al salir. Es seguro
ejecutarlo en paralelo al contenedor de produccion porque **no comparten
worker**, solo DB y filestore. **Importante**: usa `-T` para evitar
TTY allocation que rompe los pipes de SSH.

## `update_list()` quirks

- Necesario tras anyadir modulos a `auto/addons` (despues de modificar
  `addons.yaml` y regenerar).
- Rapido (~segundos) en local; mas lento en deploys grandes.
- Para script: `client.call('ir.module.module', 'update_list', [])`.
- Si te devuelve `[N, M]`, N = modulos detectados, M = modulos nuevos.

## OCA branch matching

Cada repo OCA tiene una rama por version Odoo:

| Branch | Compatible con |
|--------|----------------|
| `19.0` | Odoo 19. |
| `18.0` | Odoo 18. |
| `17.0` | Odoo 17. |
| `master` | Sin guarantia (tracking de Odoo nightly). |

Un modulo de `18.0` cargado en Odoo 19 produce error en boot
(`uninstallable: True` o crash). Verificar siempre antes:

```bash
git -C custom/src/<repo> branch --show-current
```

Debe ser `19.0` para Odoo 19.

## `auto_install` y modulos puente

Modulos como `account_accountant`, `sale_stock`, etc. tienen
`auto_install=True`: se instalan automaticamente cuando todas sus
dependencias estan instaladas. No necesitas instalarlos manualmente.

Implicacion: tras instalar `account` y `stock`, `account_stock` (si
existe) aparece como instalado sin haberlo pedido.

## Modulos en estado `uninstallable`

Causas frecuentes:

1. `__manifest__.py` con error de sintaxis Python -> ver `manifest_lint.py`.
2. Falta `installable: True` en el manifest.
3. Dependencia listada en `depends` que no existe en el deployment.
4. `external_dependencies` (Python o bin) no resueltas en imagen.

Diagnostico:

```bash
docker compose run --rm -T odoo \
  odoo --stop-after-init --no-http \
  -d $DB -u $MOD --log-level=debug 2>&1 | tail -50
```

## Cache de `ir.module.module` y workers

Odoo cachea la registry por base de datos por worker. Tras un install
real (con registry reload), TODOS los workers deben recibir la senal
SIGHUP o un restart. Doodba lo gestiona con un restart del servicio.

`module_install.py` siempre reinicia tras la operacion.
