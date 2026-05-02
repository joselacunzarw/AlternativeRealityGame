# TODO

## Estado actual

- El repo esta estable y sincronizado con `origin/master`.
- Ya quedaron implementados y subidos:
  - Vault con assets estaticos y `file_url`
  - Parser de replies por email
  - Aislamiento de memoria por `session_id`
  - Persistencia de UIDs IMAP y rate limiting en SQLite
  - Validador de casos (`backend/scripts/validate_cases.py`)
  - Panel operativo read-only (`/operations`, `/api/v1/ops/*`)
  - Notebook del detective (`/notebook`, `/api/v1/notebook`)
- La validacion manual de `martes_3` dio bien: OTP, inicio de caso, briefing, personajes, Juan, Boveda y Director.

## Deuda/pendientes actuales

- Moderador en bypass en `backend/core/orchestrator.py`
- Faltan archivos reales del Vault en `backend/assets/<case_id>/`
- Configurar `OPS_EMAIL_ALLOWLIST` en el entorno real para probar `/operations`
- Hacer pasada visual manual del Notebook con una sesion real

## Roadmap de features

1. Lint + validador de casos
   - Estado: completado
2. Panel operativo minimo
   - Estado: completado
3. Notebook del detective
   - Estado: completado
4. Mapa de relaciones
   - Estado: pendiente
5. Nudges inteligentes
   - Estado: pendiente
6. Estados emocionales de personajes
   - Estado: pendiente
7. Finales mas ramificados
   - Estado: pendiente

## Paso 2: plan de implementacion

Estado: completado.

Implementado:

- Backend `backend/api/ops.py`
- Frontend `frontend/src/components/Operations.jsx`
- Tests `backend/tests/test_ops_api.py`
- Seguridad JWT + `OPS_EMAIL_ALLOWLIST`

### Objetivo

Construir un panel operativo read-only para ver el estado real del sistema sin tocar todavia la logica narrativa ni agregar acciones administrativas destructivas.

### Alcance MVP

- Ver sesiones activas y su estado
- Ver mensajes en cola (`ScheduledMessage`)
- Ver eventos disparados (`FiredEvent`)
- Ver rate limiting reciente (`RateLimitEvent`)
- Ver mensajes entrantes procesados (`ProcessedInboundMessage`)
- Ver alertas simples derivadas de DB, por ejemplo mensajes atrasados

### Backend

Archivos a crear o tocar:

- `backend/api/ops.py`
- `backend/main.py`
- `backend/.env.example`

Endpoints propuestos:

- `GET /api/v1/ops/summary`
- `GET /api/v1/ops/sessions`
- `GET /api/v1/ops/queue`
- `GET /api/v1/ops/events`
- `GET /api/v1/ops/inbound`

Fuentes de datos ya disponibles:

- `GameSession`
- `ScheduledMessage`
- `FiredEvent`
- `RateLimitEvent`
- `ProcessedInboundMessage`
- `Message`

Datos sugeridos para `summary`:

- Conteo de sesiones por estado
- Mensajes pendientes
- Mensajes atrasados (`scheduled_at < now` e `is_delivered = false`)
- Eventos disparados en las ultimas 24h
- Rate limits en la ultima hora por canal
- Ultimos mensajes entrantes procesados

### Seguridad minima

No hacer un sistema de roles completo en este paso.

Implementar:

- JWT obligatorio
- `OPS_EMAIL_ALLOWLIST` en entorno
- `403` si el usuario autenticado no esta permitido

### Frontend

Archivos a crear o tocar:

- `frontend/src/components/Operations.jsx`
- `frontend/src/App.jsx`
- opcionalmente `frontend/src/index.css`

Pantalla inicial propuesta:

- Cards con KPIs arriba
- Tabla de sesiones activas
- Tabla de mensajes en cola
- Tabla de eventos recientes
- Tabla de rate limits
- Tabla de inbound recientes

UX minima:

- Boton de refresco
- Auto-refresh cada 20-30 segundos
- Badges visuales para `active`, `overdue`, `rate-limited`

### Fuera del MVP

- Acciones administrativas (reanudar, cancelar, reprocesar, etc.)
- Persistencia de errores de workers en tabla propia
- Sistema completo de roles
- WebSockets o streaming en vivo

### Tests

Agregar:

- `backend/tests/test_ops_api.py`

Cubrir:

- Auth requerida
- Allowlist de ops
- Agregados basicos de `summary`
- Respuesta de listas de sesiones, cola, eventos e inbound

### Orden recomendado

1. Crear `backend/api/ops.py` con endpoint `summary`
2. Agregar endpoints detallados `sessions`, `queue`, `events`, `inbound`
3. Incorporar `OPS_EMAIL_ALLOWLIST`
4. Montar ruta frontend `/operations`
5. Crear `Operations.jsx`
6. Agregar auto-refresh y badges
7. Escribir tests backend

## Paso 3: Notebook del detective

Estado: completado.

Implementado:

- Modelo `DetectiveNotebookEntry` con `user_id`, `session_id`, `entry_type`, `title`, `content`, `created_at`, `updated_at`
- Backend `backend/api/notebook.py`
- Frontend `frontend/src/components/Notebook.jsx`
- Ruta protegida `/notebook`
- Tests `backend/tests/test_notebook_api.py`

### Objetivo

Dar al jugador una herramienta persistente dentro del frontend para guardar hipotesis, personajes sospechosos, fechas clave y codigos de Vault sin depender de notas externas.

### Alcance MVP

- Notas libres por sesion activa
- Lista de sospechosos/personajes de interes
- Lista de fechas o hitos importantes
- Lista de codigos/pistas de Vault
- Persistencia entre recargas

### Backend

Archivos a crear o tocar:

- `backend/database/models.py`
- `backend/api/notebook.py`
- `backend/main.py`

Modelo sugerido:

- `DetectiveNotebookEntry`
  - `id`
  - `session_id`
  - `entry_type` (`note`, `suspect`, `timeline`, `vault_code`)
  - `title`
  - `content`
  - `created_at`
  - `updated_at`

Endpoints propuestos:

- `GET /api/v1/notebook`
- `POST /api/v1/notebook`
- `PATCH /api/v1/notebook/{entry_id}`
- `DELETE /api/v1/notebook/{entry_id}`

### Frontend

Archivos a crear o tocar:

- `frontend/src/components/Notebook.jsx`
- `frontend/src/App.jsx`

Pantalla inicial propuesta:

- Panel principal con tabs por tipo de entrada
- Formulario rapido para crear nota
- Lista editable de entradas por sesion activa

### Tests

- `backend/tests/test_notebook_api.py`

### Orden recomendado

1. Crear modelo y endpoints CRUD
2. Montar ruta frontend `/notebook`
3. Crear UI minima
4. Agregar edicion y borrado inline
5. Escribir tests backend

## Paso 4: Mapa de relaciones

### Objetivo

Visualizar en forma clara la red entre personajes, pistas, documentos y eventos para ayudar al jugador a organizar la investigacion.

### Alcance MVP

- Grafo read-only por sesion
- Nodos de personajes, documentos y pistas
- Relaciones manuales derivadas del notebook o del caso
- Vista simple con filtros

### Backend

Archivos a crear o tocar:

- `backend/api/relations.py`
- opcionalmente `backend/database/models.py`

Estrategia sugerida para MVP:

- No hacer inferencia automatica todavia
- Construir el grafo a partir de:
  - entries del notebook
  - metadata del caso (`characters`, `vault`, etc.)
  - relaciones agregadas manualmente por el jugador

Endpoints propuestos:

- `GET /api/v1/relations`
- `POST /api/v1/relations`
- `DELETE /api/v1/relations/{relation_id}`

### Frontend

Archivos a crear o tocar:

- `frontend/src/components/RelationsMap.jsx`
- `frontend/src/App.jsx`

UI sugerida:

- Canvas o SVG simple
- Filtros por tipo de nodo
- Panel lateral con detalle al seleccionar nodo

### Tests

- `backend/tests/test_relations_api.py`

### Orden recomendado

1. Definir modelo de relacion minimo
2. Exponer el grafo por API
3. Construir visualizacion simple en frontend
4. Agregar filtros y detalle lateral

## Paso 5: Nudges inteligentes

### Objetivo

Mejorar el sistema de ayuda diegetica para que los empujones dependan del progreso real del jugador y no solo del paso del tiempo.

### Alcance MVP

- Detectar estancamiento narrativo
- Sugerir desde personajes o Director una pista contextual
- Evitar nudges repetidos

### Backend

Archivos a crear o tocar:

- `backend/core/nudge_engine.py`
- `backend/database/models.py`
- `backend/core/orchestrator.py`

Modelo sugerido:

- `FiredNudge`
  - `session_id`
  - `nudge_id`
  - `fired_at`
  - `source`

Heuristicas iniciales:

- muchas horas sin mensajes del jugador
- misma pregunta repetida a varios personajes
- no uso de Vault pese a haber recibido codigos
- sesion cerca de expirar sin progreso

### Tests

- `backend/tests/test_nudge_engine.py`

### Orden recomendado

1. Formalizar heuristicas basicas
2. Registrar nudges disparados para no repetir
3. Ajustar prompts y entrega
4. Agregar cobertura de tests

## Paso 6: Estados emocionales de personajes

### Objetivo

Hacer que cada personaje responda distinto segun confianza, paranoia, cansancio, enojo o urgencia acumulada durante la partida.

### Alcance MVP

- Estado emocional persistente por personaje y sesion
- Lectura del estado en prompts de respuesta
- Cambios de tono segun acciones del jugador

### Backend

Archivos a crear o tocar:

- `backend/database/models.py`
- `backend/core/orchestrator.py`
- `backend/core/conversation_threads.py`

Modelo sugerido:

- `CharacterState`
  - `session_id`
  - `character_alias`
  - `trust`
  - `paranoia`
  - `fatigue`
  - `urgency`
  - `updated_at`

Reglas iniciales:

- insistencia agresiva sube paranoia
- preguntas empaticas suben trust
- paso del tiempo sube urgency
- exceso de contacto sube fatigue

### Tests

- `backend/tests/test_character_state.py`

### Orden recomendado

1. Persistir estado por personaje/sesion
2. Actualizar reglas de cambio de estado
3. Inyectar estado en prompts
4. Ajustar comportamiento con casos reales

## Paso 7: Finales mas ramificados

### Objetivo

Expandir el cierre de los casos para que el resultado dependa de decisiones, pruebas reunidas, personajes contactados y contenido descubierto en Vault.

### Alcance MVP

- Multiples finales por caso
- Epilogos diferenciados
- Evaluacion mas rica del Director

### Backend

Archivos a crear o tocar:

- `backend/casos/*.json`
- `backend/core/orchestrator.py`
- `backend/database/models.py`

Estrategia sugerida:

- definir en cada caso condiciones de cierre estructuradas
- dejar que el Director elija dentro de un conjunto mas acotado y explicitado
- persistir `ending_id` ademas de `verdict`

Campos nuevos sugeridos en `GameSession`:

- `ending_id`
- `ending_title`

### Frontend

Archivos a crear o tocar:

- `frontend/src/components/Profile.jsx`
- opcion de vista final o epilogo dedicado

### Tests

- `backend/tests/test_case_endings.py`

### Orden recomendado

1. Extender schema de casos para finales
2. Persistir metadatos de ending en sesion
3. Ajustar evaluacion del Director
4. Mostrar epilogo en frontend

## Nota para retomar

La proxima conversacion puede arrancar con el paso 4: Mapa de relaciones. Usar el Notebook como fuente natural para sospechosos, fechas, codigos y pistas creadas por el jugador.
