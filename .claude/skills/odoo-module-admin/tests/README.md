# Tests del skill `odoo-module-admin`

## Alcance

Solo helpers puros y construccion de comandos:

- `test_common.py`: validacion de env vars, retry, format_amount.
- `test_odoo_client_helpers.py`: `_clean_fault`.
- `test_ssh_runner.py`: construccion de comandos SSH, `--dry-run`,
  parseo de exit codes (transport vs comando), wrappers
  `docker_compose_run` / `docker_compose_restart`. **No** ejecuta SSH
  real; mockea `subprocess.run`.
- `test_manifest_lint.py`: parser AST de `__manifest__.py` y deteccion
  de errores / warnings. **No** carga Odoo.

## Lo que NO se cubre aqui

- Llamadas RPC reales (requieren Odoo 19 vivo).
- Ejecucion SSH real (requiere DOODBA_SSH_HOST configurado).
- Operaciones contra Docker (requieren contenedor doodba).
- `gitaggregate` real (requiere git remotes accesibles).

Para integracion, usar un entorno doodba de testing.

## Ejecutar

```bash
cd .claude/skills/odoo-module-admin
python3 -m pytest tests/ -v
```

## Duplicacion entre skills (importante)

`_common.py`, `odoo_client.py`, `test_common.py`,
`test_odoo_client_helpers.py` estan **duplicados verbatim** entre los
tres skills (`odoo-accounting-es`, `odoo-functional-admin`,
`odoo-module-admin`). Decision deliberada: las skills son bundles
auto-contenidos.

**Si arreglas un bug en `_common.py` u `odoo_client.py`, sincroniza el
cambio a las otras dos skills hermanas.**
