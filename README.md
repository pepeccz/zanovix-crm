<div align="center">

<pre>
                  _____                         _        ____ ____  __  __
                 |__  /__ _ _ __   _____   ___(_)_  __ / ___|  _ \|  \/  |
                   / // _` | '_ \ / _ \ \ / / | \ \/ /| |   | |_) | |\/| |
                  / /| (_| | | | | (_) \ V /| | |>  < | |___|  _ <| |  | |
                 /____\__,_|_| |_|\___/ \_/ |_|_/_/\_\ \____|_| \_\_|  |_|

              +---------------------------------------------------------+
              |  LEADS       PIPELINE        CLIENTS        SERVICES    |
              |                                                         |
              |  public  --> qualify  --> convert  --> deliver/support  |
              |  intake      RBAC         billing      client portal     |
              |                                                         |
              +---------------------------------------------------------+
</pre>

<h1>Zanovix CRM</h1>

<p><strong>CRM operativo para capturar leads, convertirlos en clientes y gestionar servicios, facturación y soporte desde un panel interno.</strong></p>

<p>
  <a href="https://github.com/pepeccz/zanovix-crm"><img src="https://img.shields.io/badge/repo-GitHub-181717.svg?logo=github" alt="GitHub repo"></a>
  <img src="https://img.shields.io/badge/python-3.11+-3776AB.svg?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Next.js-16-000000.svg?logo=nextdotjs&logoColor=white" alt="Next.js 16">
  <img src="https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black" alt="React 19">
  <img src="https://img.shields.io/badge/PostgreSQL-15-4169E1.svg?logo=postgresql&logoColor=white" alt="PostgreSQL 15">
  <img src="https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis&logoColor=white" alt="Redis 7">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED.svg?logo=docker&logoColor=white" alt="Docker ready">
</p>

</div>

---

## Que Hace

Zanovix CRM centraliza el ciclo comercial y operativo de Zanovix: recibe leads desde formularios publicos, permite calificarlos con roles internos, convertirlos en clientes, gestionar servicios contratados, mantener historico de actividad, configurar perfiles de facturacion y abrir un portal para clientes.

El proyecto combina una API FastAPI asincrona, PostgreSQL, Redis y un panel administrativo en Next.js. La arquitectura esta pensada para que las rutas HTTP sean delgadas y la logica de negocio viva en servicios y maquinas de estado.

```
Lead publico -> CRM interno -> Cliente -> Servicio -> Portal cliente
      |              |            |          |              |
 rate limit       RBAC      billing profile milestones     tickets
 raw payload      JWT       activity log     diagnostics   messages
```

---

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Servicios disponibles por defecto:

| Servicio | URL |
|----------|-----|
| API FastAPI | `http://localhost:8010` |
| Healthcheck API | `http://localhost:8010/health` |
| Admin Panel | `http://localhost:8011` |
| PostgreSQL local | `127.0.0.1:5433` |
| Redis local | `127.0.0.1:6380` |

Crear datos base:

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed_all
```

Usuarios semilla de desarrollo:

| Rol | Email | Password por defecto |
|-----|-------|----------------------|
| Admin | `admin@zanovix.com` | `dev-changeme-admin` |
| Consultor | `consultor@zanovix.com` | `dev-changeme-consultor` |
| Comercial | `comercial@zanovix.com` | `dev-changeme-comercial` |

> En staging o produccion, define siempre `SEED_ADMIN_PASSWORD`, `SEED_CONSULTOR_PASSWORD` y `SEED_COMERCIAL_PASSWORD` antes de ejecutar los seeds.

---

## Features

- **Captura publica de leads**: endpoint publico `POST /api/leads` con rate limiting por IP.
- **Gestion comercial interna**: leads, clientes, pipeline, usuarios, equipo y servicios desde el admin panel.
- **RBAC por rol**: `admin`, `comercial`, `consultor` y `client_user` con visibilidad filtrada.
- **Autenticacion JWT**: bearer token y cookie `admin_token` httpOnly para el panel.
- **Blacklist de logout en Redis**: revoca tokens por `jti` hasta su expiracion.
- **Maquinas de estado**: transiciones controladas para leads, clientes y servicios.
- **Conversion lead -> cliente**: conversion atomica de leads cualificados a clientes.
- **Perfiles de facturacion**: multiples perfiles por cliente con perfil por defecto.
- **Portal cliente**: rutas `/api/me/*` para servicios, actividad, mensajes, tickets y diagnosticos.
- **Actividad auditable**: registro de eventos comerciales y operativos.
- **Panel Next.js standalone**: preparado para despliegue en Docker con rewrites hacia la API.
- **Headers de seguridad**: CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` y `Permissions-Policy`.
- **Testing backend**: pytest con tests unitarios e integracion usando `pytest-asyncio` y `testcontainers`.
- **Testing frontend**: Jest + React Testing Library en el admin panel.

---

## Arquitectura

```
Browser
  |
  v
Next.js Admin Panel / Client Portal
  |
  |  rewrites /api/* and /health
  v
FastAPI API
  |
  +--> PostgreSQL 15  (SQLAlchemy async + Alembic)
  |
  +--> Redis 7        (JWT blacklist, rate limiting)
```

La separacion principal del backend es:

| Capa | Responsabilidad | Ubicacion |
|------|-----------------|-----------|
| Rutas HTTP | Validar entrada, aplicar dependencias, serializar salida | `api/routes/` |
| Servicios | Reglas de negocio, permisos de dominio, escrituras | `api/services/` |
| Dominio | Maquinas de estado, sanitizacion, constantes de actividad | `api/domain/` |
| Esquemas | Contratos Pydantic de entrada/salida | `api/schemas/` |
| Modelos | Entidades SQLAlchemy | `database/models/` |
| Migraciones | Versionado de schema | `database/alembic/` |
| Configuracion | Variables de entorno tipadas | `shared/config.py` |

La separacion principal del frontend es:

| Capa | Responsabilidad | Ubicacion |
|------|-----------------|-----------|
| App Router | Rutas del admin y portal cliente | `admin-panel/src/app/` |
| Componentes UI | Primitivas reutilizables Radix/Tailwind | `admin-panel/src/components/ui/` |
| Componentes compartidos | Layout, KPI, tablas y bloques de dominio | `admin-panel/src/components/shared/` |
| Cliente API | Acceso tipado al backend | `admin-panel/src/lib/api.ts` |
| Tipos TS | Contratos compartidos del panel | `admin-panel/src/lib/types.ts` |
| i18n | Traducciones y request config | `admin-panel/src/i18n/` |

---

## Modelo De Dominio

| Entidad | Proposito |
|---------|-----------|
| `User` | Usuario interno o usuario de cliente, con rol y estado activo/inactivo |
| `Lead` | Oportunidad entrante desde canal publico o carga manual |
| `Client` | Cuenta comercial convertida o creada directamente |
| `Contact` | Contactos asociados a un cliente |
| `Service` | Servicio vendido o en ejecucion para un cliente |
| `Milestone` | Hitos de un servicio |
| `ActivityLog` | Historial de actividad del cliente, lead o servicio |
| `BillingProfile` | Datos fiscales/facturacion de un cliente |
| `Message` | Mensajeria del portal cliente |
| `Ticket` | Solicitudes de soporte del cliente |

### Estados De Lead

| Estado | Transiciones permitidas |
|--------|--------------------------|
| `new` | `contacted`, `disqualified` |
| `contacted` | `qualified`, `disqualified` |
| `qualified` | `converted`, `disqualified` |
| `disqualified` | Terminal |
| `converted` | Terminal |

### Stages De Cliente

| Stage | Uso |
|-------|-----|
| `lead` | Cliente recien creado o convertido |
| `discovery_scheduled` | Discovery agendado |
| `discovery_done` | Discovery realizado |
| `proposal_sent` | Propuesta enviada |
| `active` | Cliente activo |
| `lost` | Cliente perdido |

### Estados De Servicio

| Estado | Uso |
|--------|-----|
| `scoping` | Alcance inicial |
| `running` | Ejecucion activa |
| `review` | Revision final o validacion |
| `completed` | Servicio completado |
| `maintenance` | Mantenimiento o soporte recurrente |
| `paused` | Servicio pausado |

---

## API Reference

### Autenticacion

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| `POST` | `/api/auth/login` | Publica | Login con email/password; devuelve JWT y setea cookie httpOnly |
| `POST` | `/api/auth/logout` | JWT | Revoca el token actual en Redis |
| `GET` | `/api/auth/me` | JWT | Devuelve el usuario autenticado |

### Leads

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| `POST` | `/api/leads` | Publica + rate limit | Crea un lead desde formulario publico |
| `GET` | `/api/leads` | JWT | Lista leads con filtros y scope RBAC |
| `GET` | `/api/leads/{lead_id}` | JWT | Obtiene un lead accesible para el usuario |
| `PATCH` | `/api/leads/{lead_id}` | JWT | Edita campos no relacionados con status |
| `PATCH` | `/api/leads/{lead_id}/status` | JWT | Cambia estado usando maquina de estados |
| `PATCH` | `/api/leads/{lead_id}/assign` | Admin | Asigna owner del lead |
| `POST` | `/api/leads/{lead_id}/convert` | Admin/Comercial | Convierte lead cualificado en cliente |

### Clientes Y Operacion

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| `POST` | `/api/clients` | Admin/Comercial | Crea cliente |
| `GET` | `/api/clients` | JWT | Lista clientes con filtros y scope RBAC |
| `GET` | `/api/clients/{client_id}` | JWT | Detalle con contactos, servicios, billing y actividad |
| `PATCH` | `/api/clients/{client_id}` | Admin/Comercial | Edita metadata del cliente |
| `PATCH` | `/api/clients/{client_id}/stage` | Admin/Comercial | Cambia stage con maquina de estados |
| `GET` | `/api/clients/{client_id}/contacts` | JWT | Lista contactos del cliente |
| `POST` | `/api/clients/{client_id}/contacts` | Admin/Comercial | Crea contacto |
| `PATCH` | `/api/clients/{client_id}/contacts/{contact_id}` | Admin/Comercial | Edita contacto |
| `DELETE` | `/api/clients/{client_id}/contacts/{contact_id}` | Admin | Elimina contacto |
| `GET` | `/api/activity` | Admin | Lista actividad global, opcionalmente filtrada por `client_id` |
| `GET` | `/api/clients/{client_id}/messages` | Admin/Consultor/Comercial | Lista mensajes del cliente |
| `POST` | `/api/clients/{client_id}/messages` | Admin/Consultor | Envia mensaje al cliente |
| `GET` | `/api/clients/{client_id}/tickets` | Admin/Consultor/Comercial | Lista tickets del cliente |
| `GET` | `/api/tickets/{ticket_id}` | Admin/Consultor/Comercial | Obtiene ticket |
| `PATCH` | `/api/tickets/{ticket_id}` | Admin/Consultor/Comercial | Actualiza ticket; comercial no puede cambiar status |

### Servicios, Milestones Y Facturacion

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| `GET` | `/api/services` | JWT | Lista servicios con filtros y scope RBAC |
| `GET` | `/api/services/{service_id}` | JWT | Detalle de servicio con milestones |
| `POST` | `/api/clients/{client_id}/services` | Admin/Comercial | Crea servicio para un cliente |
| `PATCH` | `/api/services/{service_id}` | JWT | Edita metadata del servicio segun permisos |
| `PATCH` | `/api/services/{service_id}/state` | JWT | Cambia estado del servicio |
| `GET` | `/api/services/{service_id}/milestones` | JWT | Lista milestones |
| `POST` | `/api/services/{service_id}/milestones` | JWT | Crea milestone |
| `PATCH` | `/api/services/{service_id}/milestones/{n}` | JWT | Edita milestone por indice `n` |
| `DELETE` | `/api/services/{service_id}/milestones/{n}` | Admin | Elimina milestone por indice `n` |
| `POST` | `/api/clients/{client_id}/billing-profiles` | Admin/Comercial | Crea perfil de facturacion |
| `GET` | `/api/clients/{client_id}/billing-profiles` | Admin/Comercial | Lista perfiles del cliente |
| `GET` | `/api/billing-profiles/{profile_id}` | Admin/Comercial | Obtiene perfil |
| `PATCH` | `/api/billing-profiles/{profile_id}` | Admin/Comercial | Edita perfil |
| `DELETE` | `/api/billing-profiles/{profile_id}` | Admin/Comercial | Elimina perfil |
| `PATCH` | `/api/billing-profiles/{profile_id}/default` | Admin/Comercial | Marca perfil como default |

### Portal Cliente

Estas rutas solo estan disponibles si `CLIENT_PORTAL_ENABLED=true`.

| Metodo | Ruta | Auth | Descripcion |
|--------|------|------|-------------|
| `GET` | `/api/me/client` | `client_user` | Cliente asociado al usuario actual |
| `GET` | `/api/me/services` | `client_user` | Servicios propios |
| `GET` | `/api/me/services/{service_id}` | `client_user` | Detalle de servicio propio |
| `GET` | `/api/me/services/{service_id}/diagnostic` | `client_user` | Diagnostico de assessment |
| `GET` | `/api/me/contacts` | `client_user` | Contactos propios |
| `GET` | `/api/me/activity` | `client_user` | Actividad propia |
| `GET` | `/api/me/messages` | `client_user` | Mensajes, soporta `?since=` |
| `POST` | `/api/me/messages` | `client_user` | Envia mensaje |
| `GET` | `/api/me/tickets` | `client_user` | Tickets propios |
| `POST` | `/api/me/tickets` | `client_user` | Abre ticket |
| `PATCH` | `/api/me/tickets/{ticket_id}` | `client_user` | Edita ticket propio sin cambiar status |

### Healthcheck

```json
{
  "status": "healthy",
  "service": "Zanovix CRM",
  "redis": "connected",
  "postgres": "connected"
}
```

---

## Configuracion

La configuracion se centraliza en `shared/config.py`. La aplicacion lee `.env` mediante Pydantic Settings.

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `PROJECT_NAME` | `Zanovix CRM` | Nombre del servicio |
| `ENVIRONMENT` | `development` | Entorno logico |
| `DATABASE_URL` | `postgresql+asyncpg://zanovix:changeme@postgres:5432/zanovix_crm` | URL async de PostgreSQL |
| `POSTGRES_DB` | `zanovix_crm` | Nombre de base de datos |
| `POSTGRES_USER` | `zanovix` | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | `changeme` | Password PostgreSQL |
| `POSTGRES_HOST` | `postgres` | Host PostgreSQL dentro de Docker |
| `POSTGRES_PORT` | `5432` | Puerto PostgreSQL dentro de Docker |
| `REDIS_URL` | `redis://redis:6379/0` | URL de Redis |
| `REDIS_PASSWORD` | vacio | Password de Redis |
| `JWT_SECRET_KEY` | `change-me-in-production-min-32-chars-secret` | Secreto de firma JWT |
| `JWT_ALGORITHM` | `HS256` | Algoritmo JWT |
| `JWT_EXPIRE_MINUTES` | `1440` | TTL del token en minutos |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Ventana de rate limit |
| `RATE_LIMIT_MAX_REQUESTS` | `20` | Maximo de requests por ventana |
| `IP_HASH_SALT` | `change-me-random-salt` | Salt para hashear IPs |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:8000,http://localhost:8001` | Origenes CORS permitidos |
| `TRUSTED_PROXIES` | vacio | Proxies confiables para `X-Forwarded-For` |
| `LOG_LEVEL` | `INFO` | Nivel de logging |
| `SENTRY_DSN` | vacio | DSN de Sentry |
| `SEED_ADMIN_PASSWORD` | `admin123` en settings, seed usa fallback dev | Password admin para seed |
| `SEED_CONSULTOR_PASSWORD` | `consultor123` en settings, seed usa fallback dev | Password consultor para seed |
| `SEED_COMERCIAL_PASSWORD` | `comercial123` en settings, seed usa fallback dev | Password comercial para seed |
| `CLIENT_PORTAL_ENABLED` | `true` | Monta o desactiva `/api/me/*` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8010` en Docker Compose | URL publica usada por el admin panel |
| `INTERNAL_API_URL` | `http://api:8000` | URL interna usada por rewrites de Next.js |

Variables que DEBEN cambiar en produccion:

- `JWT_SECRET_KEY`
- `IP_HASH_SALT`
- `POSTGRES_PASSWORD`
- `REDIS_PASSWORD`
- `SEED_ADMIN_PASSWORD`
- `SEED_CONSULTOR_PASSWORD`
- `SEED_COMERCIAL_PASSWORD`
- `CORS_ORIGINS`

---

## Desarrollo

### Backend Local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed_all
uvicorn api.main:app --reload --port 8010
```

### Frontend Local

```bash
cd admin-panel
npm install
npm run dev
```

Por defecto, el panel usa rutas relativas y `next.config.ts` proxya `/api/*` y `/health` hacia `INTERNAL_API_URL` o `http://api:8000` en Docker.

### Migraciones

```bash
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "describe change"
```

### Seeds

```bash
python -m scripts.seed_users
python -m scripts.seed_demo_leads
python -m scripts.seed_all
```

---

## Testing

### Backend

```bash
pytest
pytest tests/unit
pytest tests/integration
pytest --cov=api --cov=database --cov=shared
```

### Frontend

```bash
cd admin-panel
npm test
npm run test:coverage
```

### Linting

```bash
ruff check .
cd admin-panel && npm run lint
```

> Nota: este README no ejecuta builds. El proyecto tiene Dockerfiles de produccion, pero las verificaciones de build deben ejecutarse cuando el entorno tenga recursos suficientes.

---

## Estructura Del Proyecto

```text
zanovix-crm/
├── api/                         # FastAPI: rutas, servicios, schemas, auth, dominio
├── database/                    # SQLAlchemy models + Alembic migrations
├── shared/                      # Config, Redis, logging, rate limiter, errores comunes
├── scripts/                     # Seeds y utilidades operativas
├── tests/                       # Tests unitarios e integracion backend
├── admin-panel/                 # Next.js 16 + React 19 admin/client portal
├── docker/                      # Dockerfiles API y admin panel
├── docker-compose.yml           # PostgreSQL, Redis, API y admin panel
├── requirements.txt             # Dependencias Python
├── pyproject.toml               # Config pytest
└── alembic.ini                  # Config migraciones
```

---

## Admin Panel

Rutas principales encontradas en `admin-panel/src/app/`:

| Ruta | Proposito |
|------|-----------|
| `/login` | Login interno |
| `/dashboard` | KPIs, funnel y actividad reciente |
| `/leads` | Bandeja y gestion de leads |
| `/leads/[id]` | Detalle de lead |
| `/clients` | Listado de clientes |
| `/clients/[id]` | Detalle de cliente |
| `/pipeline` | Vista de pipeline comercial |
| `/services/[id]` | Detalle de servicio |
| `/team` | Equipo interno |
| `/users` | Usuarios |
| `/users/[id]` | Detalle de usuario |
| `/settings/config` | Configuracion funcional |
| `/settings/system` | Estado de sistema |
| `/settings/admin-users` | Administracion de usuarios internos |

Portal cliente encontrado en `admin-panel/src/app/(client-portal)/client/`:

| Ruta | Proposito |
|------|-----------|
| `/client` | Home del cliente |
| `/client/projects` | Proyectos/servicios |
| `/client/services/[id]` | Detalle de servicio propio |
| `/client/diagnostic` | Diagnostico |
| `/client/chat` | Mensajes |
| `/client/support` | Tickets |
| `/client/meetings` | Reuniones |
| `/client/documents` | Documentos |
| `/client/billing` | Facturacion |

---

## Auditoria Tecnica

### Fortalezas

- **Buena separacion backend**: rutas delgadas, servicios de dominio y modelos separados.
- **RBAC aplicado en dependencias y servicios**: reduce filtraciones entre roles.
- **Transiciones explicitas**: leads, clientes y servicios usan maquinas de estado en vez de cambios libres.
- **Healthcheck real**: `/health` comprueba Redis y PostgreSQL.
- **Docker Compose completo**: levanta base de datos, cache, API y frontend.
- **Suite de tests relevante**: incluye unitarios, integracion, migraciones, RBAC, billing profiles y conversion de leads.
- **Panel moderno**: Next.js 16, React 19, Tailwind, Radix UI y cliente API tipado.
- **Rewrites internos**: el frontend no necesita conocer directamente la URL de la API en navegacion normal.
- **Headers de seguridad documentados**: CSP y cabeceras defensivas configuradas en Next.

### Riesgos Y Deuda Detectada

| Riesgo | Evidencia | Impacto | Recomendacion |
|--------|-----------|---------|---------------|
| Comentarios heredados de MSI Automotive | `api/main.py`, `api/auth.py`, `docker/Dockerfile.*`, `alembic.ini` | Confunde mantenimiento y onboarding | Renombrar comentarios para Zanovix CRM |
| Cookie `secure=False` | `api/routes/admin.py` | Inseguro si se expone fuera de localhost/HTTP interno | Activar `secure=True` en produccion detras de HTTPS |
| Defaults inseguros | `JWT_SECRET_KEY`, `IP_HASH_SALT`, passwords y DB password | Riesgo critico si se despliega sin `.env` robusto | Fallar arranque en produccion si se usan defaults |
| CSP permite `unsafe-inline` y `unsafe-eval` | `admin-panel/src/app/next.config.headers.ts` | Aumenta superficie XSS | Migrar a nonce/hash CSP si el panel se expone publicamente |
| Redis `--requirepass` con valor vacio por defecto | `docker-compose.yml` | Redis sin password en entorno local | Exigir password fuera de desarrollo |
| `.env.example` no pudo auditarse por politica de lectura local | Restricciones de permisos del entorno | README se basa en `shared/config.py` y `docker-compose.yml` | Revisar manualmente que `.env.example` coincide con esta tabla |
| ZIP del proyecto versionado | `Zanovix CRM.zip` | Repositorio mas pesado y duplicacion de codigo | Mantener solo si es requisito de entrega; si no, mover a releases |
| Sin licencia detectada | No existe `LICENSE*` | Ambiguedad legal de uso/distribucion | Agregar licencia si el repo sera publico |

### Recomendaciones Prioritarias

1. Cambiar todos los secretos por valores fuertes antes de cualquier despliegue real.
2. Corregir referencias heredadas de MSI para que la documentacion tecnica no mienta.
3. Activar cookies seguras y endurecer CSP antes de exponer el panel fuera de una red interna.
4. Decidir si `Zanovix CRM.zip` debe vivir en Git o en un release asset.
5. Agregar `LICENSE` si el repositorio publico va a ser reutilizable por terceros.

---

## Despliegue

El despliegue Docker usa cuatro servicios:

| Servicio | Imagen/Base | Puerto host | Descripcion |
|----------|-------------|-------------|-------------|
| `postgres` | `postgres:15-alpine` | `5433` | Base de datos persistente |
| `redis` | `redis:7-alpine` | `6380` | Cache, rate limit y blacklist JWT |
| `api` | `docker/Dockerfile.api` | `8010` | FastAPI + Uvicorn |
| `admin-panel` | `docker/Dockerfile.admin-panel` | `8011` | Next.js standalone |

Checklist minima para produccion:

- [ ] `.env` con secretos fuertes y unicos.
- [ ] `CORS_ORIGINS` restringido al dominio real.
- [ ] HTTPS delante del admin panel y la API.
- [ ] `secure=True` en cookie de autenticacion.
- [ ] Redis protegido con password.
- [ ] Backups de PostgreSQL configurados.
- [ ] Migraciones ejecutadas con `alembic upgrade head`.
- [ ] Seeds ejecutados solo con passwords controladas.
- [ ] Logs y alertas conectados a la plataforma de observabilidad.

---

## Roadmap Sugerido

- Endurecer configuracion de produccion con validaciones por `ENVIRONMENT=production`.
- Documentar contrato OpenAPI exportado.
- Separar artefactos pesados como ZIPs en GitHub Releases.
- Agregar licencia y politica de contribucion si el proyecto seguira publico.
- Completar documentacion del portal cliente desde perspectiva de usuario final.
- Añadir CI para pytest, ruff, Jest y lint del admin panel.

---

<div align="center">

<p><strong>Zanovix CRM</strong> — lead capture, client operations and service delivery in one internal platform.</p>

<p><sub>Repositorio: <a href="https://github.com/pepeccz/zanovix-crm">github.com/pepeccz/zanovix-crm</a></sub></p>

</div>
