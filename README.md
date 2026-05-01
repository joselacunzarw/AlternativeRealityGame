# Expediente Abierto — Cyberpunk Noir ARG

Motor de IA conversacional para un juego de realidad alternativa (ARG) de detectives, con estética **Tech Noir**.

## Características del Sistema

- **Identidad Digital Segura**: Autenticación passwordless mediante códigos OTP por correo y sesiones JWT (24h). Protección contra fuerza bruta con lockout tras 5 intentos fallidos.
- **Diseño Cyberpunk**: Interfaz HUD/Noir con sistema de tokens dinámicos, scanlines y micro-animaciones.
- **Orquestación LangGraph**: Red de agentes de IA con 5 nodos (Director, Moderador, Director Activo, Personaje, Guardián del Tiempo) y memoria persistente por hilo conversacional (SQLite).
- **Motor de Correo**: Polling IMAP sobre Gmail cada 15 segundos. Respuestas con latencia realista calculada desde el perfil de cada personaje.
- **Rate Limiting**: Máximo configurable de emails procesados por jugador por hora (default: 20).

## Arquitectura Técnica

### Backend (FastAPI + LangGraph)

| Componente | Descripción |
|---|---|
| `core/orchestrator.py` | Grafo LangGraph con 5 nodos. Punto central del motor de juego. |
| `core/imap_poller.py` | Lee Gmail cada 15s. Enruta por `@alias` en primera línea del email. |
| `core/time_guardian.py` | Intercepta respuestas y las encola con delay realista (parsea latencia del system_prompt). |
| `core/delivery_worker.py` | Entrega mensajes encolados cuando llega su hora. Corre cada 30s. |
| `core/nudge_engine.py` | Re-engagement proactivo: nudges a las 24h, 48h y 72h de inactividad. Sin LLM, usa plantillas. |
| `core/mailer.py` | Envío SMTP via Gmail SSL. |
| `api/cases.py` | Catálogo de casos e inicio de partida (transacción atómica: rollback si el email falla). |
| `api/users.py` | Auth OTP passwordless + perfil del detective con historial de casos. |
| `api/vault.py` | Bóveda Forense: desbloqueo de evidencia con claves obtenidas en el juego. |

### Frontend (React + Vite)
- **Glassmorphism UI**: Paneles de cristal, tipografía Fira Code, paleta neón.
- **Bóveda Forense**: Componente de desencriptación de evidencia.
- **ProtectedRoute**: Navegación segura con JWT.

## Configuración Inicial

### Backend

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Completar .env con: JWT_SECRET, OPENAI_API_KEY, SMTP_USER, SMTP_APP_PASSWORD
python -m uvicorn main:app --port 8001
```

El servidor arranca con tres workers en background: IMAP poller, Delivery Worker y Nudge Engine.

### Frontend

```bash
cd frontend
npm install
npm run dev
# Corre en http://localhost:5173
```

### Variables de entorno obligatorias

| Variable | Descripción |
|---|---|
| `JWT_SECRET` | Secreto para firmar tokens. Generar con `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `OPENAI_API_KEY` | API key de OpenAI (usa gpt-4o-mini). |
| `SMTP_USER` | Email de Gmail del sistema (ej: `agencia@gmail.com`). |
| `SMTP_APP_PASSWORD` | Contraseña de aplicación de Gmail (no la contraseña normal). |
| `DEV_MODE` | `true` = respuestas inmediatas sin delay. `false` = Time Guardian activo. |

## Cómo jugar (flujo básico)

1. El jugador se registra en el frontend con su email y recibe un OTP.
2. Desde el Dashboard elige un caso y lo inicia — recibe el briefing por email.
3. Responde a los personajes enviando emails a su cuenta Gmail del sistema con:
   - Asunto que contenga `"Expediente Abierto"` o `"Caso Abierto"`.
   - Primera línea del cuerpo: `@alias_del_personaje` (ej: `@hernan.dellarno`).
4. Los personajes responden con latencia realista (configurable con `DEV_MODE=true` para desarrollo).
5. Al resolver el caso, envía un email al Director (`@director`) con la resolución.

## Casos disponibles

| ID | Título | Personajes |
|---|---|---|
| `postuma_0` | Póstuma | — |
| `grabacion_1` | La Grabación | — |
| `herencia_2` | La Herencia | — |
| `martes_3` | El Club de los Martes | Hernán, Secretaría, Juan, Paula |
| `novia_4` | La Novia | — |
| `experimento_5` | El Experimento | — |

## Equipo de desarrollo

Ver [EQUIPO_DE_TRABAJO.md](EQUIPO_DE_TRABAJO.md) para la metodología de trabajo multi-agente y el protocolo de handoff.
