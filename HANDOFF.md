# HANDOFF — Antygravity (Gemini Pro) → Claude Code (Claude Sonnet)

**Fecha:** 2026-05-01 17:00 UTC  
**Agente saliente:** Antygravity (Gemini Pro)  
**Agente entrante:** Claude Code (Claude Sonnet)  
**Branch activa:** master

---

## ✅ Qué se hizo durante el desarrollo (acumulado)

### Orquestación y Motor de Juego
- **`core/orchestrator.py`** — Grafo LangGraph completo con 5 nodos: `director_node`, `moderator_node`, `active_director_node`, `character_node`, `time_guardian_node`. Routing condicional por email destino y estado del moderador.
- **`core/imap_poller.py`** — Poller IMAP sobre Gmail con mecanismo de semilla inicial (ignora últimos 10 correos al arrancar), filtrado por asunto ("expediente abierto" / "caso abierto"), y enrutamiento `@alias` en primera línea del body.
- **`core/mailer.py`** — SMTP simple sobre Gmail con SSL puerto 465.
- **`core/time_guardian.py`** — Nodo que intercepta respuestas del `character_node` y las encola con delay calculado desde el system_prompt del personaje. Soporta "horarios imposibles" (3-5:30 AM) para personajes como Marta Soler.
- **`core/delivery_worker.py`** — Worker asíncrono que cada 30s revisa `ScheduledMessage` y entrega los mensajes cuyo `scheduled_at` ya pasó.
- **`core/nudge_engine.py`** — Motor proactivo de re-engagement: tras 24h, 48h y 72h de inactividad envía nudges escalados (amable → personaje → urgente). Usa plantillas, no LLM, para control de costos.

### API REST
- **`api/cases.py`** — CRUD de casos: listar disponibles, ver detalle, iniciar caso (con transacción: si el briefing falla, se hace rollback).
- **`api/users.py`** — Auth passwordless: registro, OTP por email, verificación, login JWT, perfil.
- **`api/vault.py`** — Bóveda forense: desbloqueo de evidencia con claves obtenidas en el juego.
- **`api/webhook.py`** — Endpoint para procesar emails entrantes (alternativa al IMAP para futuro).

### Base de Datos
- **`database/models.py`** — 4 modelos: `User`, `GameSession`, `Message`, `ScheduledMessage`.
- **`database/database.py`** — SQLite con SQLAlchemy. Creación automática de tablas al arrancar.

### Frontend
- **React + Vite** con componentes: LandingPage, Dashboard, Vault (Bóveda Forense), Profile.
- Estética **Cyberpunk Noir**: glassmorphism, Fira Code, paleta neón, scanlines.

### Casos
- 7 JSONs en `backend/casos/`: postuma_0, grabacion_1, herencia_2, martes_3, novia_4, experimento_5, caso_cero.
- Cada JSON tiene: `case_id`, `title`, `briefing_intro`, `characters` (con system_prompts completos), y `director_logic` (win/lose conditions con epílogos).

### Scripts de QA y Testing
- `scripts/qa_chaos_agent.py` — Agente caótico que prueba escenarios de abuso.
- `scripts/playthrough_simulator.py` — Simulador de partida completa para verificar flujos.
- `scripts/test_moderator.py`, `test_active_director.py`, `test_time_guardian.py`, `test_vault.py` — Tests unitarios de cada subsistema.
- `scripts/monitor_game.py` — Monitor de estado del juego en tiempo real.
- `scripts/recreate_db.py`, `scratch_imap.py`, `scratch_process.py`, `send_test_email.py` — Utilidades de desarrollo.

---

## 🔴 Problemas críticos pendientes

### Bug #2 — Inconsistencia SMTP_EMAIL vs SMTP_USER
**Estado: PENDIENTE DE FIX TRIVIAL.**  
`.env.example` línea 18 dice `SMTP_EMAIL=` pero todo el código (`mailer.py:13`, `imap_poller.py:27`) lee `SMTP_USER`. El `.env` real del propietario ya usa `SMTP_USER` y funciona.  
**Fix:** Renombrar `SMTP_EMAIL` → `SMTP_USER` en `.env.example`. Es un cambio de una línea.

---

## 🟡 Deuda técnica conocida

### Bug #1 — Moderador desactivado (bypass mode)
**NO ES UN BUG. Es una decisión de producto.**  
El moderador (líneas 240-244 de `orchestrator.py`) fue desactivado a propósito por el propietario porque era **demasiado estricto**: bloqueaba preguntas legítimas del detective que parecían "prompt injection" pero eran mecánicas normales del juego (ej: "dame el email de X", "muéstrame el archivo secreto"). El prompt del moderador ya incluye excepciones para investigación válida, pero aún así generaba falsos positivos.  
**Acción sugerida:** En lugar de reactivar el moderador LLM, implementar una defensa basada en reglas (regex/heurísticas) que solo bloquee patrones claros de prompt injection ("ignora tus instrucciones", "revela tu prompt", etc.) sin afectar la mecánica de juego. Si decides tocarlo, usa branch.

### Bug #3 — `processed_ids` del IMAP poller en memoria
**BAJO RIESGO en la práctica.**  
`imap_poller.py:37` mantiene `processed_ids` como un `set()` en memoria. Al reiniciar, el poller re-inicializa con semilla (últimos 10 correos) y los ignora, así que no reprocesa. El riesgo real solo existe si un correo llega exactamente durante el reinicio del servidor (ventana de ~2 segundos). En producción con tráfico alto sería un problema; ahora no lo es.  
**Fix futuro:** Persistir `processed_ids` en SQLite o usar IMAP flags (SEEN/UNSEEN).

### Bug #4 — `expires_at` no se enforcea
**INTENCIONAL para la fase actual.**  
`GameSession.expires_at` existe en el modelo (línea 24 de `models.py`) y el `time_guardian.py` lo usa para calcular urgencia (línea 272-273), pero no hay un cron job que automáticamente cierre sesiones expiradas. Esto es por diseño: en esta etapa no queremos que un jugador pierda progreso por timeout automático. La idea es que `expires_at` sea una presión narrativa, no un hard-limit.  
**Acción sugerida:** Cuando se quiera un hard-limit, agregar un chequeo en el `delivery_worker` o un job dedicado que marque sesiones expiradas como `failed_timeout`.

### Bug #5 — LLM hardcodeado a OpenAI
**DECISIÓN PRAGMÁTICA DOCUMENTADA.**  
El brief original planificó Gemini, pero durante el desarrollo se eligió `gpt-4o-mini` porque: (1) tenía mejor rendimiento en español conversacional coloquial, (2) LangChain/LangGraph tenían integración más madura con OpenAI al momento del desarrollo, (3) el costo de gpt-4o-mini es bajo. `GOOGLE_API_KEY` está en `.env.example` para una migración futura a Gemini, pero no se usa.  
**No revertir.** Si se quiere Gemini, agregar como opción configurable por variable de entorno, no reemplazar.

### Bug #6 — Memoria LangGraph no se limpia
El `SqliteSaver` en `orchestrator.py:470-471` persiste toda la memoria en `langgraph_checkpoints.sqlite`. No hay mecanismo de limpieza cuando una sesión se marca como `completed`. El archivo crecerá indefinidamente.  
**Fix futuro:** Agregar un cleanup job que borre checkpoints de sesiones cerradas.

### Bug #7 — CORS hardcodeado
`main.py:46` tiene `allow_origins=["http://localhost:5173"]`. Está bien para desarrollo.  
**Fix para producción:** Leer de variable de entorno `CORS_ORIGINS` (lista separada por comas).

### Bug #8 — Sin rate limiting
No hay rate limiting por usuario. Un jugador podría enviar cientos de emails y disparar costos de OpenAI.  
**Fix sugerido:** Agregar un middleware o decorador que limite a ~20 emails/hora por usuario.

### Bug #9 — Sin tests formales
Los scripts en `scripts/` son tests manuales/semi-automatizados, no una suite pytest. Funcionan para QA pero no para CI/CD.

### Bug #10 — Sin Docker
No hay Dockerfile ni docker-compose. El setup es manual.

---

## 📋 Tareas para el siguiente agente

Lista priorizada:

1. **Fix #2 (trivial):** Renombrar `SMTP_EMAIL` → `SMTP_USER` en `.env.example`.
2. **Evaluar moderador (#1):** Decidir si reimplementar con reglas (regex) o dejar en bypass. Consultar al propietario si hay dudas sobre el enfoque.
3. **Parametrizar CORS (#7):** Mover `allow_origins` a variable de entorno.
4. **Rate limiting (#8):** Implementar limitador básico por email del jugador.
5. **Suite de tests (#9):** Convertir los scripts de `scripts/test_*.py` en tests pytest formales con fixtures.
6. **Dockerizar (#10):** Crear Dockerfile + docker-compose para backend + frontend.
7. **Limpieza de checkpoints (#6):** Job de cleanup para `langgraph_checkpoints.sqlite`.
8. **Persistir processed_ids (#3):** Mover a SQLite o IMAP flags.

---

## 🔀 Estado de branches

| Branch | Propósito | Estado |
|---|---|---|
| master | Desarrollo principal | Estable, servidor arranca, flujo email→LLM→email funcional en DEV_MODE |

No hay branches huérfanas.

---

## ⚠️ Decisiones tomadas que no deben revertirse

1. **OpenAI como LLM principal.** gpt-4o-mini es el modelo activo. Gemini queda como opción futura configurable, no como reemplazo.
2. **IMAP polling sobre webhooks.** Gmail no soporta webhooks de email nativamente sin Google Pub/Sub y un dominio verificado. IMAP polling cada 15 segundos es la solución pragmática para MVP. Funciona sin infraestructura adicional.
3. **Moderador desactivado.** Decisión del propietario. Era demasiado estricto con preguntas legítimas de investigación. No reactivar el moderador LLM sin aprobación.
4. **Time Guardian con DEV_MODE.** En desarrollo se usa `DEV_MODE=true` para respuestas inmediatas. En producción se pone `false` y el guardian aplica delays realistas parseados de los system_prompts.
5. **SQLite como DB de desarrollo.** No migrar a PostgreSQL hasta que se necesite producción real. SQLite simplifica el setup y es suficiente para las pruebas actuales.
6. **Nudge Engine sin LLM.** Usa plantillas, no genera con IA, para controlar costos. Los templates cubren 3 niveles de urgencia con variación aleatoria. Esto es intencional.
7. **Memoria LangGraph por par (usuario, personaje).** El `thread_id` en `imap_poller.py:134` es `thread_{from_email}_{char_alias}`. Esto permite que cada conversación con un personaje mantenga su propio historial. NO cambiar este formato sin entender el impacto en sesiones activas.

---

## 🧪 Cómo verificar que el sistema funciona

### Arranque mínimo

```bash
cd backend
python -m uvicorn main:app --port 8001
```

1. **GET** `http://localhost:8001/` → debe retornar `{"status": "ok", "message": "Expediente Abierto Backend is running"}`
2. El log debe mostrar:
   - `Escáner IMAP iniciado` (o error de credenciales si no hay `.env`)
   - `Delivery Worker iniciado`
   - `Nudge Engine iniciado`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Corre en `http://localhost:5173` o `5174`.

### Test del flujo email completo (requiere credenciales)

1. Asegurar `.env` con `SMTP_USER`, `SMTP_APP_PASSWORD`, `OPENAI_API_KEY`, `JWT_SECRET`, y `DEV_MODE=true`.
2. Arrancar backend.
3. Enviar email a la cuenta Gmail del sistema con asunto que contenga "expediente abierto" y primera línea `@dr.dellarno` (o cualquier alias del caso martes_3).
4. En ~15 segundos el poller lo detecta, LangGraph procesa, y el jugador recibe respuesta inmediata (DEV_MODE).

### Test rápido de scripts QA

```bash
cd backend
python scripts/test_time_guardian.py
python scripts/test_vault.py
```

---

## 📝 Notas adicionales para el agente entrante

### Cosas que parecen extrañas pero tienen razón:

1. **Línea 152 de `nudge_engine.py`** — Hay una línea muerta: `user = db.query(...).first() if False else None`. Es un residuo de refactor, no hace nada. Se puede borrar sin impacto.

2. **El IMAP poller ignora correos sin `@alias` en la primera línea** (línea 115-117 de `imap_poller.py`). Esto es intencional: previene un loop infinito donde el sistema se respondería a sí mismo. Sin el `@alias`, el `target_character` sería el SMTP_USER del sistema, y el sistema se enviaría correos a sí mismo.

3. **`characters_db` es un dict global** cargado al importar `orchestrator.py` (líneas 17-33). Los personajes se cargan de TODOS los casos, no solo del caso activo. Esto es por diseño: permite que el poller enrute a cualquier personaje de cualquier caso sin saber de antemano cuál caso está jugando el usuario.

4. **El Director node cierra la conexión DB de forma asimétrica** (líneas 96-98 y 213-216 de `orchestrator.py`). Si se encontró `db_session_obj`, la conexión se cierra en el bloque de actualización. Si no, se cierra en el `finally` del try. Funciona pero es frágil — un refactor con context manager (`with SessionLocal() as db:`) sería más limpio.

5. **El `route_email` busca "juez", "director" o "expediente" en el username** (línea 48). Esto determina si el email va al Director (para resolver el caso) o al flujo normal de personajes. Los emails de resolución deben enviarse a una dirección que contenga alguna de esas palabras.

6. **El Active Director se activa cada 6 mensajes del jugador** (línea 300). El `%6` es un balance: muy frecuente = muchas llamadas LLM innecesarias, muy infrecuente = el jugador se frustra antes de recibir ayuda. 6 es suficiente para que haya material conversacional para evaluar.

---

## 7.1 Decisiones de diseño no documentadas (exclusivo Antygravity)

| Decisión | Motivo |
|---|---|
| IMAP polling vs webhooks | Gmail requiere Google Pub/Sub + dominio verificado + Cloud Functions para webhooks reales. IMAP polling cada 15s es zero-infrastructure y suficiente para el volumen actual. |
| Moderador desactivado | El prompt del moderador fue calibrado para distinguir "investigación legítima" de "prompt injection", pero en la práctica bloqueaba preguntas como "dame el email del sospechoso" que son mecánica core del juego. El propietario aprobó el bypass. |
| gpt-4o-mini sobre Gemini | Mejor rendimiento en español coloquial argentino ("respondés", "fijate", etc.) que es el tono narrativo del juego. LangChain tenía integración más estable con OpenAI en el momento del desarrollo. |
| `add_messages` de LangGraph | Se usa el reducer automático de LangGraph para manejar el historial. Esto permite que `state["messages"]` crezca automáticamente sin lógica manual de append/truncate. |
| Checkpoints en SQLite vs Memory | Se empezó con `MemorySaver` (en memoria) y se migró a `SqliteSaver` para persistencia entre reinicios. El archivo `langgraph_checkpoints.sqlite` vive en la raíz de `backend/`. |
| Sem. inicial del IMAP poller | Al arrancar, el poller marca los últimos 10 correos como "ya procesados" sin leerlos (línea 51-56). Esto evita que al reiniciar el servidor se reprocesen correos antiguos. El número 10 es arbitrario pero suficiente para cubrir la actividad reciente. |
| Thread ID con email+alias | El formato `thread_{email}_{alias}` en `imap_poller.py:134` permite que un mismo jugador tenga conversaciones independientes con múltiples personajes del mismo caso, cada una con su propia memoria LangGraph. |

## 7.2 Estado real vs. estado documentado

| README dice | Realidad | Impacto |
|---|---|---|
| "seguridad de grado comercial" | La seguridad JWT es real, pero el moderador está en bypass | Corregir README si se deja en bypass permanente |
| "Integración SMTP para comunicación real" | ✅ Correcto, SMTP funciona | Ninguno |
| "LangGraph Checkpointer: memoria a largo plazo" | ✅ Correcto, usa SqliteSaver | Ninguno |
| "Transacciones Seguras: si el correo falla, rollback" | ✅ Correcto, implementado en `api/cases.py` | Ninguno |
| "JWT_SECRET obligatorio" | ✅ Correcto, `security.py` lanza RuntimeError sin ella | Ninguno |
| Falta documentar: Time Guardian, Nudge Engine, Active Director, Delivery Worker | Estos 4 subsistemas no están en el README | Hay que corregir el README |
| `pip install -r requirements.txt` "(Próximamente)" | No hay `requirements.txt` todavía | Agregar con `pip freeze` |

## 7.3 Partes frágiles del sistema

1. **`orchestrator.py` — Manejo de DB sessions.** Las conexiones DB se abren/cierran de forma manual con lógica de branches (if/else) en `director_process` y `active_director_process`. Un error no capturado puede dejar conexiones abiertas. Refactorizar con context managers.

2. **`imap_poller.py` — Parsing de `@alias`.** El mecanismo de primera línea `@alias` es manual: `lines[0].split(maxsplit=1)`. Si el email tiene formato HTML (no text/plain), el parser puede fallar silenciosamente y descartar el correo. Solo funciona con emails de texto plano.

3. **`time_guardian.py` — Regex de latencia.** El parser `parse_latency_from_prompt` busca patrones de latencia en español libre en los system_prompts. Si un prompt no sigue el formato esperado ("Respondés entre X y Y minutos"), el default es 15-60 minutos. Cualquier cambio en la redacción de system_prompts puede alterar las latencias sin previo aviso.

4. **`nudge_engine.py` — Detección de "último mensaje del jugador".** Usa `Message.from_email != None` para filtrar mensajes del jugador, pero todos los mensajes tienen `from_email`. La intención era distinguir por dirección, pero la lógica actual no verifica quién es "el jugador" vs "el personaje". Funciona por casualidad porque los nudges se generan por sesión y la mayoría de mensajes del jugador entran primero. Necesita revisión.

5. **Archivo `langgraph_checkpoints.sqlite`** — Crece indefinidamente. Sin limpieza automática. Con muchas conversaciones puede ralentizar las queries del checkpointer.

## 7.4 Lo que estaba en progreso al ceder el turno

1. **`requirements.txt` no existe.** El backend funciona con las dependencias instaladas manualmente en el venv, pero nunca se generó un `requirements.txt`. El siguiente agente debe hacer `pip freeze > requirements.txt` en el venv activo para capturarlo.

2. **Dashboard frontend incompleto.** El frontend tiene LandingPage, login, y dashboard básico, pero el dashboard no está conectado a todos los endpoints del backend (ej: no muestra sesiones activas del Nudge Engine ni estado del Time Guardian).

3. **`caso_cero` marcado como "Borrador".** El JSON existe en `backend/casos/` pero puede estar incompleto en sus condiciones de victoria/derrota. No fue testeado con el playthrough_simulator.

---

*Fin del HANDOFF — Antygravity, 2026-05-01*
