# odoo-agent — contexto para Claude

Este repo **no es la documentación de Odoo**. Es un agente Claude Code
que asiste al usuario en la instalación, migración, administración y
explotación contable/fiscal de su instancia self-hosted **Odoo 19
Community**, desplegada con doodba (Tecnativa) y orientada a la holding
**Ikigai Magi S.L.** y sus filiales (**Camomilla Blu**, **Kura Terra**,
**Omotenashi Hama**), locale ES/CA, ámbito Cataluña/UE.

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
├── .claude/                      # capacidades del agente
│   ├── skills/                   # skills de dominio (ver abajo)
│   ├── agents/                   # subagentes (oca-module-scout, ...)
│   └── commands/                 # slash-commands (/cierre-mensual, ...)
├── docs/                         # notas propias del proyecto (infra, ikigai, migración)
└── vendor/
    └── odoo-docs/                # documentación oficial de Odoo (upstream, read-only)
```

## Capacidades del agente

Tres skills cooperativas, cada una con triggers explícitos y handoffs a
las otras dos. **Detalle completo, runbook de bootstrap y políticas
compartidas en `.claude/skills/CLAUDE.md`** — cárgalo cuando vayas a
trabajar con cualquiera de los tres dominios.

| Skill | Dominio | Privilegios |
|-------|---------|-------------|
| `odoo-accounting-es` | Operativa contable y fiscal ES diaria: facturas, pagos, conciliación, IVA/IRPF/RE, SII/Veri\*Factu/FacturaE, modelos AEAT 303/347/349/390/111/115/130/369/232/720, cierres, reporting | RPC + MCP |
| `odoo-functional-admin` | Configuración funcional vía RPC: usuarios, grupos, ACLs, record rules, multi-company, diarios, secuencias, posiciones fiscales, idiomas, `ir.cron`, parámetros | RPC + MCP |
| `odoo-module-admin` | Ciclo de vida de módulos: install/upgrade/uninstall, `addons.yaml`, `repos.yaml`, `gitaggregate`, doodba, OpenUpgrade, reinicios | RPC + **SSH + Docker** |

Subagentes:

- `oca-module-scout` — busca módulos OCA compatibles con 19.0 ante
  preguntas tipo "¿hay un módulo OCA para X?". Úsalo en lugar de hacer
  `WebFetch` inline.

Slash-commands:

- `/cierre-mensual <YYYY-MM> [--company N]` — orquesta el cierre mensual
  ES con checkpoints entre fases.

## Variables de entorno

Compartidas por las tres skills (ver tabla completa en
`.claude/skills/CLAUDE.md`):

| Variable | Uso |
|----------|-----|
| `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` | autenticación RPC/JSON-2 |
| `ODOO_FORCE_XMLRPC` | fallback opcional a XML-RPC |
| `DOODBA_SSH_HOST`, `DOODBA_PROJECT_DIR`, `DOODBA_COMPOSE_SERVICE`, `DOODBA_DB_NAME` | solo `odoo-module-admin` |
| `OPENUPGRADE_PATH` | solo migraciones con OpenUpgrade |

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
**duplicados verbatim** en las tres skills (es intencional: las skills
son bundles portables). Cuando arregles uno de estos archivos, sincroniza
los otros dos (instrucciones en `.claude/skills/CLAUDE.md`).

## Tests

```bash
for skill in odoo-accounting-es odoo-functional-admin odoo-module-admin; do
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
