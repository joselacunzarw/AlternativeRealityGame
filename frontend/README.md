# 🗄️ Expediente Abierto - Terminal de Agente (Frontend)

Esta es la terminal segura del detective, construida con **React + Vite** y un sistema de diseño customizado para inmersión total.

## 🎨 Design System: Cyberpunk Noir
El estilo visual se basa en una paleta de colores neón sobre fondos oscuros profundos, utilizando variables CSS centralizadas en `src/index.css`:
- **Neon Green**: `#00FF00` (Acciones primarias / Éxito)
- **Neon Cyan**: `#00FFFF` (Información / HUD)
- **Danger Red**: `#FF0050` (Alertas / Fracasos)
- **Glassmorphism**: Todos los paneles usan `backdrop-filter` para simular interfaces táctiles futuristas.

## 🔑 Características
- **ProtectedRoute**: Bloqueo de acceso a las vistas de Despacho y Perfil si no existe un token de sesión válido.
- **authFetch**: Helper centralizado para peticiones a la API que inyecta el token y maneja redirecciones automáticas ante expiración de sesión.
- **Bóveda Forense**: Simulador de desencriptación de archivos.

## 🛠️ Instalación y Uso

1. Instalar dependencias:
   ```bash
   npm install
   ```

2. Configurar API:
   Por defecto, el frontend intenta conectar con `http://localhost:8001`. Puedes cambiar esto creando un archivo `.env` en esta carpeta con:
   ```env
   VITE_API_URL=https://tu-api-produccion.com
   ```

3. Correr en desarrollo:
   ```bash
   npm run dev
   ```

## 🚀 Build
Para generar la versión de producción:
```bash
npm run build
```
Los archivos se generarán en la carpeta `dist/`.
