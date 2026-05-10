# Seguridad de las operaciones SSH

## Principio

Este skill ejecuta comandos en una maquina de produccion remota via
SSH. Cualquier error es potencialmente caro. La defensa en profundidad
es:

1. **Whitelist de comandos**: solo se ejecutan los listados abajo.
2. **`--dry-run` por defecto**: el usuario debe pedir explicitamente
   ejecucion real.
3. **Confirmaciones explicitas**: para operaciones destructivas, el
   skill se detiene y pide al usuario confirmacion textual antes de
   continuar.
4. **Captura de stderr / exit code**: nunca se ejecuta "fire and
   forget"; siempre se valida el exit y se reporta.

## Whitelist de comandos remotos permitidos

| Categoria | Comando | Notas |
|-----------|---------|-------|
| Lectura | `ls`, `cat`, `tail`, `head`, `git status`, `git log`, `git branch`, `df`, `free`, `ps` | Read-only. |
| Lectura Docker | `docker ps`, `docker compose ps`, `docker compose logs`, `docker compose images`, `docker exec <cnt> cat ...` | Read-only. |
| Aggregator | `gitaggregate -c <yaml>` | OK con --dry-run primero. |
| Doodba invoke | `invoke img-build`, `invoke git-aggregate`, `invoke restart`, `invoke logs` | OK. |
| Odoo lifecycle | `docker compose run --rm -T odoo odoo --stop-after-init ...` | OK con confirmacion de usuario. |
| Restart | `docker compose restart odoo` | OK con confirmacion. |
| Backup | `docker compose exec -T db pg_dump ...`, `tar czf ... filestore` | OK. |

## Comandos PROHIBIDOS

**Nunca ejecutes via este skill** (deriva al usuario / sysadmin):

- `rm` fuera de `auto/` (cualquier `rm -rf` es prohibido siempre).
- `mv` fuera de `auto/`.
- `chown`, `chmod` (puede romper permisos de doodba).
- `sudo` o `su` (escalada de privilegios).
- Cualquier comando `apt`, `apt-get`, `yum`, `dnf`.
- `systemctl` (start/stop/restart de servicios fuera del compose).
- `iptables`, `ufw` (firewall).
- Edicion in-place de `docker-compose.yml`, `odoo.conf`, `.env`
  (tiene que hacerlo el usuario humano via PR).
- `git push`, `git reset --hard`, `git clean -fdx`.
- `dropdb`, `createdb` directos (excepto en flujo de rollback con
  confirmacion explicita).
- Comandos sobre repos NO doodba (p.ej. tocar `/etc/`, `/home/<otro>/`).

Si el usuario pide algo de esta lista, **detente y explica** que esta
fuera del alcance de seguridad del skill.

## `--dry-run` por defecto

Operaciones destructivas (instalacion, upgrade, uninstall, agregacion
de repos) deben aceptar `--dry-run` y, si no esta presente, **mostrar
al usuario que harian** y pedir confirmacion antes de re-ejecutar sin
`--dry-run`.

Patron:

```python
def run(args):
    cmd = build_command(args)
    if args.dry_run:
        print(f"DRY RUN: {cmd}")
        return 0
    print(f"Executing: {cmd}")
    return subprocess.run(cmd).returncode
```

## Confirmacion del usuario

Antes de cada operacion destructiva, el SKILL.md instruye a Claude:

> **Detente y pide confirmacion al usuario** mostrando:
> - Comando exacto que se va a ejecutar.
> - Modulos / DB / contenedor afectados.
> - Estado actual y estado tras la operacion.
> - Plan de rollback si aplica.

## Reintentos y locks

Para operaciones que pueden chocar con un lock advisory de PostgreSQL
(varios upgrades concurrentes):

1. Capturar el exit code.
2. Si exit indica lock, esperar un random backoff (5-30s) y reintentar
   maximo 3 veces.
3. Si no es lock, reportar el error real y detenerse.

`scripts/ssh_runner.py` provee un retry helper.

## Logs y auditoria

Recomendado: cada operacion destructiva escribe a un fichero de
auditoria en el host remoto:

```bash
ssh "$DOODBA_SSH_HOST" \
  "echo '$(date -Iseconds) MODULE_INSTALL by claude-skill module=$MOD' \
   >> $DOODBA_PROJECT_DIR/audit.log"
```

(Esto NO esta automatizado; es una recomendacion para que el usuario
lo configure si quiere trazabilidad).

## Permisos del usuario SSH

El usuario SSH (`DOODBA_SSH_HOST`) debe ser el user `odoo` del
deployment, miembro del grupo `docker` para ejecutar `docker compose`.

**No** debe tener `sudo` sin password ni acceso a otras DBs / servicios.

Configuracion recomendada en `/etc/ssh/sshd_config.d/odoo.conf`:

```
Match User odoo
    ForceCommand none
    AllowAgentForwarding no
    AllowTcpForwarding no
    X11Forwarding no
    PermitTTY no
```

(El `PermitTTY no` te obliga a usar `-T` en `docker compose run` y
evita errores en SSH no-interactivo).

## Si SSH falla

Posibles causas (en orden de probabilidad):

1. **Network**: timeout, host unreachable. `ssh_runner.py` reintenta
   3 veces con backoff.
2. **Auth**: clave revocada o no aceptada. Detente y pide al usuario.
3. **Permission denied**: el user SSH no esta en el grupo `docker`.
4. **`docker compose` no encontrado**: revisar version o path.

Diferenciar entre fallo de SSH (exit 255) y fallo de comando remoto
(exit otros) es critico para el reintento. `ssh_runner.py` lo hace.
