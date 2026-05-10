# Estrategia de upgrade

## Tres niveles de upgrade

| Nivel | Que cambia | Frecuencia | Riesgo |
|-------|-----------|------------|--------|
| **Module upgrade** | Codigo de un addon (sin cambio de version Odoo) | Por commit en `repos.yaml` | Bajo si el codigo se ha probado. |
| **Minor Odoo upgrade** | 19.0.1 -> 19.0.2 (patch del core) | Mensual | Medio. |
| **Major Odoo upgrade** | 18 -> 19 | Anual | Alto: requiere OpenUpgrade en Community. |

## Module upgrade (lo mas comun)

Tras `git pull` en repos OCA o cambio en `repos.yaml`:

```bash
# 1. Backup primero
ssh "$DOODBA_SSH_HOST" \
  "cd $DOODBA_PROJECT_DIR && \
   docker compose exec -T db pg_dump -U odoo $DOODBA_DB_NAME > backup.sql"

# 2. Sincronizar addons
ssh "$DOODBA_SSH_HOST" "cd $DOODBA_PROJECT_DIR && invoke img-build"

# 3. Upgrade
ssh "$DOODBA_SSH_HOST" \
  "cd $DOODBA_PROJECT_DIR && \
   docker compose run --rm -T odoo \
     odoo --stop-after-init --no-http \
       -d $DOODBA_DB_NAME -u <module_names>"

# 4. Restart
ssh "$DOODBA_SSH_HOST" "cd $DOODBA_PROJECT_DIR && docker compose restart odoo"
```

`scripts/module_upgrade.py` envuelve esto.

### `--changed` flag

`module_upgrade.py --changed` detecta automaticamente que modulos cambio
comparando checksums de los manifests con los registrados en
`ir.config_parameter` (clave `__custom__.module_checksums`). Solo
upgradea los que cambiaron. Mucho mas rapido que `-u all`.

Inspirado en `click-odoo-update` de ACSONE; reimplementado aqui para
no anyadir dependencia externa.

## Pre-checks antes de cualquier upgrade

1. **Backup completo**:
   ```bash
   pg_dump -U odoo $DB > backup-$(date +%Y%m%d-%H%M).sql
   tar czf filestore-$(date +%Y%m%d-%H%M).tar.gz /var/lib/odoo/filestore/$DB
   ```
2. **Snapshot de modulos instalados**:
   ```bash
   python3 scripts/audit_module_state.py > pre-upgrade-state.json
   ```
3. **Compatibilidad de OCA**: verifica que los repos esten en la rama
   `19.0` correcta y que los manifests no marquen `installable: False`.
4. **Espacio en disco**: PostgreSQL puede temporalmente duplicar tablas.
   Verifica `df -h` -> al menos 30% libre.
5. **Mantenimiento**: avisa a usuarios; idealmente fuera de horas pico.

## Major version upgrade (Community: OpenUpgrade)

Odoo S.A. solo upgradea Enterprise/Online. Para Community es obligatorio
OpenUpgrade (OCA), que provee scripts de migracion para los modulos
core y muchos OCA.

### Requisitos

- OpenUpgrade rama destino: `19.0` (para upgrade desde 18).
- Solo permite saltos incrementales: 17 -> 18 -> 19, no 17 -> 19 directo.
- Debe ejecutarse offline (sin usuarios conectados).

### Flujo (high-level, **NO ejecutar sin replicar en staging primero**)

```bash
# 1. Replica de la DB de produccion
docker compose exec -T db createdb -O odoo prod_test
pg_restore -U odoo -d prod_test < backup.sql

# 2. Clonar OpenUpgrade rama destino
git clone -b 19.0 https://github.com/OCA/OpenUpgrade.git /tmp/openupgrade

# 3. Anyadir a addons_path (temporalmente)
docker compose run --rm -T \
  -v /tmp/openupgrade:/openupgrade:ro \
  odoo \
    odoo \
      --addons-path=/opt/odoo/addons,/openupgrade/odoo/addons,/openupgrade/addons,/opt/odoo/auto/addons \
      --upgrade-path=/openupgrade/openupgrade_scripts/scripts \
      --update all \
      --stop-after-init --no-http \
      -d prod_test \
      --load=base,web,openupgrade_framework

# 4. Iterar sobre errores hasta que termine clean.
# 5. Smoke tests: login, generar factura, modelo 303, etc.
# 6. Solo cuando esto funcione, repetir contra produccion (con backup actualizado).
```

### Modulos OCA en major upgrade

OpenUpgrade NO migra todos los modulos OCA automaticamente. Para cada
addon OCA:

- Si tiene carpeta `migrations/19.0.X.Y.Z/` -> migrate scripts oficiales.
- Si no -> el upgrader puede que falle. Opciones:
  - Desinstalar el modulo antes del upgrade y reinstalar despues.
  - Escribir manualmente `migrations/19.0.X.Y.Z/post-migrate.py`.
  - Usar `oca-port` (ACSONE) para portar el modulo si la rama 19.0 no
    existe upstream.

### Modulos custom

`migrations/<version>/pre-migrate.py` y `post-migrate.py` son la API
oficial de Odoo para migrar datos custom. Documentado en
`https://www.odoo.com/documentation/19.0/developer/reference/backend/upgrades.html`.

## Smoke tests post-upgrade

Antes de declarar exito:

1. Login admin OK.
2. `audit_module_state.py` -> ningun modulo en `to upgrade` o
   `uninstallable`.
3. Crear y postear una factura de prueba (usar skill `odoo-accounting-es`).
4. Generar modelo 303 trimestre actual (idem).
5. Conciliar un movimiento bancario simple.
6. Lanzar manualmente el cron de SII / Veri*Factu y verificar respuesta
   AEAT.
7. Revisar logs (`docker compose logs odoo --tail=200`) buscando
   `ERROR` o `CRITICAL`.

## Rollback plan (si la cosa va mal)

```bash
# 1. Parar Odoo
docker compose stop odoo

# 2. Restaurar DB
docker compose exec -T db dropdb -U odoo $DB
docker compose exec -T db createdb -U odoo $DB
docker compose exec -T db psql -U odoo $DB < backup.sql

# 3. Restaurar filestore
rm -rf /var/lib/odoo/filestore/$DB
tar xzf filestore-backup.tar.gz -C /var/lib/odoo/filestore/

# 4. Volver al codigo anterior
git -C $DOODBA_PROJECT_DIR checkout <prev_sha>

# 5. Restart
docker compose up -d odoo
```

**Tiempo de downtime tipico**: 5-30 minutos para restore.
