# Onboarding del agente

Pasos para que el agente pueda conectarse y operar contra una
instancia Odoo 19 real. Una vez el flujo esté en verde, las skills
están listas para ejecutar el bootstrap funcional, la migración de
datos y la operativa diaria.

## Prerrequisitos

- [Claude Code](https://claude.com/claude-code) instalado.
- Python 3.10+ disponible.
- Acceso a una instancia Odoo 19 Community arrancada con doodba. Si
  todavía no existe, ver `docs/infra/doodba-bootstrap.md` (pendiente).
- Un usuario "bot" en Odoo con API key, distinto del `admin` (uid 1).
  Ver más abajo.
- (Opcional, para `odoo-module-admin`) acceso SSH al host doodba con
  permiso para `docker exec` sobre el contenedor de Odoo.

## Paso 1 — Crear el bot user en Odoo

Manualmente vía la UI de Odoo (la primera vez no se puede automatizar
porque el agente aún no tiene acceso):

1. Settings → Users & Companies → Users → Create.
2. Login: `bot.contable@<dominio>` (o el que prefieras).
3. Grupos mínimos: `Internal User`, `Accounting Manager`,
   `Multi-Companies` (este último incluso para sociedad única — deja
   la puerta abierta a futuras filiales).
4. Tras guardar: `Mi Perfil` → pestaña `API Keys` → New API Key →
   copia el secreto (Odoo solo lo muestra una vez).

Importante: **no uses la API key del `admin` (uid 1)**. Las skills
tienen reglas de seguridad para no tocar `admin` y la API key del bot
permite revocarla sin romper acceso administrativo de emergencia.

## Paso 2 — Configurar el tenant

Si vas a trabajar con el tenant ya existente `inpr3mium`, salta al
paso 3. Si vas a crear un tenant nuevo:

```bash
TENANT=miempresa
cp -r docs/tenants/_template docs/tenants/$TENANT
mv docs/tenants/$TENANT/profile.yaml.example \
   docs/tenants/$TENANT/profile.yaml
mv docs/tenants/$TENANT/migration-plan.md.example \
   docs/tenants/$TENANT/migration-from-<origen>.md
# editar profile.yaml con los datos reales del cliente
```

Mínimo a completar en `profile.yaml`: `slug`, `legal_name`, `vat`,
`chart_template`, `edi_stack`, `companies`, `expected_modules`. Sin
esos campos `/onboard` no puede validar el estado de la instancia.

Ver `docs/tenants/README.md` para el modelo multi-tenant completo.

## Paso 3 — Configurar `.env`

```bash
cp .env.example .env
# editar .env con los valores reales:
#   - ODOO_AGENT_TENANT (el slug del paso 2)
#   - ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY
#   - DOODBA_* si vas a usar odoo-module-admin
```

`.env` está en `.gitignore`; nunca lo commitees.

## Paso 4 — Verificar con `/onboard`

Lanzar Claude Code en la raíz del repo y ejecutar el slash-command:

```
claude
> /onboard
```

`/onboard` orquesta una serie de smoke tests no destructivos y devuelve
una tabla verde/amarillo/rojo:

| Check | Verde | Significado |
|-------|-------|-------------|
| Profile leído | `profile.yaml` del tenant existe y parsea. | |
| `.env` cargado | Todas las variables RPC obligatorias están definidas. | |
| RPC reachable | Ping al endpoint de Odoo responde. | |
| API key válida | Auth con `ODOO_USER` + `ODOO_API_KEY` funciona. | |
| Bot tiene grupos esperados | El bot pertenece a los grupos del profile. | |
| Módulos esperados instalados | Los `expected_modules` del profile están en `installed`. | |
| SSH a doodba (si aplica) | `ssh ... 'docker ps'` devuelve el contenedor de Odoo. | |

Lo que esperar según fase:

- **Antes del bootstrap funcional** (DB recién creada): RPC y SSH
  verdes, módulos en amarillo (la mayoría aún no instalados).
- **Después del bootstrap funcional**: todo verde.
- **Después de la migración de datos**: todo verde + el agente conoce
  partners/productos reales.

## Paso 5 — Resolver semáforos en rojo

`/onboard` sugiere por cada rojo qué hacer. Patrones típicos:

- **RPC unreachable**: revisar `ODOO_URL`, certificado TLS, firewall
  del host. Si la instancia está detrás de Traefik o nginx, comprobar
  que el path no devuelve 502.
- **API key inválida**: regenerar en `Mi Perfil` → API Keys. Comprobar
  que `ODOO_USER` matches el login del bot (no el del admin).
- **Bot sin grupos**: añadir desde la UI o vía
  `odoo-functional-admin/scripts/group_assign.py` si ya tienes
  conexión.
- **Módulos faltantes**: ejecutar el bootstrap funcional (Fase 4 del
  plan en `~/.claude/plans/bien-ahora-planifiquemos-cuales-snazzy-duckling.md`).
- **SSH falla**: verificar `ssh ${DOODBA_SSH_HOST}` desde tu shell
  manualmente; el agente solo usa la misma config SSH del usuario.

## Paso 6 — Empezar a operar

Con `/onboard` verde, el agente está listo. Próximas operaciones
típicas:

- Bootstrap funcional inicial (instalar módulos, crear empresa,
  diarios, posiciones fiscales): pídeselo al agente con frase tipo
  "haz el bootstrap funcional de inpr3mium" y enrutará a las skills
  correspondientes.
- Cierre mensual: `/cierre-mensual 2026-04`.
- Migración desde el sistema origen: depende del tenant; ver
  `docs/tenants/<slug>/migration-from-*.md`.
- Cualquier operación contable o de admin: pídeselo al agente en
  lenguaje natural; las skills se activan por triggers explícitos.

## Tests del agente (independientes de la conexión Odoo)

Los tests unitarios de las skills no requieren Odoo:

```bash
for skill in odoo-accounting-es odoo-functional-admin odoo-module-admin; do
  echo "=== $skill ==="
  (cd .claude/skills/$skill && python3 -m pytest tests/ -q)
done
```

Verde antes de hacer cambios en `_common.py` o `odoo_client.py`.
