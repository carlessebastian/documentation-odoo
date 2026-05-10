---
description: Verifica que el agente puede operar contra el Odoo configurado (RPC, API key, permisos del bot, módulos esperados, SSH a doodba)
argument-hint: (sin argumentos)
allowed-tools: Skill, Bash, Read, Grep
---

# /onboard

Smoke test del agente contra la instancia Odoo activa. Reporta una
tabla **verde / amarillo / rojo** con los checks; sugiere fix para cada
rojo. **No realiza cambios** en la instancia (solo lecturas y un
opcional `docker ps` por SSH).

Úsalo:
- Tras configurar `.env` por primera vez.
- Cada vez que cambies de tenant (`ODOO_AGENT_TENANT`).
- Tras incidencias o cambios en la instancia para verificar que el
  agente sigue conectado.

## Procedimiento

Ejecuta los checks **en orden** y produce una tabla de resultados al
final. No abortes en el primer rojo: continúa con los checks que sigan
siendo posibles (p.ej. si RPC falla, salta los checks que dependen de
RPC pero ejecuta SSH si está configurado). El reporte final es lo
único que el usuario lee.

### Check 0 — Cargar `.env` y `profile.yaml`

1. Lee `.env` desde la raíz del repo. Si no existe, **rojo**: pide al
   usuario `cp .env.example .env` y rellenarlo. Aborta el resto de
   checks (sin `.env` no se puede continuar).
2. Verifica que `ODOO_AGENT_TENANT` esté definido. Si no, **rojo**: el
   tenant es obligatorio.
3. Construye la ruta `docs/tenants/$ODOO_AGENT_TENANT/profile.yaml` y
   léela. Si no existe, **rojo**: pide al usuario crear el tenant
   (`cp -r docs/tenants/_template docs/tenants/$ODOO_AGENT_TENANT`).
4. Parsea el YAML. Si no parsea, **rojo** con el error de parseo.
5. Comprueba que `legal_name`, `vat`, `chart_template`,
   `expected_modules`, `companies` estén presentes (no vacíos ni
   `<TODO_*>`). Si alguno falta o es placeholder, **amarillo**: avisa
   pero sigue con los checks de conectividad (que pueden funcionar).

### Check 1 — Variables RPC presentes

Comprueba que `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` estén
definidos en `.env` y no vacíos.

- Si falta alguno, **rojo** con la lista de variables a rellenar.
- Si todos presentes, **verde**.

### Check 2 — RPC reachable

Reusa `.claude/skills/odoo-functional-admin/scripts/odoo_client.py`
(o el de cualquiera de las 3 skills — son idénticos) para hacer un
ping. El cliente expone un `OdooClient.ping()` o equivalente; si no
existe método específico, una llamada barata como
`call('res.users', 'search_count', [[]])` con `limit=1` sirve.

```bash
cd .claude/skills/odoo-functional-admin
python3 -c "
from scripts.odoo_client import OdooClient
import os
client = OdooClient.from_env()
n = client.call('res.users', 'search_count', [[('active', '=', True)]])
print(f'OK — {n} usuarios activos')
"
```

- Verde si responde.
- Rojo si timeout, 404, 502, certificate error, etc. — sugerir
  revisar `ODOO_URL`, firewall, reverse proxy.

### Check 3 — API key válida (auth contra el bot)

Si Check 2 pasó, la auth ya funcionó (`OdooClient.from_env()` hace
authenticate). Reportar **verde** automáticamente.

Si Check 2 falló por auth (401 / `AccessDenied`), separar y reportar
en este check **rojo**: regenerar API key en `Mi Perfil → API Keys`.

### Check 4 — Bot user no es `admin` (uid 1)

Lee el `uid` con el que se autenticó el cliente. Si es `1`, **amarillo**:
recomendar crear un bot user dedicado y revocar la API key del admin.
Las skills tienen reglas de seguridad sobre uid 1 que bloquearán
operaciones críticas.

### Check 5 — Bot tiene los grupos esperados

Compara los grupos del bot (campo `groups_id` con `name_get`) contra
`bot.groups` del `profile.yaml`.

- Verde si los tiene todos.
- Amarillo si faltan algunos: lista los grupos faltantes y sugiere
  ejecutar
  `.claude/skills/odoo-functional-admin/scripts/group_assign.py
  --login $ODOO_USER --add <GRUPO>`.
- Rojo si el bot no tiene siquiera `base.group_user` (no podrá hacer
  nada).

### Check 6 — Empresa activa coincide con el profile

Lee la company por defecto del bot
(`res.users.company_id.name` y `.vat`). Compara con la primera entrada
de `companies` en el `profile.yaml`.

- Verde si coinciden nombre y VAT.
- Amarillo si no coinciden — reportar discrepancia. Puede ser
  intencionado (multi-company) o estar pendiente del bootstrap.
- Rojo si no hay ninguna company configurada.

### Check 7 — Módulos esperados instalados

Reusa `.claude/skills/odoo-module-admin/scripts/module_status.py`
(con `--changed` o sin él, según interfaz). Para cada módulo en
`profile.yaml.expected_modules`, comprobar el estado en
`ir.module.module`:

- `installed` → verde.
- `to install` / `to upgrade` → amarillo.
- `uninstalled` → rojo.
- No existe (`search` devuelve 0) → rojo, indica que el repo OCA
  correspondiente no está clonado en `addons_path`.

Reportar tabla resumida: `N/M módulos instalados, K faltantes:
[lista]`. Si hay muchos faltantes, sugerir ejecutar el bootstrap
funcional vía `odoo-module-admin/scripts/repos_aggregate.sh apply` y
`module_install.py --names <lista>`.

### Check 8 — SSH a doodba (si está configurado)

Si `DOODBA_SSH_HOST` está vacío, marcar **N/A** (no aplica). El usuario
puede no necesitar `odoo-module-admin`.

Si está configurado, ejecuta:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 "$DOODBA_SSH_HOST" \
  "docker ps --filter name=$DOODBA_COMPOSE_SERVICE --format '{{.Names}} {{.Status}}'"
```

- Verde si devuelve una línea con el container running.
- Amarillo si conecta pero el container no aparece (servicio caído o
  nombre distinto — verificar `DOODBA_COMPOSE_SERVICE`).
- Rojo si el SSH falla (key, permisos, host inalcanzable). Sugerir
  probar `ssh $DOODBA_SSH_HOST` manualmente desde la shell del usuario.

`BatchMode=yes` evita que pida contraseña si la key no está bien
configurada.

### Check 9 — Tests de las skills (offline)

Ejecuta los pytest de cada skill (no requieren conexión Odoo):

```bash
for skill in odoo-accounting-es odoo-functional-admin odoo-module-admin; do
  (cd .claude/skills/$skill && python3 -m pytest tests/ -q --tb=no) || echo "FAIL: $skill"
done
```

- Verde si los tres pasan.
- Amarillo / rojo según skill que falle.

## Salida — formato del reporte

Imprimir tabla en este formato exacto al final (Markdown), sin
columnas extra:

```
| Check | Estado | Detalle / sugerencia |
|-------|--------|----------------------|
| 0. Profile leído | ✓ verde | tenant=inpr3mium, legal_name=... |
| 1. Variables RPC | ✓ verde | |
| 2. RPC reachable | ✓ verde | 12 usuarios activos |
| 3. API key | ✓ verde | uid=42 |
| 4. Bot ≠ admin | ✓ verde | uid=42 (no es uid 1) |
| 5. Grupos del bot | ⚠ amarillo | falta base.group_multi_company. Fix: group_assign.py --login ... --add base.group_multi_company |
| 6. Empresa activa | ✓ verde | "Inteligencia del Negocio Pr3mium S.L." (ESBxxx) |
| 7. Módulos | ⚠ amarillo | 8/14 instalados. Faltan: l10n_es_aeat_mod347, ... — ejecutar bootstrap funcional |
| 8. SSH a doodba | N/A | DOODBA_SSH_HOST no configurado |
| 9. Tests skills | ✓ verde | 3/3 verde |
```

Tras la tabla, una línea de resumen:

```
Resumen: 6 verde, 2 amarillo, 0 rojo, 1 N/A → agente listo para
operar (con limitaciones: módulos pendientes, SSH no config).
```

Si hay rojos, finaliza con: `Resuelve los rojos antes de operar.`

## Notas de implementación

- No introduce código nuevo crítico: orquesta scripts ya existentes.
- Es **idempotente** y **read-only**: ejecutarlo múltiples veces no
  cambia nada en Odoo.
- Si los scripts ya tienen flag `--json` o similar, úsalo para parsear
  la salida; si no, parseo posicional sobre el stdout.
- Manejo de errores: cada check captura su propia excepción y reporta
  rojo + sugerencia. No relances la excepción a menos que sea Check 0
  (sin `.env`/profile no hay nada que validar).
