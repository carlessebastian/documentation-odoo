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
2. Auditar scripts de `odoo-functional-admin` por usos de
   `groups_id`, `category_id`, `full_name` (renombrados o eliminados
   en Odoo 19).
3. Configurar la company "Inteligencia del negocio pr3mium S.L." y
   reasignar al bot (Fase 4.2-4.3).

## Fase 4.1 — Instalación de módulos OCA (2026-05-11)

12/12 `expected_modules` instalados (`state=installed`); 75 módulos
totales en DB tras cerrar closure de dependencias; 0 módulos colgados.

### Camino largo (todo en memoria
`project_odoo19_doodba_gotchas.md` para futuros tenants):

1. **Auditoría OCA del estado real en 19.0** vía `oca-module-scout`
   (6 scouts paralelos). Solo `l10n_es_facturae` (19.0.1.0.0)
   estaba disponible de los 6 inicialmente "missing". `sii_oca`
   eliminado (no aplica al tamaño de inpr3mium); `mod232`,
   `verifactu_oca` (obligatorio 2027), `mis_builder`,
   `sepa_credit_transfer`, `sepa_direct_debit` → `deferred_modules`.
2. **Descubrir 3 repos OCA faltantes** al cerrar closure de
   `__manifest__.depends`:
   - `OCA/reporting-engine` → `report_xlsx`, `report_xml`,
     `report_qweb_parameter`.
   - `OCA/server-ux` → `date_range` (movido desde server-tools v15+).
   - `OCA/community-data-files` → `base_iso3166`, `base_bank_from_iban`.
3. **Listar 9 módulos extra en `addons.yaml`** (transitivas que
   `addons init` no symlinkea automáticamente): `l10n_es_aeat`,
   `l10n_es_partner`, `account_tax_balance`, los 6 de los 3 repos
   nuevos.
4. **5 pip pkgs añadidos a `pip.txt`** auditando
   `external_dependencies` de TODO el closure (no solo los 12
   explícitos):
   - `pycountry` (`l10n_es_facturae`, `base_iso3166`)
   - `xmlsig` (`l10n_es_facturae` — firma XML)
   - `xlsxwriter`, `xlrd` (`report_xlsx`)
   - `schwifty==2024.4.0` (`base_bank_from_iban`)
5. **Workaround `PGDATABASE=devel`**: `invoke install` apunta al
   DB hardcoded en devel.yaml. Usar
   `docker compose run --rm -e PGDATABASE=inpr3mium_dev odoo
   odoo --stop-after-init -d inpr3mium_dev -i <CSV>`.
6. **`chown` del filestore**: `docker compose exec` corre como
   uid=1000 (odoo image), pero `run --rm` mapea a uid=501 (host).
   Filestore creado en bootstrap quedó uid=1000; install via
   `run --rm` fallaba con `PermissionError`. Fix:
   `docker compose exec -T -u root odoo chown -R 501:20
   /var/lib/odoo/filestore/inpr3mium_dev`.
7. **`invoke img-build`** tras tocar `pip.txt` para que la imagen
   incluya los nuevos pip pkgs (afecta solo a `run --rm`; el
   container running tenía `pip install --user` aplicado).

### Estado al cierre

- `expected_modules` reducido a 12 efectivos. 5 en `deferred_modules`
  con `revisit_on`.
- `oca_repos` ahora 11 (los 8 originales + 3 nuevos).
- `addons.yaml` con 21 módulos OCA listados (closure completo).
- `pip.txt` doodba con 7 entradas (3 originales + 5 nuevos).
- DB `inpr3mium_dev`: 75 módulos installed, ready para Fase 4.2.

## Fase 4.2 — Empresa + idiomas + chart template (2026-05-11)

- ✅ Idiomas: `es_ES` (preinstalado) + `ca_ES` activados via
  `language_install.py --langs es_ES,ca_ES --activate`.
- ✅ Moneda `EUR` activada (estaba inactiva).
- ✅ Chart template `es_pymes` cargado vía `odoo shell` (workaround
  por bug XML-RPC en `try_loading` con segundo arg posicional —
  ver gotchas memory). Resultado: 51 cuentas `generic_coa` borradas
  y reemplazadas con 646 cuentas PGCE Pymes.
- ✅ `res.company id=1` reescrita:
  - `name`: "Inteligencia del negocio pr3mium S.L."
  - `vat`: "ESB65758682"
  - `country_id`: Spain, `state_id`: Barcelona
  - `street/city/zip`: Carrer Coneixement 7 / Gava / 08850
  - `email`/`phone`/`website`: facturas@inpr3mium.com / +34902811511 /
    https://inpr3mium.com
- ✅ Bot user (uid=8): tz Europe/Madrid + grupos extendidos con
  `account.group_account_manager` (Administrator de account) y
  `base.group_partner_manager` (Creation de partners). Conserva
  `base.group_system` para Fase 4.3 (tightening de ACL pendiente
  para Fase 4.4).
- ✅ `web.base.url.freeze = True` para evitar que el login
  sobreescriba la URL base.

### Gotchas descubiertos

- **`chart_template` en Odoo 19**: el formato corto (`es_pymes`),
  no XML-ID (`l10n_es.l10n_es_pymes`). El profile estaba con el
  formato antiguo y se corrigió.
- **`try_loading` via XML-RPC**: el segundo argumento posicional
  (`company`) se pierde en el dispatcher, dando `TypeError: missing
  'company'`. Workaround: ejecutar via `odoo shell` dentro del
  contenedor.

### Próximo paso

Fase 4.2.1 — skill `odoo-data-migration` (MVP solo-lectura) para
hacer dump de Holded antes de Fase 4.3 (diarios + secuencias).
