import React, { useState } from 'react'
import {
  Lock,
  Unlock,
  FileText,
  AlertTriangle,
  Loader2,
  Headphones,
  Image,
  Download,
} from 'lucide-react'
import { authFetch, resolveApiUrl } from '../utils/api'

function EvidenceIcon({ type, size = 40 }) {
  switch (type) {
    case 'audio':
      return <Headphones size={size} color="var(--text-primary)" />
    case 'image':
      return <Image size={size} color="var(--text-primary)" />
    default:
      return <FileText size={size} color="var(--text-primary)" />
  }
}

export default function Vault() {
  const [code, setCode] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleUnlock = async (e) => {
    e.preventDefault()
    if (!code.trim()) return

    setLoading(true)
    setResult(null)
    setError(null)

    try {
      const data = await authFetch('/api/v1/vault/unlock', {
        method: 'POST',
        body: JSON.stringify({ code: code.trim() }),
      })

      setResult(data.evidence)
      setError(null)
    } catch (err) {
      setResult(null)
      setError(err.message || 'Error desconocido al desencriptar.')
    } finally {
      setLoading(false)
    }
  }

  const downloadUrl = result?.file_url ? resolveApiUrl(result.file_url) : null

  return (
    <div className="container animate-fade-in" style={{ padding: '3rem 2rem', maxWidth: '800px', margin: '0 auto' }}>
      <div className="glass-panel" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
        <Lock size={48} color="var(--text-muted)" style={{ marginBottom: '1.5rem' }} />
        <h2 style={{ marginBottom: '1rem' }}>Boveda Forense Policial</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '3rem', maxWidth: '500px', margin: '0 auto 3rem auto' }}>
          Ingrese la Clave Criptografica provista por los sospechosos o testigos durante sus intercambios de correo para liberar la evidencia adjunta.
        </p>

        <form onSubmit={handleUnlock} style={{ display: 'flex', gap: '1rem', maxWidth: '400px', margin: '0 auto' }}>
          <input
            type="text"
            id="vault-code-input"
            className="input-field"
            placeholder="Ej: TRINIDAD-1994"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            disabled={loading}
            style={{ borderColor: error ? 'var(--danger-red)' : 'var(--border-color)', textTransform: 'uppercase' }}
          />
          <button type="submit" id="vault-unlock-btn" className="btn-primary" disabled={loading || !code.trim()}>
            {loading ? <Loader2 size={18} className="spin" /> : 'Desencriptar'}
          </button>
        </form>

        {error && (
          <p style={{ color: 'var(--danger-red)', marginTop: '1rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={16} /> {error}
          </p>
        )}

        {result && (
          <div
            id="vault-result"
            className="animate-fade-in"
            style={{
              marginTop: '3rem',
              padding: '2rem',
              background: 'rgba(0, 255, 0, 0.05)',
              border: '1px solid var(--neon-green)',
              borderRadius: '8px',
              textAlign: 'left',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
              <Unlock color="var(--neon-green)" />
              <h3 style={{ color: 'var(--neon-green)' }}>ACCESO CONCEDIDO</h3>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', background: 'rgba(0,0,0,0.3)', padding: '1.5rem', borderRadius: '4px' }}>
              <EvidenceIcon type={result.type} />
              <div>
                <h4 className="mono">{result.title}</h4>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: '0.5rem 0 1rem 0' }}>{result.desc}</p>
                <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--neon-green)', opacity: 0.7 }}>
                  TIPO: {result.type.toUpperCase()} - CLASIFICACION: RESTRINGIDO
                </span>
                {result.file_url && (
                  <div style={{ marginTop: '1rem' }}>
                    <a
                      href={downloadUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-primary"
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', textDecoration: 'none' }}
                    >
                      <Download size={16} /> Descargar archivo
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
