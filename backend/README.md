# 🧠 Expediente Abierto - Motor de Grafos (Backend)

Este es el núcleo de inteligencia y orquestación del ARG, construido con **FastAPI** y **LangGraph**.

## 🚀 Arquitectura
El backend maneja la lógica de estado del juego mediante un grafo dirigido acíclico (DAG) que decide qué personaje responde al jugador basándose en el historial almacenado en SQLite.

### Componentes Clave
- **FastAPI**: API REST para el frontend y webhooks.
- **LangGraph**: Motor de estados con persistencia.
- **SQLAlchemy**: Gestión de usuarios y sesiones.
- **IMAP Poller**: Escáner de correos entrantes (en segundo plano).

## 🛠️ Requisitos
- Python 3.10+
- OpenAI API Key
- Servidor SMTP (Gmail App Password recomendado)

## ⚙️ Configuración y Variables de Entorno
Es obligatorio configurar el archivo `.env` basado en `.env.example`:

- `JWT_SECRET`: Llave de seguridad para tokens de sesión. **El servidor no arranca sin esto.**
- `OPENAI_API_KEY`: Para el motor de narrativa GPT-4o.
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USER`, `SMTP_APP_PASSWORD`: Para que el juego pueda enviarte correos.
- `IMAP_SERVER`, `IMAP_USER`, `IMAP_PASSWORD`: Para que el juego pueda leer tus respuestas.

## 🏃 Ejecución

1. Activar entorno virtual e instalar dependencias.
2. Iniciar el servidor:
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8001 --reload
   ```

## 🔐 Seguridad
La API está protegida por JWT. El endpoint `/api/v1/auth/request-otp` genera un código de 6 dígitos que se envía por correo para validar la identidad del detective.
