# Doodba bootstrap — provisión del entorno Odoo 19

Runbook para arrancar una instancia Odoo 19 Community con
[doodba](https://github.com/Tecnativa/doodba-copier-template) (Tecnativa).
**Manual.** El agente no provisiona infraestructura — solo opera
sobre una instancia ya existente.

Dos modos cubiertos:

- **[Modo A — Docker local](#modo-a--docker-local-mac-o-linux)**:
  para tests, desarrollo y primer arranque del agente. Sin TLS, sin
  dominio público, todo en `localhost:8069`.
- **[Modo B — gcloud Compute Engine](#modo-b--gcloud-compute-engine)**:
  producción. VM en GCP, Docker, dominio
  `erp.inpr3mium.com` con Let's Encrypt, backups y firewall.

Recomendación: arranca primero en Modo A para validar el agente
contra una instancia real (aunque sea local). Pasa a Modo B cuando
todo esté en verde y haya consenso para producción.

---

## Prerrequisitos comunes

- **Git** con acceso a GitHub.
- **Python 3.10+** + pipx (para `copier` y `git-aggregator`).
- **Docker** y **Docker Compose v2** (>= 2.20).
- **Odoo 19 Community** repo accesible (público en `odoo/odoo`).
- Un editor con sintaxis YAML.

Instalar copier + git-aggregator (una sola vez por máquina):

```bash
pipx install copier
pipx install git-aggregator
```

---

## Modo A — Docker local (Mac o Linux)

> ⚠️ **Esta sección está superada por
> [`local-deployment-guide.md`](local-deployment-guide.md)**, que
> recoge las correcciones aplicadas tras el primer despliegue real
> (2026-05-10). Sigue la guía corregida para evitar 10 gotchas
> conocidas (entre otros: `.empty` placeholder bug en macOS, wizard
> web 500, creación de DB obligatoriamente por CLI, `groups_id` →
> `group_ids` en Odoo 19, API key 90-day cap, bug `_json2` del
> cliente). Los pasos abajo son la versión teórica original; los
> dejo como referencia hasta que `local-deployment-guide.md`
> demuestre tener cobertura completa para varios despliegues.

Objetivo: levantar Odoo 19 + PostgreSQL en tu máquina local con un
proyecto doodba listo para que el agente conecte vía RPC en
`http://localhost:19069` (no 8069 — ver guía corregida).

### A.1 Crear el proyecto doodba

Elige una ubicación fuera del repo `odoo-agent` (no quieres mezclar
el código del agente con la instancia operativa):

```bash
# Sugerencia: ~/Documents/code/odoo-instances/inpr3mium-local
mkdir -p ~/Documents/code/odoo-instances
cd ~/Documents/code/odoo-instances

copier copy --trust gh:Tecnativa/doodba-copier-template inpr3mium-local
cd inpr3mium-local
```

Copier hará preguntas. Respuestas recomendadas para Modo A:

| Pregunta de copier | Respuesta sugerida (local) |
|--------------------|----------------------------|
| Project name | `inpr3mium-local` |
| Organization GitHub | (vacío o tu user) |
| Odoo version | `19.0` |
| Project license | `OEEL-1` o equivalente (no relevante en local) |
| Domain | `localhost` |
| Production domain | (vacío) |
| Test domain | (vacío) |
| Backup type | `none` (no backups en local) |
| Smtp relay | `none` |
| Postgres version | `16-alpine` |
| Odoo proxy mode | `false` (no traefik en local) |
| Use Sentry / Logsdash | `false` |

> Si Copier no acepta `none` para algún campo, deja el default —
> luego ignoras ese servicio.

### A.2 Configurar `repos.yaml` y `addons.yaml`

Las plantillas del agente están en
`.claude/skills/odoo-module-admin/assets/repos.yaml.example`. Copia su
contenido como base:

```bash
cd ~/Documents/code/odoo-instances/inpr3mium-local
cp ~/Documents/code/odoo-agent/.claude/skills/odoo-module-admin/assets/repos.yaml.example \
   odoo/custom/src/repos.yaml
```

Edita `odoo/custom/src/repos.yaml` y pinéalo a `19.0` para los repos
listados en `profile.yaml.oca_repos` de inpr3mium:

- `l10n-spain`
- `server-tools`
- `server-auth`
- `account-financial-tools`
- `account-financial-reporting`
- `web`
- `queue`
- `bank-payment`

Igual con `addons.yaml`:

```bash
cp ~/Documents/code/odoo-agent/.claude/skills/odoo-module-admin/assets/addons.yaml.example \
   odoo/custom/src/addons.yaml
```

Edítalo dejando solo:

```yaml
ONLY:
  ENVIRONMENT:
    - devel
    - test
    - prod

server-tools:
  - "*"

l10n-spain:
  - l10n_es_aeat_mod303
  - l10n_es_aeat_mod347
  - l10n_es_aeat_mod349
  - l10n_es_aeat_mod390
  - l10n_es_aeat_mod111
  - l10n_es_aeat_mod115
  - l10n_es_aeat_mod232
  - l10n_es_aeat_sii_oca
  - l10n_es_verifactu_oca
  - l10n_es_facturae

account-financial-tools:
  - "*"

account-financial-reporting:
  - mis_builder
  - account_financial_report

bank-payment:
  - account_payment_mode
  - account_banking_sepa_direct_debit
  - account_banking_sepa_credit_transfer

queue:
  - queue_job
```

(Los `"*"` activan todos los addons del repo; si quieres ser más
estricto pones la lista explícita.)

### A.3 Sincronizar repos OCA con git-aggregator

```bash
cd odoo/custom/src
gitaggregate -c repos.yaml -e
```

Tarda 5-15 min la primera vez (clona ~8 repos OCA).

Verifica:

```bash
ls -1 .   # debe haber server-tools/, l10n-spain/, etc.
```

### A.4 Arrancar el stack

Volver a la raíz del proyecto:

```bash
cd ~/Documents/code/odoo-instances/inpr3mium-local

# Construir las imágenes
docker compose build odoo

# Levantar todo (postgres + odoo)
docker compose up -d
```

Verifica:

```bash
docker compose ps
docker compose logs -f odoo --tail=100
```

Espera a ver `HTTP service (werkzeug) running on ...` o equivalente.
La primera vez suele tardar 30-60 segundos en estar listo.

### A.5 Crear la base de datos

Abre `http://localhost:8069/web/database/manager` en el navegador y
usa el wizard:

- **Master Password**: la del `odoo.conf` (por defecto `admin` en
  doodba dev — cámbiala antes de exponer).
- **Database Name**: `inpr3mium_dev` (debe coincidir con `ODOO_DB`
  en `.env` del agente).
- **Email**: cualquiera (será el admin temporal — luego creas el bot).
- **Password**: cualquier cosa.
- **Language**: Spanish (es_ES).
- **Country**: Spain.
- **Demo data**: ❌ NO marcar (queremos DB limpia).

Click **Create database**. Tras 1-2 minutos estará lista.

### A.6 Crear el bot user para el agente

Ya dentro de Odoo (logueado como admin), seguir el paso 1 de
[`docs/onboarding.md`](../onboarding.md):

1. Settings → Users & Companies → Users → Create.
2. Name: `Bot Contable`.
3. Login: `bot.contable@inpr3mium.com` (el del `profile.yaml`).
4. Grupos: `Internal User`, `Multi Companies`. (Los grupos de
   `Accounting Manager` aparecerán cuando se instalen los módulos
   `account*`. De momento déjalo en básicos; el agente añadirá los
   contables después.)
5. Save.
6. Click sobre el usuario → pestaña `API Keys` → New API Key →
   description "agent-local" → copia el secreto.

### A.7 Configurar el `.env` del agente

```bash
cd ~/Documents/code/odoo-agent
cp .env.example .env
```

Editar `.env`:

```bash
ODOO_AGENT_TENANT=inpr3mium

ODOO_URL=http://localhost:8069
ODOO_DB=inpr3mium_dev
ODOO_USER=bot.contable@inpr3mium.com
ODOO_API_KEY=<el secreto del paso A.6>

# Modo A: el agente y doodba están en la misma máquina; los scripts de
# odoo-module-admin pueden ejecutar docker exec directo en lugar de SSH.
# Configurar como SSH a localhost para reusar la lógica de ssh_runner.py
# (alternativa: omitir y operar solo con RPC).
DOODBA_SSH_HOST=localhost
DOODBA_PROJECT_DIR=/Users/<tu_user>/Documents/code/odoo-instances/inpr3mium-local
DOODBA_COMPOSE_SERVICE=odoo
DOODBA_DB_NAME=inpr3mium_dev
```

> Nota sobre SSH a localhost: si quieres que `odoo-module-admin`
> funcione contra el Docker local, asegúrate de tener el SSH server de
> macOS habilitado (`System Settings → General → Sharing → Remote
> Login`) y tu propia clave en `~/.ssh/authorized_keys`. Como
> alternativa más simple, puedes ejecutar los scripts directamente
> sin la indirección SSH durante Modo A.

### A.8 Verificar con `/onboard`

```bash
cd ~/Documents/code/odoo-agent
claude
> /onboard
```

Esperado en este punto:
- Profile leído ✓
- Variables RPC ✓
- RPC reachable ✓
- API key válida ✓
- Bot ≠ admin ✓
- Empresa activa ⚠️ (es la company por defecto del wizard, no la de
  inpr3mium — se arregla en Bloque C).
- Módulos esperados ❌ (DB recién creada, sin OCA — esperado;
  Bloque C los instala).
- SSH a doodba ✓ o N/A.
- Tests offline ✓.

Si llegas aquí con la mayoría en verde/amarillo, **Modo A
completado**.

---

## Modo B — gcloud Compute Engine

Producción futura. **No ejecutar todavía** — esta sección es
referencia para cuando se decida pasar a producción.

### B.1 Visión general de la arquitectura

```
[ Internet ]
    |
    | https://erp.inpr3mium.com (Let's Encrypt)
    v
[ Cloud DNS ] ── A record ──> [ Compute Engine VM ]
                                    |
                                    +-- Docker
                                    |     +-- traefik (reverse proxy + TLS)
                                    |     +-- odoo (doodba 19.0)
                                    |     +-- postgres 16
                                    |
                                    +-- Cloud SQL backup hourly (opcional)
                                    +-- gcloud ops agent (logs + metrics)
```

Decisiones de tamaño orientativas para inpr3mium (sociedad pequeña,
volumen de facturación moderado):

- VM: `e2-small` (2 vCPU shared, 2 GB RAM) o `e2-medium` (2 vCPU
  shared, 4 GB RAM) — empezar por `e2-small`, escalar si hay
  problemas de rendimiento. ~12-25 €/mes.
- Disk: `pd-balanced` 30 GB (suficiente para DB + filestore en una
  sociedad pequeña los primeros años).
- Región: `europe-southwest1` (Madrid) por latencia y RGPD.

### B.2 Pasos previos

1. Proyecto GCP creado y facturación activa.
2. CLI `gcloud` instalada y autenticada.
3. Dominio `inpr3mium.com` con DNS administrable (Cloud DNS o
   tu registrar). Crear registro A `erp.inpr3mium.com` apuntando a
   la IP estática reservada.
4. Habilitar APIs: Compute Engine, Cloud DNS, Secret Manager.

### B.3 Provisión de la VM (esquema, no detalle)

```bash
# IP estática
gcloud compute addresses create erp-inpr3mium-ip \
  --region=europe-southwest1

# VM
gcloud compute instances create erp-inpr3mium \
  --zone=europe-southwest1-b \
  --machine-type=e2-small \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=30GB \
  --boot-disk-type=pd-balanced \
  --address=erp-inpr3mium-ip \
  --tags=http-server,https-server \
  --metadata=enable-oslogin=TRUE
```

### B.4 Setup del host

SSH al host y:

1. Instalar Docker + Docker Compose v2.
2. Configurar firewall: solo 22 (SSH desde IP del operador), 80, 443.
3. Crear usuario no-root para doodba con su propia clave.
4. `sudo usermod -aG docker $USER`.

### B.5 Proyecto doodba en producción

Mismos pasos que Modo A.1-A.3, pero con respuestas de copier:

| Pregunta de copier | Respuesta sugerida (prod) |
|--------------------|----------------------------|
| Domain | `erp.inpr3mium.com` |
| Production domain | `erp.inpr3mium.com` |
| Backup type | `borgmatic` o `s3` (a definir) |
| Smtp relay | configurar SMTP corporativo |
| Odoo proxy mode | `true` (traefik delante) |

### B.6 Traefik + Let's Encrypt

doodba-copier-template incluye traefik con configuración para
Let's Encrypt automático cuando `Odoo proxy mode = true`. Verificar
que:

- El servicio `traefik` está en el `docker-compose.yml` resultante.
- Los certificados se persisten en un volumen.
- Email de Let's Encrypt apunta a una dirección monitorizada.

### B.7 Backups

A definir según presupuesto y RPO/RTO. Opciones:

- **Borgmatic** dentro del propio host hacia un bucket GCS (más
  barato, requiere configurar key rotation).
- **Cloud SQL** en lugar de PostgreSQL en contenedor (más caro pero
  con backups automáticos gestionados).

Decisión diferida; documentar en este archivo cuando se tome.

### B.8 Migración Modo A → Modo B

Cuando estés listo para promover Modo A a Modo B:

1. `pg_dump` de `inpr3mium_dev` desde Modo A.
2. Copiar el filestore de `inpr3mium-local` a la VM.
3. Restaurar dump en Postgres del Modo B.
4. Actualizar `.env` del agente apuntando a la VM
   (`ODOO_URL=https://erp.inpr3mium.com`,
   `DOODBA_SSH_HOST=user@erp-inpr3mium`).
5. Ejecutar `/onboard` y validar.

---

## Bitácora

Cuando ejecutes este runbook contra inpr3mium real, **deja constancia
en `docs/tenants/inpr3mium/bootstrap-log.md`**:

- Fecha del provisioning.
- Modo (A o B), comandos relevantes ejecutados.
- Versiones (doodba template commit, odoo, postgres, OCA repos).
- Incidencias y cómo se resolvieron.

Esto permite a futuras sesiones del agente conocer el estado real
sin tener que inferirlo.
