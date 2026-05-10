# Tests del skill `odoo-functional-admin`

## Alcance

Solo helpers puros (sin red, sin Odoo real):

- `test_common.py`: validacion de env vars, retry on network, format_amount.
- `test_odoo_client_helpers.py`: `_clean_fault` para extraer mensajes de error.
- `test_company_setup.py`: `normalize_vat`, `detect_parent_cycle`.
- `test_user_provision.py`: `normalize_login`, `validate_group_xmlid`.
- `test_ext_id_upsert.py`: `parse_xmlid`.

Las llamadas RPC reales (XML-RPC / JSON-2) no se cubren aqui; requieren
una instancia Odoo 19 viva. Para pruebas de integracion, montar Odoo en
Docker / doodba y ejecutar los scripts contra un DB de testing.

## Ejecutar

```bash
cd .claude/skills/odoo-functional-admin
python3 -m pytest tests/ -v
```

## Nota importante: duplicacion entre skills

Los ficheros `_common.py` y `odoo_client.py` (y los tests
`test_common.py`, `test_odoo_client_helpers.py`) estan **duplicados
verbatim** entre los tres skills (`odoo-accounting-es`,
`odoo-functional-admin`, `odoo-module-admin`). Esta es una decision
deliberada: las skills de Anthropic deben ser bundles autocontenidos y
portables (un usuario debe poder copiar la carpeta del skill a otro
proyecto sin enlaces rotos).

**Si arreglas un bug en `_common.py` u `odoo_client.py` aqui, sincroniza
el cambio a las otras dos skills hermanas**. Util:

```bash
diff -ru \
  ../odoo-accounting-es/scripts/_common.py \
  scripts/_common.py
```

## Cobertura objetivo

- 100% de funciones puras testeables.
- 0% de scripts CLI (cobertura via pruebas de integracion fuera de pytest).
