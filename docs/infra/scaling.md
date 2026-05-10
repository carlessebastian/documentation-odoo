# Escalado de Odoo 19 Community self-hosted

Guía de **buenas prácticas para dimensionar y escalar** una instancia
Odoo 19 Community desplegada con doodba bajo carga creciente. Recoge
las recomendaciones de la documentación oficial vendorizada en
`vendor/odoo-docs/` y las complementa con prácticas estándar del
ecosistema OCA / doodba que no aparecen upstream.

> **Audiencia**: el humano que provisiona la infraestructura y el
> agente cuando deba razonar sobre rendimiento. Esta guía es
> **referencia read-only**: ninguna skill la ejecuta automáticamente.

> **Aplicabilidad**: agnóstica al tenant. `inpr3mium` (sociedad única,
> migración Holded) es el field test del agente y previsiblemente
> cabrá en una sola máquina pequeña sin necesitar nada de esto.
> `fedefarma` (tenant futuro, migración Axional) sí necesitará
> aplicar buena parte de esta guía desde el día 1.

> **Fuentes**: las citas tipo `(deploy.rst:182)` apuntan a
> `vendor/odoo-docs/content/administration/on_premise/deploy.rst`; las
> tipo `(cli.rst:590)` a
> `vendor/odoo-docs/content/developer/reference/cli.rst`. Todas
> verificadas contra la rama 19.0 al redactar.

---

## Resumen ejecutivo — matriz por tamaño

Etapas orientativas; el dimensionado real depende del perfil de uso
(intensidad de EDI, reporting, e-commerce, etc.), no solo del nº de
usuarios.

| Etapa | Usuarios concurrentes | Topología | Acciones clave |
|---|---|---|---|
| **S** | < 30 | 1 nodo (Odoo + PG en misma VM, contenedores doodba) | Multi-process, Nginx + TLS + X-Sendfile, `limit_*` ajustados, backups. Cron en mismo nodo. |
| **M** | 30 – 150 | 1 nodo Odoo + PG dedicado en otra VM | Tunear PG (`shared_buffers`, `work_mem`, `max_connections`). Instalar `queue_job` y mover EDI / SII / batch a jobs async. Vigilar `limit_time_real` hits. Filestore en disco rápido o NFS. |
| **L** | 150 + | LB → N nodos HTTP + 1 nodo cron+gevent+queue_job + PG primario + réplica de lectura | Filestore externo (NFS/EFS o S3 vía OCA `base_attachment_object_storage`). Sesiones compartidas o sticky `session_id`. CDN para `/web/assets`. PgBouncer en modo `session`. Réplica PG para reporting/BI. Monitorización (Prometheus, `pg_stat_statements`). |

> **Regla de transición**: no escalar horizontalmente hasta haber
> agotado la verticalización del nodo único. La mayoría de problemas
> de "Odoo va lento" se resuelven antes con (a) tunear workers + PG,
> (b) reescribir un par de campos computados o vistas mal diseñadas,
> (c) mover el batch pesado a `queue_job`. Saltar a multi-nodo sin
> esto añade complejidad sin resolver el cuello de botella real.

---

## 1. Servidor multi-proceso (workers)

Odoo trae dos servidores integrados (`deploy.rst:182`):

- **Multi-thread** (default Docker): un hilo por request. Limitado por
  el GIL de Python → solo desarrollo / demos / Windows.
- **Multi-process**: pool de procesos worker + reaper, escapa al GIL,
  **es el modo de producción** y solo está disponible en Linux
  (`deploy.rst:204`).

Se activa con `--workers N > 0` (`cli.rst:590`).

### Cálculo de workers

Reglas oficiales (`deploy.rst:208-213`):

- `workers = (#CPU * 2) + 1`
- `1 worker ≈ 6 usuarios concurrentes`
- Los cron workers también consumen CPU → contar aparte.

### Cálculo de RAM

Modelo oficial (`deploy.rst:215-222`): se asume 80 % de requests
ligeros (~150 MB) y 20 % pesados (~1 GB). RAM total estimada:

```
RAM = #workers * (0.8 * 150 MB + 0.2 * 1024 MB)
    ≈ #workers * 325 MB
```

A esto hay que sumar el worker gevent, los cron workers, RAM para PG
si está en la misma máquina, y margen para el SO.

### Ejemplo oficial

`deploy.rst:237-256`: 4 CPU / 8 hilos, 60 usuarios concurrentes.

- Teórico necesario: `60 / 6 = 10` workers.
- Teórico máximo: `(4 * 2) + 1 = 9` workers.
- Decisión: 8 HTTP workers + 1 cron, ~3 GB RAM solo para Odoo.

### Snippet `odoo.conf` con `limit_*`

Flags definidos en `cli.rst:600-637`:

```ini
[options]
workers = 8                           ; HTTP workers (multi-process)
max_cron_threads = 2                  ; cron workers (procesos extra)

; Reciclaje por requests (evita fugas de memoria acumuladas)
limit_request = 8192

; Reciclaje por memoria
limit_memory_soft = 2147483648        ; 2 GiB — kill al final del request
limit_memory_hard = 2684354560        ; 2.5 GiB — kill inmediato

; Reciclaje por tiempo
limit_time_cpu = 60                   ; CPU seconds por request
limit_time_real = 120                 ; wall time — mata SQL colgadas

; Cron workers (opcional, default 0 = sin límite)
limit_time_worker_cron = 0
```

El **reaper** mata el worker en cuanto cruza el `soft` (al final del
request en curso) o el `hard` (inmediato). Los hits frecuentes de
`limit_memory_hard` son señal de fuga; los de `limit_time_real`
suelen ser N+1 en ORM o `compute` no almacenado disparándose en bucle.

### Traducción a doodba (`docker-compose.override.yml`)

doodba lee variables de entorno y las traduce a `odoo.conf` en
`entrypoint`. Variables relevantes (consulta el README de
`Tecnativa/doodba` para la lista completa):

```yaml
services:
  odoo:
    environment:
      WORKERS: 8
      LIMIT_TIME_CPU: 60
      LIMIT_TIME_REAL: 120
      LIMIT_TIME_REAL_CRON: 600
      LIMIT_MEMORY_SOFT: 2147483648
      LIMIT_MEMORY_HARD: 2684354560
      LIMIT_REQUEST: 8192
      MAX_CRON_THREADS: 2
      PROXY_MODE: "true"
```

Si la imagen base no expone alguna variable, sobreescribir
directamente `auto/odoo.conf` o pasar flags vía `command:` en el
override.

---

## 2. Worker gevent dedicado (websocket / Discuss)

En multi-process, Odoo arranca automáticamente un worker
event-driven en `--gevent-port` (default `8072`) para `/websocket/`
(`deploy.rst:224-232`). Sin él, las conexiones long-poll del módulo
Discuss y las notificaciones en vivo saturan los workers HTTP
normales y degradan la latencia general.

Requisitos para que funcione bien:

- `proxy_mode = True` en `odoo.conf` (`deploy.rst:268`).
- Reverse proxy que rutee `/websocket/*` al puerto gevent — ver
  bloque nginx canónico en `deploy.rst:294-340`:

```nginx
upstream odoo      { server 127.0.0.1:8069; }
upstream odoochat  { server 127.0.0.1:8072; }   # gevent

location /websocket {
    proxy_pass http://odoochat;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;
}
```

En topología multi-nodo (etapa **L**), el worker gevent suele vivir
en el nodo "no HTTP" junto al cron y a los runners de `queue_job`
(ver §7).

---

## 3. Cron workers separados

`max_cron_threads` arranca procesos cron **además** de los HTTP
workers (`cli.rst:639-644`). En despliegues WSGI o multi-nodo, el
patrón idiomático es un proceso/contenedor Odoo dedicado con
(`deploy.rst:399-410`):

```
odoo-bin --workers=-1 --max-cron-threads=N --no-http
```

Esto:

- Garantiza que un cron pesado (informes, EDI, vacuum) **nunca**
  bloquea respuestas HTTP a usuarios.
- Permite escalar workers HTTP y cron en máquinas distintas.
- Ese mismo proceso puede servir `/websocket/` retirando `--no-http`
  y enrutando con el `gevent-port` (`deploy.rst:421-425`).

En doodba multi-nodo: definir un servicio `odoo-cron` aparte del
`odoo` HTTP, compartiendo `addons_path`, filestore y DB.

---

## 4. Reverse proxy (Nginx)

Capa imprescindible incluso en etapa **S**. Bloque canónico en
`deploy.rst:286-359`. Funciones:

- **Terminación TLS** + HSTS + redirect HTTP→HTTPS.
- **Compresión gzip** de `/web/assets/*` y respuestas JSON.
- **Routing websocket** a `--gevent-port` (§2).
- **`proxy_mode = True`** en Odoo: el ORM lee cabeceras reales
  (`X-Forwarded-*`) en lugar de las del proxy (`deploy.rst:268`).
- **Servir estáticos directamente** sin pasar por Odoo
  (`deploy.rst:429-507`): los `static/` de cada módulo se sirven
  desde el FS, con `Content-Security-Policy: default-src 'none'`.
- **`X-Sendfile` / `X-Accel`** para filestore (`deploy.rst:509-543`):
  Odoo verifica permisos pero la transferencia del binario la hace
  Nginx. Reduce I/O y memoria de los workers en cuanto hay descargas
  recurrentes (PDFs de facturas, fotos de productos, adjuntos
  pesados). Activa con `--x-sendfile` + bloque:

```nginx
location /web/filestore {
    internal;
    alias /path/to/odoo/data-dir/filestore;
    add_header Content-Security-Policy $upstream_http_content_security_policy;
    add_header X-Content-Type-Options nosniff;
}
```

> El path exacto se descubre arrancando Odoo con `--x-sendfile` y
> visitando `/web/filestore` directamente vía Odoo: la advertencia
> en logs contiene la config necesaria (`deploy.rst:540-543`).

---

## 5. PostgreSQL bajo carga

Cuando los workers están bien dimensionados, el siguiente cuello de
botella es siempre PostgreSQL. La documentación upstream solo cubre
conectividad básica (`deploy.rst:75-114`); el resto es práctica de
campo estándar.

### Conexiones

Cada worker abre su propio pool de conexiones:

```
max_connections ≥ workers + max_cron_threads + 1 (gevent) + margen
```

Por nodo Odoo. En etapa **L** con varios nodos, multiplicar.

### PgBouncer

En multi-nodo o cuando `max_connections` se dispara:

- Modo **`session`**: seguro con Odoo. Mantén la conexión durante
  toda la sesión cliente.
- Modo **`transaction`**: **no usar**. Odoo emplea `SET LOCAL`,
  advisory locks (`pg_advisory_xact_lock`, base de `Environment`) y
  prepared statements; el modo transaction rompe estas garantías.
- Modo **`statement`**: incompatible.

### Tuning básico (referencia, no recetario)

```
shared_buffers           ≈ 25 % RAM
effective_cache_size     ≈ 75 % RAM
work_mem                 ajustar por carga (cuidado: es por sort/hash, no por conexión)
maintenance_work_mem     1-2 GB (ayuda a VACUUM, REINDEX)
checkpoint_completion_target = 0.9
wal_compression          on
random_page_cost         1.1 (SSD/NVMe)
```

### Topología

- **Etapa S/M**: PG en misma máquina (S) o VM dedicada (M)
  conectado por TCP/SSL (`deploy.rst:165-175`).
- **Etapa L**: primario + réplica streaming. Odoo no usa réplicas de
  lectura nativamente, pero:
  - El reporting y BI pesado puede apuntar a la réplica (vía
    conexiones DB directas, no Odoo).
  - Algunas integraciones OCA permiten redirigir queries
    específicas, pero la regla segura es: **escrituras al primario,
    extracción analítica a la réplica**.

### Observabilidad

Imprescindible en M+:

- `pg_stat_statements` activado (extension).
- `auto_explain` con `auto_explain.log_min_duration` para capturar
  planes de queries lentas.
- Slow query log de PG.
- En Odoo: `--log-handler odoo.sql_db:DEBUG` puntualmente para cazar
  N+1.

---

## 6. Filestore externalizado

Por defecto el filestore vive en `data_dir/filestore/<dbname>/`
(local al contenedor Odoo). Multi-nodo o backups serios obligan a
externalizarlo.

### Opciones

| Opción | Cuándo | Notas |
|---|---|---|
| **Disco local rápido** (NVMe) | Etapa S/M, un solo nodo | Más simple. Backup = snapshot del volumen + dump PG. |
| **NFS / EFS** | Multi-nodo en mismo VPC / DC | Compartido por todos los nodos Odoo. Cuidado con latencia (afecta a vista de adjuntos). |
| **S3 / MinIO** vía OCA `base_attachment_object_storage` | L+, o cuando el filestore crece a TB | Reduce I/O del nodo, permite lifecycle (Glacier para adjuntos viejos), CDN para servirlos. Requiere instalar y configurar el módulo OCA correspondiente. |

### Sesiones

Las sesiones HTTP de Odoo se serializan a fichero en
`data_dir/sessions/`. En multi-nodo, dos opciones:

- **Compartir** `sessions/` por NFS junto al filestore.
- **Sticky sessions** en el LB sobre la cookie `session_id` (más
  simple, pero un nodo caído tira las sesiones que tenía pegadas).

> Etapa M con un solo nodo: no hay problema, sessions están en local.

---

## 7. Escalado horizontal multi-nodo (etapa L)

Topología de referencia:

```
                            ┌─ odoo-http-1 (workers HTTP)
LB (HAProxy / Nginx) ──────┼─ odoo-http-2 (workers HTTP)
   sticky session_id        ├─ odoo-http-N (workers HTTP)
                            │
                            └─ odoo-bg-1   (cron + gevent + queue_job runner)
                                  --workers=-1 --max-cron-threads=4
                                  --gevent-port habilitado para /websocket

                  ┌── PG primario ── streaming ──> PG réplica (read-only / BI)
                  └── Filestore + sessions  (NFS o S3)
```

Reglas:

- Mismo `addons_path` y misma versión exacta en todos los nodos. Con
  doodba esto se garantiza vía `repos.yaml` + `gitaggregate`
  (gestionado por la skill `odoo-module-admin`).
- DB **única** — Odoo no soporta sharding nativo. La escalabilidad
  horizontal vale para front HTTP, no para datos.
- Filestore + `sessions/` compartidos (o sticky sessions, ver §6).
- LB distribuye HTTP entre los `odoo-http-*`; `/websocket` siempre
  va al nodo `odoo-bg`.
- Despliegues rolling: drenar tráfico de un nodo en el LB, aplicar
  upgrade de módulos en `odoo-bg` (que tiene `--no-http`), restaurar.

---

## 8. OCA `queue_job` — async para picos

No está en los docs upstream, pero es **la** herramienta canónica
del ecosistema OCA para absorber carga asíncrona. Repo OCA: `queue`.

### Qué hace

Convierte llamadas a métodos en jobs persistidos en `queue.job` con:

- Reintentos con backoff configurable.
- Prioridades.
- **Channels** (capacidades por tipo de carga; p. ej. canal `edi`
  con concurrencia 2, canal `pdf` con concurrencia 4).
- Runner dedicado (HTTP daemon `queue_job` runner) o ejecución sobre
  workers HTTP normales.

### Casos típicos previstos en `fedefarma`

- **Facturación masiva** de fin de mes: mover el `action_post`
  iterado a jobs por chunks.
- **Envíos SII / Veri\*Factu / FacturaE** en lote: si AEAT tarda 30 s
  en responder, el usuario no debe esperar.
- **Importación / sincronización** con sistemas externos (PIM, WMS).
- **Generación masiva de PDFs** (facturas mensuales, packing lists).
- **Recálculos** pesados de stock, costes, márgenes.

### Integración doodba

Añadir el repo a `repos.yaml`:

```yaml
./odoo/custom/src/queue:
  defaults:
    depth: 1
  remotes:
    oca: https://github.com/OCA/queue.git
  target:
    oca 19.0
  merges:
    - oca 19.0
```

Incluir `queue_job` (y opcionalmente `queue_job_cron`,
`queue_job_subscribe`, etc.) en `addons.yaml`. La skill
`odoo-module-admin` se encarga del install/upgrade.

Configurar el runner en `odoo.conf`:

```ini
[queue_job]
channels = root:1,edi:2,pdf:4
```

Y exponer su endpoint HTTP solo en red interna.

---

## 9. Higiene de código y datos

Bajo carga, la diferencia entre "fluido" y "lento" suele estar aquí
más que en el dimensionado físico.

### Modelado

- **Campos computados**: decidir `store=True` con `depends`
  correcto **solo** cuando se usa para filtrar, ordenar, agrupar o
  exportar. Si es decorativo, no almacenar — el storage tiene su
  coste de actualización.
- **Índices explícitos**: `index=True` en M2O y `Char` que aparezcan
  en filtros frecuentes; índices funcionales SQL para casos
  específicos (lower, GIN para JSONB).
- **`ondelete='restrict'`** o cascadas costosas: revisar en tablas
  grandes (`account.move.line`, `stock.move.line`).

### Acceso

- Evitar bucles `for record in recordset: record.x` cuando se puede
  hacer `recordset.mapped('x')` o `read_group`.
- `prefetch_fields` y batch reads.
- `with_context(prefetch_fields=False)` cuando el patrón no se
  beneficia.

### Datos históricos

Tablas que crecen sin freno y degradan listados:

- `mail.message`, `mail.tracking.value`, `mail.notification`.
- `bus.bus` (limpieza vía `gc` periódico).
- `ir.attachment` (mover a S3 con OCA storage).
- `account.move.line` (no se borra; se archiva por ejercicio
  cerrado y se índiza).

OCA `mail`/`server-tools` aporta vacuum jobs configurables.

### Profiling

- `--log-handler odoo.sql_db:DEBUG` puntualmente.
- Module `odoo` profiler `/odoo/profiler/...` (Settings → Developer).
- `EXPLAIN (ANALYZE, BUFFERS)` en PG para planes reales.

---

## 10. Monitorización y alertas

Etapa M+: imprescindible. Recomendado desde S si el cliente es
crítico.

### Métricas

- **OCA `prometheus_exporter`** (repo OCA `server-tools`): expone
  `/metrics` con workers vivos, cola HTTP, errores, hits de
  `limit_*`, queries lentas, tamaño de tablas.
- **`pg_stat_statements`** + exportador a Prometheus
  (`postgres_exporter`).
- **node_exporter** en cada VM (CPU, RAM, disco, red).

### Alertas mínimas

- CPU sostenida > 80 % durante > 5 min.
- Cola HTTP creciente (workers ocupados al 100 %).
- Hits frecuentes de `limit_memory_hard` → fuga.
- Hits frecuentes de `limit_time_real` → query lenta o N+1.
- Réplica PG con `replication_lag > X s`.
- `queue.job` con jobs en estado `failed` > N.
- Filestore al 80 % de capacidad.

### Watchdog de CPU

El ejemplo oficial (`deploy.rst:242`) sugiere monitorizar la carga
en una máquina de 8 hilos para mantenerla en el rango **7 – 7,5**:
señal de aprovechamiento sin saturación. Es una regla de pulgar útil
para decidir cuándo añadir un nodo.

---

## Apéndice — checklist por etapa

### Etapa S (< 30 usuarios)

- [ ] Multi-process activo (`workers ≥ 1`).
- [ ] `max_cron_threads ≥ 1`.
- [ ] `limit_memory_*`, `limit_time_*`, `limit_request` ajustados.
- [ ] Nginx con TLS, HSTS, gzip, `proxy_mode = True`.
- [ ] `/websocket` ruteado al `--gevent-port`.
- [ ] `--x-sendfile` + bloque `/web/filestore` interno.
- [ ] Backups diarios PG + filestore, con copia off-site
      (`deploy.rst:651`).
- [ ] `dbfilter` configurado, `list_db = False`
      (`deploy.rst:576-587`).

### Etapa M (30 – 150 usuarios)

Todo lo anterior, más:

- [ ] PG en VM dedicada con TLS.
- [ ] Tuning PG (`shared_buffers`, `work_mem`, `effective_cache_size`).
- [ ] `pg_stat_statements` + `auto_explain` activos.
- [ ] OCA `queue_job` instalado; EDI / SII / batch movidos a jobs.
- [ ] Filestore en disco rápido o NFS.
- [ ] Monitorización Prometheus + alertas mínimas.
- [ ] Vacuum / archivado configurado para `mail.message`,
      `bus.bus`, `mail.tracking.value`.

### Etapa L (150+ usuarios)

Todo lo anterior, más:

- [ ] LB con sticky `session_id` o sesiones compartidas.
- [ ] N nodos `odoo-http-*` + 1 nodo `odoo-bg`
      (cron + gevent + `queue_job` runner).
- [ ] Filestore en S3 / MinIO vía OCA
      `base_attachment_object_storage`, o NFS/EFS.
- [ ] PgBouncer en modo `session` delante de PG.
- [ ] Réplica PG streaming para BI / reporting offload.
- [ ] CDN para `/web/assets/*` (assets versionados por hash).
- [ ] Plan de despliegue rolling documentado.
- [ ] Runbook de incidencias ligado a métricas Prometheus.

---

## Referencias

- `vendor/odoo-docs/content/administration/on_premise/deploy.rst`
  — System configuration (sección canónica).
- `vendor/odoo-docs/content/developer/reference/cli.rst`
  — todos los flags `--workers`, `--limit-*`,
  `--max-cron-threads`, `--gevent-port`, `--x-sendfile`.
- `Tecnativa/doodba` README — variables de entorno expuestas en la
  imagen.
- OCA `queue` — https://github.com/OCA/queue
- OCA `storage` — https://github.com/OCA/storage
  (`base_attachment_object_storage`, `cloud_storage_*`).
- OCA `server-tools` — https://github.com/OCA/server-tools
  (`prometheus_exporter`, vacuum modules).
