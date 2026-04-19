import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, ShieldAlert, KeyRound, Terminal } from 'lucide-react'

export default function LandingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8001";

  const handleRequestOtp = () => {
    if(!email.includes('@')) return;
    setLoading(true);
    fetch(`${API_URL}/api/v1/auth/request-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    })
    .then(r => r.json())
    .then(data => {
      setLoading(false);
      if (data.success) setStep(2);
    })
    .catch(err => {
      console.error("OTP request failed", err);
      setLoading(false);
    })
  }

  const handleVerifyOtp = () => {
    if(otp.length < 6) return;
    setLoading(true);
    fetch(`${API_URL}/api/v1/auth/verify-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, code: otp })
    })
    .then(r => {
      if(!r.ok) throw new Error("Código incorrecto o expirado");
      return r.json();
    })
    .then(data => {
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('userEmail', data.email);
        navigate('/dashboard');
      }
    })
    .catch(err => {
      alert("Error: Código incorrecto o expirado.");
      setLoading(false);
      setStep(1);
    })
  }

  return (
    <div className="container" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
      <div className="glass-panel animate-fade-in" style={{ maxWidth: '800px', width: '100%', padding: '3rem 2rem', position: 'relative', overflow: 'hidden', cursor: 'default' }}>
        
        {/* Neon top accent line */}
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: 'linear-gradient(90deg, transparent, var(--neon-green), transparent)' }}></div>
        
        {/* Decorative corner markers */}
        <div style={{ position: 'absolute', top: '12px', left: '12px', width: '20px', height: '20px', borderTop: '2px solid var(--neon-green)', borderLeft: '2px solid var(--neon-green)', opacity: 0.5 }}></div>
        <div style={{ position: 'absolute', top: '12px', right: '12px', width: '20px', height: '20px', borderTop: '2px solid var(--neon-green)', borderRight: '2px solid var(--neon-green)', opacity: 0.5 }}></div>
        <div style={{ position: 'absolute', bottom: '12px', left: '12px', width: '20px', height: '20px', borderBottom: '2px solid var(--neon-green)', borderLeft: '2px solid var(--neon-green)', opacity: 0.5 }}></div>
        <div style={{ position: 'absolute', bottom: '12px', right: '12px', width: '20px', height: '20px', borderBottom: '2px solid var(--neon-green)', borderRight: '2px solid var(--neon-green)', opacity: 0.5 }}></div>

        <ShieldAlert size={48} color="var(--neon-green)" style={{ margin: '0 auto 1.5rem auto', filter: 'drop-shadow(0 0 8px rgba(0,255,0,0.4))' }} />

        <h1 style={{ fontSize: '2.5rem', marginBottom: '1rem', color: '#fff', letterSpacing: '-1px' }}>
          La Verdad Está en Tu <span className="text-neon-cyan">Buzón</span>
        </h1>
        <p style={{ fontSize: '1.1rem', color: 'var(--text-muted)', marginBottom: '2.5rem', maxWidth: '550px', margin: '0 auto 2.5rem auto', lineHeight: 1.7 }}>
          Ingresa al sistema encriptado de la agencia mediante Auth de un solo uso.
        </p>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', alignItems: 'center', background: 'rgba(0,0,0,0.5)', padding: '2rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
          {step === 1 ? (
            <>
              <p className="mono" style={{ color: 'var(--neon-green)', fontSize: '0.8rem', marginBottom: '0.5rem', alignSelf: 'flex-start', marginLeft: '10%', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Terminal size={12} /> INGRESE SU CREDENCIAL OFICIAL (MAIL)
              </p>
              <input 
                type="email" 
                placeholder="agente@dominio.com" 
                className="input-field" 
                style={{ width: '80%', textAlign: 'left' }}
                onChange={(e) => setEmail(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRequestOtp()}
              />
              <button className="btn-primary" onClick={handleRequestOtp} style={{ width: '80%', marginTop: '0.5rem' }} disabled={loading}>
                {loading ? 'SINCRONIZANDO...' : <>SOLICITAR PASE DE ACCESO <ChevronRight size={16} /></>}
              </button>
            </>
          ) : (
            <>
              <p className="mono" style={{ color: 'var(--neon-cyan)', fontSize: '0.8rem', marginBottom: '0.5rem', alignSelf: 'flex-start', marginLeft: '10%', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <KeyRound size={12} />
                INGRESE CÓDIGO OTP RECIBIDO EN {email.toUpperCase()}
              </p>
              <input 
                type="text" 
                placeholder="000000" 
                maxLength={6}
                className="input-field" 
                style={{ width: '80%', textAlign: 'center', fontSize: '1.8rem', letterSpacing: '0.8rem', color: 'var(--neon-cyan)' }}
                onChange={(e) => setOtp(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleVerifyOtp()}
              />
              <button className="btn-primary" onClick={handleVerifyOtp} style={{ width: '80%', marginTop: '0.5rem', background: 'var(--neon-cyan)', borderColor: 'var(--neon-cyan)', color: 'var(--bg-dark)' }} disabled={loading}>
                {loading ? 'COMPROBANDO FIRMA...' : <>VERIFICAR IDENTIDAD <ChevronRight size={16} /></>}
              </button>
            </>
          )}
        </div>

        <p className="mono" style={{ fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '2rem', letterSpacing: '0.15em' }}>
          SISTEMA PROTEGIDO POR ENCRIPTACIÓN JWT DE GRADO MILITAR
        </p>
      </div>
    </div>
  )
}
