# Odoo 19 — Community vs Enterprise (matriz de módulos)

> **Material de referencia cross-tenant**. No describe arquitectura
> interna de Odoo (eso vive en `docs/architecture/`) ni infraestructura
> de despliegue (`docs/infra/`). Es la matriz que sirve para responder
> "¿qué tengo en cada edición y dónde están los gaps reales?" sin
> tener que reconstruirla cada vez que un tenant se replantea la
> decisión.

> **Documento consumido por**: `docs/tenants/inpr3mium/edition-evaluation-plan.md`
> (criterios C1-C10 + Anexo B se apoyan en esta tabla). Cualquier
> tenant futuro que vaya a evaluar edition (especialmente fedefarma)
> debería leer este doc primero.

## Metadata

- **Versión Odoo cubierta**: **19.0** (rama estable a 2026-05).
- **Fuentes**:
  - Página pública oficial Odoo S.A. *Community vs Enterprise*.
  - Conocimiento estable del ecosistema Odoo 19 a fecha de creación.
  - Verificación directa vía GitHub API del estado de OCA en `19.0`
    (rama existe, último commit reciente, módulos accesibles vía
    `repos/OCA/<repo>/contents/<module>?ref=19.0`).
- **Limitación honesta**: el repo `odoo/enterprise` es privado. La
  enumeración de módulos Enterprise se construye desde la página
  pública de Odoo S.A. + conocimiento del ecosistema, NO desde el
  manifest real del repo. Si algún caso es crítico para una decisión,
  verificarlo puntualmente vía release notes de Odoo o pidiendo trial
  7 días sin compromiso a Odoo S.A.
- **Caducidad**: la matriz refleja el estado a **2026-05-12**. Tres
  cosas pueden invalidarla con el tiempo:
  - Odoo S.A. saca módulos nuevos cada release (mayo + octubre
    típicamente).
  - OCA portea módulos a 19.0 que hoy figuran como `❌`.
  - Algún módulo Enterprise se mueve a Community (raro pero ocurre,
    e.g., `accountant` parts en versiones futuras).

  **Política**: revisar la matriz cada vez que un tenant active Fase
  E.0 de su evaluation plan, no antes. No mantener proactivamente.

## Cómo leer las columnas

- **CE core**: ¿viene en Odoo Community out-of-the-box?
- **EE core**: ¿viene en Enterprise out-of-the-box (sin pagar IAP
  adicional)?
- **OCA 19.0**: ¿hay módulo OCA en rama 19.0 que cubra lo mismo? Valores:
  - `✅ maduro` — production-ready, comparable a Enterprise
  - `⚠️ parcial` — funciona pero con menos features o más rough
  - `❌ no portado` — solo en versiones anteriores (16/17/18)
  - `❌` — no existe homólogo OCA, ni en versiones anteriores
  - `n/a` — no aplica (la capacidad ya está en CE core)
- **Gap real**: ¿hay un caso de uso concreto donde Community + OCA NO
  cubre lo que Enterprise sí? Valores:
  - `⚠️ alto` — diferenciador material en muchos contextos
  - `⚠️ medio` — diferenciador en algunos contextos
  - `⚠️ bajo` — diferenciador marginal
  - `—` — paridad razonable (CE+OCA cubren lo necesario)
  - `empate` — explicitamente equivalente

---

## 1. Contabilidad y finanzas

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| Facturación básica (`account` = Invoicing) | ✅ | ✅ | n/a | — |
| Asientos manuales, conciliación básica | ✅ | ✅ | n/a | — |
| Contabilidad analítica completa (multi-axis, distribution) | ✅ (`analytic`) | ✅ | n/a | — |
| App "Accounting" con menú propio (`accountant`) | ❌ | ✅ | ❌ no hay homólogo | ⚠️ medio |
| **P&L / Balance / Cash Flow con estructura legal** (`account_reports`) | ❌ | ✅ | `account_financial_report` ⚠️ parcial (da Trial Balance + Mayor + IVA, NO P&L/Balance estructurados) | ⚠️ **alto** |
| **Localización ES — P&L y Balance PGCE** | ❌ | ✅ (`l10n_es_reports`) | `l10n_es_mis_report` ❌ no portado (depende de `mis_builder` ❌) | ⚠️ **alto** |
| Drilldown jerárquico balance → asiento → factura | ⚠️ rudimentario | ✅ | ❌ | ⚠️ medio |
| Comparativos multi-período (este mes vs hace año) | ❌ nativo | ✅ | ⚠️ vía mis_builder cuando se porte | ⚠️ medio |
| Audit trail completo de campos contables | ⚠️ vía `auditlog` OCA | ✅ nativo (`account_audit_trail`) | ✅ `auditlog` maduro | — |
| **Consolidación multi-empresa** | ❌ | ✅ (`account_consolidation`) | `account_consolidation` ⚠️ rough en 19.0 | ⚠️ alto (importa para fedefarma) |
| Followup customer automatizado (recordatorios escalonados) | ❌ | ✅ | ✅ `account_followup` OCA | — |
| Asset management (inmovilizado + amortización) | ⚠️ básico | ✅ avanzado | ⚠️ `account_asset_management` parcial | ⚠️ medio |
| Budgets (presupuestos con seguimiento) | ❌ | ✅ | ✅ `account_budget_oca` | — |
| Lock dates / fiscal periods | ✅ | ✅ | n/a | — |
| AI-powered invoice extraction (OCR) | ❌ | ✅ vía IAP (paga por uso adicional) | ⚠️ varios proyectos OCA pero ninguno production-grade | ⚠️ bajo (alternativas: Klippa, Rossum externos) |
| Bank reconciliation con sugerencias automáticas (reconciliation models) | ⚠️ widget básico | ✅ matching automático | ⚠️ `account_reconcile_oca` parcial | ⚠️ bajo-medio |
| Spreadsheet financiero reactivo (tipo Excel embebido) | ❌ | ✅ (Odoo Spreadsheet) | ❌ | ⚠️ medio |

## 2. Localización España y EDI

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| Plan PGCE Pymes / Full | ✅ (`l10n_es`) | ✅ | n/a | — |
| Modelos AEAT 303, 347, 349, 390, 111, 115, 130, 369 | ❌ | ❌ | ✅ `l10n_es_aeat_*` maduros | — *(empate: ambas dependen de OCA)* |
| Modelo 232 (operaciones vinculadas) | ❌ | ❌ | ❌ no portado 19.0 | ⚠️ bajo (anual) |
| Modelo 720 (bienes en extranjero) | ❌ | ❌ | ⚠️ existe en 18.0, sin port 19.0 verificado | ⚠️ bajo |
| **SII (Suministro Inmediato AEAT)** | ❌ | ✅ `l10n_es_edi_sii` Enterprise | `l10n_es_aeat_sii_oca` ✅ | empate — fedefarma necesita; ambas opciones existen |
| **Veri\*Factu** | ❌ | ⚠️ Odoo S.A. anuncia para 2026-27 pre-obligación | ❌ no portado (PR cerrado feb-26) | ⚠️ **alto para fedefarma** si gran empresa (Veri\*Factu obligatorio antes para >6M€) |
| **FacturaE** (FACe + futuro B2B Crea y Crece) | ❌ | ✅ `l10n_es_edi_facturae` Enterprise | ✅ `l10n_es_facturae` OCA | empate |
| Recargo de Equivalencia | ❌ | ✅ vía localización ES | ✅ `l10n_es` core | — |
| Régimen de Caja IVA | ❌ | ✅ vía localización ES | ✅ `l10n_es_aeat_mod303` con flag | — |
| **TPV Spain certified (Reglamento Anti-Fraude 11/2021)** | ❌ | ✅ `l10n_es_pos_anti_fraud` Enterprise | ⚠️ status incierto en 19.0 | ⚠️ **alto si se opera POS B2C** |

## 3. Compras, inventario, fabricación

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| Compras (`purchase`) | ✅ | ✅ | n/a | — |
| Inventory básico (`stock`) | ✅ | ✅ | n/a | — |
| Multi-warehouse con routes/rules avanzadas | ✅ | ✅ | n/a | — |
| MRP I básico (BoM, work orders) | ✅ (`mrp`) | ✅ | n/a | — |
| MRP II avanzado (planning, MPS, work centers con OEE) | ⚠️ básico | ✅ `mrp_workorder` + `mrp_mps` Enterprise | ⚠️ `mrp_mps_*` OCA limitado | ⚠️ medio si se fabrica |
| PLM (gestión cambios de BOM con versionado) | ❌ | ✅ (`mrp_plm`) | ❌ | ⚠️ bajo |
| Mantenimiento (`maintenance`) | ✅ | ✅ | n/a | — |
| Quality control | ❌ | ✅ (`quality`) | ⚠️ `quality_control_oca` parcial | ⚠️ medio si se certifican lotes |
| Lots / serial numbers con trazabilidad | ✅ básica | ✅ avanzada con cosechado de datos | n/a | — |
| Barcode scanner mobile | ❌ | ✅ (`stock_barcode`) | ⚠️ varios proyectos OCA rough | ⚠️ medio si almacén operativo |

## 4. Ventas, CRM, suscripciones

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| Sales (`sale`) | ✅ | ✅ | n/a | — |
| CRM básico | ✅ | ✅ | n/a | — |
| VoIP / CTI integrado (click-to-call) | ❌ | ✅ (`voip`) | ⚠️ `connector_asterisk` rough | ⚠️ bajo |
| **Subscriptions (`sale_subscription`)** — facturación recurrente con upsell/downgrade | ❌ | ✅ | ⚠️ `contract` OCA (similar pero distinto modelo) | ⚠️ bajo-medio (relevante si hay retainers) |
| Rental | ❌ | ✅ (`sale_renting`) | ❌ | ⚠️ bajo |
| Sales pricing rules complejas (price lists con fechas, categorías, customer-specific) | ✅ básico | ✅ avanzado | n/a | — |

## 5. Proyectos y servicios

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| Project (`project`) | ✅ | ✅ | n/a | — |
| Timesheet (`hr_timesheet`) | ✅ | ✅ | n/a | — |
| Helpdesk (ticket management) | ⚠️ vía `project` rudimentario | ✅ (`helpdesk`) | ⚠️ `helpdesk_mgmt` OCA — distinto enfoque | ⚠️ medio |
| Field Service (visitas técnicas, geolocalización, mobile app) | ❌ | ✅ (`industry_fsm`) | ❌ | ⚠️ bajo (no aplica casos servicios profesionales B2B) |
| Planning (asignación recursos con Gantt) | ❌ | ✅ (`planning`) | ⚠️ `project_task_dependency` parcial | ⚠️ bajo-medio |
| Appointments (booking online) | ❌ | ✅ (`appointment`) | ❌ | ⚠️ bajo |

## 6. RRHH y nóminas

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| Employees + Departments | ✅ | ✅ | n/a | — |
| Time off (vacaciones) | ✅ | ✅ | n/a | — |
| Recruitment | ✅ | ✅ | n/a | — |
| Payroll genérico | ❌ (módulo eliminado de CE en 16+) | ✅ (`hr_payroll`) | ⚠️ `payroll_community` existe | ⚠️ alto |
| **Payroll Spain (nómina ES con SS, IRPF, finiquito)** | ❌ | ❌ Odoo no lo tiene de fábrica | ⚠️ `l10n_es_payroll_*` OCA rough | **empate** — habitualmente se externaliza (A3/Sage/Nomina.com) |
| Expenses (notas de gasto) | ✅ | ✅ | n/a | — |
| Appraisal / Surveys | ⚠️ surveys básico | ✅ appraisal completo | ❌ appraisal | ⚠️ bajo |

## 7. Marketing y eCommerce

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| Website builder | ✅ | ✅ avanzado (más temas, blocks) | n/a | — |
| eCommerce (`website_sale`) | ✅ | ✅ | n/a | — |
| Marketing Automation (campañas multi-step) | ❌ | ✅ (`marketing_automation`) | ⚠️ `marketing_automation_oca` parcial | ⚠️ medio |
| Email Marketing (mass mailing) | ✅ básico | ✅ avanzado | n/a | — |
| Events (gestión eventos + ticketing) | ✅ básico | ✅ con livestreaming | n/a | — |
| Surveys / NPS | ✅ | ✅ | n/a | — |
| eLearning | ✅ básico | ✅ con certificación + páginas premium | n/a | — |
| Social Marketing (Facebook/LinkedIn/X post + ads) | ❌ | ✅ | ❌ | ⚠️ bajo |

## 8. Productividad y colaboración

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| Conversaciones internas (`mail`) | ✅ | ✅ | n/a | — |
| **Documents** (gestión documental con workspaces, OCR, workflows) | ❌ | ✅ (`documents`) | ⚠️ `dms` OCA mucho más simple | ⚠️ **alto** a 50+ users |
| **Sign** (firma electrónica con certificados eIDAS) | ❌ | ✅ (`sign`) | ⚠️ `sign_oca` solo firma simple, no eIDAS | ⚠️ **alto** si se firman contratos B2B |
| Approvals (workflows de aprobación con steps) | ❌ | ✅ (`approvals`) | ❌ | ⚠️ medio |
| Knowledge (wiki interna con embebido de tablas live) | ❌ | ✅ | ⚠️ `document_page` OCA muy básico | ⚠️ bajo-medio |
| Discuss canales + threads + DMs | ✅ | ✅ + integraciones (WhatsApp, MS Teams) | n/a en integraciones | ⚠️ bajo |
| Calendar (`calendar`) | ✅ | ✅ | n/a | — |
| VoIP / phone integration | ❌ | ✅ | ⚠️ | ⚠️ bajo |

## 9. Customización y desarrollo

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| Acceso al ORM, RPC, API keys | ✅ | ✅ | n/a | — *(idéntico, no es diferenciador)* |
| Custom modules (Python + XML) | ✅ | ✅ | n/a | — |
| **Studio** (drag-and-drop view editor + automations) | ❌ | ✅ (`web_studio`) | ❌ no equivalente | ⚠️ **alto a 50+ users — diferenciador #1** |
| Server actions vía UI | ✅ básico | ✅ + Studio integration | n/a | — |
| Automated actions (`base_automation`) | ✅ | ✅ + UI mejor en Studio | n/a | — |
| Custom reports via Studio | ❌ | ✅ | ❌ | ⚠️ medio |
| OWL components custom (frontend) | ✅ (vía dev) | ✅ (vía dev o Studio) | n/a | — |

## 10. Punto de Venta (POS)

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| POS básico touch | ✅ | ✅ | n/a | — |
| POS con balanza/báscula | ⚠️ vía OCA | ✅ nativo | ⚠️ `pos_scale_*` OCA limitado | ⚠️ medio si se venden productos pesados |
| POS para Restaurante | ✅ | ✅ avanzado (planos de mesa, etc.) | n/a | — |
| POS Loyalty / Gift card | ❌ | ✅ | ⚠️ `pos_loyalty` OCA parcial | ⚠️ bajo |
| **POS Spain anti-fraude (R.D. 1007/2023)** | ❌ | ✅ (`l10n_es_pos_anti_fraud`) | ⚠️ no claro en 19.0 | ⚠️ **alto si se opera POS B2C** |

## 11. Integraciones nativas

| Capacidad | CE core | EE core | OCA 19.0 | Gap real |
|---|---|---|---|---|
| **Bank synchronization automática** (Plaid/Salt Edge/Ponto/etc.) | ❌ | ✅ ~25.000 bancos | ⚠️ `account_statement_import_online_qonto` ✅ pero otros providers ❌ no portados | ⚠️ medio (Qonto cubierto, otros bancos no) |
| Amazon Connector | ❌ | ✅ | ⚠️ `connector_amazon` OCA rough | ⚠️ bajo |
| eBay Connector | ❌ | ✅ | ❌ | ⚠️ bajo |
| WhatsApp Business | ❌ | ✅ | ❌ | ⚠️ bajo |
| Google Calendar / Outlook bidireccional | ❌ | ✅ | ⚠️ parcial | ⚠️ bajo |
| Microsoft 365 / Exchange | ❌ | ✅ | ❌ | ⚠️ bajo |
| SMS provider integrado | ⚠️ vía custom | ✅ vía IAP (paga por SMS) | ⚠️ `sms_provider_*` OCA varios | ⚠️ bajo |
| Avalara tax calculation | ❌ | ✅ | ❌ | ⚠️ irrelevante (España no necesita Avalara) |

## 12. IAP (In-App Purchases) — solo Enterprise + pago adicional

Servicios "extra" que sí o sí cuestan dinero adicional sobre la
suscripción Enterprise (no incluidos):

- **OCR de facturas** (~0.10 € por factura procesada)
- **SMS** (~0.05 € por SMS)
- **VOIP minutes**
- **Lead enrichment** (datos de empresas vía clearbit-like)
- **Partner autocomplete** (rellena datos de empresa por VAT/nombre)
- **Document upgrade service** (actualización oficial 19→20)

En CE estos servicios no existen, se montan ad-hoc con APIs externas
(Klippa, Twilio, etc.).

---

## Lectura sintética

### Gaps reales (⚠️ alto/medio) que cargan a una migración seria

1. **Reporting estatutario PGCE** (P&L + Balance) — alto siempre.
2. **Studio** — alto a 50+ users; irrelevante a 1-3 users.
3. **Documents + Sign** — alto a escala media/grande con workflows
   reales de contratos.
4. **Veri\*Factu** si el tenant cae bajo obligación temprana
   (gran empresa) — alto.
5. **Consolidación multi-empresa** para reporting de holding — alto.
6. **POS Spain anti-fraude** si se opera POS B2C — alto.
7. **MRP II + Quality** si se fabrica con certificación de lotes —
   medio-alto.

### Empates reales (CE+OCA cubre razonable)

- AEAT mod303/347/349/390/etc. — empate (ambos dependen de OCA español).
- FacturaE — empate.
- SII — empate (ambas opciones existen y funcionan).
- Asset management — empate parcial.
- Followup customer — empate.
- Budgets — empate.
- API/RPC — empate total.
- Payroll Spain — empate (ninguna lo cubre, se externaliza).

### Gaps que la gente cree que existen y NO existen

- **Acceso API**: idéntico ambas. Ambas exponen XML-RPC, JSON-RPC,
  API keys, `base_automation`. Enterprise no añade endpoints; añade
  *modelos* (Documents, Sign, etc.) accesibles por la misma API.
- **Multi-company básico**: ambos lo cubren bien (la consolidación
  contable SÍ difiere).
- **Workflows básicos**: ambos vía `base_automation`.
- **OWL / desarrollo custom**: idéntico.
- **Multi-warehouse**: idéntico en CE y EE.
- **Variantes de producto**: idéntico.

### Heurística rápida por tamaño/escala

| Perfil | Recomendación tentativa |
|---|---|
| 1-5 users, B2B servicios, sin POS, sin fabricación | **CE + OCA** suficiente. Self-port mis_builder cuando se necesite reporting managerial. |
| 10-30 users, multi-empresa pequeña, contabilidad ES | **Frontera**. Depende mucho de Studio y del valor de Documents+Sign en su flujo. Eval A/B realmente justificada. |
| 30+ users, multi-empresa, holding, POS B2C, fabricación | **EE** prácticamente garantizado. El coste se amortiza solo en reducir custom dev y en reportes consolidados. |
| Cualquier tamaño con obligación SII temprana + Veri\*Factu pre-2027 | **EE** preferible (módulos EDI Enterprise mejor mantenidos). |

Esta heurística es orientativa, no sustituye una eval A/B con
criterios fijados (ver `docs/tenants/<slug>/edition-evaluation-plan.md`
template cuando exista).

## Mantenimiento de este documento

- **Quién lo actualiza**: el agente, pero solo bajo trigger explícito
  (Fase E.0 de algún tenant). NO mantenimiento proactivo entre
  evaluaciones.
- **Cuándo refrescar**:
  - Antes de iniciar Fase E.0 de cualquier tenant.
  - Si Odoo S.A. anuncia release mayor (20.0 esperada para Q4 2026).
  - Si OCA mergea ports masivos (típicamente tras release de Odoo).
- **Cómo refrescar**:
  - Releer página oficial Odoo S.A. *Community vs Enterprise* (o sus
    release notes 19.x si ha habido punteo desde la creación).
  - Re-verificar OCA 19.0 con `gh api` para los módulos marcados como
    `❌ no portado` o `⚠️ parcial` — quizá ya estén disponibles.
  - Actualizar la fecha del frontmatter.
  - Si cambian los gaps reales materialmente, registrar el cambio en
    el "Histórico" abajo.

## Histórico

| Fecha | Cambio |
|---|---|
| 2026-05-12 | Documento inicial creado a partir de conversación operador inpr3mium sobre proyección a fedefarma. 12 secciones funcionales + síntesis + heurística rápida + política de mantenimiento. |
