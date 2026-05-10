# Patrones `docker exec` para Odoo (doodba)

## Ejecucion vs run

| Comando | Uso |
|---------|-----|
| `docker exec` | Ejecuta dentro del contenedor que YA esta corriendo. |
| `docker compose run --rm` | Levanta un contenedor efimero del servicio. |

Para operaciones de install/upgrade en doodba, **prefiere `compose run --rm -T`**
porque:

- No interfiere con los workers HTTP que estan sirviendo trafico.
- Sale limpiamente con `--stop-after-init`.
- `--rm` borra el contenedor efimero al terminar.
- `-T` desactiva TTY allocation (necesario para SSH no interactivo).

## SSH + docker compose run (canonico)

```bash
ssh -o StrictHostKeyChecking=accept-new "$DOODBA_SSH_HOST" \
  "cd $DOODBA_PROJECT_DIR && \
   docker compose run --rm -T odoo \
     odoo \
       --stop-after-init \
       --no-http \
       -d $DOODBA_DB_NAME \
       -i l10n_es_aeat_mod303 \
       --logfile /var/log/odoo/install.log"
```

**No uses ssh `-tt`** (force TTY) en estos casos: rompe la captura de
stdout y los exit codes vuelven 0 cuando el comando real fallo.

## Exit codes esperados

| Code | Significado |
|------|-------------|
| 0 | Operacion exitosa. |
| 1 | Error generico de Odoo (manifest invalido, dep faltante). |
| 2 | Argumentos CLI invalidos. |
| 137 | Killed (OOM, signal 9). |
| 130 | Interrupted (Ctrl-C). |
| 255 | SSH falla (no se llego a ejecutar). |

`scripts/ssh_runner.py` parsea exit codes y diferencia "SSH fallo"
(`255`) de "Odoo fallo" (otros). Esta distincion es critica para
reintentos.

## Streaming de logs

Para operaciones largas (`-u all` puede tardar 30+ minutos), capturar
y mostrar logs en vivo:

```bash
ssh "$DOODBA_SSH_HOST" \
  "cd $DOODBA_PROJECT_DIR && \
   docker compose run --rm -T odoo odoo --stop-after-init --no-http \
     -d $DOODBA_DB_NAME -u all --logfile=/dev/stderr 2>&1"
```

`--logfile=/dev/stderr` redirige logs a stderr para que SSH los traiga
en streaming (vs un fichero que solo se lee al terminar). Combinar con
`tee /var/log/odoo/upgrade.log` localmente si quieres copia.

## Ejecutar como user `odoo` (no root)

Por defecto la imagen doodba ejecuta como user `odoo` (UID 999 o el
que se haya configurado). `docker compose run` lo respeta sin
necesidad de `-u`.

Si necesitas root puntualmente (raro):

```bash
docker compose run --rm -T -u root odoo bash -c "..."
```

**Evitar root**: cambios al filesystem como root crean ficheros que
luego el user `odoo` no puede modificar -> errores oscuros despues.

## Shell de Odoo (`odoo shell`)

Para inspeccion interactiva NO recomendable via SSH no-interactivo;
para uso ad-hoc desde el host del usuario:

```bash
ssh -t "$DOODBA_SSH_HOST" \
  "cd $DOODBA_PROJECT_DIR && docker compose exec odoo odoo shell -d $DB"
```

(`-t` aqui SI es correcto porque queremos TTY interactivo; no lo
mezcles con la captura programatica de output).

## `db_filter` y multi-db

Si la instancia tiene varias DBs, `--no-database-list` y `--db_filter`
limitan que DBs son visibles. En operaciones one-shot pasamos `-d <db>`
explicito y no necesitamos preocuparnos.

## Comprobar que el comando esta cogiendo la imagen correcta

```bash
ssh "$DOODBA_SSH_HOST" \
  "cd $DOODBA_PROJECT_DIR && docker compose images odoo"
```

Si la imagen es vieja (antes de un cambio en `addons.yaml`), regenera
con `invoke img-build` o `docker compose build odoo`.

## Captura de stderr en scripts Python

`scripts/ssh_runner.py` usa:

```python
result = subprocess.run(
    ["ssh", host, cmd],
    capture_output=True,
    text=True,
    timeout=timeout_seconds,
    check=False,
)
return result.returncode, result.stdout, result.stderr
```

Importante: `check=False` para que no lance excepcion en exit no-cero
y podamos diferenciar tipos de error.

## Errores frecuentes

- **`the input device is not a TTY`**: anyadir `-T` a `docker compose run`.
- **`docker: Error response from daemon: ... no such service: odoo`**:
  el servicio se llama distinto en `docker-compose.yml` (a veces `web`,
  `app`). Setear `DOODBA_COMPOSE_SERVICE`.
- **`unable to find user odoo: no matching entries in passwd`**: imagen
  base distinta a doodba. El skill asume doodba; ver `references/doodba-topology.md`
  seccion non-doodba fallback.
- **Hangs sin output durante minutos**: probablemente `--logfile`
  apunta a fichero y no a stderr -> output buffered. Cambiar a
  `--logfile=/dev/stderr`.
