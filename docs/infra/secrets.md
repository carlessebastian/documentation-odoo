# Gestión de secretos

Política de qué se versiona, qué no, y dónde vive cada tipo de
secreto del proyecto `odoo-agent`.

## Tipos de secretos

| Secreto | Dónde vive | ¿Versiona? |
|---------|-----------|-----------|
| API key del bot Odoo (`ODOO_API_KEY`) | `.env` local | ❌ NO (`.gitignore`) |
| Master password de Odoo (gestor de DBs) | `odoo.conf` del proyecto doodba | ❌ NO |
| SSH key para `DOODBA_SSH_HOST` | `~/.ssh/` del operador | ❌ NO |
| Contraseñas de PostgreSQL | env vars del compose o secret manager | ❌ NO |
| Certificado digital AEAT (FNMT/Camerfirma) | dentro del filestore de Odoo + copia maestra fuera del repo | ❌ NO |
| Credenciales SMTP corporativo | `odoo.conf` o secret manager | ❌ NO |
| Tokens de la API de Holded (para ETL) | `.env` con prefijo `HOLDED_*` | ❌ NO |

| No-secreto | Dónde vive | ¿Versiona? |
|-----------|-----------|-----------|
| `profile.yaml` del tenant (NIF, dirección, módulos) | `docs/tenants/<slug>/` | ✅ SÍ |
| `.env.example` (plantilla con valores de ejemplo) | raíz del repo | ✅ SÍ |
| Cualquier dato del [registro mercantil](https://www.registradores.org/) | repo o docs | ✅ SÍ |

## `.gitignore` aplicable

Confirmado en `.gitignore` del repo:

```
.env
.env.*
!.env.example
```

Si commiteas un secreto por error, **no basta con `git rm`**: rota el
secreto. Para Odoo: regenera la API key. Para AEAT: revoca y reemite
el certificado.

## Copia maestra de secretos

Mantén una copia maestra fuera del proyecto en un gestor:

- **1Password / Bitwarden / KeePassXC** para credenciales del operador.
- **GCP Secret Manager** (en Modo B) para los secretos del host.
- Backup offline encriptado del certificado digital AEAT (LL `.p12`
  con contraseña fuerte).

## Rotación

Recomendado:

- API keys de Odoo: rotar tras incidente o cambio de operador. No
  tienen expiración propia; tú decides.
- Certificado digital AEAT: válido 4 años (FNMT) o 3 (Camerfirma).
  **Apuntar fecha de expiración** en `docs/tenants/inpr3mium/` y
  poner recordatorio 60 días antes.
- Contraseñas: rotar tras cambio de personal o tras 1 año.

## Acceso al certificado AEAT desde Odoo

Para SII / Veri\*Factu / FacturaE, Odoo necesita el certificado
digital de la sociedad cargado vía:

- UI: Settings → Companies → editar → pestaña "Edición Electrónica"
  (depende del módulo).
- Archivo: el `.p12` se sube a Odoo (queda en el filestore, no en el
  repo).

**Nunca** subir el `.p12` ni la contraseña del certificado al repo,
ni siquiera en docs/tenants/. La copia maestra del `.p12` debe vivir
en el gestor de contraseñas con la passphrase como secreto separado.
