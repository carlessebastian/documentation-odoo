# Tests del skill odoo-accounting-es

Suite pytest sobre las funciones puras del skill (validacion NIF/CIF/NIE,
parsers de periodos, helpers comunes). NO requieren conexion Odoo ni
variables de entorno.

## Ejecutar

Desde la raiz del skill:

```bash
cd .claude/skills/odoo-accounting-es
python3 -m pytest tests/ -v
```

O con `uv` si esta disponible:

```bash
uv run pytest tests/ -v
```

## Cobertura actual

| Modulo | Tests | Cubre |
|--------|-------|-------|
| `test_common.py` | 11 | `require_env`, `format_amount`, `retry_on_network` (incluido NO retry de errores de negocio) |
| `test_verify_es_compliance.py` | 28 | `_clean_vat`, `validate_dni`, `validate_nie`, `validate_cif`, `validate_es_vat` con fixtures validas e invalidas |
| `test_odoo_client_helpers.py` | 4 | `_clean_fault` (parseo de mensajes UserError) |
| `test_aged_balance.py` | 11 | Funcion `_bucket` con todos los rangos de antiguedad |
| `test_period_parsing.py` | 17 | Parsers de "2026Q1", "2026-05", "2026" en `run_aeat_report`, `vat_book`, `recurring_invoice` |

Total: ~71 assertions sobre logica que NO depende de Odoo.

## Que NO cubre

- Llamadas RPC reales (`OdooClient.call`, `search_read`, etc.) - requieren
  instancia Odoo o mocks complejos.
- Wizards (`account.payment.register`, `account.move.reversal`) - solo
  testables E2E contra Odoo.
- EDI SII / Verifactu / FacturaE - requieren AEAT sandbox.

Para tests de integracion E2E ver el plan futuro o ejecutar manualmente
con env vars contra una instancia de prueba.

## Anadir nuevos tests

Convencion:
- Una clase `TestXxx` por funcion publica.
- Usar `@pytest.mark.parametrize` para multiples fixtures.
- Tests rapidos (< 100 ms cada uno); evitar I/O.
- Si necesitas mockear `requests`, usa `monkeypatch.setattr` o
  `unittest.mock.patch`.

## Dependencias

Solo `pytest`. No requiere `requests` (los modulos del skill lo importan
de forma diferida).

```bash
pip install pytest  # o: uv add --dev pytest
```
