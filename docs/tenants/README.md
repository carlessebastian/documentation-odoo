# docs/tenants/

Un perfil por despliegue. **El agente es multi-tenant**: el código de
las skills (en `.claude/skills/`) es agnóstico al cliente; los datos
específicos de cada despliegue viven aquí.

## Cómo elegir el tenant activo

```bash
# en .env
ODOO_AGENT_TENANT=inpr3mium
```

Al inicio de cada sesión que toque la instancia Odoo, el agente lee
`docs/tenants/$ODOO_AGENT_TENANT/profile.yaml` para conocer la sociedad
activa, su NIF, plan contable, EDI stack, módulos esperados, etc.

Si `ODOO_AGENT_TENANT` no está definido o el directorio no existe,
`/onboard` falla en rojo y pide configurar.

## Layout

```
docs/tenants/
├── README.md              # este archivo
├── _template/             # plantilla; copiar para nuevos tenants
│   ├── README.md
│   ├── profile.yaml.example
│   └── migration-plan.md.example
├── inpr3mium/             # tenant real activo
│   ├── README.md
│   ├── profile.yaml       # NIF, plan, diarios, FPs, módulos
│   └── migration-from-holded.md
└── (futuros)              # p.ej. fedefarma/, ...
```

## Crear un tenant nuevo

```bash
TENANT=miempresa
cp -r docs/tenants/_template docs/tenants/$TENANT
mv docs/tenants/$TENANT/profile.yaml.example \
   docs/tenants/$TENANT/profile.yaml
mv docs/tenants/$TENANT/migration-plan.md.example \
   docs/tenants/$TENANT/migration-plan.md
# editar profile.yaml con datos reales
echo "ODOO_AGENT_TENANT=$TENANT" >> .env
```

Luego `claude` en el repo y `/onboard` para validar.

## Convenciones

- **Slug**: minúsculas, sin espacios ni acentos, `[a-z0-9_-]+`. Es la
  clave que usan tanto el directorio como la env var.
- **`profile.yaml`** es la fuente de verdad de los datos del tenant
  para el agente. No duplicar esos datos en otros archivos del repo.
- **Datos sensibles** (API keys, contraseñas, certificados) **NO**
  van aquí — van en `.env` o en un gestor de secretos. El
  `profile.yaml` puede versionarse en git (asegúrate primero de que
  el repo es privado o de que los VATs / nombres no son confidenciales
  para el cliente).
- **Notas operativas** del tenant (bitácoras de cierres, incidencias,
  decisiones puntuales) van también dentro de su directorio en
  archivos `*.md` adicionales.
