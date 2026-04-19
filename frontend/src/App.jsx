import React from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import { Shield, LogOut } from 'lucide-react'
import './index.css'

import LandingPage from './components/LandingPage'
import Dashboard from './components/Dashboard'
import Vault from './components/Vault'
import Profile from './components/Profile'
import ProtectedRoute from './components/ProtectedRoute'

function Navigation() {
  const location = useLocation()
  const navigate = useNavigate()
  const isLoggedIn = !!localStorage.getItem('token')
  
  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('userEmail')
    navigate('/')
  }

  // Don't render navbar on landing page
  if (location.pathname === '/') return null;

  return (
    <nav className="navbar">
      <Link to="/dashboard" className="logo-text" style={{ textDecoration: 'none' }}>
        <Shield size={18} /> EXPEDIENTE<span style={{ color: "var(--text-muted)", fontWeight: 300 }}>ABIERTO</span>
      </Link>
      
      <div className="nav-links">
        <Link to="/dashboard" className={location.pathname === '/dashboard' ? 'active' : ''}>Despacho</Link>
        <Link to="/profile" className={location.pathname === '/profile' ? 'active' : ''}>Legajo</Link>
        {isLoggedIn && (
          <a onClick={handleLogout} style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <LogOut size={12} /> Salir
          </a>
        )}
      </div>
    </nav>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Navigation />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="/vault" element={<ProtectedRoute><Vault /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App

