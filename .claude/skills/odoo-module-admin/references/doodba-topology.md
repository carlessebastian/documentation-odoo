# Doodba topology (Tecnativa)

## Layout esperado

`doodba` es la plantilla de Tecnativa para Odoo en Docker (basada en
Copier). Estructura tipica de un proyecto:

```
/opt/doodba/ikigai/                 ← DOODBA_PROJECT_DIR
├── docker-compose.yml              ← stack runtime
├── docker-compose.override.yml     ← overrides locales
├── invoke.yaml                     ← config de pyinvoke (opcional)
├── odoo/
│   ├── auto/
│   │   ├── addons/                 ← symlinks generados por addons.yaml
│   │   └── ...
│   ├── custom/
│   │   ├── src/
│   │   │   ├── addons.yaml         ← que addons activar
│   │   │   ├── repos.yaml          ← repos OCA + custom (git-aggregator)
│   │   │   ├── private/            ← addons internos no-OCA
│   │   │   ├── account-financial-tools/   ← clones OCA
│   │   │   ├── server-tools/
│   │   │   ├── l10n-spain/
│   │   │   └── ...
│   │   ├── conf.d/                 ← snippets de odoo.conf
│   │   ├── dependencies/           ← deps extra (apt/pip)
│   │   └── ssh/                    ← claves para repos privados
│   └── ...
├── volumes/
│   ├── odoo/
│   │   ├── filestore/              ← sesiones, attachments
│   │   └── data/
│   └── db/                         ← postgres data
└── ...
```

## docker-compose servicios tipicos

| Servicio | Imagen / build | Funcion |
|----------|----------------|---------|
| `odoo` | build local con doodba base image | Worker HTTP de Odoo. |
| `db` | `postgres:15` (o version compatible) | Base de datos. |
| `proxy` | `traefik:2` | Reverse proxy HTTPS (a veces). |
| `mailhog` o `smtp` | (en devel) | SMTP de pruebas. |
| `letsencrypt-companion` | nginx + acme | Cert autorenewal. |

El servicio Odoo se llama `odoo` por convencion (override-able via
`DOODBA_COMPOSE_SERVICE`).

## Mounts criticos

```
volumes:
  - ./odoo/auto/addons:/opt/odoo/auto/addons:ro
  - ./odoo/custom:/opt/odoo/custom:ro
  - ./volumes/odoo/filestore:/var/lib/odoo/filestore
```

Implicacion: cuando ejecutas `gitaggregate` o `pip install` localmente
en el host, los cambios se ven dentro del contenedor sin rebuild
**solo si los mounts cubren la ruta**. Para cambios en `auto/addons`,
basta restart. Para cambios en imagen base (apt deps, base image),
requiere `docker compose build`.

## `addons.yaml`

Define que modulos de cada repo activar. Ejemplo:

```yaml
private:
  - "*"   # todos los addons en custom/src/private
account-financial-tools:
  - account_lock_date_update
  - account_move_line_purchase_info
l10n-spain:
  - "*"
server-tools:
  - auditlog
  - base_technical_user
ONLY:
  CI: <2>
  EXCEPT:
    - some_addon_skipped_in_ci
```

doodba procesa este YAML y crea symlinks en `auto/addons` apuntando a
los modulos de cada repo clonado en `custom/src/<repo>/`.

## `repos.yaml`

Procesado por `git-aggregator`. Formato:

```yaml
custom/src/server-tools:
  defaults:
    depth: 1
  remotes:
    oca: https://github.com/OCA/server-tools.git
  merges:
    - oca 19.0
  target: oca 19.0

custom/src/l10n-spain:
  remotes:
    oca: https://github.com/OCA/l10n-spain.git
  merges:
    - oca 19.0
  target: oca 19.0

custom/src/private:
  remotes:
    origin: [email protected]:ikigai/odoo-private.git
  merges:
    - origin 19.0
  target: origin 19.0
```

`gitaggregate -c repos.yaml` clona/actualiza todos los repos.

## Comandos via `invoke` (pyinvoke)

doodba expone tareas predefinidas:

| Comando | Que hace |
|---------|----------|
| `invoke develop` | Build inicial + run en modo dev. |
| `invoke install` | Instala dependencias del template. |
| `invoke img-build` | Build de la imagen Odoo con dependencias. |
| `invoke git-aggregate` | Atajo de `gitaggregate -c custom/src/repos.yaml`. |
| `invoke restart` | Reinicia el servicio odoo. |
| `invoke logs` | tail -f de logs. |
| `invoke shell` | Abre shell de Odoo (`odoo shell -d <db>`). |

Los scripts del skill pueden llamar via `ssh <host> 'cd $PROJECT && invoke ...'`
o directamente `docker compose ...`.

## Non-doodba fallback

Si el deployment NO es doodba sino plain `docker-compose` con un volumen
de addons custom:

- `repos.yaml` / `addons.yaml` / `auto/addons` no existen.
- En su lugar hay `custom_addons/` o similar montado en `/mnt/extra-addons`.
- `gitaggregate` no aplica; el usuario hara `git pull` manual o tendra
  cada repo como submodulo.
- El skill sigue siendo util para `module_install.py`, `module_upgrade.py`
  (que solo dependen de SSH + docker exec), pero `repos_aggregate.sh` y
  `addons_pull.sh` no son llamables.

Si el deployment es **bare-metal con systemd** (sin Docker):
- `docker exec` se reemplaza por `sudo -u odoo /opt/odoo/odoo-bin ...`.
- Restart: `sudo systemctl restart odoo`.
- En este caso, este skill necesita ajustes en los scripts SSH; los
  helpers Python (`module_status.py`, `manifest_lint.py`) siguen
  funcionando porque solo usan RPC / lectura local.

Para activar el path bare-metal hay que setear
`DOODBA_COMPOSE_SERVICE=` (vacio) y los scripts adaptan el comando.

## Caches y locks

- `auto/addons` es read-only desde el contenedor; modificaciones se
  hacen en `custom/src/` y `addons.yaml`.
- doodba cachea la lista de addons en `auto/addons-checksum`. Tras un
  cambio de `addons.yaml`, hay que regenerar.
- PostgreSQL usa locks advisory (`pg_advisory_xact_lock`) durante
  upgrades; varios `odoo-bin -u` simultaneos esperan en cola.
