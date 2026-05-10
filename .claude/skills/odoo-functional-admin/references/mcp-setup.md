# Setup MCP - usar el skill con un servidor MCP de Odoo

El skill funciona standalone (los `scripts/` llaman a Odoo directamente
via XML-RPC / JSON-2). Anadir un **MCP server** mejora la experiencia
para lecturas conversacionales ad-hoc ("muestrame las facturas pendientes
de cobro de clientes espanoles >5.000 EUR") sin tener que ejecutar un
script.

Esta guia documenta el setup recomendado para Claude Code y Claude
Desktop.

## Por que MCP + skill

- **Skill**: codifica conocimiento de dominio (PGCE, AEAT, Verifactu) +
  workflows determinísticos idempotentes (factura, pago, cierre).
- **MCP**: expone tools genericos CRUD sobre cualquier modelo Odoo
  (search_records, get_record, list_models). Util para Q&A.

Sin MCP, Claude usa los scripts del skill (mas verboso pero igualmente
funcional). Con MCP, Claude puede explorar el ERP por su cuenta antes de
ejecutar un workflow del skill.

## Servidores MCP Odoo recomendados

| Repo | Recomendado para |
|------|------------------|
| **`ivnvxd/mcp-server-odoo`** | Caso general. Mas maduro (MPL-2.0). Modulo `mcp_server` opcional en Odoo Apps con ACL granular. Soporta XML-RPC en 14-19 |
| **`tuanle96/mcp-odoo`** | Si quieres seguridad extra (escritura gateada por aprobacion). Soporta JSON-2 nativo en Odoo 19+ |
| **`pantalytics/odoo-mcp-pro`** | Si necesitas hosted con OAuth y soporte JSON-2 nativo |

Para este skill, recomendacion por defecto: **`ivnvxd/mcp-server-odoo`**.

## Instalacion - Claude Code

### Comando de un paso

```bash
claude mcp add odoo \
  --env ODOO_URL=https://odoo.miempresa.cat \
  --env ODOO_DB=miempresa_prod \
  --env ODOO_API_KEY=tu_api_key_aqui \
  -- uvx mcp-server-odoo
```

Lo de despues de `--` es el comando que arranca el server. `uvx` instala
y ejecuta `mcp-server-odoo` aislado en su propio venv (recomendado).

### Verificar

```bash
claude mcp list
# Deberia mostrar:
# odoo: connected
```

Las tools expuestas se listan con prefijo `mcp__odoo__*` (p.ej.
`mcp__odoo__search_records`). El `allowed-tools` del frontmatter del
skill ya incluye `mcp__odoo__*`, asi que el skill puede usarlas sin pedir
permiso.

## Instalacion - Claude Desktop

Editar `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) o `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "odoo": {
      "command": "uvx",
      "args": ["mcp-server-odoo"],
      "env": {
        "ODOO_URL": "https://odoo.miempresa.cat",
        "ODOO_DB": "miempresa_prod",
        "ODOO_API_KEY": "tu_api_key_aqui"
      }
    }
  }
}
```

Reiniciar Claude Desktop. La conexion aparece como icono en la barra de
herramientas inferior.

## Variables de entorno compartidas con el skill

El skill espera **las mismas** variables que el MCP server:

| Variable | Skill | MCP |
|----------|-------|-----|
| `ODOO_URL` | Si | Si |
| `ODOO_DB` | Si | Si |
| `ODOO_API_KEY` | Si | Si |
| `ODOO_USER` | Solo si `ODOO_FORCE_XMLRPC=1` | Solo modo password (no recomendado) |
| `ODOO_FORCE_XMLRPC` | Si (opcional) | No (usa XML-RPC por defecto) |

Setearlas en `.bashrc` / `.zshrc` o un `.env` cargado por el shell para
que **ambos** las vean. NO commitear el `.env` (el `.gitignore` del skill
lo cubre).

## Permisos (`allowed-tools`)

El frontmatter del skill incluye:

```yaml
allowed-tools:
  - Read
  - Bash(python3:*)
  - Bash(uv:*)
  - mcp__odoo__*
```

Esto significa:
- Cuando el skill se invoca, **no se pide permiso** para ejecutar
  `python3 ...`, `uv ...` ni para llamar tools `mcp__odoo__*`.
- Si lanzas el skill sin MCP configurado, las llamadas
  `mcp__odoo__*` simplemente no estaran disponibles (Claude usara los
  scripts).

Si quieres restringir mas (p.ej. solo `mcp__odoo__search_records` y
`mcp__odoo__get_record`, bloqueando escritura), edita el frontmatter:

```yaml
allowed-tools:
  - Read
  - Bash(python3:*)
  - mcp__odoo__search_records
  - mcp__odoo__get_record
```

Cualquier otra tool MCP requerira aprobacion manual.

## Modulo opcional en Odoo (`mcp_server`)

`ivnvxd` publica un modulo de pago (~99 EUR) en Odoo Apps que da control
fino:

- ACL por modelo (whitelist explicita).
- Audit log de llamadas MCP en `mcp.server.log`.
- Rate limiting.

Sin el modulo, el server funciona en modo "YOLO" usando solo la API key
(con los permisos del usuario que la genero). Para produccion con datos
sensibles, considera el modulo o un usuario bot con permisos minimos.

## Restringir el usuario bot

Recomendacion: crear un usuario `claude-bot@miempresa.cat` con:

1. Sin password (solo API key, deshabilita login UI).
2. Grupos: `Accounting / Accountant` (lectura/escritura contable) +
   `Sales / User` (lectura ventas).
3. **No** `Settings / Administration` (evita modificar config).
4. **No** `Technical Features` (evita rompedor de modelos).

API key con duracion **persistente** (no caduca) en
`Mi perfil > Seguridad de la cuenta > API Keys`.

## Troubleshooting

### "MCP server failed to start"

```bash
# Verificar que uvx esta instalado:
which uvx || pip install uv

# Probar el server manualmente:
uvx mcp-server-odoo --help

# Inspector visual:
npx @modelcontextprotocol/inspector uvx mcp-server-odoo
```

### "Authentication failed"

- Comprobar que `ODOO_API_KEY` no contiene espacios al final.
- Verificar que la key sigue activa: `Mi perfil > Seguridad`.
- Si la instancia tiene multiples DBs sin `dbfilter`, verificar
  `ODOO_DB`.

### "Tool mcp__odoo__xyz not found"

- Refrescar la lista de tools en Claude Code: `claude mcp restart odoo`.
- Verificar version del server: `pip show mcp-server-odoo`.

### "Slow responses"

- El primer `uvx mcp-server-odoo` baja el paquete (lento). Ejecuciones
  posteriores son inmediatas.
- Si tu Odoo esta lejos de tu maquina, considera correr el MCP server en
  el mismo datacenter via Docker:
  ```bash
  docker run -d --name odoo-mcp \
    -e ODOO_URL=https://odoo.local \
    -e ODOO_DB=prod -e ODOO_API_KEY=xxx \
    ghcr.io/ivnvxd/mcp-server-odoo
  ```

## Combinacion tipica de uso

1. Usuario: "muestrame las facturas pendientes de cobro de Tecnativa SL"
   - Claude usa `mcp__odoo__search_records` (lectura via MCP).
2. Usuario: "envia un recordatorio de cobro de nivel 2 a las que llevan
   mas de 30 dias"
   - Claude carga la reference `treasury.md` del skill.
   - Claude ejecuta `scripts/dunning.py --level 2 --dry-run` primero.
   - Tras confirmacion, ejecuta sin `--dry-run`.
3. Usuario: "cierra el trimestre Q1"
   - Claude ejecuta `scripts/period_close_checklist.py --from
     2026-01-01 --to 2026-03-31`.
   - Si todo OK, ejecuta `scripts/run_aeat_report.py --model 303
     --period 2026Q1`.

El MCP es ideal para el paso 1; los scripts del skill son ideales para
los pasos 2 y 3 (acciones idempotentes con validacion).

## Alternativa: sin MCP, solo skill

Funciona perfectamente. Para lecturas ad-hoc:

```bash
python3 scripts/odoo_client.py search_read account.move \
  '[["payment_state","in",["not_paid","partial"]]]' \
  '["id","name","partner_id","amount_residual"]' 50
```

Mas verboso que MCP pero sin dependencias adicionales.
