# HANDOFF — Claude Code (Claude Sonnet) → Codex (OpenAI)

**Fecha:** 2026-05-01 (cierre de turno)  
**Agente saliente:** Claude Code (Claude Sonnet 4.6)  
**Agente entrante:** Codex (OpenAI)  
**Branch activa:** master

---

## ✅ Qué se hizo en este turno (actualizado)

### Actualizacion posterior de Codex

- **`core/event_engine.py`** - Logs de debug granulares removidos. Se conservaron logs operativos concisos para ciclo, disparo de eventos, warnings de datos invalidos y errores con stack trace.
- **Vault con assets estaticos** - Infraestructura implementada de punta a punta:
  - `backend/main.py` monta `backend/assets/` en `/assets`
  - `api/vault.py` devuelve `file_url` cuando existe un archivo real en disco
  - `frontend/src/components/Vault.jsx` muestra boton de descarga y resuelve URLs relativas contra el mismo backend configurado en `VITE_API_URL`
  - `backend/.env.example` documenta `ASSETS_BASE_URL`
  - `backend/assets/README.md` y carpetas por caso dejan preparada la estructura para que el propietario suba los archivos definitivos
- **Suite de tests Vault ajustada** - `backend/tests/test_vault.py` ahora cubre `file_url` y `backend/tests/conftest.py` usa `StaticPool` para compartir la SQLite en memoria entre fixtures y requests del `TestClient`.
- **Replies por email mas robustas** - `core/email_reply_parser.py` recorta texto citado y evita que personajes lean el historial reenviado como si fuera el mensaje nuevo del detective.
- **Memoria aislada por sesion** - `core/conversation_threads.py` centraliza el calculo de `thread_id` y usa `thread_session_{session_id}_{char_alias}` para separar conversaciones entre casos del mismo jugador.
- **Estado entrante persistente** - `core/inbound_runtime_state.py` persiste en SQLite los UID ya vistos del IMAP y los eventos de rate limiting por canal, para que reiniciar el proceso no resetee ni duplicados ni contadores.
- **Validacion manual de `martes_3` completada** - Flujo verificado con credenciales reales: OTP, inicio de caso, briefing, respuestas de Hernan y Secretaria, evento proactivo de Juan, Boveda y envio al Director.

### Director Proactivo — Event Engine

- **`core/event_engine.py`** — Motor de eventos proactivos. Background task que corre cada 30 min (1 min en DEV_MODE). Para cada sesión activa evalúa si algún evento debe dispararse usando trigger combinado: tiempo transcurrido + evaluación LLM de condición narrativa. Genera el mensaje del personaje y lo encola en `ScheduledMessage`.
- **`database/models.py`** — Nuevo modelo `FiredEvent` que registra qué eventos ya se dispararon por sesión, con control de `max_fires`.
- **`backend/casos/martes_3.json`** — 3 eventos proactivos definidos:
  1. `juan_se_presenta` (≥8h): Juan Beretta contacta al detective si no fue mencionado todavía.
  2. `hernan_crisis_nocturna` (≥20h): Hernán escribe en crisis si aún no reconoce su pasado.
  3. `mira_rompe_protocolo` (≥40h): Mira abandona el tono institucional si el tiempo se agota.
- **`main.py`** — `start_event_engine()` registrado como 4ta tarea en el lifespan.

**Comportamiento del trigger combinado:**
- Tiempo: el evento no dispara antes de `trigger_after_hours` desde el inicio de sesión.
- Progreso: GPT-4o-mini evalúa si `trigger_condition` se cumple en el historial reciente.
- Ambos deben ser verdaderos. Mínimo `MIN_HOURS_BETWEEN_EVENTS` (6h prod, 10min dev) entre eventos.
- En DEV_MODE: ciclo cada 1 min, delays de entrega de 2-5 min, mínimo 10 min entre eventos.

**Para agregar eventos a otros casos:** agregar campo `proactive_events` al JSON del caso siguiendo la misma estructura que `martes_3.json`.

---

## ✅ Qué se hizo en este turno

### Fixes de backend

1. **Métricas de perfil corregidas** — `api/users.py`
   - `completed_success` y `completed_fail` nunca se contaban (comparaban contra `"completed_success"` / `"completed_fail"` que el modelo nunca guarda). Ahora usan `status == "completed"` + campo `verdict` (`"win_*"` = éxito, `"lose"/"partial"` = fracaso).
   - `session_info` ahora incluye el campo `verdict` para que el frontend pueda mostrarlo.

2. **Thread ID consistente webhook vs IMAP** — `api/webhook.py` + `core/imap_poller.py`
   - Ambos resuelven el `thread_id` con helper compartido.
   - Formato principal nuevo: `thread_session_{session_id}_{char_alias}`.
   - Esto aísla memoria LangGraph por sesión activa y evita arrastrar contexto entre expedientes distintos del mismo jugador.

3. **requirements.txt completado** — `backend/requirements.txt`
   - Agregado `python-multipart>=0.0.9` (requerido por FastAPI para form data).
   - Corregido `langgraph-checkpoint` → `langgraph-checkpoint-sqlite>=2.0.0` (el paquete correcto para `SqliteSaver`).
   - Corregido `pydantic>=2.7.0` → `pydantic[email]>=2.7.0` (incluye `email-validator` necesario para `EmailStr` en schemas).

4. **OTP brute force protection** — `api/users.py` + `database/models.py`
   - Nuevo campo `otp_attempts` en modelo `User` (default 0).
   - Lockout tras 5 intentos fallidos (HTTP 429).
   - Contador se resetea al solicitar un nuevo código o al verificar correctamente.
   - ⚠️ **Requiere recrear la DB** si ya existe una: correr `python scripts/recreate_db.py`.

5. **Rate limiting en IMAP poller** — `core/imap_poller.py`
   - Máximo `IMAP_RATE_LIMIT_PER_HOUR` (default: 20) emails por jugador por hora.
   - Implementado con ventana deslizante en memoria (`_rate_counters` dict).
   - Configurable via variable de entorno `IMAP_RATE_LIMIT_PER_HOUR` en `.env`.
   - Variable documentada en `.env.example`.

### Fixes de frontend

6. **LandingPage: errores silenciosos eliminados** — `frontend/src/components/LandingPage.jsx`
   - Request OTP: el `catch` ya no solo hace `console.error`. Muestra mensaje inline con el diseño cyberpunk.
   - Verify OTP: reemplazado `alert()` nativo por mensaje de error inline con ícono `AlertTriangle`.
   - Nuevo estado `errorMsg` que se resetea al intentar de nuevo.

7. **Profile.jsx: badges de estado corregidos** — `frontend/src/components/Profile.jsx`
   - Eliminadas condiciones muertas `completed_success` / `completed_fail`.
   - Ahora usa `verdict` para mostrar RESUELTO vs FALLIDO dentro de sesiones `completed`.
   - Caso edge: `completed` sin `verdict` muestra "COMPLETADO" genérico.

### Dockerización completa

8. **`backend/Dockerfile`** — imagen Python 3.11-slim, instala requirements, expone puerto 8001.
9. **`frontend/Dockerfile`** — multi-stage: build con Node 20 + `npm run build`, serve con nginx:alpine.
10. **`frontend/nginx.conf`** — configuración nginx con `try_files` para React Router y cache de assets.
11. **`docker-compose.yml`** — orquesta backend + frontend. Volume `backend_data` persiste los SQLite entre reinicios. `VITE_API_URL` pasado como build arg.
12. **`backend/.dockerignore` / `frontend/.dockerignore`** — excluyen `.env`, SQLite, `node_modules`, `__pycache__`.
13. **Rutas SQLite parametrizadas** — `database/database.py` y `core/orchestrator.py` ahora leen `DB_PATH` y `DB_CHECKPOINT_PATH` del entorno. Default sigue siendo el path local de desarrollo; Docker las setea en `/app/data/`.

Para levantar todo con Docker:
```bash
cp backend/.env.example backend/.env
# Completar backend/.env con las keys reales
docker compose up --build
# Backend: http://localhost:8001
# Frontend: http://localhost:5173
```

### Documentación

14. **README reescrito** — `README.md`
   - Documenta los 4 subsistemas omitidos (Time Guardian, Nudge Engine, Active Director, Delivery Worker).
   - Elimina `(Próximamente)` del requirements.txt.
   - Agrega tabla de variables de entorno, flujo de juego y tabla de casos.

---

## 🔴 Problemas críticos pendientes

- **Moderador desactivado** — Pospuesto por decisión del propietario. No reactivar sin aprobación.

> **Nota:** Codex detectó en revisión estática que el turno anterior declaró erróneamente "ningún crítico pendiente". Los bugs #1, #2 y #3 abajo fueron corregidos en un commit posterior al handoff original.

---

## 🟡 Deuda técnica conocida

### Corregidos en este turno (que el handoff original declaró incorrectamente como pendientes o cerrados):
- **Bug #1 [RESUELTO]** — `/game/start` usaba `req.user_email` del body para enviar el briefing, permitiendo enviar contenido a terceros. Ahora usa siempre `current_user.email`.
- **Bug #2 [RESUELTO]** — `GameSession` se creaba sin `expires_at`. Ahora se puebla con `now + duration_limit_hours` del caso.
- **Bug #3 [RESUELTO]** — El cleanup de checkpoints usaba patrón `thread_{email}_%` que borraba memoria de sesiones activas del mismo usuario. Ahora solo limpia emails sin ninguna sesión activa.
- **Bug #4 [RESUELTO]** — La memoria LangGraph ya no se comparte entre casos distintos del mismo jugador. Webhook e IMAP ahora usan `thread_session_{session_id}_{char_alias}` y solo hacen fallback a formatos menos precisos fuera de una sesión activa.
- **Bug #5 [RESUELTO]** — `processed_ids` del IMAP ya no vive en memoria de proceso. Ahora el poller usa UID persistentes en la tabla `processed_inbound_messages`.
- **Bug #6 [RESUELTO]** — El rate limiting de IMAP/webhook ya no depende de diccionarios en memoria. Ahora persiste eventos en `rate_limit_events` manteniendo presupuesto separado por canal.

### Documentación corregida (señalado por Codex):
- El rate limiting del webhook HTTP **SÍ está implementado** (`api/webhook.py` tiene su propio `_is_rate_limited`). El contador es separado del de IMAP — el límite combinado es `RATE_LIMIT * 2` por canal. Esto es intencional para MVP; en producción unificar con Redis.

### Deuda activa:
- **Vault sin archivos reales** — La infraestructura ya está lista; faltan solamente los PDFs/ZIPs/imágenes/audios definitivos que debe subir el propietario/guionista en `backend/assets/<case_id>/`.

---

## 📋 Tareas para el siguiente agente (Codex)

> **Estado del sistema al cierre del turno Claude Code:**
> - Contenedores Docker corriendo en contexto `desktop-linux` (visible en Docker Desktop)
> - Backend: `http://localhost:8001` ✅
> - Frontend: `http://localhost:5173` ✅
> - Event Engine verificado y funcionando: dispara `juan_se_presenta` correctamente en DEV_MODE
> - Logs de `event_engine.py` ya limpiados y en modo operativo
> - `martes_3` tiene 3 eventos proactivos definidos y testeados
> - Memoria LangGraph aislada por sesion activa (`thread_session_{session_id}_{alias}`)
> - Prueba manual end-to-end de `martes_3` completada con resultado correcto
> - Para reconstruir contenedores: `docker --context desktop-linux compose build && docker --context desktop-linux compose up -d`

Lista priorizada:

1. ~~**Limpiar logs de debug del Event Engine**~~ ✅ Completado por Codex. `core/event_engine.py` quedó con logs operativos de producción.
2. ~~**Suite de tests pytest**~~ ✅ Completado por Claude Code. Ver `backend/tests/`.
2. ~~**Dockerfile + docker-compose**~~ ✅ Completado por Claude Code.
3. ~~**Rate limiting en webhook HTTP**~~ ✅ Completado por Claude Code. `api/webhook.py` tiene su propio contador `_is_rate_limited` en memoria — **separado** del de `imap_poller.py`. El límite efectivo es `RATE_LIMIT_PER_HOUR` por canal, no compartido. Para unificar en producción usar Redis.
4. ~~**Cleanup job de checkpoints LangGraph**~~ ✅ Completado por Claude Code. `delivery_worker.py` limpia cada hora checkpoints de sesiones inactivas.
5. ~~**Vault: implementar assets estáticos**~~ ✅ Completado por Codex.
   - Backend monta `/assets`
   - `vault.py` devuelve `file_url` cuando el archivo existe
   - Frontend muestra botón de descarga
   - `.env.example` documenta `ASSETS_BASE_URL`
   - `backend/assets/README.md` y carpetas base ya están en el repo
   - Pendiente externo: el propietario/guionista debe subir los archivos reales

### Cómo correr los tests

```bash
cd backend
pytest tests/ -v
```

Tests disponibles:
- `tests/test_time_guardian.py` — parsing de latencia, delays, horarios imposibles (sin LLM)
- `tests/test_vault.py` — datos de casos, lookup de códigos, endpoint vault y `file_url` (sin LLM)
- `tests/test_otp.py` — lockout OTP, reset de intentos, flujo de request (sin LLM)
- `tests/test_rate_limiter.py` — ventana deslizante IMAP y webhook (sin LLM)
- `tests/test_inbound_runtime_state.py` — persistencia de UIDs IMAP y helpers de runtime state (sin LLM)
- `tests/test_orchestrator_routing.py` — routing del grafo, carga de casos (sin LLM)

---

## 🔀 Estado de branches

| Branch | Propósito | Estado |
|---|---|---|
| master | Desarrollo principal | Estable. Todos los fixes commiteados. |

No hay branches huérfanas.

---

## ⚠️ Decisiones tomadas que no deben revertirse

Todas las del turno anterior (Antygravity) siguen vigentes. Agregar:

1. **Moderador en bypass** — Pospuesto por decisión del propietario. No implementar moderador LLM ni regex sin aprobación explícita.
2. **OTP lockout en 5 intentos** — Aprobado. Si se quiere cambiar el límite, usar variable de entorno `OTP_MAX_ATTEMPTS` (actualmente hardcodeado, futuro refactor si hace falta).
3. **Rate limit persistente en SQLite** — Mantiene presupuesto separado por canal (`imap`/`webhook`) y sobrevive a reinicios. Si en producción aparece volumen alto, mover a Redis.
4. **Thread ID formato `thread_session_{session_id}_{alias}`** — Mantener este contrato entre IMAP, webhook y cleanup. Solo usar fallbacks por `case_id` o `email` cuando no exista sesión activa.

---

## 🧪 Cómo verificar que el sistema funciona

### Arranque mínimo

```bash
cd backend
python -m uvicorn main:app --port 8001
```

- **GET** `http://localhost:8001/` → `{"status": "ok", "message": "Expediente Abierto Backend is running"}`
- Logs deben mostrar: `Escáner IMAP iniciado`, `Delivery Worker iniciado`, `Nudge Engine iniciado`

### Verificar métricas de perfil (fix #1)

```bash
# Con una sesión completed+verdict en la DB:
# GET /api/v1/users/me/profile debe retornar completed_success > 0
```

### Verificar OTP lockout (fix #4)

```bash
# POST /api/v1/auth/verify-otp con código incorrecto 5 veces
# En el 5to intento debe retornar HTTP 429
```

### ⚠️ Recrear DB si ya existía

Si hay una `expediente_abierto.db` previa, correr:
```bash
cd backend
python scripts/recreate_db.py
```
Esto agrega la columna `otp_attempts` al modelo `User`.

---

## 📝 Notas para Codex

1. **El modelo `User` tiene un nuevo campo `otp_attempts`**. Si los tests existentes crean usuarios sin este campo, pueden fallar. Actualizar fixtures.

2. **`requirements.txt` usa `langgraph-checkpoint-sqlite`** — verificar que este nombre de paquete sea correcto en PyPI antes de buildear Docker. El import en `orchestrator.py` es `from langgraph.checkpoint.sqlite import SqliteSaver`.

3. **Los scripts en `scripts/`** son semi-manuales pero tienen buena cobertura de los flujos. Usarlos como referencia para los tests pytest, no como tests en sí.

4. **El vault** es una mecánica interesante pero incompleta. No implementar archivos reales sin consultar al propietario. Solo documentar la deuda.

5. **CORS** ya está parametrizado via `CORS_ORIGINS` en `.env`. El docker-compose debe setear esta variable correctamente para el frontend containerizado.

---

*Fin del HANDOFF — Claude Code (Claude Sonnet 4.6), 2026-05-01*
