# Odoo 19 admin skills

This directory hosts three cooperating Claude Agent Skills for managing
self-hosted Odoo 19 Community deployments. Spanish/Catalan locale,
doodba (Tecnativa) Docker deployment. The skills are **tenant-agnostic**
— per-tenant configuration lives in `docs/tenants/<slug>/profile.yaml`,
selected via the `ODOO_AGENT_TENANT` env var.

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
- **"Crea una filial nueva y haz su primera factura"** ->
  functional-admin runs `subsidiary_bootstrap.py` (company + journals +
  fiscal positions); accounting-es posts the invoice afterwards.
- **"Migra de Odoo 18 a 19"** -> module-admin runs `openupgrade_run.py`
  on a staging DB; once green, the user does the cutover manually.

## Shared environment

All three skills consume:

| Variable | Used by | Purpose |
|----------|---------|---------|
| `ODOO_AGENT_TENANT` | All three | Active tenant slug (subdir of `docs/tenants/`) |
| `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY` | All three | RPC / JSON-2 auth |
| `ODOO_FORCE_XMLRPC` | All three | Optional XML-RPC fallback |
| `DOODBA_SSH_HOST`, `DOODBA_PROJECT_DIR` | module-admin only | SSH target |
| `DOODBA_COMPOSE_SERVICE`, `DOODBA_DB_NAME` | module-admin only | docker compose service name + DB |
| `OPENUPGRADE_PATH` | module-admin (`openupgrade_run.py` only) | OpenUpgrade clone path on host |

Full template in repo-root `.env.example`.

## Reading the active tenant

At the start of any session that will touch the Odoo instance, read
`docs/tenants/$ODOO_AGENT_TENANT/profile.yaml` to know:

- The tenant's legal name(s) and VAT(s).
- Chart of accounts template (`l10n_es.l10n_es_full` vs `l10n_es_pymes`).
- EDI stack (`oca` vs `enterprise`).
- Journals, fiscal positions, taxes that apply (RE, IVA Caja, intra-UE).
- The list of `expected_modules` (used by `/onboard` to verify state).

Pass tenant data into scripts as CLI flags (`--name`, `--vat`,
`--chart-template`, etc.). The skills' scripts are designed to be
agnostic — the tenant profile is the user-supplied parameter source.

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

## Bootstrap runbook: greenfield deployment

This is the canonical sequence to bootstrap a fresh deployment, using
all three skills. **Each step is run by the corresponding skill**;
Claude handles the routing automatically when the user says something
like "set up `<TENANT>` from scratch".

Before starting, the agent reads
`docs/tenants/$ODOO_AGENT_TENANT/profile.yaml` and substitutes
placeholders below (`<TENANT_NAME>`, `<TENANT_VAT>`, etc.) with real
values. The narrative examples ("Acme S.L.", `ESB99999999`) are
**fictional** and only there to make the runbook concrete.

### 0. Prerequisites (manual, outside the skills)

- doodba project initialized via `copier copy` from
  `Tecnativa/doodba-copier-template`.
- `docker compose up -d` running.
- A bot user (e.g. `bot.admin`) with API key, and SSH key pushed to
  `DOODBA_SSH_HOST`. Env vars set in `.env`.
- Empty Odoo DB created (no chart_template installed yet).
- `docs/tenants/$ODOO_AGENT_TENANT/profile.yaml` filled in.
- `/onboard` reports green for connectivity (modules can still be
  pending — this runbook installs them).

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

The exact module list comes from `expected_modules` in the tenant
profile.

### 2. Languages and base settings — `odoo-functional-admin`

```bash
.claude/skills/odoo-functional-admin/scripts/language_install.py \
  --langs es_ES,ca_ES --activate

.claude/skills/odoo-functional-admin/scripts/settings_param.py \
  set web.base.url <ODOO_URL>
```

### 3. Company creation — `odoo-functional-admin`

For a **single-company** tenant:

```bash
.claude/skills/odoo-functional-admin/scripts/subsidiary_bootstrap.py \
  --name "<TENANT_NAME>" --vat <TENANT_VAT> \
  --chart-template <CHART_TEMPLATE> \
  --ensure-years 2026,2027
```

For a **holding + subsidiaries** tenant (example with fictional
"Acme Holdings S.L."):

```bash
# Holding (parent)
.claude/skills/odoo-functional-admin/scripts/subsidiary_bootstrap.py \
  --name "Acme Holdings S.L." --vat ESB99999999 \
  --chart-template l10n_es.l10n_es_full \
  --ensure-years 2026,2027

# Subsidiary
.claude/skills/odoo-functional-admin/scripts/subsidiary_bootstrap.py \
  --name "Acme Iberia S.L." --vat ESB88888888 \
  --parent-vat ESB99999999 \
  --ensure-years 2026,2027
```

### 4. Bot users and API keys — `odoo-functional-admin`

```bash
# Bot for accounting automation (limited scope)
.claude/skills/odoo-functional-admin/scripts/user_provision.py \
  --login bot.contable@<TENANT_DOMAIN> --name "Bot Contable" \
  --groups base.group_user,account.group_account_manager,base.group_multi_company \
  --company-vats <COMMA_SEPARATED_VATS>

.claude/skills/odoo-functional-admin/scripts/apikey_provision.py \
  --login bot.contable@<TENANT_DOMAIN> --label automation
```

### 5. Multi-company global rules — `odoo-functional-admin`

Even for single-company tenants, leave the rule in place so future
expansion is safe:

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
- `docs/tenants/README.md` — multi-tenant model and how to add a tenant.
