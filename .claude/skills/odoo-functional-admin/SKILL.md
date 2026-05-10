---
name: odoo-functional-admin
description: |
  Usa este skill SOLO para configuracion administrativa funcional de Odoo 19
  Community self-hosted (RPC / JSON-2 / MCP, sin SSH): crear y mantener
  usuarios (`res.users`), grupos (`res.groups`), ACLs (`ir.model.access`)
  y reglas de registro (`ir.rule`); montar la estructura multi-empresa
  (`res.company` con padre/hijo, branches, holding "Ikigai Magi" + filiales
  Camomilla Blu, Kura Terra, Omotenashi Hama); asignar `company_ids` a
  usuarios; crear diarios (`account.journal`) con secuencias (`ir.sequence`)
  prefijadas por anyo; configurar posiciones fiscales
  (`account.fiscal.position`) intra-UE / Recargo de Equivalencia /
  exportacion / IVA Caja; ajustar parametros de sistema
  (`res.config.settings`, `ir.config_parameter`); habilitar idiomas
  (es_ES, ca_ES, it_IT, en_US) y monedas; gestionar acciones programadas
  (`ir.cron`). Activa este skill aunque el usuario solo diga "crea un
  usuario", "permisos", "que el comercial solo vea sus clientes",
  "regla de registro", "nueva empresa", "branch", "diario nuevo",
  "secuencia con prefijo de anyo", "posicion fiscal intracomunitaria",
  "activa multi-company", "create user", "record rule", "sequence prefix",
  "fiscal position", "ir.cron", "scheduled action".

  DO NOT trigger for (handoff to sibling skills):
    - Crear/postear facturas, registrar pagos, conciliar extractos,
      enviar SII / Veri*Factu, ejecutar modelos AEAT, cierres periodicos
      -> use skill `odoo-accounting-es`.
    - Instalar / actualizar / desinstalar modulos, gestionar
      `addons.yaml` o `repos.yaml`, ejecutar `gitaggregate`,
      reiniciar el contenedor Odoo, `odoo-bin -i/-u`, dependencias pip
      -> use skill `odoo-module-admin`.

  No usar para tareas no-Odoo (frontend, devops generico, traducciones
  sueltas, sysadmin Linux, PostgreSQL backups).
license: MIT
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash(python3:*)
  - Bash(uv:*)
  - WebFetch
  - mcp__odoo__*
metadata:
  version: "0.1.0"
  target_odoo_version: "19.0"
---

# Skill: Odoo 19 Community + administracion funcional (ES/CA)

Este skill convierte a Claude en administrador funcional de una instancia
self-hosted de Odoo 19 Community. Su alcance es **configuracion** (usuarios,
grupos, permisos, multi-company, diarios, secuencias, posiciones fiscales,
ir.cron, parametros), no operativa contable ni administracion de modulos.

Asume modulos `base`, `mail`, `account`, `l10n_es` ya instalados. Si el
usuario pide instalar un modulo, deriva al skill `odoo-module-admin`.

## Contexto multi-empresa por defecto

El despliegue tipico cubierto por este skill es:

- Holding **Ikigai Magi S.L.** (matriz, Espana, EUR).
- Filial **Camomilla Blu S.L.** (Espana, EUR).
- Filial **Kura Terra S.L.** (Espana, EUR).
- Participada **Omotenashi Hama** (puede ser persona fisica/autonomo).

Las tres primeras suelen ser `res.company` separadas con `parent_id` para
reflejar la jerarquia. La participada puede ser `res.company` separada o
quedar fuera de la consolidacion segun decision del usuario. Ver
`references/multi-company.md`.

## Variables de entorno requeridas

| Variable | Proposito |
|----------|-----------|
| `ODOO_URL` | URL base, p.ej. `https://odoo.miempresa.cat` |
| `ODOO_DB` | Nombre de la base, p.ej. `miempresa_prod` |
| `ODOO_USER` | Login del bot (necesario para fallback XML-RPC) |
| `ODOO_API_KEY` | API key generada en *Mi perfil > Seguridad > API Keys* |
| `ODOO_FORCE_XMLRPC` | (Opcional) `1` para forzar XML-RPC |

Si falta cualquiera, **detente y pidela al usuario antes de ejecutar nada**.

## Tabla de despacho: peticion -> script -> reference

| El usuario pide... | Ejecuta | Antes lee |
|--------------------|---------|-----------|
| **Multi-empresa** | | |
| Crear empresa filial / branch | `scripts/company_setup.py --name X --vat Y --parent ID` | `references/multi-company.md` |
| **Bootstrap completo** de una filial (company + chart + diarios + FPs) | `scripts/subsidiary_bootstrap.py --name X --vat Y --parent-vat Z` | `references/multi-company.md`, `references/journals-sequences.md`, `references/fiscal-config.md` |
| Snapshot del arbol de empresas | `scripts/audit_admin_state.py --section companies` | `references/multi-company.md` |
| Configurar consolidacion intercompany | `scripts/intercompany_setup.py --src N --dst M` | `references/multi-company.md` |
| **Usuarios y grupos** | | |
| Crear usuario interno | `scripts/user_provision.py --login ... --groups XMLID,XMLID` | `references/users-groups-acls.md` |
| Anyadir / quitar grupo a usuario | `scripts/group_assign.py --user N --add XMLID --remove XMLID` | `references/users-groups-acls.md` |
| Crear API key para un usuario | `scripts/apikey_provision.py --login X --label Y` | `references/users-groups-acls.md` |
| Auditar permisos de un modelo | `scripts/access_rule_audit.py --model res.partner` | `references/users-groups-acls.md` |
| Crear regla de registro | `scripts/record_rule_create.py --name X --model M --groups GS --domain D` | `references/users-groups-acls.md` |
| **Diarios y secuencias** | | |
| Crear diario contable de setup | `scripts/journal_setup.py --type sale --code VENT --company N` | `references/journals-sequences.md` |
| Crear secuencia con prefijo de anyo | `scripts/sequence_setup.py --code account.move.kt --prefix 'KT/%(range_year)s/'` | `references/journals-sequences.md` |
| **Fiscal** | | |
| Crear posicion fiscal intra-UE | `scripts/fiscal_position_setup.py --preset intra_eu --company N` | `references/fiscal-config.md` |
| Crear posicion fiscal Recargo Equivalencia | `scripts/fiscal_position_setup.py --preset rec_eq --company N` | `references/fiscal-config.md` |
| **Idioma y parametros** | | |
| Activar idiomas (ES, CA, IT, EN) | `scripts/language_install.py --langs es_ES,ca_ES --activate` | `references/scheduled-actions.md` |
| Get/set parametro de sistema | `scripts/settings_param.py get\|set\|delete\|list <key> [value]` | `references/users-groups-acls.md` |
| **Acciones programadas** | | |
| Listar / pausar / reanudar `ir.cron` | `scripts/cron_manage.py list\|pause\|resume\|run --id N` | `references/scheduled-actions.md` |
| Ejecutar un cron ya | `scripts/cron_manage.py run --id N` | `references/scheduled-actions.md` |
| **Idempotencia / data load** | | |
| Upsert por `ir.model.data` ext-ID | `scripts/ext_id_upsert.py --xmlid module.name --model M --vals JSON` | `references/data-import-export.md` |
| **Auditoria** | | |
| Snapshot global (companies, users, journals, crons) | `scripts/audit_admin_state.py` | `references/users-groups-acls.md` |

## Reglas de seguridad que debes cumplir SIEMPRE

1. **Nunca toques `admin` (uid 1) sin confirmacion explicita.** Modificar
   sus grupos o desactivarlo deja la base sin acceso administrativo
   recuperable solo via shell de PostgreSQL.
2. **Multi-company**: al crear cualquier registro con `company_id`,
   pasalo explicitamente. No dependas del `company_id` por defecto del
   bot. Si el modelo tiene `_check_company_auto=True`, una incoherencia
   bloqueara el `create()`.
3. **Reglas de registro globales** (sin `groups`, no by-passable) sobre
   `res.partner`, `res.users`, `res.company`, `account.move`: **detente y
   pide confirmacion** explicita con un resumen del impacto antes de
   crearlas. Una regla mal escrita puede ocultar registros a *todos* los
   usuarios.
4. **Secuencias de facturacion espanola** (`account.move` tipo
   `out_invoice` / `out_refund`): deben usar `implementation='no_gap'`.
   La numeracion con saltos es ilegal en Espana para facturas emitidas.
5. **Padre/hijo de empresas**: una `res.company` que ya es `parent_id`
   de otra **no** puede convertirse despues en branch / hija. La
   decision es semi-irreversible. Confirma antes.
6. **Operaciones masivas**: cualquier write/unlink que afecte a >5
   registros en `res.users`, `res.company`, `account.journal`,
   `ir.rule`, `ir.cron`: detente y pide confirmacion mostrando un
   diff/resumen.
7. **Idempotencia**: cuando el usuario diga "configura X", asume que
   puede haberse hecho antes. Usa `scripts/ext_id_upsert.py` o
   `search_read` previo en lugar de `create()` ciego.

## Workflow: crear un usuario interno (canonico)

1. Pide al usuario (si no lo dio): nombre, login (email), idioma
   (`es_ES` / `ca_ES` / `it_IT` / `en_US`), zona horaria, **company_id
   por defecto**, **company_ids permitidas**, rol (administrador /
   contabilidad / ventas / portal).
2. Mapea rol a XML-IDs de grupo: ver `references/users-groups-acls.md`.
3. Comprueba con `scripts/user_provision.py --dry-run --login X` si ya
   existe; si si, propone update en lugar de crear.
4. Ejecuta `scripts/user_provision.py` con `--groups <XMLID>,<XMLID>`.
5. Devuelve resumen: `id`, `login`, grupos resueltos a nombres legibles,
   companies, idioma. Sugiere ejecutar `action_reset_password` para que
   el usuario reciba la invitacion por email.

## Workflow: dar de alta una filial nueva (canonico)

1. Decide branch vs company: si comparte plan contable, pais y CIF con
   la matriz -> **branch**. Si tiene CIF distinto y libros separados ->
   **company** independiente con `parent_id`. Ver
   `references/multi-company.md` para el arbol de decision.
2. **Detente y confirma** la decision con el usuario; recuerda que es
   semi-irreversible.
3. Ejecuta `scripts/company_setup.py --name "Kura Terra S.L." --vat
   ESB99999999 --parent <ikigai_id>`.
4. El script crea la company, copia el chart_template `l10n_es` si
   procede, y crea los diarios estandar VENT/COMP/BANC/CAJA via
   `scripts/journal_setup.py`.
5. Anyade la company a `admin.company_ids` para que el humano la vea.

## Skills hermanos (handoff)

| Si el usuario pide... | Usa el skill |
|-----------------------|--------------|
| Crear/postear facturas, conciliar, modelos AEAT | `odoo-accounting-es` |
| Enviar SII / Veri*Factu / FacturaE | `odoo-accounting-es` |
| Cierres periodicos, P&L, balance, libro mayor | `odoo-accounting-es` |
| Instalar/actualizar/desinstalar modulos | `odoo-module-admin` |
| `addons.yaml`, `repos.yaml`, gitaggregate, doodba | `odoo-module-admin` |
| Reiniciar contenedor Odoo, `odoo-bin -i/-u` | `odoo-module-admin` |

Cuando el usuario pide configurar un diario y *acto seguido* postear una
factura en el, **divide en dos pasos**: este skill crea el diario; el
skill `odoo-accounting-es` postea la factura.

## Punteros a las references

- `references/multi-company.md` - `res.company`, branches, holding
  Ikigai, allowed_company_ids, `_check_company_auto`, reglas globales.
- `references/users-groups-acls.md` - `res.users`, `res.groups` (Many2many
  syntax `(0,0,{}) (4,id) (3,id) (6,0,[ids])`), `ir.model.access` CSV,
  `ir.rule` con dominio, XML-IDs frecuentes.
- `references/journals-sequences.md` - `account.journal`, `ir.sequence`,
  tokens `%(range_year)s`, `no_gap` legal, `restrict_mode_hash_table`.
- `references/fiscal-config.md` - posiciones fiscales con `auto_apply`,
  mapeos de impuestos y cuentas, presets ES (interior, intra-UE,
  exportacion, RecEqv, IVA Caja).
- `references/scheduled-actions.md` - `ir.cron` config, intervals,
  `method_direct_trigger`, debug.
- `references/data-import-export.md` - `ir.model.data` ext-IDs,
  upsert idempotente, `base_import.import` via JSON-2.
- `references/domain-syntax.md` - dominios Odoo, operadores, `read_group`.
- `references/mcp-setup.md` - configuracion del MCP server `odoo` para
  lectura conversacional desde Claude Desktop.

## Calidad y tests

```bash
cd .claude/skills/odoo-functional-admin
python3 -m pytest tests/ -v
```

Cubre helpers puros (validacion VAT, regex de XML-ID, deteccion de
ciclos de `parent_id`, normalizacion de login). No requiere conexion
Odoo (los modulos importan `requests` solo cuando hay RPC real).

## Evals

`evals/evals.json` lista prompts should-trigger / should-not-trigger /
handoff. Ver tras editar la `description:` de este skill o de los
skills hermanos.
