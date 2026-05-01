# Expediente Abierto — Reglamento de Trabajo Multi-Agente

> **Versión:** 1.0  
> **Fecha:** 2026-05-01  
> **Propietario del producto:** Jose Lacunza  
> **Estado:** Activo

---

## 0. Para el agente que lee esto por primera vez

Este documento es tu briefing completo. Antes de escribir una sola línea de código:
1. Lee este documento entero.
2. Lee `HANDOFF.md` si existe — contiene el estado exacto dejado por el agente anterior.
3. Lee el `README.md` del proyecto.
4. Si algo contradice otro documento, este reglamento tiene precedencia. Anota la contradicción en tu `HANDOFF.md` al terminar.

---

## 1. El Proyecto

**Nombre:** Expediente Abierto  
**Tipo:** ARG (Alternate Reality Game) de detectives jugado enteramente por email.  
**Concepto central:** El jugador recibe un caso ficticio y lo resuelve conversando por correo real con testigos y sospechosos que son agentes de IA autónomos con personalidad, memoria y secretos propios.

### Stack técnico
| Capa | Tecnología |
|---|---|
| Backend | Python 3.x + FastAPI |
| Orquestación IA | LangGraph (StateGraph + SqliteSaver) |
| LLM | OpenAI GPT-4o-mini (activo) / Gemini (en .env, sin usar) |
| Email entrante | IMAP polling sobre Gmail (cada 15s) |
| Email saliente | SMTP Gmail con App Password |
| Base de datos | SQLite (desarrollo) |
| Frontend | React + Vite |
| Auth | JWT + OTP passwordless |

### Estructura del repositorio
```
AlternativeRealityGame/
├── backend/
│   ├── api/              → Routers FastAPI (cases, users, vault, webhook)
│   ├── casos/            → JSONs de cada caso (7 casos)
│   ├── core/             → Lógica de negocio central
│   │   ├── orchestrator.py    ⚠️ ARCHIVO CRÍTICO — ver reglas
│   │   ├── imap_poller.py
│   │   ├── mailer.py
│   │   ├── time_guardian.py
│   │   ├── nudge_engine.py
│   │   ├── delivery_worker.py
│   │   └── security.py
│   ├── database/         → Modelos SQLAlchemy y conexión
│   ├── models/           → Schemas Pydantic
│   └── scripts/          → QA, simuladores, herramientas de testing
├── frontend/
│   └── src/
│       └── components/   → LandingPage, Dashboard, Vault, Profile
├── design-system/        → Documentación del sistema de diseño Cyberpunk Noir
├── HANDOFF.md            → Estado dejado por el último agente (generado por cada agente)
├── EQUIPO_DE_TRABAJO.md  → Este archivo
└── README.md
```

### Casos disponibles
| ID | Título | Estado |
|---|---|---|
| `postuma_0` | Póstuma | Disponible |
| `grabacion_1` | La Grabación | Disponible |
| `herencia_2` | La Herencia | Disponible |
| `martes_3` | El Club de los Martes | **Caso activo / referencia** |
| `novia_4` | La Novia | Disponible |
| `experimento_5` | El Experimento | Disponible |
| `caso_cero` | Caso Cero | Borrador |

---

## 2. El Equipo

### Agente 1 — Antygravity (Gemini Pro)
**Turno:** Primero  
**Fortaleza diferencial:** Ventana de contexto masiva. Puede leer el proyecto completo en una sola pasada. Construyó el código base existente, por lo que posee contexto de decisiones arquitectónicas no documentadas.  
**Responsabilidad principal:** Completar y estabilizar el trabajo iniciado, corregir deuda técnica propia, y dejar la base lista para el siguiente agente.

### Agente 2 — Claude Code (Claude Sonnet)
**Turno:** Segundo  
**Fortaleza diferencial:** Ejecución directa en el repositorio (lectura, escritura, bash). Fuerte en razonamiento arquitectónico, seguridad y verificación de cambios. Puede ejecutar y confirmar que el código funciona.  
**Responsabilidad principal:** Correcciones críticas de seguridad y estabilidad, tests de integración, coordinación técnica del sistema.

### Agente 3 — Codex (OpenAI)
**Turno:** Tercero  
**Fortaleza diferencial:** Generación de código rápida y precisa desde especificaciones concretas. Excelente siguiendo patrones establecidos. Ideal para implementar features bien definidas.  
**Responsabilidad principal:** Implementar features nuevas sobre la base saneada por los dos agentes anteriores.

---

## 3. Metodología de Trabajo — Relay Race

### Principio central
**Un agente trabaja a la vez.** No hay trabajo paralelo. Cuando un agente llega al límite de su contexto/tokens disponibles, entrega el turno al siguiente. El siguiente agente asume la responsabilidad total del proyecto hasta que también necesite ceder el turno.

### Ciclo de un turno
```
1. ONBOARDING
   └── Leer este documento + HANDOFF.md + README.md

2. TRABAJO
   └── Ejecutar tareas según prioridades del HANDOFF.md y/o las
       instrucciones del propietario del producto para este turno

3. CIERRE
   ├── Generar HANDOFF.md actualizado (ver Sección 4)
   ├── Hacer commit de todos los cambios con mensaje descriptivo
   ├── Si hubo branches: asegurarse de que estén mergeadas o documentadas
   └── Notificar al propietario que el turno está completo
```

### Cuándo ceder el turno
- Cuando el contexto disponible es insuficiente para continuar con seguridad.
- Cuando se llega a un punto de decisión que requiere input del propietario.
- Cuando la tarea activa fue completada y no hay instrucciones para continuar.
- **Nunca** ceder el turno con cambios sin commitear o con el sistema en estado roto.

---

## 4. Protocolo de Handoff

Al finalizar cada turno, el agente saliente **debe** generar o actualizar `HANDOFF.md` en la raíz del repositorio. Este archivo es el contrato entre agentes.

### Estructura obligatoria de HANDOFF.md

```markdown
# HANDOFF — [Nombre del Agente] → [Nombre del Siguiente Agente]

**Fecha:** YYYY-MM-DD HH:MM UTC  
**Agente saliente:** [Nombre]  
**Agente entrante:** [Nombre]  
**Branch activa:** [nombre o "main"]

---

## ✅ Qué se hizo en este turno

- [Lista concreta de cambios realizados, con archivos afectados]
- Ejemplo: "Corregida inconsistencia SMTP_EMAIL → SMTP_USER en mailer.py y .env.example"

## 🔴 Problemas críticos pendientes

- [Problemas que DEBEN resolverse antes de avanzar]
- Si no hay: escribir "Ninguno."

## 🟡 Deuda técnica conocida

- [Problemas no críticos que se detectaron pero no se resolvieron]

## 📋 Tareas para el siguiente agente

Lista priorizada de lo que debe hacerse a continuación:
1. [Tarea más urgente]
2. [Segunda tarea]
...

## 🔀 Estado de branches

| Branch | Propósito | Estado |
|---|---|---|
| main | Producción | [descripción del estado] |
| [otras] | [propósito] | [mergeada/activa/abandonada] |

## ⚠️ Decisiones tomadas que no deben revertirse

- [Decisiones arquitectónicas o de diseño tomadas en este turno]
- Ejemplo: "Se decidió mantener OpenAI como LLM principal. Gemini queda para v2."

## 🧪 Cómo verificar que el sistema funciona

Pasos mínimos para confirmar que el backend está operativo:
1. `cd backend && python -m uvicorn main:app --port 8001`
2. GET http://localhost:8001/ → debe retornar `{"status": "ok"}`
3. [Otros pasos específicos si aplican]

## 📝 Notas adicionales para el agente entrante

[Cualquier contexto, advertencia o sugerencia que no encaje arriba]
```

---

## 5. Reglas de Trabajo

### 5.1 Reglas generales

1. **No romper el sistema entre turnos.** Si un turno termina con el servidor caído o con tests fallando, el agente saliente debe arreglarlo antes de ceder. No se hereda un sistema roto.

2. **Commits atómicos y descriptivos.** Cada commit debe tener sentido por sí solo. Formato sugerido:
   ```
   [tipo]: descripción corta
   
   Detalle opcional si el cambio no es evidente.
   ```
   Tipos: `fix`, `feat`, `refactor`, `test`, `docs`, `chore`

3. **No comentar el código sin razón.** Solo se comenta el **por qué**, nunca el **qué**. El código bien nombrado se documenta solo.

4. **No inventar decisiones de producto.** Si algo requiere una decisión que no está documentada (precios, nombre del producto, géneros narrativos), se deja pendiente en el HANDOFF.md y se consulta al propietario. No se asume.

5. **No tocar casos JSON sin instrucción explícita.** Los archivos en `backend/casos/` son contenido de producto. Los cambios técnicos a su estructura requieren aprobación. Los cambios narrativos siempre requieren aprobación.

### 5.2 Regla especial — `backend/core/orchestrator.py`

**Este archivo es zona de alta tensión.**

Concentra: routing del grafo, lógica del Director, lógica del Moderador, lógica del Active Director, configuración del character node, y compilación del grafo LangGraph. Un cambio mal hecho aquí puede romper el flujo completo del juego.

Protocolo obligatorio para modificar `orchestrator.py`:
- Documentar qué se va a cambiar y por qué en el commit message.
- Hacer el cambio en una branch separada (`feature/orquestador-[descripcion]`).
- Verificar el flujo completo antes de mergear (ver script `scripts/playthrough_simulator.py`).
- Registrar el cambio en la sección "Decisiones tomadas" del HANDOFF.md.

### 5.3 Reglas de branches

Se trabaja en `main` por defecto. Se crea una branch **solo** cuando:
- El cambio afecta `orchestrator.py`.
- Se implementa una feature compleja que puede quedar a medio hacer al agotar tokens.
- El propietario lo solicita explícitamente.

Naming de branches:
```
fix/descripcion-corta
feat/descripcion-corta
refactor/descripcion-corta
```

Toda branch debe mergearse o documentarse como abandonada en el HANDOFF.md. No dejar branches huérfanas.

### 5.4 Variables de entorno

El archivo `.env` nunca se commitea. `.env.example` debe estar siempre sincronizado con las variables reales que usa el código. Si se agrega una variable nueva, se agrega también al `.env.example` con valor vacío y comentario descriptivo.

Variables críticas actuales:
```
JWT_SECRET         → Obligatoria. Sin esto el sistema no arranca de forma segura.
OPENAI_API_KEY     → Obligatoria para los nodos LLM.
SMTP_USER          → Email de Gmail del sistema. (⚠️ el .env.example dice SMTP_EMAIL — inconsistencia a corregir)
SMTP_APP_PASSWORD  → Contraseña de aplicación de Gmail.
DEV_MODE           → true = Time Guardian desactivado (respuestas inmediatas). Usar true en desarrollo.
GOOGLE_API_KEY     → Opcional. Para migración futura a Gemini.
```

---

## 6. Problemas Conocidos (estado al inicio del proyecto)

Esta sección documenta los problemas detectados en el análisis inicial. Cada agente debe marcar los que resuelva con `[RESUELTO - Agente X - fecha]`.

| # | Severidad | Problema | Archivo |
|---|---|---|---|
| 1 | 🔴 Crítico | Moderador de seguridad bypasseado — prompt injection sin defensa | `core/orchestrator.py:241` |
| 2 | 🔴 Crítico | Inconsistencia SMTP: `.env.example` define `SMTP_EMAIL` pero el código lee `SMTP_USER` | `core/mailer.py:13` / `.env.example` |
| 3 | 🟡 Importante | `processed_ids` del IMAP poller vive en memoria — se pierden al reiniciar el servidor | `core/imap_poller.py:37` |
| 4 | 🟡 Importante | `expires_at` en GameSession no se enforcea — sesiones nunca expiran de verdad | `database/models.py` |
| 5 | 🟡 Importante | LLM hardcodeado a OpenAI (`gpt-4o-mini`) — el brief planificó Gemini. Decisión no documentada | `core/orchestrator.py` |
| 6 | 🟡 Importante | Aislamiento de memoria LangGraph por `thread_id` no se limpia al cerrar sesión | `core/orchestrator.py:488` |
| 7 | 🟠 Menor | CORS hardcodeado a `localhost:5173` — no parametrizable para producción | `main.py:46` |
| 8 | 🟠 Menor | Sin rate limiting por usuario — jugadores insistentes pueden disparar costos | Backend general |
| 9 | 🟠 Menor | Sin tests formales — hay scripts QA pero no suite de tests | `scripts/` |
| 10 | 🟠 Menor | Sin Docker / docker-compose — despliegue manual | Raíz del repo |

---

## 7. Lo que Antygravity debe entregar al final de su turno

Antygravity tiene contexto privilegiado por haber construido el sistema. Además de seguir el protocolo estándar de handoff, su `HANDOFF.md` debe incluir las siguientes secciones adicionales obligatorias:

### 7.1 Decisiones de diseño no documentadas
Por cada decisión arquitectónica que tomó durante la construcción y que no está en ningún archivo, debe documentarla. Ejemplos:
- Por qué se eligió IMAP polling sobre webhooks de email.
- Por qué el moderador fue desactivado (bypass temporal o decisión de diseño).
- Por qué `gpt-4o-mini` en lugar de Gemini si el brief planificó Gemini.
- Cualquier patrón en el código que parezca extraño pero tenga una razón.

### 7.2 Estado real vs. estado documentado
Una lista de discrepancias entre lo que dice el README y lo que realmente hace el código. Formato:
```
README dice: X
Realidad: Y
Impacto: [ninguno / menor / hay que corregir el README]
```

### 7.3 Partes frágiles del sistema
Código que funciona pero que sabe que es frágil o que requiere cuidado especial. No tiene que ser un bug — puede ser un patrón que solo funciona bajo ciertas condiciones.

### 7.4 Lo que estaba en progreso al ceder el turno
Si hay trabajo a medio terminar, documentarlo con precisión:
- Qué se empezó.
- En qué punto quedó.
- Qué falta para completarlo.
- Archivos afectados.

---

## 8. Criterios de calidad del proyecto

El código producido por cualquier agente debe cumplir:

- **Funciona:** el servidor arranca, el endpoint `/` responde, el flujo email→LLM→email completa sin errores en DEV_MODE.
- **No regresiona:** los casos existentes siguen siendo cargados correctamente por el orquestador.
- **No expone secretos:** ningún commit contiene `.env`, API keys, passwords ni tokens.
- **Es legible:** nombres de variables y funciones en español o inglés consistente con el archivo donde viven. No mezclar idiomas dentro de un mismo módulo.
- **No sobre-ingeniería:** si una solución simple resuelve el problema, es la correcta. No se abstraen patrones para casos hipotéticos futuros.

---

## 9. Contacto con el propietario del producto

**Email:** joselacunzarw@gmail.com  

Consultar al propietario cuando:
- Una decisión de producto bloquea el trabajo técnico.
- Se detecta una contradicción en los requerimientos.
- El alcance del turno no está claro.
- Se va a tomar una decisión irreversible que afecte la experiencia del jugador.

No consultar al propietario por decisiones técnicas internas que no afecten la experiencia de juego.

---

## 10. Historial de turnos

| Turno | Agente | Fecha inicio | Fecha cierre | Estado |
|---|---|---|---|---|
| 1 | Antygravity (Gemini Pro) | Pendiente | — | Pendiente |
| 2 | Claude Code (Claude Sonnet) | — | — | En espera |
| 3 | Codex (OpenAI) | — | — | En espera |

*Este historial debe actualizarse al inicio y al cierre de cada turno.*

---

*Fin del reglamento — versión 1.0*  
*Generado por Claude Code el 2026-05-01*
