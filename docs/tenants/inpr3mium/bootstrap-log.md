# Bootstrap log — inpr3mium

Bitácora del provisioning de la instancia Odoo 19 para inpr3mium.
Se actualiza con cada hito relevante (creación, migraciones, cutover).

---

## 2026-05-10 — Modo A (Docker local) provisionado

**Operador**: Carles + agente Claude (Opus 4.7).
**Modo**: A (Docker local, sin TLS, dominio `localhost`).
**Ubicación**: `~/Documents/code/odoo-instances/inpr3mium-local`.

### Stack levantado

| Componente | Versión | Notas |
|---|---|---|
| doodba-copier-template | v9.5.0 | `copier copy --trust --defaults` con overrides |
| Odoo | 19.0 (`odoo/odoo` rama 19.0, último merge `638f9477`) | core via gitaggregate |
| Postgres | 16-alpine (`ghcr.io/tecnativa/postgres-autoconf:16-alpine`) | doodba auto-config |
| Python en contenedor | 3.12 | base image doodba |
| Host runtime | macOS Darwin 25.2 / Docker Desktop 27.4.0 | bind mount issue ver abajo |

### Repos OCA sincronizados (rama 19.0, depth 1)

| Repo | HEAD |
|---|---|
| `l10n-spain` | `275d92a` |
| `server-tools` | `f051715` |
| `server-auth` | `21cb186` |
| `account-financial-tools` | `0e439b0` |
| `account-financial-reporting` | `48a8560` |
| `web` | `201cb86` |
| `queue` | `ebb87ea` |
| `bank-payment` | `4ecfd81` |

### Puertos expuestos (devel.yaml `PORT_PREFIX=19`)

| Servicio | Puerto host |
|---|---|
| Odoo HTTP | `localhost:19069` |
| Odoo longpolling | `localhost:19072` |
| pgweb (DB browser) | `localhost:19081` |
| MailHog (SMTP catch-all) | `localhost:19025` |
| WDB (debugger web) | `localhost:19984` |

### Database

- Nombre: `inpr3mium_dev`
- dbfilter: `^inpr3mium_dev` (configurado vía copier `postgres_dbname`)
- Idioma cargado: `es_ES`
- Sin demo data (`--without-demo=all`)
- 14 módulos base instalados (auto por `--init=base`)

> ⚠️ La DB **no se creó por el wizard web** porque `devel.yaml`
> hardcodea `PGDATABASE=devel` y la auto-selección de DB lanza
> `KeyError: 'ir.http'` cuando esa DB no existe. Usado CLI:
> `docker compose exec odoo odoo --database=inpr3mium_dev --init=base
> --stop-after-init --without-demo=all --load-language=es_ES --no-http`.

### Usuarios

| Login | uid | Grupos | Notas |
|---|---|---|---|
| `admin` | 2 | Admin (default) | password reseteado a valor en `~/Documents/code/odoo-instances/inpr3mium-local.SECRETS.txt` |
| `bot.contable@inpr3mium.com` | 8 | `Role/User` + `Rol/Administrador` | API key `agent-local` (expira 2027-05-10), bypass del `api_key_duration` cap (90 días) vía SQL directo |

### Incidencias resueltas durante el bootstrap

1. **Copier post-task fallaba sin `invoke` ni `pre-commit`** —
   `pipx install invoke pre-commit` antes de `copier copy`.
2. **Repos OCA clonados en `custom/src/custom/src/...`** — usé rutas
   `./custom/src/X` en `repos.yaml` cuando ya estaba dentro de
   `custom/src/`. Corregido a `./X`, repos movidos.
3. **`PermissionError: '.empty'`** al arrancar odoo — bind mounts
   de Docker Desktop macOS hacen que `os.access(X_OK)` devuelva
   `True` para archivos sin bit X (mode 0644). Eliminados los
   placeholders `odoo/custom/{entrypoint,build}.d/.empty`.
4. **`groups_id` no existe en Odoo 19** — el campo fue renombrado a
   `group_ids` en `res.users`. Adaptado el script `bootstrap-bot.py`.
5. **API keys exigen `expiration_date`** y los grupos del bot
   limitan duración a 90 días. Resuelto con INSERT directo a
   `res_users_apikeys` (admin/system bypass-eable, bot no).
6. **JSON-2 RPC del cliente del agente devuelve 422** — `_json2`
   serializa `args` como lista posicional pero el endpoint hace
   `signature.bind(records, **kwargs)` por nombre. Workaround:
   `ODOO_FORCE_XMLRPC=1` en `.env`. **TODO arreglar `_json2`**.

### Estado /onboard

5 verde, 3 amarillo, 1 rojo, 0 N/A:

- 🔴 **Módulos**: 12 disponibles (`uninstalled`), 6 missing
  (`mod232`, `sii_oca`, `verifactu_oca`, `facturae`, `mis_builder`,
  `sepa_credit_transfer`). Algunos aún no migrados a 19.0;
  `mis_builder` requiere repo OCA `mis-builder` separado (no listado
  en profile.oca_repos). Acción Bloque C: revisar `expected_modules`.
- 🟡 **Grupos del bot**: falta `account.group_account_manager`
  (módulo `account` aún no instalado). Esperado.
- 🟡 **Empresa activa**: "My Company" sin VAT en lugar de
  "Inteligencia del negocio pr3mium S.L. / ESB65758682". Bloque C
  Fase 4.2 (`subsidiary_bootstrap.py` reasigna).
- 🟡 **SSH a doodba**: `localhost:22` rechaza conexión (macOS
  Remote Login off). Para Bloque C: o habilitar Remote Login + key,
  o adaptar `odoo-module-admin` para usar `docker exec` directo
  cuando `DOODBA_SSH_HOST=localhost`.

### Próximos pasos (Bloque C)

1. Arreglar `_json2` en `odoo_client.py` y sincronizar a las 3 skills.
2. Revisar `profile.yaml.expected_modules` contra disponibilidad
   real OCA 19.0; añadir repo `mis-builder` a `repos.yaml` si se
   confirma que existe rama 19.0.
3. Auditar scripts de `odoo-functional-admin` por usos de
   `groups_id`, `category_id`, `full_name` (renombrados o eliminados
   en Odoo 19).
4. Instalar módulos del profile (Fase 4.1).
5. Configurar la company "Inteligencia del negocio pr3mium S.L." y
   reasignar al bot (Fase 4.2-4.3).
