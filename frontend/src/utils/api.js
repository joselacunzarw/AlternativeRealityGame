/**
 * authFetch — Wrapper de fetch que maneja JWT y sesiones expiradas.
 * 
 * - Inyecta el header Authorization automáticamente.
 * - Si el backend responde 401/403, limpia el token y redirige al login.
 * - Lanza un error con el detalle del backend para errores 4xx/5xx.
 */

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8001";

export async function authFetch(path, options = {}) {
  const token = localStorage.getItem('token');
  
  const headers = {
    ...options.headers,
  };
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  
  if (options.body && typeof options.body === 'string') {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });
  
  // Sesión expirada o token inválido
  if (response.status === 401 || response.status === 403) {
    localStorage.removeItem('token');
    localStorage.removeItem('userEmail');
    window.location.href = '/';
    throw new Error('Sesión expirada. Redirigiendo al login...');
  }
  
  // Errores del servidor
  if (!response.ok) {
    let detail = `Error ${response.status}`;
    try {
      const errBody = await response.json();
      detail = errBody.detail || errBody.message || detail;
    } catch {
      // El body no era JSON
    }
    throw new Error(detail);
  }
  
  return response.json();
}
