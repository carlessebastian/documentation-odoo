# Edition evaluation plan — Community vs Enterprise

> **Track paralelo a la migración Holded → Odoo**, NO la sustituye. La
> migración continúa sobre Community (Bloques C-D del `PLAN.md`); este
> documento define cómo evaluar Enterprise *sobre el resultado* de la
> migración para tomar decisión informada antes de que fedefarma
> obligue a comprometerse.

## 1. Contexto y drivers

**Situación**:

- inpr3mium en migración desde Holded sobre Odoo 19 **Community** +
  stack OCA (l10n-spain, server-tools, account-financial-reporting,
  bank-payment, etc.). Fundaciones financieras + loaders 0 + loader
  partners ya en producción local.
- fedefarma proyectado a **fin de 2026**, ~**50 usuarios**, multi-empresa,
  fuente Axional (no Holded). Driver explícito: integración API con
  sistemas existentes.
- A 50 usuarios el coste recurrente de Enterprise pasa de "marginal" a
  "significativo" (~18.6 k€/año solo por fedefarma a precio público).
- Migrar a Enterprise tiene sentido sobre todo si se hace **antes de
  comprometer fedefarma**, aprovechando que inpr3mium aún no tiene
  cutover (no hay datos en producción real).

**Driver original cuestionado**: el operador citó "API access" como
razón principal para Enterprise. **Corrección**: ambas ediciones exponen
exactamente la misma superficie API (XML-RPC, JSON-RPC, API keys,
`base_automation`). Enterprise no añade endpoints; añade *modelos*
(Documents, Sign, Studio, Field Service, etc.) accesibles vía la misma
API estándar. La decisión, por tanto, debe basarse en otros drivers
(reporting, customización no-code, multi-empresa, soporte) y no en
acceso API.

**Drivers reales identificados a escala fedefarma (50 users multi-co)**:

| Driver | Peso | Impacto |
|---|---|---|
| Reporting management ad-hoc (dashboards, P&L, balance PGCE) | alto | sin Enterprise → self-port mis_builder + l10n_es_mis_report o vivir con Trial Balance |
| Customización por no-developer (Studio) | medio-alto | sin Enterprise → cada vista/automation requiere developer |
| Multi-empresa con consolidación real | alto | sin Enterprise → OCA `account_consolidation` (rough) |
| Documents + Sign nativos | medio | a 50 users, cobra valor operativo real |
| Soporte oficial Odoo S.A. | medio | comunidad GitHub vs SLA contractual |
| Integración API | nulo | igual en ambas ediciones |
| Coste recurrente | -alto | 0 € (Community) vs ~16-19 k€/año (Enterprise inpr3mium+fedefarma) |

## 2. Hipótesis a validar

**H1**: Enterprise reduce el coste de mantenimiento del stack OCA-pinneado
suficiente para justificar la suscripción a escala fedefarma (50 users).

**H2**: `account_reports` + `l10n_es_reports` (Enterprise) cubren el
reporting estatutario y management que `account_financial_report` (OCA)
+ `mis_builder` (deferred) NO cubren hoy.

**H3**: Studio reduce el tiempo de implementación de customizaciones
funcionales (formularios, vistas, automatizaciones) en al menos un
factor 5x respecto a desarrollo en módulos custom.

**H4**: La migración Holded → Odoo ya hecha (loaders, transformaciones,
ext_id strategy) es **portable a Enterprise sin reescribir nada
material**, porque ambas ediciones comparten exactamente el mismo
core (`account.move`, `res.partner`, `ir.model.data`, ORM, RPC).

H4 es probablemente cierta a priori, pero conviene verificarla en la
práctica: clonar la BBDD CE → instalar Enterprise → ver qué se rompe.

## 3. Metodología: A/B paralelo en local

**Configuración**:

- **Stack A**: doodba existente, `inpr3mium-ce` (Community + OCA).
  Continúa recibiendo loaders de la migración en marcha.
- **Stack B**: doodba nuevo, `inpr3mium-ee` (Enterprise). Arranca
  desde un clone de la BBDD CE en un punto estable.
- Periodo de evaluación: **4-6 semanas máx** (timebox estricto).
- Comparación contra criterios fijados *antes* de empezar (sección 4).
- Tras decisión: matar el perdedor sin nostalgia.

**Por qué clone de BBDD y no re-migrar**: re-correr loaders contra
Enterprise duplica trabajo, arrastra bugs de timing, y NO valida H4
(que es lo que queremos validar). Clone garantiza datos idénticos
bit-a-bit y nos dice exactamente qué módulos Enterprise rompen al
instalarse sobre datos ya migrados.

**Cuándo arrancar**: tras cerrar **Fase 5.3** (validación con subset
2024+2025). Razones:

- Antes de 5.3 los datos son demasiado escasos para evaluar reporting.
- Después de 5.3 hay 2 años de histórico real con cuadre validado →
  base sólida para A/B de informes financieros.
- Si esperamos a 5.4 (histórico completo) o 5.5 (cutover), la decisión
  llega demasiado tarde para influir en fedefarma fin de año.

## 4. Criterios de decisión (fijar AHORA, no a posteriori)

Pesos sobre 100. La edición ganadora es la que más puntos suma sobre
los siguientes criterios. **Importante**: las puntuaciones se asignan
durante Fase E.4, no antes. Lo que se fija ahora son los criterios
y sus pesos.

| # | Criterio | Peso | Cómo se mide |
|---|---|---|---|
| C1 | Disponibilidad inmediata de **P&L PGCE** y **Balance Situación PGCE** | 15 | binario (sí/no out-of-the-box, sin self-port) |
| C2 | Esfuerzo en construir **dashboard de margen por familia de producto** desde cero | 15 | tiempo en horas para un usuario funcional sin tocar código |
| C3 | Calidad UX del **drilldown** desde balance/P&L → asiento → factura | 10 | escala 1-5 evaluada con flujo de auditoría real (3 facturas distintas) |
| C4 | Esfuerzo en **portar** todos los assets actuales (loaders, ext_ids, custom journals, taxes mapeadas) | 15 | horas reales en Fase E.3 + nº incidencias |
| C5 | **Tax report 303** generado con misma fidelidad que stack OCA actual | 10 | comparación lado a lado de mod303 generado en CE vs EE para Q1 2025 (datos reales) |
| C6 | **Multi-empresa**: crear segunda company "fedefarma-test" + asiento intercompany + reporting consolidado | 10 | escala 1-5 |
| C7 | **Coste anual** proyectado a topología final (inpr3mium + fedefarma) | 10 | invertido: menor coste = más puntos |
| C8 | **Lock-in**: facilidad de salir de la edición elegida en futuro | 5 | escala 1-5 (Community gana naturalmente) |
| C9 | Aprovechamiento del **trabajo ya hecho** en la migración Holded | 5 | escala 1-5 (validación H4) |
| C10 | **Soporte** ante incidencia bloqueante (simulación: abrir issue real) | 5 | tiempo a primera respuesta accionable |

Total: 100. Decisión por mayor suma. Si diferencia <10 puntos → empate
técnico → se rompe a favor de Community (menor coste y menos lock-in
como tie-breaker razonable).

## 5. Topología

```
┌─────────────────────────────────────────────────────────┐
│                  Mac local (Carles)                     │
│                                                          │
│  ┌────────────────────┐       ┌────────────────────┐   │
│  │ doodba/inpr3mium-ce│       │ doodba/inpr3mium-ee│   │
│  │  port 19069        │       │  port 19169        │   │
│  │  DB inpr3mium_dev  │       │  DB inpr3mium_ee   │   │
│  │  addons:           │       │  addons:           │   │
│  │   odoo/odoo CE     │       │   odoo/odoo CE     │   │
│  │   OCA/* (existente)│       │   odoo/enterprise  │   │
│  │                    │       │   OCA/* (subset)   │   │
│  └─────────┬──────────┘       └──────────┬─────────┘   │
│            │                             │              │
│            └──────────────┬──────────────┘              │
│                           ▼                             │
│              ┌─────────────────────────┐                │
│              │ PostgreSQL 16 (shared)  │                │
│              │  - inpr3mium_dev        │                │
│              │  - inpr3mium_ee         │                │
│              └─────────────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

**Decisiones**:

- **Doodba separados** (no multi-DB sobre un único doodba). Razón:
  multi-DB obliga a compartir addons path → el `odoo/enterprise` estaría
  presente para ambas instancias → no es A/B real.
- **PostgreSQL compartido**: ahorra recursos y simplifica el clone
  (`pg_dump | pg_restore` en local, sin transferencia de red).
- **Filestore separado**: cada stack su carpeta. El clone copia
  filestore inicial; tras eso, divergen.
- **Mismo `.env` con dos perfiles**: `.env.ce` y `.env.ee` con sus
  respectivos `ODOO_AGENT_TENANT`, `ODOO_DB`, `ODOO_URL`,
  `DOODBA_PROJECT_DIR`, `DOODBA_COMPOSE_SERVICE`. Symlink rotativo o
  exportar el correcto en cada sesión.
- **Bot user duplicado**: mismo login (`bot.contable@inpr3mium.com`)
  en ambas DBs con misma API key (clone lo trae). Operativamente
  transparente para los scripts del agente.

**Tenant slugs**:

- Mantener `inpr3mium` para el stack CE (no renombrar para no romper
  paths existentes). Se trata como "inpr3mium-ce" implícito.
- Crear nuevo tenant `inpr3mium-ee` con su propia carpeta
  `docs/tenants/inpr3mium-ee/` que es **fork ligero** del de inpr3mium
  (profile.yaml con `edition: enterprise`, expected_modules ajustados,
  resto referencia el original).

## 6. Plan por fases

### Fase E.0 — Pre-flight (sin coste, antes de pagar nada)

| Tarea | Deliverable | Criterio de salida |
|---|---|---|
| Confirmar criterios C1-C10 con operador | sección 4 firmada | operador acepta pesos |
| Confirmar timebox 4-6 semanas | calendario con start/end | start ≥ Fase 5.3 cerrada, end ≤ start + 6 sem |
| Confirmar coste eval (~93-150 €) | aprobación operador | go/no-go explícito |
| Decidir camino comercial: directo Odoo S.A. o vía partner | elección registrada | si partner → contactar 1-2 candidatos |
| Generar deploy key SSH + dar acceso al repo `odoo/enterprise` | `~/.ssh/id_ed25519_odoo_enterprise` + key añadida en perfil | `gh api repos/odoo/enterprise --jq '.permissions'` devuelve acceso |

**Compra**: una vez aprobado, suscribir Custom plan en
`https://www.odoo.com/odoo-pricing` (3 users inpr3mium para empezar).
Pagar mensual, no anual (queremos poder cancelar limpio si gana
Community).

### Fase E.1 — Spin up Enterprise stack

| Tarea | Deliverable |
|---|---|
| Clonar carpeta doodba existente a `~/code/odoo-agent/infra/doodba-inpr3mium-ee/` | árbol replicado |
| Editar `docker-compose.yml`: cambiar puertos (19069→19169), nombre servicio | yaml válido |
| Añadir `odoo/enterprise` en `repos.yaml` con SSH URL + deploy key | repos.yaml diff |
| Añadir entrada en `addons.yaml` para que `auto/addons` incluya enterprise | yaml válido |
| `gitaggregate` para traer enterprise | repo clonado, sha pinned |
| `invoke img-build` para reconstruir imagen con nuevo addons path | imagen built |
| Levantar stack vacío (sin DB) y verificar que `127.0.0.1:19169` responde | curl 200 |

### Fase E.2 — Clone CE → EE

| Tarea | Deliverable |
|---|---|
| Detener loaders en CE temporalmente para snapshot consistente | confirmación operador |
| `pg_dump inpr3mium_dev > inpr3mium_dev.sql` | dump file |
| `createdb inpr3mium_ee && pg_restore` | DB creada idéntica |
| `rsync filestore/inpr3mium_dev/ filestore/inpr3mium_ee/` | filestore clonado |
| Activar suscripción en EE: `Settings → Subscription → Enter code` | banner Enterprise activo |
| Verificación inicial RPC: bot puede login en EE | `module_status.py` devuelve 75 módulos installed (mismos que CE) |
| Reanudar loaders en CE | CE sigue avanzando |

**De aquí en adelante CE y EE divergen**. Los criterios E1.1 y E4
deben evaluarse ANTES de que la divergencia haga el A/B incomparable.
Si los loaders pendientes son sustanciales (loaders 2-10), considerar
re-clonar tras 5.4 cerrada.

### Fase E.3 — Migrar a Enterprise modules

| Tarea | Deliverable | Verificación |
|---|---|---|
| Instalar `accountant` en EE | state=installed | menú "Contabilidad" aparece |
| Instalar `account_reports` (auto-dep de accountant) | idem | reports aparecen bajo Contabilidad |
| Instalar `l10n_es_reports` | idem | P&L y Balance PGCE disponibles |
| Desinstalar `account_financial_report` (OCA) en EE — redundante | state=uninstalled | sin errores |
| Decidir EDI: instalar `l10n_es_edi_facturae` Enterprise + desinstalar `l10n_es_facturae` (OCA) | módulos cambiados | smoke test FacturaE en EE |
| Instalar `documents` + `sign` para evaluación C2 | idem | apps disponibles |
| Instalar `web_studio` para evaluación C2 | idem | botón Studio en top bar |
| Verificar que datos clonados (3.177 partners, 186 cuentas, journals, taxes) **siguen accesibles y consistentes** tras instalación | `audit_module_state.py` + spot-check 5 partners + 3 facturas | sin diferencias funcionales |

**Riesgo crítico de esta fase**: alguna instalación Enterprise puede
sobrescribir datos custom (e.g., taxes mapeadas con `[holded: <key>]`
o journals con prefijos inpr3mium específicos). **Tomar snapshot RPC
de CE ANTES** y diff post-Fase E.3 contra EE para detectar
divergencias funcionales. Documentar todo en
`snapshots/edition-eval/2026-XX-XX_post-ee-install.json`.

### Fase E.4 — Evaluación contra criterios

Para **cada criterio C1-C10**:

1. Definir el escenario de prueba concreto (qué se hace exactamente).
2. Ejecutar en CE → cronometrar / evaluar.
3. Ejecutar en EE → cronometrar / evaluar.
4. Anotar puntuación por edición en hoja
   `evaluation-scorecard.md` con evidencia (screenshot, log,
   timing, snippet de output).
5. NO ajustar pesos retroactivamente.

**Granularidad temporal**: dedicar 1-2 sesiones de 2-3h por semana
durante 4 semanas. No hacerlo a tirones — los criterios cualitativos
(C3, C6) requieren reposo entre evaluaciones.

### Fase E.5 — Día de decisión

Ceremonia formal (puede ser 30 min de soledad con la scorecard, no
hace falta solemnidad):

1. Sumar puntuaciones por edición.
2. Aplicar tie-breaker (Community gana si diferencia <10).
3. Registrar decisión en `docs/tenants/inpr3mium/memory/decisions-log.md`
   con fecha, scorecard final, razón principal.
4. Actualizar `profile.yaml` con `edition: <ce|ee>`.
5. Actualizar `docs/tenants/_template/profile.yaml` con la decisión
   por defecto para futuros tenants (especialmente fedefarma).
6. Actualizar `MEMORY.md` del tenant con puntero a la decisión.

### Fase E.6 — Wind-down + cutover

**Si gana Community**:

- Cancelar suscripción Enterprise antes del próximo billing cycle.
- Borrar deploy key del repo `odoo/enterprise`.
- Detener stack EE, borrar `inpr3mium_ee` DB y filestore.
- Conservar `docs/tenants/inpr3mium-ee/` como archivo
  (`docs/tenants/_archived/inpr3mium-ee-eval-2026/`) para futura
  referencia si se reabre la pregunta.
- Continuar migración Holded sobre CE como hasta ahora.
- Plan futuro: self-port `mis_builder` cuando 5.5 cerrada (~1-2 días).

**Si gana Enterprise**:

- Renombrar tenants: `inpr3mium` → `inpr3mium-ce-archived`,
  `inpr3mium-ee` → `inpr3mium`. Cuidado con paths en scripts.
- Migrar bookmarks, scripts, dashboards a la EE como producción.
- Decidir cutover real con operador (probablemente alineado con
  Fase 5.5 original; el cutover a Enterprise *ES* el cutover de
  producción).
- Detener stack CE, borrar DB y filestore (tras dump de seguridad
  archivado offline durante 6 meses).
- Actualizar plan fedefarma para nacer directamente sobre EE.
- Suscribir license adicional cuando llegue Fase 6 fedefarma.

## 7. Coste estimado

### Coste de la evaluación (Fases E.0 → E.5)

| Concepto | Coste |
|---|---|
| Suscripción Custom plan inpr3mium 3 users × 1 mes | ~93 € |
| (Opcional) +1 mes si timebox se desliza | +93 € |
| Tiempo operador (Carles) | ~16-24h spread en 4-6 sem |
| Recursos Mac (CPU/RAM/disk) | despreciable |
| **Total comprometido si CE gana** | **~93-186 €** |

### Coste recurrente en producción (Fase E.6 en adelante)

**Si gana Community**:

| Concepto | Coste |
|---|---|
| Licencias | 0 € |
| Self-port `mis_builder` + `l10n_es_mis_report` | ~1-2 días dev one-time |
| Self-port `account_banking_sepa_credit_transfer` (cuando se necesite) | ~1-2 días dev one-time |
| Mantenimiento OCA (gitaggregate periódico, breaking changes) | bajo |
| **Total año 1** | **~0 € recurrente + 2-4 días dev one-time** |

**Si gana Enterprise** (precios públicos España 2026 sin descuentos):

| Concepto | Coste anual |
|---|---|
| inpr3mium 3 users × 31 €/mes × 12 | ~1.116 € |
| fedefarma 50 users × 31 €/mes × 12 | ~18.600 € |
| **Subtotal** | **~19.716 €** |
| Con prepago anual (-10%) y partner Silver (-10%) | ~16-17 k€/año |
| Coste de migrar inpr3mium a EE (Fase E.3-E.6) | absorbido en eval |
| Coste de migrar fedefarma directamente sobre EE | igual que sobre CE |

## 8. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Suscripción Enterprise se renueva por descuido tras decisión CE | media | 93 € no recuperables | calendario reminder + facturación mensual no anual |
| Fase E.3 rompe datos clonados (modificaciones Enterprise destructivas) | baja-media | re-trabajo Fase E.2 | snapshot RPC pre-instalación + diff post; nunca trabajar contra el clone "vivo" sin backup |
| Drift CE↔EE durante eval (CE sigue migrando, EE no) | alta | comparación injusta de criterios que dependen de volumen de datos | re-clonar al inicio de Fase E.4 si han pasado >2 semanas o >2 loaders desde Fase E.2 |
| Timebox se desliza → comparación muere por inercia | alta | quedarse con CE por agotamiento | calendario duro; si pasa de 6 semanas, abort y decidir con datos parciales |
| Criterio C3/C6 (cualitativos) sesgados por familiaridad con CE | media | ventaja artificial CE | hacer C3/C6 último, después de 2 semanas usando ambos |
| Partner negociación retrasa start | baja | dilación E.0 | si tarda >1 semana, ir directo a Odoo S.A. y reabrir partner solo si gana Enterprise |
| `odoo/enterprise` repo no portea algún módulo crítico ES en 19.0 | baja | scope EE más reducido del esperado | en E.0 verificar disponibilidad 19.0 de `accountant`, `account_reports`, `l10n_es_reports`, `l10n_es_edi_facturae`, `web_studio`, `documents`, `sign` antes de pagar |

## 9. Implicaciones para fedefarma

Independientemente del resultado, el agente queda mejor posicionado
para fedefarma:

- **Si gana CE**: el plan de fedefarma ya está validado en CE, pero
  con la conciencia de que a 50 users hay que reabrir la pregunta
  Enterprise específicamente para ese tenant — no asumir que el
  resultado de inpr3mium se traslada sin más, porque el cálculo de
  coste cambia drásticamente con volumen.
- **Si gana EE**: fedefarma nace en EE directamente. Se ahorra el
  paso E.3 (migración EE intermedia) que costaría 10x más a 50 users
  que a 3.

En ambos casos: la evaluación entrena al agente para operar Enterprise
(scripts del skill `odoo-module-admin` deberán tener compatibilidad
EE — la mayoría ya la tienen, pero modulos como `accountant`/Studio
añaden gotchas específicos que el agente debe documentar tras E.3).

## 10. Preguntas abiertas para el operador

1. **Timebox**: ¿4 o 6 semanas máx? Default propuesto: 4 sem desde
   Fase 5.3 cerrada.
2. **Camino comercial**: ¿directo `odoo.com/pricing` o vía partner?
   Si partner, ¿tienes alguno en mente o quieres recomendaciones (2-3
   con experiencia España + doodba)?
3. **Cuándo arrancar**: ¿al cerrar 5.3 (datos suficientes pero no
   completos) o al cerrar 5.4 (histórico completo, mejor base de
   eval pero llegamos justos a fedefarma)?
4. **Pesos C1-C10**: ¿asumes los propuestos o quieres ajustar? Los
   más sensibles son C7 (coste, 10) y C2 (Studio, 15).
5. **Eval de Studio (C2)**: ¿quién la hace? Tú no eres usuario
   funcional típico (eres developer), así que puede sesgar. ¿Hay
   alguien en inpr3mium o tu entorno que pueda hacer el escenario
   "construir dashboard de margen sin tocar código" en frío?
6. **Coste eval**: ¿confirmas los ~93-186 € como aceptables?
7. **Scope eval**: ¿añades algún criterio adicional que no esté en
   C1-C10? (e.g., calidad UX en mobile, integración con Slack/Teams,
   etc.)

## 11. Checklist accionable inmediato

Antes de empezar Fase E.0:

- [ ] Operador lee este documento completo y confirma sección 2 (hipótesis)
      y sección 4 (criterios + pesos).
- [ ] Responder las 7 preguntas de sección 10.
- [ ] Marcar fecha tentativa de start (post Fase 5.3) en calendario.
- [ ] Verificar que `odoo/enterprise` 19.0 contiene los módulos críticos
      (verificación pre-pago):
  ```bash
  # En la sesión que active esta fase, ejecutar:
  for m in accountant account_reports l10n_es_reports \
           l10n_es_edi_facturae web_studio documents sign \
           account_consolidation; do
    echo -n "$m: "
    gh api "repos/odoo/enterprise/contents/$m/__manifest__.py?ref=19.0" \
      --jq '.size' 2>&1 | head -1 | grep -qE '^[0-9]+$' \
      && echo "OK" || echo "MISSING"
  done
  ```
  (requiere que Carles ya tenga acceso al repo privado; si no, este
  check se posterga a justo después de la suscripción).

## Annex A — Activación de license Enterprise en doodba

Resumen de pasos canónicos para que cuando llegue Fase E.1 esté todo
documentado:

1. **Suscripción**: `https://www.odoo.com/pricing` → "Custom" → 3
   users → checkout. Recibes email con `subscription_code`.
2. **Acceso al repo privado**: tras suscribirte, Odoo añade tu cuenta
   GitHub como colaborador del repo `odoo/enterprise` (si no, abrir
   ticket support@odoo.com con tu GitHub username).
3. **Deploy key**: generar SSH key dedicada, añadirla en
   `https://github.com/odoo/enterprise/settings/keys` (permiso read).
4. **`repos.yaml` doodba**:
   ```yaml
   ./odoo/enterprise:
     defaults:
       depth: $DEPTH_DEFAULT
     remotes:
       enterprise: git@github.com:odoo/enterprise.git
     target: enterprise 19.0
     merges:
       - enterprise 19.0
   ```
5. **`addons.yaml` doodba**: añadir entrada para que `enterprise/*`
   se incluya en `auto/addons`.
6. **Build & up**: `invoke img-build && docker compose up -d`.
7. **Activar license**: dos vías equivalentes:
   - **UI**: login como admin → `Settings → Subscription → Enter
     code` → pegar subscription_code.
   - **CLI**: `docker exec -u odoo odoo odoo --stop-after-init -d
     <db> --load-language es_ES --enterprise-code=<code>` (sintaxis
     puede variar; verificar en docs Enterprise).
8. **Verificación**: el banner amarillo "You are using a free trial"
   desaparece; `Settings → Subscription` muestra fecha de expiración
   correcta.

## Annex B — Mapping OCA → Enterprise para inpr3mium

> **Versión completa cross-tenant** de esta tabla en
> [`docs/reference/community-vs-enterprise-modules.md`](../../reference/community-vs-enterprise-modules.md)
> (12 secciones funcionales + síntesis + heurística por tamaño). Lo de
> abajo es el subset relevante para inpr3mium concretamente.

Listado de módulos del stack actual y su equivalencia Enterprise.
Sirve para Fase E.3 y como referencia post-decisión.

| OCA actual | Enterprise equivalente | Acción Fase E.3 |
|---|---|---|
| `account_financial_report` | `account_reports` (parte de `accountant`) | desinstalar OCA, instalar Enterprise |
| `mis_builder` *(deferred)* | `account_reports` + Spreadsheet | no instalar OCA, no necesario |
| `l10n_es_facturae` | `l10n_es_edi_facturae` | desinstalar OCA, instalar Enterprise (validar smoke test FacturaE) |
| `l10n_es_aeat_mod303` | (no equivalente Enterprise para España) | mantener OCA en ambas ediciones |
| `l10n_es_aeat_mod347/349/390/111/115/130` | (idem, no hay Enterprise) | mantener OCA |
| `account_payment_mode`, `account_payment_order` | (no equivalente directo) | mantener OCA |
| `account_banking_sepa_direct_debit` | nativo en `account_payment` Enterprise | evaluar si vale la pena migrar (probablemente no, ya funciona) |
| `account_banking_sepa_credit_transfer` *(deferred)* | nativo Enterprise | con EE → resuelto, no self-port |
| `auditlog` | `audit_logs` Enterprise (subset) | evaluar gap; OCA es más completo, mantener OCA |
| `queue_job` | (no equivalente serio) | mantener OCA |
| `server-tools/*` (varios) | parcialmente nativos | revisar caso a caso, mayoría no necesarias en EE |
| `web/*` (varios) | parcialmente nativos | revisar caso a caso |

**Observación clave**: el stack EE para inpr3mium NO es "Enterprise
solo" — sigue necesitando ~10-15 módulos OCA específicos de España
(toda la familia AEAT). El cambio efectivo es ~5 módulos OCA
sustituidos por equivalentes Enterprise + Studio/Documents/Sign como
adición.

## Histórico

| Fecha | Cambio |
|---|---|
| 2026-05-12 | Documento inicial creado tras conversación operador sobre proyección a fedefarma. Pendiente: ejecutar Fase E.0. |
