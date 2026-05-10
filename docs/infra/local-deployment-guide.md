# Despliegue local de Odoo 19 con doodba — guía corregida

Procedimiento **probado y refinado** para arrancar Odoo 19 Community
con doodba en Docker local (macOS o Linux). Reemplaza Modo A de
`doodba-bootstrap.md` cuando haya divergencia: incorpora todas las
correcciones descubiertas durante el primer despliegue real
(`inpr3mium-local`, 2026-05-10).

> **Audiencia**: el humano que provisiona la instancia y el agente
> Claude que pueda automatizarlo. El agente ya conoce estas
> correcciones por memoria; este documento es la fuente
> canónica versionada.
>
> **Aplicabilidad**: Docker local en macOS Darwin + Docker Desktop, o
> Linux nativo. Para producción gcloud usar Modo B de
> `doodba-bootstrap.md`.

---

## Tabla de gotchas — referencia rápida

| # | Gotcha | Sección |
|---|---|---|
| 1 | `copier copy` falla sin `invoke` y `pre-commit` | [§1](#1-prerrequisitos) |
| 2 | Passwords en `.copier-answers.yml` (versionado) | [§2](#2-copier-no-interactivo-con-passwords-aleatorios) |
| 3 | gitaggregate paths relativos al cwd | [§3](#3-reposyaml-paths-relativos) |
| 4 | `.empty` placeholder revienta el entrypoint en bind mounts macOS | [§4](#4-eliminar-empty-placeholders-solo-macos) |
| 5 | `/web/database/manager` da 500 si `PGDATABASE=devel` no existe | [§5](#5-creacion-de-db-via-cli-no-via-web-wizard) |
| 6 | Puertos `PORT_PREFIX=19` (no 8069) | [§6](#6-puertos-expuestos) |
| 7 | API keys exigen `expiration_date` y groups limitan a 90 días | [§7](#7-bot-user--api-key) |
| 8 | `groups_id` renombrado a `group_ids` en Odoo 19 | [§7](#7-bot-user--api-key) |
| 9 | Cliente del agente: `_json2` da 422 → forzar XML-RPC | [§9](#9-env-del-agente-y-onboard) |
| 10 | macOS bloquea `pip3 install --user` (PEP 668) → usar pipx | [§1](#1-prerrequisitos) |

---

## 0. Convenciones

- `<TENANT>` = slug del cliente (ej. `inpr3mium`). Se usa en nombres
  de carpeta, DB y bot user.
- Las instancias viven **fuera** del repo del agente, en
  `~/Documents/code/odoo-instances/<TENANT>-local/`. Esto evita que
  el `git status` del agente tenga ruido.
- Los secretos generados al vuelo se guardan en
  `~/Documents/code/odoo-instances/<TENANT>-local.SECRETS.txt`
  (mode 0600), **fuera** del proyecto doodba (porque
  `.copier-answers.yml` no está en gitignore).

---

## 1. Prerrequisitos

Tres herramientas Python que el runbook original no menciona pero
**son obligatorias**: `copier`, `git-aggregator` y `invoke` ejecutan
el wizard y los hooks; `pre-commit` es invocado por `invoke develop`.
Sin ellos, `copier copy` aborta en mid-run y deja todo a medias
(rollback completo).

```bash
# Una sola vez por máquina (macOS bloquea pip --user por PEP 668)
pipx install copier
pipx install git-aggregator
pipx install invoke
pipx install pre-commit
```

Verifica:

```bash
copier --version          # ≥ 9.5
gitaggregate -h           # 4.x
invoke --version          # ≥ 3.0
pre-commit --version      # ≥ 4.0
docker info               # daemon corriendo (Docker Desktop arrancado)
docker compose version    # v2.20+
```

`pytest` para los tests offline también vía pipx (con deps inyectadas):

```bash
pipx install pytest
pipx inject pytest pyyaml requests
```

---

## 2. Copier no-interactivo con passwords aleatorios

El wizard interactivo es lento y propenso a equivocarse. Usar
`--defaults` + `--data` para overrides clave. Generar passwords
**fuera** del wizard y guardarlos antes de invocarlo, porque
`.copier-answers.yml` se commitea por defecto y queremos que ese
fichero no contenga el secreto en claro a futuro (por ahora sí lo
contiene; revisar si doodba añade soporte de Secret Manager).

```bash
SLUG=<TENANT>
INSTANCES_DIR=~/Documents/code/odoo-instances
mkdir -p "$INSTANCES_DIR"

# Passwords aleatorios — guardar ANTES de copier
ADMIN_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
DB_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
SECRETS_FILE="$INSTANCES_DIR/$SLUG-local.SECRETS.txt"
cat > "$SECRETS_FILE" <<EOF
# Generados $(date +%Y-%m-%d) para $SLUG-local. NO COMMITEAR.
ODOO_ADMIN_MASTER_PASSWORD=$ADMIN_PW
POSTGRES_PASSWORD=$DB_PW
EOF
chmod 600 "$SECRETS_FILE"
```

Lanzar copier:

```bash
cd "$INSTANCES_DIR"
copier copy --trust --defaults \
  --data project_name=$SLUG-local \
  --data project_author="<Tu Nombre>" \
  --data odoo_version=19.0 \
  --data odoo_proxy="" \
  --data odoo_initial_lang=es_ES \
  --data odoo_admin_password="$ADMIN_PW" \
  --data postgres_version=16 \
  --data postgres_dbname=${SLUG}_dev \
  --data postgres_password="$DB_PW" \
  --data compose_version=v2+ \
  gh:Tecnativa/doodba-copier-template $SLUG-local
```

> **`postgres_version=16`** y no `18` (default actual): muchos
> addons OCA todavía no soportan PG18 en 19.0. Cambiar a 17/18
> cuando los repos pinneados confirmen compatibilidad.
>
> **`postgres_dbname=${SLUG}_dev`**: este valor fija
> `odoo_dbfilter=^${SLUG}_dev` en el odoo.conf generado, lo que
> permite auto-selección de DB sin pasar `?db=` en cada URL.

---

## 3. `repos.yaml`: paths relativos

`gitaggregate -c repos.yaml -e` se ejecuta desde
`odoo/custom/src/`. Las claves del YAML son rutas **relativas a
ese cwd**. Usar `./<repo>` (no `./custom/src/<repo>`) o los repos se
clonan a `custom/src/custom/src/<repo>`.

Mantener el bloque `./odoo:` que doodba ya provee (core Odoo via
OCB) y **anexar** los repos OCA del `profile.yaml` del tenant:

```yaml
# odoo/custom/src/repos.yaml
./odoo:
  defaults:
    depth: $DEPTH_DEFAULT
  remotes:
    ocb: https://github.com/OCA/OCB.git
    odoo: https://github.com/odoo/odoo.git
    openupgrade: https://github.com/OCA/OpenUpgrade.git
  target: ocb $ODOO_VERSION
  merges:
    - ocb $ODOO_VERSION

./l10n-spain:
  defaults: { depth: 1 }
  remotes: { oca: https://github.com/OCA/l10n-spain.git }
  target: oca 19.0
  merges: [ oca 19.0 ]

./server-tools:
  defaults: { depth: 1 }
  remotes: { oca: https://github.com/OCA/server-tools.git }
  target: oca 19.0
  merges: [ oca 19.0 ]

# ... (server-auth, account-financial-tools, account-financial-reporting,
#      web, queue, bank-payment — uno por cada entry de profile.oca_repos)
```

Sincronizar:

```bash
cd odoo/custom/src
ODOO_VERSION=19.0 DEPTH_DEFAULT=1 DEPTH_MERGE=100 \
  gitaggregate -c repos.yaml -e
```

Tarda 5-15 min la primera vez. Si los repos quedaron mal ubicados,
mover sin re-clonar:

```bash
cd odoo/custom/src
mv custom/src/* . && rmdir custom/src custom
```

`gitaggregate` reconoce los repos en el path nuevo (la metadata
git va con ellos) y la siguiente ejecución solo verifica refs.

---

## 4. Eliminar `.empty` placeholders (solo macOS)

Doodba crea `odoo/custom/{entrypoint,build}.d/.empty` como placeholder
de directorio. Su entrypoint Python en el contenedor evalúa:

```python
if os.access(command, os.X_OK) and not os.path.isdir(command):
    subprocess.check_call(command)
```

En **bind mounts de Docker Desktop macOS** (osxfs / VirtioFS),
`os.access(X_OK)` devuelve `True` aunque el archivo en el host
tenga mode 0644. Resultado al arrancar Odoo:

```
PermissionError: [Errno 13] Permission denied:
'/opt/odoo/custom/entrypoint.d/.empty'
```

Bug conocido del file sharing layer. Solución:

```bash
rm -f odoo/custom/entrypoint.d/.empty odoo/custom/build.d/.empty
```

La carpeta vacía es suficiente; el `os.listdir` del entrypoint
devuelve `[]` y el bucle no ejecuta nada. **En Linux nativo no es
necesario** (el bit X se respeta correctamente).

---

## 5. Creación de DB vía CLI (no vía web wizard)

`devel.yaml` hardcodea `PGDATABASE=devel`. Si esa DB no existe,
**toda petición HTTP** (`/`, `/web/login`,
`/web/database/manager`, `/web/database/selector`) devuelve
**HTTP 500** con `KeyError: 'ir.http'` porque el dispatcher de Odoo
intenta cargar el registry de la DB inexistente antes de servir
nada — incluso para endpoints que técnicamente no la requieren.

> **Por qué ocurre**: el `ir.http._dispatch` se lookupea desde el
> registry de la DB resuelta por dbfilter/Host, y al no haber DB
> alguna que coincida con `^${POSTGRES_DBNAME}` ni con `^devel`, falla.

**No usar el wizard web** para la primera DB. Usar CLI:

```bash
docker compose exec -T odoo odoo \
  --database=${SLUG}_dev \
  --init=base \
  --stop-after-init \
  --without-demo=all \
  --load-language=es_ES \
  --no-http
```

Esto crea la DB, instala `base` y carga el idioma `es_ES`. Tras
terminar (1-2 min), el dbfilter `^${SLUG}_dev` matchea y los
endpoints HTTP pasan a funcionar normalmente.

Alternativa: para arrancar el wizard web, exportar
`PGDATABASE=${SLUG}_dev` en un docker-compose override antes de
levantar el stack. Pero el CLI es más reproducible y evita el
issue del `master_password` (que en doodba dev defaulta a `admin`,
no al `odoo_admin_password` de copier).

---

## 6. Puertos expuestos

`devel.yaml` mapea con `${PORT_PREFIX:-19}` (default `19`):

| Servicio | Puerto host |
|---|---|
| Odoo HTTP | `localhost:19069` |
| Odoo longpolling | `localhost:19072` |
| pgweb (DB browser) | `localhost:19081` |
| MailHog (SMTP catch-all) | `localhost:19025` |
| WDB (debugger web) | `localhost:19984` |

Para usar `8069` exporta `PORT_PREFIX=8` en `.env` del proyecto
doodba (no del agente). El concat de strings da `8069`.

El `.env` del agente debe apuntar al puerto real:

```bash
ODOO_URL=http://localhost:19069
```

---

## 7. Bot user + API key

### Cambios de modelo en Odoo 19

Antes de escribir scripts contra `res.users` / `res.groups`:

| Lo que era | En Odoo 19 |
|---|---|
| `res.users.groups_id` | `res.users.group_ids` ✅ |
| `res.users.groups_id_full` | `res.users.all_group_ids` (incluye implied) |
| `res.groups.category_id` | ❌ eliminado |
| `res.groups.full_name` | ❌ eliminado, solo `name` |
| `_generate(scope, name)` | `_generate(scope, name, expiration_date)` ✅ obligatorio |

Los xmlids (`base.group_user`, `base.group_system`, etc.) **no han
cambiado**. En la UI los nombres se ven traducidos: "Role / User"
para `group_user`, "Rol / Administrador" para `group_system`.

### API keys: el cap de 90 días

`_check_expiration_date` impone:

```python
if not self.env.is_system():
    if not date:
        raise ValidationError("expiration_date obligatorio")
    max_duration = max(g.api_key_duration for g in self.env.user.all_group_ids) or 1
    if date > now() + timedelta(days=max_duration):
        raise ValidationError(f"No puede exceder {max_duration} días")
```

`group_user` define `api_key_duration=90` por defecto. Generar una
key como **el bot mismo** está limitado a 90 días. Generar como
admin (env.user system) bypassea el check pero la key acaba
asociada al admin (la SQL inserta `self.env.user.id`).

**Opciones**:

1. **INSERT directo en SQL** (dev/bootstrap, conveniente):

   ```python
   from odoo.addons.base.models.res_users import (
       KEY_CRYPT_CONTEXT, API_KEY_SIZE, INDEX_SIZE,
   )
   import binascii, os

   raw_key = binascii.hexlify(os.urandom(API_KEY_SIZE)).decode()
   env.cr.execute("""
       INSERT INTO res_users_apikeys
              (name, user_id, scope, expiration_date, key, index)
       VALUES (%s,   %s,      %s,    %s,              %s,  %s)
       RETURNING id
   """, [
       "agent-local",
       bot.id,
       "rpc",
       datetime.utcnow() + timedelta(days=365),  # naive UTC
       KEY_CRYPT_CONTEXT.hash(raw_key),
       raw_key[:INDEX_SIZE],
   ])
   secret = raw_key  # devolver al usuario
   ```

2. **Subir `api_key_duration` del grupo** (producción), p.ej. 365.
3. **Rotación cada 90d** vía cron y `_generate` estándar.

### Bot durante el bootstrap

El runbook recomienda permisos limitados (`group_user` +
`group_account_manager` + `group_multi_company`). Pero hasta que
los módulos `account` estén instalados, esos grupos no existen, y
para auditar `ir.module.module` (Bloque C) hace falta admin.

**Estrategia pragmática**: durante Bloque B y C el bot tiene
`base.group_system`. Tras Fase 4.4, tightenear a roles funcionales.

### Script de bootstrap del bot

`bootstrap-bot.py` (ejecutar con
`docker compose exec -T -e BOT_PW=... odoo odoo shell -d <db> --no-http`):

```python
import os, binascii
from datetime import datetime, timedelta
from odoo.addons.base.models.res_users import (
    KEY_CRYPT_CONTEXT, API_KEY_SIZE, INDEX_SIZE,
)

bot_login = "bot.contable@<tenant>.com"
bot_pw = os.environ["BOT_PW"]

bot = env["res.users"].search([("login", "=", bot_login)], limit=1)
if not bot:
    bot = env["res.users"].create({
        "name": "Bot Contable",
        "login": bot_login,
        "password": bot_pw,
        "group_ids": [(6, 0, [
            env.ref("base.group_user").id,
            env.ref("base.group_system").id,  # bootstrap-only
        ])],
    })

# API key vía SQL (bypass cap 90d)
raw_key = binascii.hexlify(os.urandom(API_KEY_SIZE)).decode()
env.cr.execute("""
    INSERT INTO res_users_apikeys (name, user_id, scope, expiration_date, key, index)
    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
""", [
    "agent-local",
    bot.id,
    "rpc",
    datetime.utcnow() + timedelta(days=365),
    KEY_CRYPT_CONTEXT.hash(raw_key),
    raw_key[:INDEX_SIZE],
])
print(f"BOT_API_KEY={raw_key}")
env.cr.commit()
```

Verificar la key vía JSON-RPC desde fuera del contenedor:

```bash
curl -s -X POST -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"service\":\"common\",\"method\":\"authenticate\",\"args\":[\"${SLUG}_dev\",\"$BOT_LOGIN\",\"$API_KEY\",{}]}}" \
  http://localhost:19069/jsonrpc | jq
# debe devolver {"result": <uid>, ...}
```

---

## 8. Resetear el password de admin

Por defecto `admin/admin`. Para evitarlo, en el mismo `bootstrap-bot.py`:

```python
admin = env.ref("base.user_admin")
admin.write({"password": os.environ["ADMIN_PW"]})
```

Y guardar `ADMIN_PW` en el `.SECRETS.txt`.

---

## 9. `.env` del agente y `/onboard`

### `.env` para Modo A

```bash
ODOO_AGENT_TENANT=<TENANT>

ODOO_URL=http://localhost:19069
ODOO_DB=<TENANT>_dev
ODOO_USER=bot.contable@<TENANT>.com
ODOO_API_KEY=<el secreto generado>

# IMPORTANTE: Odoo 19 cambió el contrato del JSON-2 RPC; el cliente
# del agente actual hace 422 en JSON-2. XML-RPC funciona sin cambios.
# Quitar cuando _json2 se arregle (TODO Bloque C).
ODOO_FORCE_XMLRPC=1

# Doodba en la misma máquina; SSH+docker exec se configura en Bloque C
DOODBA_SSH_HOST=localhost
DOODBA_PROJECT_DIR=/Users/<tu_user>/Documents/code/odoo-instances/<TENANT>-local
DOODBA_COMPOSE_SERVICE=odoo
DOODBA_DB_NAME=<TENANT>_dev
```

### Estado esperado de `/onboard` tras Modo A

| Check | Esperado | Por qué |
|---|---|---|
| 0. Profile | 🟢 | tenant + profile.yaml válidos |
| 1. Vars RPC | 🟢 | `.env` completo |
| 2. RPC reachable | 🟢 | XML-RPC contra `localhost:19069` |
| 3. API key | 🟢 | uid > 1 |
| 4. Bot ≠ admin | 🟢 | bot tiene su uid (admin = uid 2) |
| 5. Grupos del bot | 🟡 | falta `account.group_account_manager` (módulo no instalado todavía) |
| 6. Empresa activa | 🟡 | "My Company" sin VAT (se reasigna en Fase 4.2) |
| 7. Módulos | 🔴 | DB vacía: 0/N instalados, esperado |
| 8. SSH a doodba | 🟡 | `localhost:22` rechaza (Remote Login off en macOS) |
| 9. Tests skills | 🟢 | 242 tests offline |

Si llegas aquí con esta distribución, **agente conectado**. Los
amarillos/rojo se resuelven en Bloque C.

---

## 10. Flujo end-to-end resumido

Para un tenant nuevo, el flujo completo (10-15 min sin contar
gitaggregate ni docker build):

```bash
# Variables del despliegue
SLUG=<tenant>
INSTANCES_DIR=~/Documents/code/odoo-instances
PROJECT_DIR=$INSTANCES_DIR/$SLUG-local
SECRETS_FILE=$INSTANCES_DIR/$SLUG-local.SECRETS.txt
AGENT_REPO=~/Documents/code/odoo-agent

# 1. Prereqs (una vez por máquina) — ver §1
# 2. Generar passwords + secretos
mkdir -p "$INSTANCES_DIR"
ADMIN_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
DB_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
USER_ADMIN_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
BOT_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
cat > "$SECRETS_FILE" <<EOF
# $SLUG-local — $(date +%Y-%m-%d). NO COMMITEAR.
ODOO_ADMIN_MASTER_PASSWORD=$ADMIN_PW
POSTGRES_PASSWORD=$DB_PW
ODOO_ADMIN_USER_PASSWORD=$USER_ADMIN_PW
BOT_CONTABLE_PASSWORD=$BOT_PW
EOF
chmod 600 "$SECRETS_FILE"

# 3. Copier
cd "$INSTANCES_DIR"
copier copy --trust --defaults \
  --data project_name=$SLUG-local \
  --data odoo_version=19.0 --data odoo_proxy="" \
  --data odoo_initial_lang=es_ES \
  --data odoo_admin_password="$ADMIN_PW" \
  --data postgres_version=16 \
  --data postgres_dbname=${SLUG}_dev \
  --data postgres_password="$DB_PW" \
  --data compose_version=v2+ \
  gh:Tecnativa/doodba-copier-template $SLUG-local

# 4. Eliminar .empty (solo macOS) — §4
cd "$PROJECT_DIR"
rm -f odoo/custom/{entrypoint,build}.d/.empty

# 5. repos.yaml + addons.yaml — §3
# (copiar plantillas desde el tenant profile.yaml.oca_repos)
# Editar a mano o copiar de un tenant existente.

# 6. gitaggregate
cd odoo/custom/src
ODOO_VERSION=19.0 DEPTH_DEFAULT=1 DEPTH_MERGE=100 gitaggregate -c repos.yaml -e

# 7. Docker build + up
cd "$PROJECT_DIR"
docker compose build odoo
docker compose up -d
sleep 20
docker compose ps  # verificar que odoo, db, smtp están up

# 8. Crear DB vía CLI — §5
docker compose exec -T odoo odoo \
  --database=${SLUG}_dev --init=base \
  --stop-after-init --without-demo=all \
  --load-language=es_ES --no-http

# 9. Bot user + API key — §7
# Editar bootstrap-bot.py con bot_login del profile, y:
docker compose exec -T -e ADMIN_PW="$USER_ADMIN_PW" -e BOT_PW="$BOT_PW" \
  odoo odoo shell -d ${SLUG}_dev --no-http < /tmp/bootstrap-bot.py
# Anotar BOT_API_KEY del output → añadir a $SECRETS_FILE.

# 10. .env del agente — §9
cd "$AGENT_REPO"
cp .env.example .env
# Editar .env con los valores del bot y ODOO_FORCE_XMLRPC=1

# 11. Verificar conectividad
ODOO_AGENT_TENANT=$SLUG /onboard  # desde Claude Code
```

---

## Cuándo este documento queda obsoleto

Mantener actualizado mientras:

- El cliente del agente (`odoo_client.py`) tenga el bug de `_json2`.
  Cuando se arregle, eliminar la sección `ODOO_FORCE_XMLRPC=1` y la
  fila #9 de la tabla.
- Doodba use `.empty` en `entrypoint.d/build.d/`. Si Tecnativa los
  cambia a archivos con `.gitkeep` o similares, revisar §4.
- Odoo 19.x mantenga el cap de 90 días en `api_key_duration`. Si
  cambia (o se centraliza en ICP), actualizar §7.
- macOS Docker Desktop tenga el bug de `os.access(X_OK)` en bind
  mounts. Verificar contra Docker Desktop > 4.40 si es relevante.

Cuando un punto se quede obsoleto, **eliminar la sección completa**
(no dejar tachados ni "fixed in vX.Y" comments). El git log lleva
la historia.
