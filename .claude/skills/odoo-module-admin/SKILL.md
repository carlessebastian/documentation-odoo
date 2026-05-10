---
name: odoo-module-admin
description: |
  Usa este skill SOLO para gestionar el ciclo de vida de modulos en una
  instancia Odoo 19 Community self-hosted desplegada con Docker / doodba
  (Tecnativa). Cubre: instalar/actualizar/desinstalar modulos del core,
  OCA o custom; mantener `addons.yaml` y `repos.yaml`; ejecutar
  `gitaggregate` (git-aggregator) para sincronizar repos OCA pinneados
  a 19.0; orquestar `odoo-bin -i` / `-u` con `--stop-after-init` via
  `ssh ... 'docker exec odoo ...'`; reiniciar el contenedor; auditar
  `ir.module.module` (states uninstalled / to install / installed /
  to upgrade / to remove); validar `__manifest__.py` antes de instalar;
  diferencias `external_dependencies` vs `pip list` del contenedor;
  recomendar modulos OCA `l10n-spain`, `server-tools`, `server-auth`,
  `account-financial-tools`, `account-financial-reporting`, `web`,
  `queue`, `bank-payment`. Activa este skill aunque el usuario solo
  diga "instala el modulo X", "actualiza modulos", "OCA", "addons_path",
  "addons.yaml", "repos.yaml", "gitaggregate", "doodba", "git pull en
  /opt/doodba", "reinicia Odoo", "modulo no aparece en Apps",
  "pip install odoo-addon falla", "migrar de 17 a 19", "OpenUpgrade",
  "install module", "upgrade -u all", "module crashes at boot".

  DO NOT trigger for (handoff to sibling skills):
    - Crear/postear facturas, registrar pagos, conciliar extractos,
      modelos AEAT, SII / Veri*Factu / FacturaE
      -> use skill `odoo-accounting-es`.
    - Crear/modificar usuarios, grupos, ACLs, reglas de registro,
      multi-company, diarios y secuencias como configuracion,
      posiciones fiscales, ir.cron, parametros de sistema
      -> use skill `odoo-functional-admin`.

  No usar para sysadmin generico (nginx, certbot, PostgreSQL backups,
  systemd troubleshooting fuera de Odoo) ni desarrollo de modulos
  custom desde cero (eso es trabajo de un developer humano).
license: MIT
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash(python3:*)
  - Bash(uv:*)
  - Bash(ssh:*)
  - Bash(git:*)
  - Bash(pip:*)
  - Bash(docker:*)
  - WebFetch
metadata:
  version: "0.1.0"
  target_odoo_version: "19.0"
  deployment: "docker-doodba-tecnativa"
---

# Skill: Odoo 19 Community + administracion de modulos (Docker / doodba)

Este skill convierte a Claude en administrador de modulos de una instancia
Odoo 19 Community desplegada con la plantilla **Tecnativa doodba**
(`docker-compose` + estructura `src/repos.yaml`, `src/addons.yaml`,
`auto/addons`). Cubre el ciclo install/upgrade/uninstall via
combinacion de:

- **RPC** sobre `ir.module.module` (estado, busqueda, dependencias).
- **SSH + `docker exec`** para `odoo-bin -i/-u`, `gitaggregate`, restart.
- **Lectura local** de `__manifest__.py` para validar antes de tocar nada.

Si el deployment NO es doodba (instalacion bare-metal con systemd, otra
template Docker, instalacion via pip puro), el skill sigue siendo util
pero algunas referencias a `gitaggregate` o `auto/addons` no aplican
(ver `references/doodba-topology.md`, seccion "non-doodba fallback").

## Variables de entorno requeridas

| Variable | Proposito |
|----------|-----------|
| `ODOO_URL` | URL base, p.ej. `https://odoo.miempresa.cat` |
| `ODOO_DB` | Nombre de la base, p.ej. `miempresa_prod` |
| `ODOO_USER` | Login del bot (para fallback XML-RPC). |
| `ODOO_API_KEY` | API key del bot. |
| `DOODBA_SSH_HOST` | Host SSH, p.ej. `odoo@erp.ikigaimagi.com` |
| `DOODBA_PROJECT_DIR` | Path remoto al proyecto doodba, p.ej. `/opt/doodba/ikigai` |
| `DOODBA_COMPOSE_SERVICE` | (Opcional) Nombre del servicio en compose, default `odoo`. |
| `DOODBA_DB_NAME` | (Opcional) Si difiere de `ODOO_DB`. |

Si falta cualquiera, **detente y pidela al usuario antes de ejecutar nada**.
Especialmente `DOODBA_SSH_HOST` y `DOODBA_PROJECT_DIR`: sin SSH solo
puedes hacer operaciones RPC de auditoria, no install/upgrade.

## Tabla de despacho

| El usuario pide... | Ejecuta | Antes lee |
|--------------------|---------|-----------|
| **Inspeccion** | | |
| Estado de un modulo | `scripts/module_status.py --names X,Y,Z` | `references/module-lifecycle.md` |
| Snapshot de todos los modulos | `scripts/audit_module_state.py` | `references/module-lifecycle.md` |
| Validar `__manifest__.py` antes de instalar | `scripts/manifest_lint.py path/to/module` | `references/module-lifecycle.md` |
| Diff dependencias pip | `scripts/pip_deps_check.py --names X,Y` | `references/docker-exec-patterns.md` |
| **Instalacion / upgrade / uninstall** | | |
| Instalar modulo (production) | `scripts/module_install.py --names X` | `references/module-lifecycle.md`, `references/docker-exec-patterns.md` |
| Actualizar modulo(s) | `scripts/module_upgrade.py --names X,Y` | `references/upgrade-strategy.md` |
| Desinstalar modulo | `scripts/module_uninstall.py --names X` | `references/module-lifecycle.md` |
| **Repos OCA / addons** | | |
| Sincronizar repos.yaml | `scripts/repos_aggregate.sh` (--dry-run primero) | `references/git-aggregator.md`, `references/addons-yaml.md` |
| Reconstruir auto/addons tras pull | `scripts/addons_pull.sh` | `references/doodba-topology.md` |
| **Operativa Docker** | | |
| Reiniciar contenedor Odoo | `scripts/docker_restart.sh` | `references/docker-exec-patterns.md`, `references/ssh-safety.md` |
| Ejecutar comando arbitrario en Odoo container | `scripts/docker_exec.sh -- <cmd>` | `references/docker-exec-patterns.md` |
| **Migracion de version** | | |
| Migrar 18 -> 19 con OpenUpgrade | (multi-paso, ver `references/upgrade-strategy.md`) | `references/upgrade-strategy.md` |

## Reglas de seguridad que debes cumplir SIEMPRE

1. **NUNCA `odoo-bin -u all` en produccion sin backup previo**. Pide al
   usuario un dump (`pg_dump`) y tar del filestore antes. Si el usuario
   se niega, detente y pide confirmacion explicita por escrito.
2. **Prefiere `module_upgrade.py` (que envuelve `odoo-bin -u`) sobre
   `-u all`**: actualizar solo lo necesario reduce ventana de riesgo.
3. **`button_immediate_install` via RPC recarga la registry y rompe la
   conexion**. El skill usa SSH como path canonico para
   install/upgrade/uninstall en produccion. La via RPC se considera
   solo para entornos dev y exige reconexion.
4. **Apps list desactualizada**: tras anyadir carpetas nuevas en
   `auto/addons`, los modulos no aparecen hasta que llamamos
   `update_list()`. `module_install.py` lo hace automaticamente.
5. **OCA branch matching es estricto**: un modulo de
   `OCA/server-tools/18.0` NO carga en Odoo 19. Antes de instalar,
   verifica que la rama del repo OCA en `repos.yaml` sea exactamente
   `19.0`.
6. **Dependencias en `__manifest__.py['depends']`** las instala Odoo
   automaticamente; NO instales manualmente en orden arbitrario, deja
   al loader hacer su topological sort.
7. **Desinstalar borra datos del modulo**: `unlink` de los registros
   propietarios (campos custom, modelos `_auto=True`). Datos de modelos
   estandar (`account.move`, `res.partner`) sobreviven, pero columnas
   custom no. **Detente y pide confirmacion explicita** antes de cada
   uninstall, mostrando los modelos definidos por el modulo.
8. **`--dry-run` por defecto en operaciones SSH destructivas**. El
   usuario debe pedir explicitamente la ejecucion real.
9. **Comandos SSH permitidos** (whitelist; ver `references/ssh-safety.md`):
   `docker exec`, `docker compose`, `gitaggregate`, `cd`, `git status`,
   `git log`, `cat`, `tail`, `ls`. **Prohibido**: `rm`, `mv` fuera de
   `auto/`, `chown`, edicion de `docker-compose.yml`, cualquier comando
   que requiera sudo fuera del usuario `odoo`.

## Workflow: instalar un modulo (canonico)

1. Pide al usuario el nombre tecnico (`l10n_es_aeat_mod303`, no
   "Modelo 303"). Si no lo sabe, ayudale via `references/oca-ecosystem.md`.
2. Verifica el estado actual:
   `scripts/module_status.py --names l10n_es_aeat_mod303`.
3. Si `state == "installed"`: avisa al usuario, sugiere `module_upgrade.py`.
4. Si `state == "uninstallable"`: detente; el manifest tiene errores.
   Muestra el manifest con `manifest_lint.py` para diagnosticar.
5. Si `state == "uninstalled"`: continua.
6. Si el modulo aparece como "no encontrado": probablemente falta
   refrescar la apps list **o** el modulo no esta en `addons.yaml` o
   `repos.yaml`. Sugiere ejecutar `repos_aggregate.sh --dry-run` y
   anyadir la entrada a YAML.
7. Ejecuta `scripts/manifest_lint.py /path/to/module` localmente si
   tienes el repo clonado, para validar antes de tocar produccion.
8. **Detente y pide confirmacion** mostrando: nombre, version del
   manifest, dependencias que se instalaran tambien (transitivas).
9. Ejecuta `scripts/module_install.py --names l10n_es_aeat_mod303`.
   El script:
   1. Llama `update_list()` via RPC.
   2. Hace SSH + `docker exec odoo odoo --stop-after-init -d <db>
      -i l10n_es_aeat_mod303 --no-http`.
   3. Tras terminar, reinicia el contenedor para reanudar HTTP normal.
   4. Verifica via RPC que el modulo paso a `state="installed"`.

## Workflow: upgrade tras `git pull` en repos OCA

1. Pregunta al usuario que repos hizo pull.
2. Verifica que las ramas son `19.0` con `git -C <ruta> branch --show-current`.
3. Ejecuta `scripts/repos_aggregate.sh --dry-run` para ver el diff que
   `gitaggregate` aplicaria.
4. Una vez confirmado, ejecuta `scripts/repos_aggregate.sh` (sin --dry-run).
5. Reconstruye auto/addons: `scripts/addons_pull.sh`.
6. **Backup**: pide al usuario `pg_dump` antes de seguir.
7. Ejecuta `scripts/module_upgrade.py --changed` para detectar y
   actualizar solo lo cambiado. Esto envuelve `odoo-bin -u <names>`.
8. Reinicia: `scripts/docker_restart.sh`.
9. Verifica: `scripts/audit_module_state.py | jq '.[] | select(.state != "installed")'`.

## Workflow: desinstalar un modulo

1. Comprueba dependientes con `scripts/module_status.py --names X
   --include-rdepends`. Si hay modulos instalados que dependen de X,
   listalos al usuario y pide confirmacion (Odoo desinstalara la cadena).
2. Lista los modelos definidos por el modulo:
   `scripts/module_status.py --names X --models`.
3. **Detente y pide confirmacion** mostrando modelos y datos que se
   perderan. Pide backup.
4. Ejecuta `scripts/module_uninstall.py --names X --confirm`.
5. Verifica que el state paso a `uninstalled`.

## Skills hermanos (handoff)

| Si el usuario pide... | Usa el skill |
|-----------------------|--------------|
| Crear factura, postear, conciliar, modelos AEAT | `odoo-accounting-es` |
| Enviar SII / Veri*Factu / FacturaE | `odoo-accounting-es` |
| Crear/modificar usuarios, grupos, ACLs | `odoo-functional-admin` |
| Crear diarios o secuencias como *configuracion inicial* | `odoo-functional-admin` |
| Configurar multi-company, branches, holding | `odoo-functional-admin` |
| Crear/pausar `ir.cron` | `odoo-functional-admin` |

Caso fronterizo: "instala el modulo `account_intercompany` y configurame
las reglas". Este skill instala el modulo; **deriva** la configuracion
de las reglas a `odoo-functional-admin` (`scripts/intercompany_setup.py`).

## Punteros a las references

- `references/doodba-topology.md` - layout Tecnativa, volumes, mounts;
  "non-doodba fallback" para deploys ad-hoc.
- `references/module-lifecycle.md` - states de `ir.module.module`,
  loader, `update_list()`, RPC vs SSH.
- `references/git-aggregator.md` - formato `repos.yaml`, pinning sha vs
  branch, conflictos en pulls.
- `references/addons-yaml.md` - formato `addons.yaml`, ONLY/EXCEPT,
  generacion de `auto/addons`.
- `references/docker-exec-patterns.md` - `docker exec -u odoo`, exit
  codes, log streaming, `--no-http`.
- `references/upgrade-strategy.md` - pre-checks, OpenUpgrade para saltos
  mayores, smoke test.
- `references/ssh-safety.md` - whitelist de comandos, --dry-run, locks.
- `references/domain-syntax.md` - dominios Odoo (compartido con accounting-es).

## Calidad y tests

```bash
cd .claude/skills/odoo-module-admin
python3 -m pytest tests/ -v
```

Cubre helpers puros: parser de `__manifest__.py`, construccion de
comandos SSH (con `--dry-run`), parseo de exit codes. **No** ejecuta
SSH ni RPC reales; las llamadas se mockean. Para integracion,
ejecutar contra una instancia doodba de testing.

## Evals

`evals/evals.json` lista should-trigger / should-not-trigger / handoff.
