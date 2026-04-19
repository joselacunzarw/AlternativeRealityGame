import React, { useState, useEffect } from 'react'
import { FolderKanban, Play, AlertTriangle, Radio, Shield } from 'lucide-react'
import { authFetch } from '../utils/api'

export default function Dashboard() {
  const [casos, setCasos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [alertMsg, setAlertMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [showWarningModal, setShowWarningModal] = useState(null);
  
  const userEmail = localStorage.getItem('userEmail');

  const loadCases = () => {
    setLoading(true);
    setErrorMsg("");
    authFetch('/api/v1/cases')
      .then(data => {
        setCasos(data.cases || []);
        setLoading(false);
      })
      .catch(err => {
        console.error("Error cargando casos:", err);
        setErrorMsg(err.message);
        setLoading(false);
      });
  }

  useEffect(() => {
    loadCases();
  }, []);

  const activeCase = casos.find(c => c.status === 'active');

  const initiateCase = (caseId) => {
    setErrorMsg("");
    authFetch('/api/v1/game/start', {
      method: "POST",
      body: JSON.stringify({ user_email: userEmail, case_id: caseId })
    })
    .then(data => {
      setAlertMsg(data.message || "Caso iniciado");
      setShowWarningModal(null);
      loadCases();
      setTimeout(() => setAlertMsg(""), 4000);
    })
    .catch(err => {
      setShowWarningModal(null);
      setErrorMsg(err.message);
      setTimeout(() => setErrorMsg(""), 6000);
    });
  }

  const handleStartRequest = (caseId) => {
    if (activeCase && activeCase.id !== caseId) {
      setShowWarningModal(caseId);
    } else {
      initiateCase(caseId);
    }
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem', position: 'relative' }}>
      
      {/* === CRITICAL WARNING MODAL === */}
      {showWarningModal && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(4px)' }}>
          <div className="glass-panel animate-fade-in" style={{ maxWidth: '500px', border: '1px solid var(--danger-red)', textAlign: 'center', cursor: 'default' }}>
            <AlertTriangle size={48} color="var(--danger-red)" style={{ margin: '0 auto 1rem auto', filter: 'drop-shadow(0 0 10px rgba(255,0,80,0.5))' }} />
            <h2 style={{ color: 'var(--danger-red)', marginBottom: '1rem', fontFamily: "'Fira Code', monospace" }}>ADVERTENCIA CRÍTICA</h2>
            <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', lineHeight: 1.7 }}>
              Ya tienes un expediente en curso: <strong style={{ color: 'var(--neon-cyan)' }}>{activeCase?.title}</strong>. 
              Si aceptas una nueva asignación, el caso anterior será archivado permanentemente y se considerará un <strong style={{ color: 'var(--danger-red)' }}>FRACASO</strong> en tu legajo.
            </p>
            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <button className="btn-outline" onClick={() => setShowWarningModal(null)}>CANCELAR</button>
              <button className="btn-danger" onClick={() => initiateCase(showWarningModal)}>
                ABANDONAR Y PROCEDER
              </button>
            </div>
          </div>
        </div>
      )}

      {/* === ACTIVE CASE HUD BANNER === */}
      {activeCase && (
        <div className="active-case-banner">
          <div>
            <p className="mono" style={{ color: 'var(--neon-cyan)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Radio size={14} className="animate-pulse" /> EXPEDIENTE EN CURSO
            </p>
            <h2 style={{ fontSize: '1.8rem', marginTop: '0.5rem' }}>{activeCase.title}</h2>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', maxWidth: '300px', textAlign: 'right', fontFamily: "'Fira Code', monospace", lineHeight: 1.6 }}>
            Revisa tu bandeja de correo para directivas. El tiempo es una variable que no controlamos.
          </p>
        </div>
      )}

      {/* === SECTION HEADER === */}
      <header style={{ marginBottom: '2rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
        <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <FolderKanban color="var(--neon-green)" size={28} style={{ filter: 'drop-shadow(0 0 8px rgba(0,255,0,0.3))' }} /> 
          {activeCase ? "Otros Expedientes Disponibles" : "Expedientes Disponibles"}
        </h1>
        <p className="mono" style={{ color: 'var(--text-dim)', marginTop: '0.5rem', fontSize: '0.7rem' }}>
          <Shield size={10} style={{ display: 'inline', marginRight: 4 }} /> SISTEMA CENTRAL DE ARCHIVOS // ACCESO NIVEL ORO
        </p>
      </header>

      {/* === ALERT TOAST === */}
      {alertMsg && (
        <div className="glass-panel" style={{ background: 'rgba(0,255,0,0.05)', color: 'var(--neon-green)', borderColor: 'rgba(0,255,0,0.3)', padding: '1rem', marginBottom: '1.5rem', cursor: 'default' }}>
          {alertMsg}
        </div>
      )}

      {/* === ERROR TOAST === */}
      {errorMsg && (
        <div className="glass-panel" style={{ background: 'rgba(255,0,80,0.05)', color: 'var(--danger-red)', borderColor: 'rgba(255,0,80,0.3)', padding: '1rem', marginBottom: '1.5rem', cursor: 'default', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertTriangle size={16} /> {errorMsg}
        </div>
      )}

      {/* === CASE GRID === */}
      {loading ? (
        <p className="mono animate-pulse" style={{ color: 'var(--neon-green)', fontSize: '0.85rem' }}>CONTACTANDO SERVIDORES DE LA AGENCIA...</p>
      ) : (
        <div className="grid-cards">
          {casos.filter(c => c.status !== 'active').map((caso) => (
            <div key={caso.id} className="glass-panel" style={{ opacity: caso.status === 'bloqueado' ? 0.4 : 1, cursor: 'default' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <h3 className="mono text-neon-green" style={{ fontSize: '0.85rem' }}>{caso.id.toUpperCase()}</h3>
                <span className="badge badge-active" style={{ fontSize: '0.65rem' }}>
                  {caso.hours}HS LIMIT
                </span>
              </div>
              
              <h2 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>{caso.title}</h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '2rem', minHeight: '60px', lineHeight: 1.6 }}>
                {caso.desc}
              </p>

              {caso.status === 'disponible' || caso.status === 'abandonado' || (caso.status && caso.status.startsWith && caso.status.startsWith('completed')) ? (
                <button className="btn-primary" style={{ width: '100%' }} onClick={() => handleStartRequest(caso.id)}>
                  <Play size={14} /> INICIAR EXPEDIENTE
                </button>
              ) : (
                <button className="btn-outline" style={{ width: '100%', opacity: 0.4, cursor: 'not-allowed' }} disabled>
                  EXPEDIENTE BLOQUEADO
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

