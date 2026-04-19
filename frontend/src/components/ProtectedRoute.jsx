import { Navigate } from 'react-router-dom'

/**
 * ProtectedRoute — Bloquea acceso a rutas privadas si no hay token JWT.
 * Si el token no existe en localStorage, redirige al landing (/).
 */
export default function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token')
  
  if (!token) {
    return <Navigate to="/" replace />
  }
  
  return children
}
