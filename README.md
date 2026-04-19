# 🕶️ Expediente Abierto - Cyberpunk Noir ARG

Motor de IA conversacional para un juego de realidad aumentada (ARG) de detectives, con estética **Tech Noir** y seguridad de grado comercial.

## 🚀 Características del Sistema

- **Identidad Digital Segura**: Autenticación *passwordless* mediante códigos OTP por correo y sesiones JWT (24h).
- **Diseño Cyberpunk Pro Max**: Interfaz HUD/Noir diseñada con un sistema de tokens dinámicos, *scanlines* y micro-animaciones.
- **Orquestación LangGraph**: Red de agentes de IA que manejan la narrativa de múltiples personajes con memoria persistente (SQLite).
- **Motor de Correo**: Integración SMTP para comunicación real entre el detective (jugador) y los sospechosos (agentes).

## 🛠️ Arquitectura Técnica

### Backend (FastAPI + LangGraph)
- **LangGraph Checkpointer**: Capacidad de "memoria a largo plazo" para que los NPCs recuerden conversaciones pasadas.
- **Transacciones Seguras**: Lógica de inicio de casos protegida; si el correo de briefing falla, la base de datos revierte los cambios automáticamente.
- **Seguridad Estricta**: JWT_SECRET obligatorio y endpoints protegidos con inyección de identidad del jugador.

### Frontend (React + Vite)
- **Glassmorphism UI**: Paneles de cristal, tipografía *Fira Code* y paleta neón optimizada para legibilidad.
- **Bóveda Forense**: Componente de desencriptación de evidencia basado en claves obtenidas durante el juego.
- **ProtectedRoute**: Navegación segura que protege el despacho y los perfiles de agentes no autorizados.

## ⚙️ Configuración Inicial

1. **Backend**:
   - `cd backend`
   - Crear entorno virtual: `python -m venv venv`
   - Instalar dependencias: `pip install -r requirements.txt` (Próximamente)
   - Configurar sesion: Copiar `.env.example` a `.env` y completar las keys.
   - Iniciar: `python -m uvicorn main:app --port 8001`

2. **Frontend**:
   - `cd frontend`
   - Instalar dependencias: `npm install`
   - Iniciar: `npm run dev` (Corre en `http://localhost:5173` o `5174`)

## 📂 Estructura del Caso Activo
Actualmente el sistema está configurado para el caso **"El Club de los Martes"**: Una trama de traición médica y secretos industriales en la ciudad de Leiden.
