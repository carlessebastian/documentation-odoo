# Odoo 19 admin skills (Ikigai Magi)

This directory hosts three cooperating Claude Agent Skills for managing
a self-hosted Odoo 19 Community deployment for the holding **Ikigai
Magi S.L.** and its subsidiaries (Camomilla Blu, Kura Terra,
Omotenashi Hama). Spanish/Catalan locale, doodba (Tecnativa) Docker
deployment.

## Skills

| Skill | Domain | Triggers on | Tools |
|-------|--------|-------------|-------|
| `odoo-accounting-es` | Daily accounting and tax filing | factura, asiento, conciliacion, modelo 303, SII, Veri*Factu | RPC, MCP |
| `odoo-functional-admin` | Users, groups, ACLs, multi-company, journals, sequences, fiscal positions, ir.cron, settings | crear usuario, regla de registro, nueva empresa, diario nuevo, posicion fiscal, ir.cron | RPC, MCP |
| `odoo-module-admin` | Module install/upgrade/uninstall, addons.yaml, repos.yaml, gitaggregate, doodba, OpenUpgrade | instalar modulo, OCA, addons_path, doodba, migrar version | RPC, **SSH + Docker** |

The split is deliberate:

1. **Trigger precision**: each skill's `description:` includes
   `DO NOT trigger for ... -> use skill X` clauses pointing at siblings.
   Without that, the broad term "Odoo" would match all three.
2. **Privilege isolation**: only `odoo-module-admin` declares
   `Bash(ssh:*)` / `Bash(docker:*)` in `allowed-tools`. Functional and
   accounting skills cannot SSH into production.
3. **Per-domain references**: each skill keeps its detailed knowledge
   in `references/*.md` and stays under the ~500-line ceiling for
   `SKILL.md`.

## How they cooperate

The skills are independent but cross-reference each other in their
SKILL.md "Skills hermanos" sections. Claude routes between them based
on the user's request. Common patterns:

- **"Instala l10n_es_aeat_mod303 y configura los permisos"** -> module-admin
  installs; functional-admin assigns groups to the relevant users.
- **"Crea Kura Terra como filial y haz su primera factura"** ->
  functional-admin runs `subsidiary_bootstrap.py` (company + journals +
  fiscal positions); accounting-es posts the invoice afterwards.
- **"Migra de Odoo 18 a 19"** -> module-admin runs `openupgrade_run.py`
  on a staging DB; once green, the user does the cutover manually.

## Shared environment

All three skills consume:

| Variable | Used by | Purpose |
|----------|---------|---------|
| `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` | All three | RPC / JSON-2 auth |
| `ODOO_FORCE_XMLRPC` | All three | Optional XML-RPC fallback |
| `DOODBA_SSH_HOST`, `DOODBA_PROJECT_DIR` | module-admin only | SSH target |
| `DOODBA_COMPOSE_SERVICE`, `DOODBA_DB_NAME` | module-admin only | docker compose service name + DB |
| `OPENUPGRADE_PATH` | module-admin (`openupgrade_run.py` only) | OpenUpgrade clone path on host |

## Duplicated infrastructure

`scripts/_common.py`, `scripts/odoo_client.py`, `tests/conftest.py`,
`tests/test_common.py`, `tests/test_odoo_client_helpers.py` are
**verbatim duplicates** across the three skills. This is intentional:
Anthropic skills are designed as self-contained portable bundles; a
user must be able to copy a skill directory to another project and
have it work without external links.

**Bug-fix policy**: when fixing `_common.py` or `odoo_client.py` in
one skill, sync the change to the other two. A quick check:

```bash
diff -ru \
  .claude/skills/odoo-accounting-es/scripts/_common.py \
  .claude/skills/odoo-functional-admin/scripts/_common.py
diff -ru \
  .claude/skills/odoo-accounting-es/scripts/_common.py \
  .claude/skills/odoo-module-admin/scripts/_common.py
```

## Running tests

Per-skill, since each `tests/conftest.py` injects only its own
`scripts/` into `sys.path`:

```bash
for skill in odoo-accounting-es odoo-functional-admin odoo-module-admin; do
  echo "=== $skill ==="
  (cd .claude/skills/$skill && python3 -m pytest tests/ -q)
done
```

## Bootstrap runbook: greenfield Ikigai deployment

This is the canonical sequence to bootstrap a fresh deployment, using
all three skills. **Each step is run by the corresponding skill**;
Claude handles the routing automatically when the user says "set up
Ikigai from scratch".

### 0. Prerequisites (manual, outside the skills)

- doodba project initialized via `copier copy` from
  `Tecnativa/doodba-copier-template`.
- `docker compose up -d` running.
- A bot user (e.g. `bot.admin`) with API key, and SSH key pushed to
  `DOODBA_SSH_HOST`. Env vars set.
- Empty Odoo DB created (no chart_template installed yet).

### 1. Install OCA repos and base modules — `odoo-module-admin`

```bash
# Configure repos.yaml + addons.yaml (use assets/ as templates)
# Then:
.claude/skills/odoo-module-admin/scripts/repos_aggregate.sh apply
.claude/skills/odoo-module-admin/scripts/addons_pull.sh

# Install l10n_es and AEAT modules
.claude/skills/odoo-module-admin/scripts/module_install.py \
  --names l10n_es,l10n_es_aeat_mod303,l10n_es_aeat_mod347,\
l10n_es_aeat_mod349,l10n_es_aeat_mod390,\
l10n_es_aeat_sii_oca,l10n_es_facturae

# OCA tooling for accounting reports
.claude/skills/odoo-module-admin/scripts/module_install.py \
  --names mis_builder,account_financial_report,\
account_payment_mode,account_banking_sepa_direct_debit,\
auditlog,queue_job
```

### 2. Languages and base settings — `odoo-functional-admin`

```bash
.claude/skills/odoo-functional-admin/scripts/language_install.py \
  --langs es_ES,ca_ES,it_IT --activate

.claude/skills/odoo-functional-admin/scripts/settings_param.py \
  set web.base.url https://erp.ikigaimagi.com
```

### 3. Holding company — `odoo-functional-admin`

```bash
# Holding (parent)
.claude/skills/odoo-functional-admin/scripts/subsidiary_bootstrap.py \
  --name "Ikigai Magi S.L." --vat ESB12345678 \
  --chart-template l10n_es.l10n_es_full \
  --ensure-years 2026,2027

# Subsidiaries
.claude/skills/odoo-functional-admin/scripts/subsidiary_bootstrap.py \
  --name "Camomilla Blu S.L." --vat ESB22222222 \
  --parent-vat ESB12345678 \
  --ensure-years 2026,2027

.claude/skills/odoo-functional-admin/scripts/subsidiary_bootstrap.py \
  --name "Kura Terra S.L." --vat ESB33333333 \
  --parent-vat ESB12345678 \
  --ensure-years 2026,2027
```

### 4. Bot users and API keys — `odoo-functional-admin`

```bash
# Bot for accounting automation (limited scope)
.claude/skills/odoo-functional-admin/scripts/user_provision.py \
  --login bot.contable@... --name "Bot Contable" \
  --groups base.group_user,account.group_account_manager,base.group_multi_company \
  --company-vats ESB12345678,ESB22222222,ESB33333333

.claude/skills/odoo-functional-admin/scripts/apikey_provision.py \
  --login bot.contable@... --label automation
```

### 5. Multi-company global rules — `odoo-functional-admin`

```bash
.claude/skills/odoo-functional-admin/scripts/record_rule_create.py \
  --name "res.partner: company" \
  --model res.partner \
  --groups "" \
  --domain "['|', ('company_id','=',False), ('company_id','in',company_ids)]" \
  --force
```

### 6. Smoke test with first invoice — `odoo-accounting-es`

Use the existing accounting skill scripts to post a test invoice and
trigger SII/Veri*Factu pipelines.

## Versioning

- Each skill's `metadata.version` follows semver-ish.
- The trio is versioned together via git tags on this repo.
- When a breaking change lands in `_common.py` or `odoo_client.py`,
  bump minor in all three skills simultaneously.

## See also

- `odoo-accounting-es/SKILL.md` — daily accounting operations.
- `odoo-functional-admin/SKILL.md` — admin configuration (no SSH).
- `odoo-module-admin/SKILL.md` — module lifecycle (SSH + Docker).
