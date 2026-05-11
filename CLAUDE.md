# odoo-agent — contexto para Claude

> **🔖 Al inicio de cada sesión, lee primero
> [`docs/PLAN.md`](docs/PLAN.md)** — es el single source of truth del
> estado del desarrollo. Indica la última fase completada, el próximo
> paso, y permite retomar sesiones interrumpidas sin perder
> contexto. Tras completar cualquier paso del roadmap, actualízalo
> (regla en memoria).

Este repo **no es la documentación de Odoo**. Es un agente Claude Code
que asiste al usuario en la instalación, migración, administración y
explotación contable/fiscal de instancias self-hosted **Odoo 19
Community**, desplegadas con doodba (Tecnativa). Foco en localización
española (ES/CA, ámbito Cataluña/UE).

El agente es **multi-tenant**: cada despliegue (cliente / holding /
sociedad) vive como un perfil bajo `docs/tenants/<slug>/`. La sesión
activa se selecciona con la env var `ODOO_AGENT_TENANT`. Tenant activo
en este momento: **`inpr3mium`** (Inteligencia del Negocio Pr3mium S.L.,
sociedad única, migra desde Holded). Tenants futuros previstos:
`fedefarma` (migra desde Axional). Lee
`docs/tenants/$ODOO_AGENT_TENANT/profile.yaml` al inicio de cada
sesión para conocer la sociedad activa antes de operar.

La documentación oficial de Odoo está vendorizada en `vendor/odoo-docs/`
como **material de referencia de solo lectura**. Cuando necesites
entender una feature funcional o un módulo del core (cómo funciona
`account.move`, qué hace `l10n_es_edi_*`, flujos de WMS, etc.), busca
ahí con `Grep` o `Read`.

## Estructura del repo

```
odoo-agent/
├── CLAUDE.md                     # este archivo
├── README.md                     # presentación pública del agente
├── .env.example                  # plantilla de configuración local
├── .claude/                      # capacidades del agente
│   ├── skills/                   # skills de dominio (ver abajo)
│   ├── agents/                   # subagentes (oca-module-scout, ...)
│   └── commands/                 # slash-commands (/onboard, /cierre-mensual, ...)
├── docs/                         # notas propias del proyecto
│   ├── onboarding.md             # primer arranque del agente
│   ├── infra/                    # provisión doodba, host, secrets
│   └── tenants/                  # un perfil por despliegue
│       ├── _template/            # plantilla para crear nuevos tenants
│       └── inpr3mium/            # tenant activo
└── vendor/
    └── odoo-docs/                # documentación oficial de Odoo (upstream, read-only)
```

## Capacidades del agente

Cuatro skills cooperativas: tres operan sobre la instancia Odoo
self-hosted; la cuarta (`holded-export`) es un exportador **read-only**
sobre un origen externo (Holded SaaS) usado como input para la
migración a Odoo. Cada una con triggers explícitos y handoffs a las
otras. **Detalle completo, runbook de bootstrap y políticas
compartidas en `.claude/skills/CLAUDE.md`** — cárgalo cuando vayas a
trabajar con cualquiera de los cuatro dominios.

| Skill | Dominio | Privilegios |
|-------|---------|-------------|
| `odoo-accounting-es` | Operativa contable y fiscal ES diaria: facturas, pagos, conciliación, IVA/IRPF/RE, SII/Veri\*Factu/FacturaE, modelos AEAT 303/347/349/390/111/115/130/369/232/720, cierres, reporting | RPC + MCP |
| `odoo-functional-admin` | Configuración funcional vía RPC: usuarios, grupos, ACLs, record rules, multi-company, diarios, secuencias, posiciones fiscales, idiomas, `ir.cron`, parámetros | RPC + MCP |
| `odoo-module-admin` | Ciclo de vida de módulos: install/upgrade/uninstall, `addons.yaml`, `repos.yaml`, `gitaggregate`, doodba, OpenUpgrade, reinicios | RPC + **SSH + Docker** |
| `holded-export` | **Read-only** export desde Holded SaaS (API REST con header `key:`): contactos, productos, documentos, asientos, PDFs originales escaneados. Dump JSONL + PDFs + manifest en `docs/tenants/<slug>/holded-export/<YYYY-MM-DD>/`. Insumo para Fase 5 (migración) | HTTP GET only |

Subagentes:

- `oca-module-scout` — busca módulos OCA compatibles con 19.0 ante
  preguntas tipo "¿hay un módulo OCA para X?". Úsalo en lugar de hacer
  `WebFetch` inline.

Slash-commands:

- `/onboard` — verifica que el agente puede operar contra el Odoo
  configurado en `.env` (ping RPC, validar API key, listar módulos,
  validar permisos del bot, comprobar SSH a doodba).
- `/cierre-mensual <YYYY-MM> [--company N]` — orquesta el cierre mensual
  ES con checkpoints entre fases.

## Variables de entorno

Compartidas por las tres skills (plantilla completa en `.env.example`):

| Variable | Uso |
|----------|-----|
| `ODOO_AGENT_TENANT` | slug del tenant activo (subdir de `docs/tenants/`) |
| `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` | autenticación RPC/JSON-2 |
| `ODOO_FORCE_XMLRPC` | fallback opcional a XML-RPC |
| `DOODBA_SSH_HOST`, `DOODBA_PROJECT_DIR`, `DOODBA_COMPOSE_SERVICE`, `DOODBA_DB_NAME` | solo `odoo-module-admin` |
| `OPENUPGRADE_PATH` | solo migraciones con OpenUpgrade |
| `HOLDED_API_KEY` | solo `holded-export` |

Mantén las claves en un `.env` local; nunca las commitees.

## Política de routing entre skills

Las descripciones de cada skill incluyen cláusulas
`DO NOT trigger for ... -> use skill X`. Respétalas: si el usuario pide
"crea un usuario y haz su primera factura", esto es **dos skills**
(`odoo-functional-admin` para el usuario, `odoo-accounting-es` para la
factura), no una. Para tareas mixtas como "instala l10n_es_aeat_mod303
y configura los permisos", el módulo lo instala `odoo-module-admin` y
los grupos los asigna `odoo-functional-admin`.

## Infraestructura compartida entre skills

`scripts/_common.py`, `scripts/odoo_client.py`, `tests/conftest.py`,
`tests/test_common.py`, `tests/test_odoo_client_helpers.py` están
**duplicados verbatim** en las tres skills Odoo (es intencional: las
skills son bundles portables). Cuando arregles uno de estos archivos,
sincroniza los otros dos (instrucciones en `.claude/skills/CLAUDE.md`).

`holded-export` solo duplica `_common.py` + `conftest.py` +
`test_common.py` — no toca Odoo, no necesita `odoo_client.py`.

## Tests

```bash
for skill in odoo-accounting-es odoo-functional-admin odoo-module-admin holded-export; do
  echo "=== $skill ==="
  (cd .claude/skills/$skill && python3 -m pytest tests/ -q)
done
```

## Documentación upstream de Odoo (`vendor/odoo-docs/`)

Es el fork de `odoo/documentation` rama `19.0` desde el que partió este
proyecto. Se conserva tal cual:

- Para construir HTML local de un subset (rara vez necesario):
  `cd vendor/odoo-docs && pip install -r requirements.txt && make fast`.
- Licencia upstream: **CC-BY-NC-SA 4.0** (`vendor/odoo-docs/LICENSE`).
  Se aplica solo a esos contenidos; las skills y código del agente en
  `.claude/` declaran su propia licencia (`MIT` en cada `SKILL.md`).
- No editar contenido upstream sin un motivo claro: si se actualiza,
  conviene poder hacer rebase desde `odoo/documentation` 19.0 sin
  conflictos.
