import React, { useState } from 'react'
import { Lock, Unlock, FileText, AlertTriangle } from 'lucide-react'

// Simulador temporal de contraseñas de las pruebas estáticas
const MOCK_DB = {
  'TRINIDAD-1994': { title: '1994_osvaldo_radio.mp3', type: 'audio', desc: 'Audio confidencial interceptado en dial local. Contiene confesión.' },
  'LUNA': { title: 'pruebatres.pdf', type: 'doc', desc: 'Reporte balístico de la pericia no revelada.' }
}

export default function Vault() {
  const [code, setCode] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(false);

  const handleUnlock = (e) => {
    e.preventDefault();
    if(MOCK_DB[code.toUpperCase()]) {
      setResult(MOCK_DB[code.toUpperCase()]);
      setError(false);
    } else {
      setResult(null);
      setError(true);
    }
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '3rem 2rem', maxWidth: '800px', margin: '0 auto' }}>
      
      <div className="glass-panel" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
        <Lock size={48} color="var(--text-muted)" style={{ marginBottom: '1.5rem' }} />
        <h2 style={{ marginBottom: '1rem' }}>Bóveda Forense Policial</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '3rem', maxWidth: '500px', margin: '0 auto 3rem auto' }}>
          Ingrese la Clave Criptográfica provista por los sospechosos o testigos durante sus intercambios de correo para liberar la evidencia adjunta.
        </p>

        <form onSubmit={handleUnlock} style={{ display: 'flex', gap: '1rem', maxWidth: '400px', margin: '0 auto' }}>
          <input 
            type="text" 
            className="input-field" 
            placeholder="Ej: LUNA-049" 
            value={code}
            onChange={(e) => setCode(e.target.value)}
            style={{ borderColor: error ? 'var(--danger-color)' : 'var(--border-color)', textTransform: 'uppercase' }}
          />
          <button type="submit" className="btn-primary">
            Desencriptar
          </button>
        </form>

        {error && (
          <p style={{ color: 'var(--danger-color)', marginTop: '1rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={16} /> Clave inválida o revocada.
          </p>
        )}

        {result && (
          <div className="animate-fade-in" style={{ marginTop: '3rem', padding: '2rem', background: 'rgba(16, 185, 129, 0.05)', border: '1px solid var(--success-color)', borderRadius: '8px', textAlign: 'left' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
              <Unlock color="var(--success-color)" />
              <h3 style={{ color: 'var(--success-color)' }}>ACCESO COCNEDIDO</h3>
            </div>
            
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', background: 'rgba(0,0,0,0.3)', padding: '1.5rem', borderRadius: '4px' }}>
              <FileText size={40} color="var(--text-main)" />
              <div>
                <h4 className="mono">{result.title}</h4>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: '0.5rem 0 1rem 0' }}>{result.desc}</p>
                <button className="btn-outline" style={{ padding: '0.4rem 1rem', fontSize: '0.75rem', borderColor: 'var(--success-color)', color: 'var(--success-color)' }}>
                  Descargar Archivo
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
