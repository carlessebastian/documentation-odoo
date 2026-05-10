# git-aggregator (`gitaggregate`)

## Que es

`git-aggregator` es la herramienta que doodba (y muchos integradores
OCA) usan para mantener un conjunto de repos git sincronizado a un
estado declarativo descrito en `repos.yaml`. Permite:

- Clonar repos con un solo comando.
- Hacer merge de varias ramas/PRs en una "branch local consolidada".
- Pinear a SHA o a branch.
- Filtrar (`shallow`, `depth`).

Repo upstream: `acsone/git-aggregator` (PyPI: `git-aggregator`).

## Formato `repos.yaml`

```yaml
custom/src/server-tools:
  defaults:
    depth: 1
    shallow: true
  remotes:
    oca: https://github.com/OCA/server-tools.git
    fork: [email protected]:ikigai/server-tools.git
  merges:
    - oca 19.0
    - fork ikigai/19.0/feature_X
  target: oca 19.0    # rama final commiteada localmente
```

| Clave | Significado |
|-------|-------------|
| `defaults` | Aplicado a todos los remotes (depth, shallow). |
| `remotes` | Map `<alias>: <url>`. |
| `merges` | Lista en orden de merge: `<remote_alias> <ref>`. `ref` puede ser branch, tag, sha o `refs/pull/N/head`. |
| `target` | Rama destino donde se materializan los merges. |
| `defaults.depth: 1` | Shallow clone (mas rapido, mas pequeno). |
| `fetch_all` | Si True, fetcha todos los refs. |

## Pinning

| Como | Sintaxis | Cuando usar |
|------|----------|-------------|
| Branch flotante | `oca 19.0` | Dev/test; siempre el ultimo commit de `19.0`. |
| Tag | `oca v19.0.1.0.0` | Releases marcadas. |
| SHA | `oca a1b2c3d4...` | **Production** (reproducibilidad). |
| Pull request | `oca refs/pull/123/head` | Para probar fixes upstream antes de merge. |

**Recomendacion**: en produccion, pinear por SHA. Cuando sale un fix,
actualizar el SHA explicitamente en `repos.yaml`, commit, redeploy.

## Comandos

```bash
# Aplicar todo el repos.yaml (fetch + merge + checkout)
gitaggregate -c custom/src/repos.yaml

# Solo un proyecto (path)
gitaggregate -c custom/src/repos.yaml -d custom/src/l10n-spain

# Ver que haria sin tocar (parsed config + plan)
gitaggregate -c custom/src/repos.yaml --do-push false --show-closed-prs

# Push de los targets a sus remotes (raro; no necesario en doodba)
gitaggregate -c custom/src/repos.yaml --push
```

doodba alias: `invoke git-aggregate` y `invoke img-build` (que ademas
rebuild a la imagen).

## Conflictos durante `gitaggregate`

Si dos remotes mergeados modifican las mismas lineas, el merge falla y
deja el repo en estado conflictivo. **gitaggregate aborta**, no commitea
parcialmente. Resolucion:

1. SSH al host, ir al directorio del repo conflictivo.
2. `git status` para ver los unmerged paths.
3. Resolver manualmente (edit + `git add`).
4. `git commit`.
5. Re-ejecutar `gitaggregate`.

Para evitar conflictos en doodba, se recomienda **un solo remote por
repo en produccion**, salvo casos puntuales con PRs upstream.

## Conjunto canonico de repos para Odoo 19 ES Community

```yaml
custom/src/account-financial-tools:
  remotes:
    oca: https://github.com/OCA/account-financial-tools.git
  merges: [oca 19.0]
  target: oca 19.0

custom/src/account-financial-reporting:
  remotes:
    oca: https://github.com/OCA/account-financial-reporting.git
  merges: [oca 19.0]
  target: oca 19.0

custom/src/bank-payment:
  remotes:
    oca: https://github.com/OCA/bank-payment.git
  merges: [oca 19.0]
  target: oca 19.0

custom/src/l10n-spain:
  remotes:
    oca: https://github.com/OCA/l10n-spain.git
  merges: [oca 19.0]
  target: oca 19.0

custom/src/server-auth:
  remotes:
    oca: https://github.com/OCA/server-auth.git
  merges: [oca 19.0]
  target: oca 19.0

custom/src/server-tools:
  remotes:
    oca: https://github.com/OCA/server-tools.git
  merges: [oca 19.0]
  target: oca 19.0

custom/src/server-ux:
  remotes:
    oca: https://github.com/OCA/server-ux.git
  merges: [oca 19.0]
  target: oca 19.0

custom/src/web:
  remotes:
    oca: https://github.com/OCA/web.git
  merges: [oca 19.0]
  target: oca 19.0

custom/src/queue:
  remotes:
    oca: https://github.com/OCA/queue.git
  merges: [oca 19.0]
  target: oca 19.0
```

Para Veri*Factu / TicketBAI / SII en Community, anyadir `l10n-spain`
(que ya cubre la mayoria) y opcionalmente repos custom segun lo que
falte.

## Caveat sobre OCA en 19.0 (mayo 2026)

Algunos modulos OCA todavia no estan migrados a 19.0 al momento de
escribir este skill. Antes de instalar:

1. `git -C custom/src/<repo> branch --show-current` -> debe ser `19.0`.
2. `cat custom/src/<repo>/<modulo>/__manifest__.py | grep -E "version|installable"`.
3. Si `installable: False`, el modulo aun no esta listo para 19.

Si un modulo OCA esperado no existe en `19.0`, posibilidades:

- Esta migracion en curso (PR abierto upstream): esperar o portar
  manualmente con `oca-port`.
- El modulo se ha consolidado en otro modulo o en core.
- El modulo se ha deprecado.
