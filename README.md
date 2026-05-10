# odoo-agent

Agente [Claude Code](https://claude.com/claude-code) para administrar
instancias self-hosted de **Odoo 19 Community** desplegadas con
[doodba](https://github.com/Tecnativa/doodba-copier-template) (Tecnativa)
sobre Docker. Foco en localización española (ES/CA, ámbito
Cataluña/UE).

El agente es **multi-tenant**: cada despliegue (cliente, holding o
sociedad individual) tiene su perfil bajo `docs/tenants/<slug>/`, y la
sesión activa se selecciona con la env var `ODOO_AGENT_TENANT`. Esto
permite reusar el mismo agente para distintas empresas sin tocar el
código de las skills.

El proyecto nació como fork de `odoo/documentation` (rama 19.0) y ha
evolucionado: la documentación oficial de Odoo se conserva como
referencia vendorizada en `vendor/odoo-docs/`, y la raíz del repo está
ahora dedicada al agente.

## Qué hace

El agente acompaña en cuatro frentes:

1. **Instalación y bootstrap** de la instancia (módulos del core, OCA,
   localización española, multi-empresa).
2. **Migración** del sistema actual a Odoo 19 (vía OpenUpgrade en
   staging, con cutover manual).
3. **Administración funcional**: usuarios, grupos, ACLs, record rules,
   multi-company, diarios, secuencias, posiciones fiscales,
   acciones programadas.
4. **Operativa contable y fiscal española diaria**: facturación, pagos,
   conciliación, IVA/IRPF/RE, SII / Veri\*Factu / FacturaE, modelos AEAT
   (303, 347, 349, 390, 111, 115, 130, 369, 232, 720), cierres,
   reporting financiero.

## Cómo está organizado

```
odoo-agent/
├── CLAUDE.md                     # contexto del proyecto para Claude
├── .env.example                  # plantilla de configuración local
├── .claude/                      # capacidades del agente
│   ├── skills/                   # 3 skills (ver tabla abajo)
│   ├── agents/                   # subagentes (oca-module-scout)
│   └── commands/                 # slash-commands (/onboard, /cierre-mensual)
├── docs/                         # notas propias del proyecto
│   ├── onboarding.md             # primer arranque del agente
│   ├── infra/                    # provisión doodba, host, secrets
│   └── tenants/<slug>/           # perfil por despliegue
└── vendor/
    └── odoo-docs/                # documentación oficial de Odoo (read-only)
```

### Skills

| Skill | Dominio | Privilegios |
|-------|---------|-------------|
| [`odoo-accounting-es`](.claude/skills/odoo-accounting-es/SKILL.md) | Operativa contable y fiscal ES | RPC + MCP |
| [`odoo-functional-admin`](.claude/skills/odoo-functional-admin/SKILL.md) | Configuración administrativa funcional | RPC + MCP |
| [`odoo-module-admin`](.claude/skills/odoo-module-admin/SKILL.md) | Ciclo de vida de módulos, doodba, migraciones | RPC + SSH + Docker |

El split es deliberado: cada skill tiene triggers precisos para no
solaparse y solo `odoo-module-admin` puede SSH-ear al host. Detalle en
[`.claude/skills/CLAUDE.md`](.claude/skills/CLAUDE.md).

### Subagentes y comandos

- **`oca-module-scout`** — agente especializado que busca módulos OCA
  compatibles con 19.0 cuando se le describe una funcionalidad.
- **`/onboard`** — verifica conectividad y permisos contra el Odoo
  configurado en `.env`. Punto de entrada habitual al usar el agente
  con un tenant nuevo.
- **`/cierre-mensual <YYYY-MM>`** — orquesta el cierre mensual ES con
  checkpoints entre fases (compliance, libros IVA, P&L, balance,
  modelos AEAT).

## Requisitos

- [Claude Code](https://claude.com/claude-code) instalado.
- Una instancia Odoo 19 Community accesible vía RPC/JSON-2.
- Para `odoo-module-admin`, acceso SSH al host doodba y `docker exec`
  permitido.
- Python 3.10+ para correr los scripts de cada skill.

## Configuración

```bash
cp .env.example .env
# editar .env con los valores reales
```

Variables mínimas (plantilla completa en
[`.env.example`](.env.example), playbook detallado en
[`docs/onboarding.md`](docs/onboarding.md)):

| Variable | Uso |
|----------|-----|
| `ODOO_AGENT_TENANT` | slug del tenant activo (subdir de `docs/tenants/`) |
| `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` | autenticación RPC/JSON-2 |
| `DOODBA_SSH_HOST`, `DOODBA_PROJECT_DIR`, `DOODBA_COMPOSE_SERVICE`, `DOODBA_DB_NAME` | solo para `odoo-module-admin` |

Verifica la configuración ejecutando `/onboard` dentro de Claude Code.

## Tests

```bash
for skill in odoo-accounting-es odoo-functional-admin odoo-module-admin; do
  echo "=== $skill ==="
  (cd .claude/skills/$skill && python3 -m pytest tests/ -q)
done
```

## Documentación oficial de Odoo

Se conserva en [`vendor/odoo-docs/`](vendor/odoo-docs/) como referencia
de solo lectura. Para construir el HTML localmente:

```bash
cd vendor/odoo-docs
pip install -r requirements.txt
make fast
```

## Licencia

- El código del agente (`.claude/`) y notas propias se publican bajo
  **MIT** (cada `SKILL.md` declara la suya).
- La documentación upstream de Odoo en `vendor/odoo-docs/` se mantiene
  bajo su licencia original **CC-BY-NC-SA 4.0**
  (ver [`vendor/odoo-docs/LICENSE`](vendor/odoo-docs/LICENSE)).
