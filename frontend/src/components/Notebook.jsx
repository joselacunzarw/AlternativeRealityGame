import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  CalendarDays,
  FileText,
  KeyRound,
  Loader2,
  NotebookPen,
  Plus,
  Save,
  Trash2,
  UserRoundSearch,
  X,
} from 'lucide-react'
import { authFetch } from '../utils/api'

const ENTRY_TYPES = [
  { id: 'note', label: 'Notas', singular: 'Nota', icon: FileText },
  { id: 'suspect', label: 'Personas', singular: 'Persona', icon: UserRoundSearch },
  { id: 'timeline', label: 'Fechas', singular: 'Fecha', icon: CalendarDays },
  { id: 'vault_code', label: 'Vault', singular: 'Clave', icon: KeyRound },
]

const emptyForm = {
  entry_type: 'note',
  title: '',
  content: '',
}

function formatDate(value) {
  if (!value) return 'SIN DATOS'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'SIN DATOS'
  return date.toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function typeMeta(entryType) {
  return ENTRY_TYPES.find((type) => type.id === entryType) || ENTRY_TYPES[0]
}

function TypeButton({ type, active, onClick }) {
  const Icon = type.icon
  return (
    <button
      type="button"
      className={active ? 'btn-primary' : 'btn-outline'}
      onClick={onClick}
      style={{ padding: '0.65rem 0.9rem', minWidth: '110px' }}
    >
      <Icon size={14} /> {type.label}
    </button>
  )
}

export default function Notebook() {
  const [activeSession, setActiveSession] = useState(null)
  const [entries, setEntries] = useState([])
  const [activeType, setActiveType] = useState('note')
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const loadNotebook = useCallback(async () => {
    setError('')
    try {
      const data = await authFetch('/api/v1/notebook')
      setActiveSession(data.active_session || null)
      setEntries(data.entries || [])
      setMessage(data.message || '')
    } catch (err) {
      setError(err.message || 'No se pudo cargar el notebook.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const initialLoad = window.setTimeout(() => loadNotebook(), 0)
    return () => window.clearTimeout(initialLoad)
  }, [loadNotebook])

  const filteredEntries = useMemo(
    () => entries.filter((entry) => entry.entry_type === activeType),
    [entries, activeType],
  )

  const counts = useMemo(() => {
    return entries.reduce((acc, entry) => {
      acc[entry.entry_type] = (acc[entry.entry_type] || 0) + 1
      return acc
    }, {})
  }, [entries])

  const handleCreate = async (event) => {
    event.preventDefault()
    if (!form.title.trim() || saving || !activeSession) return

    setSaving(true)
    setError('')
    try {
      const data = await authFetch('/api/v1/notebook', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      setEntries((current) => [data.entry, ...current])
      setActiveType(data.entry.entry_type)
      setForm({ ...emptyForm, entry_type: form.entry_type })
    } catch (err) {
      setError(err.message || 'No se pudo guardar la entrada.')
    } finally {
      setSaving(false)
    }
  }

  const startEditing = (entry) => {
    setEditingId(entry.id)
    setEditDraft({
      entry_type: entry.entry_type,
      title: entry.title,
      content: entry.content,
    })
  }

  const cancelEditing = () => {
    setEditingId(null)
    setEditDraft(null)
  }

  const saveEdit = async (entryId) => {
    if (!editDraft?.title?.trim() || saving) return

    setSaving(true)
    setError('')
    try {
      const data = await authFetch(`/api/v1/notebook/${entryId}`, {
        method: 'PATCH',
        body: JSON.stringify(editDraft),
      })
      setEntries((current) => current.map((entry) => (entry.id === entryId ? data.entry : entry)))
      cancelEditing()
    } catch (err) {
      setError(err.message || 'No se pudo actualizar la entrada.')
    } finally {
      setSaving(false)
    }
  }

  const deleteEntry = async (entryId) => {
    if (saving) return

    setSaving(true)
    setError('')
    try {
      await authFetch(`/api/v1/notebook/${entryId}`, { method: 'DELETE' })
      setEntries((current) => current.filter((entry) => entry.id !== entryId))
      if (editingId === entryId) cancelEditing()
    } catch (err) {
      setError(err.message || 'No se pudo borrar la entrada.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="container" style={{ padding: '4rem 2rem', textAlign: 'center' }}>
        <p className="mono animate-pulse text-neon-green" style={{ fontSize: '0.85rem' }}>ABRIENDO NOTEBOOK DEL DETECTIVE...</p>
      </div>
    )
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem' }}>
      <header style={{ marginBottom: '2rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <NotebookPen color="var(--neon-green)" size={28} />
            NOTEBOOK
          </h1>
          <p className="mono" style={{ color: 'var(--text-dim)', marginTop: '0.5rem', fontSize: '0.72rem' }}>
            {activeSession ? activeSession.case_title || activeSession.game_id : 'SIN EXPEDIENTE ACTIVO'}
          </p>
        </div>
        {activeSession && (
          <span className="badge badge-active" style={{ alignSelf: 'flex-start', marginTop: '0.35rem' }}>
            SESION #{activeSession.id}
          </span>
        )}
      </header>

      {error && (
        <div className="glass-panel" style={{ cursor: 'default', background: 'rgba(255,0,80,0.05)', color: 'var(--danger-red)', borderColor: 'rgba(255,0,80,0.3)', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {!activeSession ? (
        <div className="glass-panel" style={{ cursor: 'default', textAlign: 'center', padding: '3rem 2rem' }}>
          <NotebookPen size={42} color="var(--text-muted)" style={{ marginBottom: '1rem' }} />
          <h2 style={{ fontSize: '1.2rem', marginBottom: '0.75rem' }}>NO HAY EXPEDIENTE ACTIVO</h2>
          <p style={{ color: 'var(--text-muted)' }}>{message || 'Inicia un caso para activar el notebook.'}</p>
        </div>
      ) : (
        <>
          <section className="glass-panel" style={{ cursor: 'default', marginBottom: 'var(--space-xl)' }}>
            <form onSubmit={handleCreate} style={{ display: 'grid', gap: 'var(--space-md)' }}>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                {ENTRY_TYPES.map((type) => (
                  <TypeButton
                    key={type.id}
                    type={type}
                    active={form.entry_type === type.id}
                    onClick={() => setForm((current) => ({ ...current, entry_type: type.id }))}
                  />
                ))}
              </div>

              <input
                className="input-field"
                type="text"
                placeholder="Titulo"
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
                maxLength={140}
              />
              <textarea
                className="input-field"
                placeholder="Contenido"
                value={form.content}
                onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))}
                rows={4}
                style={{ resize: 'vertical', minHeight: '120px' }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button className="btn-primary" type="submit" disabled={saving || !form.title.trim()}>
                  {saving ? <Loader2 size={16} className="spin" /> : <Plus size={16} />}
                  Crear entrada
                </button>
              </div>
            </form>
          </section>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: 'var(--space-lg)' }}>
            {ENTRY_TYPES.map((type) => {
              const Icon = type.icon
              return (
                <button
                  key={type.id}
                  type="button"
                  className={activeType === type.id ? 'btn-primary' : 'btn-outline'}
                  onClick={() => setActiveType(type.id)}
                  style={{ padding: '0.65rem 0.9rem' }}
                >
                  <Icon size={14} /> {type.label} ({counts[type.id] || 0})
                </button>
              )
            })}
          </div>

          <section className="glass-panel" style={{ cursor: 'default', padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: 'var(--space-lg)', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
              <h2 className="text-neon-green" style={{ fontSize: '1rem' }}>{typeMeta(activeType).label.toUpperCase()}</h2>
              <span className="mono" style={{ color: 'var(--text-dim)', fontSize: '0.72rem' }}>{filteredEntries.length} REGISTRO(S)</span>
            </div>

            {filteredEntries.length === 0 ? (
              <div style={{ padding: 'var(--space-2xl)', textAlign: 'center' }}>
                <p className="mono" style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>SIN REGISTROS</p>
              </div>
            ) : (
              <div style={{ display: 'grid', gap: '1px', background: 'rgba(255,255,255,0.04)' }}>
                {filteredEntries.map((entry) => {
                  const meta = typeMeta(entry.entry_type)
                  const Icon = meta.icon
                  const isEditing = editingId === entry.id

                  return (
                    <article key={entry.id} style={{ background: 'var(--panel-bg)', padding: 'var(--space-lg)' }}>
                      {isEditing ? (
                        <div style={{ display: 'grid', gap: 'var(--space-md)' }}>
                          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                            {ENTRY_TYPES.map((type) => (
                              <TypeButton
                                key={type.id}
                                type={type}
                                active={editDraft.entry_type === type.id}
                                onClick={() => setEditDraft((current) => ({ ...current, entry_type: type.id }))}
                              />
                            ))}
                          </div>
                          <input
                            className="input-field"
                            value={editDraft.title}
                            onChange={(event) => setEditDraft((current) => ({ ...current, title: event.target.value }))}
                            maxLength={140}
                          />
                          <textarea
                            className="input-field"
                            value={editDraft.content}
                            onChange={(event) => setEditDraft((current) => ({ ...current, content: event.target.value }))}
                            rows={4}
                            style={{ resize: 'vertical', minHeight: '120px' }}
                          />
                          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', flexWrap: 'wrap' }}>
                            <button type="button" className="btn-outline" onClick={cancelEditing}>
                              <X size={14} /> Cancelar
                            </button>
                            <button type="button" className="btn-primary" onClick={() => saveEdit(entry.id)} disabled={saving || !editDraft.title.trim()}>
                              <Save size={14} /> Guardar
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: 'grid', gap: 'var(--space-md)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'flex-start' }}>
                            <div style={{ display: 'flex', gap: '0.85rem', alignItems: 'flex-start' }}>
                              <Icon size={20} color="var(--neon-green)" style={{ marginTop: '0.15rem' }} />
                              <div>
                                <h3 style={{ fontSize: '1rem', marginBottom: '0.35rem' }}>{entry.title}</h3>
                                <p className="mono" style={{ color: 'var(--text-dim)', fontSize: '0.66rem' }}>
                                  {meta.singular.toUpperCase()} // {formatDate(entry.updated_at)}
                                </p>
                              </div>
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                              <button type="button" className="btn-outline" onClick={() => startEditing(entry)} style={{ padding: '0.55rem 0.75rem' }}>
                                <Save size={13} /> Editar
                              </button>
                              <button type="button" className="btn-danger" onClick={() => deleteEntry(entry.id)} style={{ padding: '0.55rem 0.75rem' }}>
                                <Trash2 size={13} /> Borrar
                              </button>
                            </div>
                          </div>
                          {entry.content && (
                            <p style={{ color: 'var(--text-muted)', whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                              {entry.content}
                            </p>
                          )}
                        </div>
                      )}
                    </article>
                  )
                })}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
