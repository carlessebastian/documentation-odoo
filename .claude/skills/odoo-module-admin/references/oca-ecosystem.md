# Ecosistema OCA: feature -> repositorio

Cuando el usuario pide "un modulo para X", esta tabla mapea features a
repositorios OCA y modulos concretos. Verifica siempre la disponibilidad
en rama `19.0` antes de recomendar (algunos siguen sin migrar a mayo
2026).

## Referencia rapida (ES Community)

### Localizacion espanola

| Feature | Repo | Modulo(s) |
|---------|------|-----------|
| Plan contable PGCE 2008 | core | `l10n_es` |
| Modelo 303 (IVA trimestral) | OCA/l10n-spain | `l10n_es_aeat_mod303` |
| Modelo 347 (operaciones >3000 EUR) | OCA/l10n-spain | `l10n_es_aeat_mod347` |
| Modelo 349 (intra-UE) | OCA/l10n-spain | `l10n_es_aeat_mod349` |
| Modelo 390 (IVA anual) | OCA/l10n-spain | `l10n_es_aeat_mod390` |
| Modelo 111/115/130 | OCA/l10n-spain | `l10n_es_aeat_mod111`, `l10n_es_aeat_mod115`, `l10n_es_aeat_mod130` |
| Modelo 369 (OSS) | OCA/l10n-spain | `l10n_es_aeat_mod369` |
| Modelo 232 (operaciones vinculadas) | OCA/l10n-spain | `l10n_es_aeat_mod232` |
| Modelo 720 (bienes en exterior) | OCA/l10n-spain | `l10n_es_aeat_mod720` |
| SII (envio en tiempo real) | OCA/l10n-spain | `l10n_es_aeat_sii_oca` |
| Veri*Factu (pendiente migracion 19.0) | OCA/l10n-spain | `l10n_es_verifactu_oca` (verificar) |
| TicketBAI (Pais Vasco) | OCA/l10n-spain | `l10n_es_ticketbai_*` |
| Facturae (FACe) | OCA/l10n-spain | `l10n_es_facturae` |
| Validacion NIF/CIF/NIE | OCA/l10n-spain | `l10n_es_partner` |
| Validacion VAT VIES UE | OCA/community-data-files | `partner_vat_check_vies` |
| Recargo Equivalencia | core (l10n_es) | tax codes incluidos |
| IVA de Caja | core (l10n_es) | tax codes incluidos |
| IGIC (Canarias) | OCA/l10n-spain-igic | `l10n_es_igic` (verificar 19.0) |

### Cuentas, finanzas, reporting

| Feature | Repo | Modulo(s) |
|---------|------|-----------|
| Cuadro financiero personalizable | OCA/account-financial-reporting | `account_financial_report` |
| Reporting con formula (BPC-style) | OCA/account-financial-reporting | `mis_builder`, `mis_builder_budget` |
| VAT Book / Libro IVA | OCA/account-financial-reporting | `account_vat_period_end_statement` |
| Lock dates extendido | OCA/account-financial-tools | `account_lock_date_update` |
| Asientos automaticos (auto-post) | OCA/account-financial-tools | `account_move_auto_post` |
| Cancel posted invoices (controlado) | OCA/account-invoicing | `account_invoice_cancel_paid` |
| Numerar facturas por rango (anual) | core (`ir.sequence.date_range`) | sin modulo extra |
| Tax balance / IVA balance | OCA/account-financial-reporting | `account_tax_balance` |
| Conciliacion bancaria avanzada | OCA/bank-statement-import | `account_bank_statement_import_*` |
| Conciliacion N43 (Espana) | OCA/l10n-spain | `l10n_es_account_bank_statement_import_n43` |
| CAMT.053 import | OCA/bank-statement-import | `account_bank_statement_import_camt` |
| CSV bank import | OCA/bank-statement-import | `account_bank_statement_import_csv` |

### Pagos / SEPA / domiciliacion

| Feature | Repo | Modulo(s) |
|---------|------|-----------|
| SEPA Direct Debit | OCA/bank-payment | `account_banking_sepa_direct_debit` |
| SEPA Credit Transfer | OCA/bank-payment | `account_banking_sepa_credit_transfer` |
| Mandatos SEPA | OCA/bank-payment | `account_banking_mandate` |
| Modos de pago | OCA/bank-payment | `account_payment_mode` |
| Pago por partner | OCA/bank-payment | `account_payment_partner` |
| Lotes de pago | OCA/bank-payment | `account_payment_order` |

### Multi-empresa / consolidacion / intercompany

| Feature | Repo | Modulo(s) |
|---------|------|-----------|
| Intercompany invoicing (OCA) | OCA/multi-company | `account_invoice_inter_company` |
| Intercompany sales/purchase | OCA/multi-company | `sale_order_inter_company`, `purchase_order_inter_company` |
| Consolidacion (Adhoc) | OCA/account-consolidation | `account_consolidation` |
| Multi-company defaults | OCA/multi-company | `multi_company_default` |

### Servidor / herramientas / DevOps

| Feature | Repo | Modulo(s) |
|---------|------|-----------|
| Audit log | OCA/server-tools | `auditlog` |
| Auto-update modulos | OCA/server-tools | `module_auto_update` |
| Email environment indicator | OCA/server-tools | `mail_environment` |
| Database cleanup | OCA/server-tools | `database_cleanup` |
| Technical user (sin email) | OCA/server-tools | `base_technical_user` |
| Mass editing | OCA/server-ux | `mass_editing` |
| Multi-step wizard | OCA/server-ux | `base_search_fuzzy` |
| Queue jobs (asincronos) | OCA/queue | `queue_job`, `queue_job_cron` |

### Auth / SSO / API

| Feature | Repo | Modulo(s) |
|---------|------|-----------|
| OAuth2 | OCA/server-auth | `auth_oauth_environment` |
| LDAP | OCA/server-auth | `auth_ldap_*` |
| SAML SSO | OCA/server-auth | `auth_saml` |
| Session timeout | OCA/server-auth | `auth_session_timeout` |
| API REST extendida | OCA/rest-framework | `base_rest`, `base_rest_auth_api_key` |
| Webhooks salientes | OCA/web-api | `endpoint`, `webhook` |

### UI / web

| Feature | Repo | Modulo(s) |
|---------|------|-----------|
| Web responsive (mobile) | OCA/web | `web_responsive` |
| Search avanzado | OCA/web | `web_search_with_and` |
| No bubble ("read-mode" UI) | OCA/web | `web_no_bubble` |
| Tree view editable | OCA/web | `web_tree_dynamic_colored_field` |
| Themes | OCA/themes | varios |

### CRM / Sales / Purchase / Inventory

| Feature | Repo | Modulo(s) |
|---------|------|-----------|
| CRM extendido | OCA/crm | varios |
| Sale ordering tweaks | OCA/sale-workflow | varios |
| Purchase tweaks | OCA/purchase-workflow | varios |
| Stock multi-warehouse | OCA/stock-logistics-warehouse | varios |

### HR / Payroll

| Feature | Repo | Modulo(s) |
|---------|------|-----------|
| HR extendido | OCA/hr | varios |
| Payroll Espana | OCA/l10n-spain (subset) | `l10n_es_payroll`, parcial |

## Como buscar un modulo concreto

1. **Web**: `https://github.com/OCA/<repo>/tree/19.0/<module_name>`
2. **Manifest**: `cat custom/src/<repo>/<module>/__manifest__.py`
3. **PyPI** (modulos OCA empaquetados): `pip search odoo-addon-<name>` (la
   organizacion OCA publica como `odoo-addon-*` en PyPI con version
   minor sincronizada).
4. **Listado completo**: `https://odoo-community.org/shop` filtrando por
   v19.

## Como decidir si un modulo OCA es production-ready en 19.0

Verificar en orden:

1. Existe `19.0/<module>/__manifest__.py` en el repo upstream.
2. `installable: True` en el manifest.
3. `version: '19.0.x.y.z'`.
4. Tiene tests (carpeta `tests/`).
5. Hay PRs cerrados recientemente sobre el modulo (signo de mantenimiento).
6. Issues abiertos sobre 19.0: revisar tracker.

Si alguno falla, usa `oca_port.py` para portar (si la version anterior
funciona) o queda pendiente del PR de migracion upstream.

## Pendientes en 19.0 al cierre de mayo 2026

Repos con migracion parcial a 19.0; verificar por modulo:

- `OCA/l10n-spain` — la mayoria de modulos AEAT migrados; algunos (e.g.
  `l10n_es_aeat_mod347` ha tenido bugs reportados en febrero 2026)
  pueden requerir un PR especifico.
- `OCA/account-consolidation` — migracion progresiva.
- `OCA/web` — `web_responsive` y los principales suelen estar OK.
- `OCA/queue` — `queue_job` esta migrado.

**Verificar siempre via `manifest_lint.py path/to/module`** antes de
prometer instalacion al usuario.
