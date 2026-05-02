import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  Clock,
  Database,
  Mail,
  Radio,
  RefreshCw,
  ServerCog,
  ShieldCheck,
} from 'lucide-react'
import { authFetch } from '../utils/api'

const emptyOps = {
  summary: null,
  sessions: [],
  queue: [],
  events: [],
  inbound: { processed: [], rate_limits: [] },
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

function shortEmail(email) {
  if (!email) return 'SIN DATOS'
  return email.length > 32 ? `${email.slice(0, 29)}...` : email
}

function statusBadge(status, isExpired = false) {
  if (isExpired) return <span className="badge badge-abandoned">EXPIRADO</span>
  if (status === 'active') return <span className="badge badge-active">ACTIVO</span>
  if (status === 'completed') return <span className="badge badge-resolved">COMPLETADO</span>
  if (status === 'abandonado' || status === 'failed_timeout') {
    return <span className="badge badge-abandoned">{status}</span>
  }
  return <span className="badge">{status || 'SIN ESTADO'}</span>
}

function queueBadge(item) {
  if (item.is_delivered) return <span className="badge badge-resolved">ENTREGADO</span>
  if (item.is_overdue) return <span className="badge badge-abandoned">ATRASADO</span>
  return <span className="badge badge-active">PENDIENTE</span>
}

function TableShell({ title, icon, children, empty }) {
  return (
    <section className="glass-panel" style={{ cursor: 'default', padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: 'var(--space-lg)', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {icon}
        <h2 className="text-neon-green" style={{ fontSize: '1rem' }}>{title}</h2>
      </div>
      {empty ? (
        <div style={{ padding: 'var(--space-xl)', textAlign: 'center' }}>
          <p className="mono" style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>SIN REGISTROS</p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>{children}</div>
      )}
    </section>
  )
}

function Kpi({ label, value, tone = 'green', icon }) {
  const colorByTone = {
    green: 'var(--neon-green)',
    red: 'var(--danger-red)',
    gold: 'var(--neon-gold)',
    cyan: 'var(--neon-cyan)',
  }
  const color = colorByTone[tone] || colorByTone.green

  return (
    <div className={`stat-card ${tone === 'red' ? 'red' : tone === 'gold' ? 'gold' : 'green'}`} style={{ textAlign: 'left' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
        <p className="stat-label">{label}</p>
        <span style={{ color, opacity: 0.7 }}>{icon}</span>
      </div>
      <p
        className="stat-number"
        style={{ color, fontSize: typeof value === 'string' && value.length > 4 ? '1.35rem' : undefined }}
      >
        {value}
      </p>
    </div>
  )
}

export default function Operations() {
  const [ops, setOps] = useState(emptyOps)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState(null)

  const loadOps = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError('')

    try {
      const [summary, sessionsData, queueData, eventsData, inboundData] = await Promise.all([
        authFetch('/api/v1/ops/summary'),
        authFetch('/api/v1/ops/sessions'),
        authFetch('/api/v1/ops/queue'),
        authFetch('/api/v1/ops/events'),
        authFetch('/api/v1/ops/inbound'),
      ])

      setOps({
        summary,
        sessions: sessionsData.sessions || [],
        queue: queueData.queue || [],
        events: eventsData.events || [],
        inbound: {
          processed: inboundData.processed || [],
          rate_limits: inboundData.rate_limits || [],
        },
      })
      setLastUpdated(new Date())
    } catch (err) {
      setError(err.message || 'No se pudo cargar el panel operativo.')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    const initialLoad = window.setTimeout(() => loadOps(), 0)
    const interval = window.setInterval(() => loadOps(true), 30000)
    return () => {
      window.clearTimeout(initialLoad)
      window.clearInterval(interval)
    }
  }, [loadOps])

  const rateLimitSummary = useMemo(() => {
    const rows = ops.summary?.rate_limits_last_hour || []
    if (!rows.length) return '0'
    return rows.map((row) => `${row.scope}:${row.count}`).join(' / ')
  }, [ops.summary])

  if (loading) {
    return (
      <div className="container" style={{ padding: '4rem 2rem', textAlign: 'center' }}>
        <p className="mono animate-pulse text-neon-green" style={{ fontSize: '0.85rem' }}>SINCRONIZANDO TELEMETRIA OPERATIVA...</p>
      </div>
    )
  }

  return (
    <div className="container animate-fade-in" style={{ padding: '2rem', maxWidth: '1400px' }}>
      <header style={{ marginBottom: '2rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <ServerCog color="var(--neon-green)" size={28} />
            PANEL OPERATIVO
          </h1>
          <p className="mono" style={{ color: 'var(--text-dim)', marginTop: '0.5rem', fontSize: '0.72rem' }}>
            ULTIMA SYNC: {lastUpdated ? formatDate(lastUpdated.toISOString()) : 'SIN DATOS'}
          </p>
        </div>
        <button className="btn-outline" onClick={() => loadOps(true)} disabled={refreshing}>
          <RefreshCw size={14} className={refreshing ? 'spin' : ''} />
          {refreshing ? 'ACTUALIZANDO' : 'REFRESCAR'}
        </button>
      </header>

      {error && (
        <div className="glass-panel" style={{ cursor: 'default', background: 'rgba(255,0,80,0.05)', color: 'var(--danger-red)', borderColor: 'rgba(255,0,80,0.3)', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertTriangle size={18} /> {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 'var(--space-lg)', marginBottom: 'var(--space-xl)' }}>
        <Kpi label="Sesiones activas" value={ops.summary?.active_sessions ?? 0} icon={<Activity size={20} />} />
        <Kpi label="Cola pendiente" value={ops.summary?.pending_messages ?? 0} tone="cyan" icon={<Clock size={20} />} />
        <Kpi label="Mensajes atrasados" value={ops.summary?.overdue_messages ?? 0} tone={ops.summary?.overdue_messages ? 'red' : 'green'} icon={<AlertTriangle size={20} />} />
        <Kpi label="Eventos 24h" value={ops.summary?.events_last_24h ?? 0} tone="gold" icon={<Radio size={20} />} />
        <Kpi label="Rate limits 1h" value={rateLimitSummary} tone="cyan" icon={<ShieldCheck size={20} />} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 'var(--space-xl)' }}>
        <TableShell title="Sesiones" icon={<Activity size={18} color="var(--neon-green)" />} empty={!ops.sessions.length}>
          <table className="mission-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Detective</th>
                <th>Caso</th>
                <th>Estado</th>
                <th>Inicio</th>
                <th>Expira</th>
                <th>Veredicto</th>
              </tr>
            </thead>
            <tbody>
              {ops.sessions.map((session) => (
                <tr key={session.id}>
                  <td>{session.id}</td>
                  <td title={session.user_email}>{shortEmail(session.user_email)}</td>
                  <td>{session.case_title || session.game_id}</td>
                  <td>{statusBadge(session.status, session.is_expired)}</td>
                  <td>{formatDate(session.started_at)}</td>
                  <td>{formatDate(session.expires_at)}</td>
                  <td>{session.verdict || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>

        <TableShell title="Cola de mensajes" icon={<Mail size={18} color="var(--neon-green)" />} empty={!ops.queue.length}>
          <table className="mission-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Estado</th>
                <th>De</th>
                <th>Para</th>
                <th>Asunto</th>
                <th>Programado</th>
                <th>Atraso</th>
              </tr>
            </thead>
            <tbody>
              {ops.queue.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{queueBadge(item)}</td>
                  <td title={item.from_email}>{shortEmail(item.from_email)}</td>
                  <td title={item.to_email}>{shortEmail(item.to_email)}</td>
                  <td>{item.subject || '-'}</td>
                  <td>{formatDate(item.scheduled_at)}</td>
                  <td>{item.minutes_overdue !== null && item.minutes_overdue !== undefined ? `${item.minutes_overdue}m` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--space-xl)' }}>
          <TableShell title="Eventos disparados" icon={<Radio size={18} color="var(--neon-green)" />} empty={!ops.events.length}>
            <table className="mission-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Evento</th>
                  <th>Caso</th>
                  <th>Detective</th>
                  <th>Fecha</th>
                </tr>
              </thead>
              <tbody>
                {ops.events.map((event) => (
                  <tr key={event.id}>
                    <td>{event.id}</td>
                    <td>{event.event_id}</td>
                    <td>{event.case_title || event.game_id || '-'}</td>
                    <td title={event.user_email}>{shortEmail(event.user_email)}</td>
                    <td>{formatDate(event.fired_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>

          <TableShell title="Inbound procesado" icon={<Database size={18} color="var(--neon-green)" />} empty={!ops.inbound.processed.length}>
            <table className="mission-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Fuente</th>
                  <th>External ID</th>
                  <th>De</th>
                  <th>Fecha</th>
                </tr>
              </thead>
              <tbody>
                {ops.inbound.processed.map((item) => (
                  <tr key={item.id}>
                    <td>{item.id}</td>
                    <td>{item.source}</td>
                    <td>{item.external_id}</td>
                    <td title={item.from_email}>{shortEmail(item.from_email)}</td>
                    <td>{formatDate(item.processed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableShell>
        </div>

        <TableShell title="Rate limits recientes" icon={<ShieldCheck size={18} color="var(--neon-green)" />} empty={!ops.inbound.rate_limits.length}>
          <table className="mission-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Canal</th>
                <th>Actor</th>
                <th>Fecha</th>
              </tr>
            </thead>
            <tbody>
              {ops.inbound.rate_limits.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td><span className="badge badge-active">{item.scope}</span></td>
                  <td title={item.actor_email}>{shortEmail(item.actor_email)}</td>
                  <td>{formatDate(item.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableShell>
      </div>
    </div>
  )
}
