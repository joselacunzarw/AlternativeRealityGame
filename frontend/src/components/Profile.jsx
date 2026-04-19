import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, CheckCircle, XCircle, Clock, Shield } from 'lucide-react'

export default function Profile() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const userEmail = localStorage.getItem('userEmail');
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8001";

  useEffect(() => {
    const token = localStorage.getItem('token');

    if (!token || !userEmail) {
      navigate('/');
      return;
    }

    fetch(`${API_URL}/api/v1/users/me/profile`, {
      headers: { "Authorization": `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => {
        setProfile(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error cargando perfil:", err);
        setLoading(false);
      });
  }, [userEmail, navigate, API_URL]);

  if (loading) return (
    <div className="container" style={{ padding: '4rem 2rem', textAlign: 'center' }}>
      <p className="mono animate-pulse text-neon-green" style={{ fontSize: '0.85rem' }}>DESCIFRANDO LEGAJO OPERATIVO...</p>
    </div>
  );

  if (!profile) return (
    <div className="container" style={{ padding: '4rem 2rem', textAlign: 'center' }}>
      <p className="text-danger">ERROR: LEGAJO NO ENCONTRADO.</p>
    </div>
  );

  // Combine active_case + history into one list for the table
  const allSessions = [];
  if (profile.active_case) allSessions.push(profile.active_case);
  if (profile.history) allSessions.push(...profile.history);

  const metrics = profile.metrics || {};
  // Total includes active case + past
  const totalCases = (profile.active_case ? 1 : 0) + (metrics.total_played || 0);

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem' }}>
      
      {/* === HEADER === */}
      <header style={{ marginBottom: '2.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1.5rem' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Shield color="var(--neon-green)" size={28} style={{ filter: 'drop-shadow(0 0 8px rgba(0,255,0,0.3))' }} />
          LEGAJO OPERATIVO
        </h1>
        <div style={{ marginTop: '0.75rem', display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
          <p className="mono text-neon-cyan" style={{ fontSize: '0.8rem' }}>
            <User size={12} style={{ display: 'inline', marginRight: 4 }} /> {profile.email}
          </p>
          <p className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            <Clock size={12} style={{ display: 'inline', marginRight: 4 }} /> MIEMBRO DESDE: {new Date(profile.joined_at || Date.now()).toLocaleDateString('es-AR', { month: 'long', year: 'numeric' }).toUpperCase()}
          </p>
        </div>
      </header>

      {/* === STATS ROW === */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-lg)', marginBottom: 'var(--space-2xl)' }}>
        <div className="stat-card gold">
          <p className="stat-label">Casos Asignados</p>
          <p className="stat-number" style={{ color: 'var(--neon-gold)' }}>{totalCases}</p>
        </div>
        <div className="stat-card green">
          <p className="stat-label">Éxitos Confirmados</p>
          <p className="stat-number" style={{ color: 'var(--neon-green)' }}>{metrics.completed_success || 0}</p>
          <CheckCircle size={20} color="var(--neon-green)" style={{ margin: '0.5rem auto 0', opacity: 0.6 }} />
        </div>
        <div className="stat-card red">
          <p className="stat-label">Abandonados</p>
          <p className="stat-number" style={{ color: 'var(--danger-red)' }}>{metrics.abandoned || 0}</p>
          <XCircle size={20} color="var(--danger-red)" style={{ margin: '0.5rem auto 0', opacity: 0.6 }} />
        </div>
      </div>

      {/* === MISSION HISTORY TABLE === */}
      <div className="glass-panel" style={{ cursor: 'default', padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: 'var(--space-lg)', borderBottom: '1px solid var(--border-color)' }}>
          <h2 className="text-neon-green" style={{ fontSize: '1rem' }}>HISTORIAL DE MISIONES</h2>
        </div>
        
        {allSessions.length > 0 ? (
          <table className="mission-table">
            <thead>
              <tr>
                <th>Expediente</th>
                <th>Inicio</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {allSessions.map((s, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{s.title || s.game_id?.toUpperCase() || 'DESCONOCIDO'}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{new Date(s.started_at).toLocaleDateString('es-AR')}</td>
                  <td>
                    {s.status === 'active' && <span className="badge badge-active animate-pulse">ACTIVO</span>}
                    {s.status === 'abandonado' && <span className="badge badge-abandoned">ABANDONADO</span>}
                    {(s.status === 'completed_success' || s.status === 'completed') && <span className="badge badge-resolved">RESUELTO</span>}
                    {s.status === 'completed_fail' && <span className="badge badge-abandoned">FALLIDO</span>}
                    {!['active','abandonado','completed','completed_success','completed_fail'].includes(s.status) && <span className="badge" style={{ color: 'var(--text-muted)' }}>{s.status?.toUpperCase()}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: 'var(--space-2xl)', textAlign: 'center' }}>
            <p className="mono" style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>NO HAY MISIONES REGISTRADAS EN SU LEGAJO.</p>
          </div>
        )}
      </div>
    </div>
  )
}
