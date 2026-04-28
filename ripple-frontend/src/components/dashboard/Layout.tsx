import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from '../../store/authStore'
import { useRealtimeRisk } from '../../hooks/useRealtimeRisk'

export default function Layout() {
  const { user, logout, restore } = useAuthStore()
  const nav = useNavigate()
  const { scores, connected, lastPrediction } = useRealtimeRisk()

  useEffect(() => { restore() }, [])
  useEffect(() => {
    if (!user && !localStorage.getItem('token')) nav('/login', { replace: true })
  }, [user])

  const critical = Object.values(scores).filter(s => s.level === 'critical').length
  const high     = Object.values(scores).filter(s => s.level === 'high').length
  const total    = Object.keys(scores).length

  const navItems = [
    { to: '/graph',      icon: '⬡', label: '3D Graph', highlight: true },
    { to: '/simulation', icon: '▶', label: 'Simulate',  highlight: true },
    { to: '/events',     icon: '⚡', label: 'Events', highlight: true },
    { to: '/analytics',  icon: '📊', label: 'Analytics', highlight: true },
    { to: '/agent',      icon: '🤖', label: 'AI Agent', highlight: true },
  ]

  return (
    <div style={{ display: 'flex', height: '100vh', background: '#02020a', color: '#e2e8f0', overflow: 'hidden' }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width: 220, flexShrink: 0,
        background: 'rgba(4,4,16,0.98)',
        borderRight: '1px solid rgba(239,68,68,0.1)',
        display: 'flex', flexDirection: 'column',
        padding: '1.25rem 0',
      }}>

        {/* Brand */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '0 1rem 1rem',
          borderBottom: '1px solid rgba(255,255,255,0.04)',
          marginBottom: 10,
        }}>
          <div style={{ position: 'relative', width: 28, height: 28, flexShrink: 0 }}>
            <svg width="28" height="28" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="5" fill="#ef4444" filter="url(#glow)" />
              <circle cx="18" cy="18" r="11" fill="none" stroke="#ef4444" strokeWidth="1.5"
                strokeDasharray="5 3" opacity="0.7" />
              <circle cx="18" cy="18" r="17" fill="none" stroke="#ef4444" strokeWidth="0.75"
                strokeDasharray="3 4" opacity="0.25" />
              <defs>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="2" result="blur" />
                  <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
              </defs>
            </svg>
          </div>
          <div>
            <div style={{ fontFamily: 'Space Mono,monospace', fontWeight: 700, fontSize: 12, color: '#f8fafc', letterSpacing: '.04em' }}>
              RIPPLE<span style={{ color: '#ef4444' }}>GRAPH</span>
            </div>
            <div style={{ fontSize: 9, color: '#334155', letterSpacing: '.1em' }}>SUPPLY CHAIN AI</div>
          </div>
        </div>

        {/* Live indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '0 1rem .75rem', fontSize: 11 }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: connected ? '#22c55e' : '#374151',
            boxShadow: connected ? '0 0 8px rgba(34,197,94,0.8)' : 'none',
            flexShrink: 0,
          }} />
          <span style={{ color: connected ? '#22c55e' : '#374151', fontFamily: 'Space Mono,monospace', fontSize: 10 }}>
            {connected ? 'LIVE' : 'OFFLINE'}
          </span>
          {critical > 0 && (
            <span style={{
              marginLeft: 'auto', background: 'rgba(239,68,68,0.12)',
              color: '#ef4444', fontSize: 9, fontWeight: 700,
              padding: '2px 6px', borderRadius: 4, border: '1px solid rgba(239,68,68,0.3)',
              boxShadow: '0 0 8px rgba(239,68,68,0.3)', letterSpacing: '.05em',
            }}>
              {critical} CRIT
            </span>
          )}
        </div>

        {/* Nav */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: '0 .5rem', flex: 1 }}>
          {navItems.map(({ to, icon, label, highlight }) => (
            <NavLink key={to} to={to} style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 9,
              padding: '9px 12px', borderRadius: 8,
              fontSize: 13, fontWeight: 500, textDecoration: 'none',
              color: isActive ? '#f1f5f9' : (highlight ? '#f97316' : '#475569'),
              background: isActive
                ? (highlight ? 'rgba(249,115,22,0.1)' : 'rgba(239,68,68,0.07)')
                : 'transparent',
              border: isActive ? `1px solid ${highlight ? 'rgba(249,115,22,0.25)' : 'rgba(239,68,68,0.15)'}` : '1px solid transparent',
              transition: 'all .15s',
              boxShadow: isActive && highlight ? '0 0 12px rgba(249,115,22,0.2)' : 'none',
            })}>
              <span style={{ fontSize: 15 }}>{icon}</span>
              {label}
              {label === 'Simulate' && (
                <span style={{
                  marginLeft: 'auto', fontSize: 9, fontWeight: 700,
                  padding: '1px 5px', borderRadius: 4,
                  background: 'rgba(249,115,22,0.15)', color: '#f97316',
                  border: '1px solid rgba(249,115,22,0.3)',
                }}>NEW</span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Risk summary */}
        <div style={{
          margin: '0 .5rem', background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.04)', borderRadius: 10, padding: '10px 12px',
        }}>
          <div style={{ fontSize: 9, color: '#334155', letterSpacing: '.1em', marginBottom: 8, fontFamily: 'Space Mono,monospace' }}>
            RISK OVERVIEW
          </div>
          {[
            { color: '#ef4444', label: 'Critical', val: critical, glow: true },
            { color: '#f97316', label: 'High',     val: high },
            { color: '#64748b', label: 'Monitored',val: total },
          ].map(({ color, label, val, glow }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginBottom: 5 }}>
              <span style={{
                width: 7, height: 7, borderRadius: '50%', background: color, flexShrink: 0,
                boxShadow: glow && val > 0 ? `0 0 6px ${color}` : 'none',
              }} />
              <span style={{ flex: 1, color: '#475569' }}>{label}</span>
              <span style={{
                color: val > 0 ? color : '#334155', fontWeight: 700,
                fontFamily: 'Space Mono,monospace', fontSize: 13,
              }}>{val}</span>
            </div>
          ))}
        </div>

        {/* Last pipeline result */}
        {lastPrediction && (
          <div style={{
            margin: '.5rem .5rem 0',
            background: 'rgba(239,68,68,0.06)',
            border: '1px solid rgba(239,68,68,0.15)',
            borderRadius: 8, padding: '8px 10px',
            boxShadow: '0 0 16px rgba(239,68,68,0.1)',
          }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#ef4444', marginBottom: 3, display: 'flex', gap: 5, alignItems: 'center' }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#ef4444', animation: 'pulse2 1s infinite' }} />
              {lastPrediction.urgency} ALERT
            </div>
            <div style={{ fontSize: 10, color: '#64748b' }}>
              ${(lastPrediction.revenue / 1e9).toFixed(2)}B · {lastPrediction.critical} critical
            </div>
          </div>
        )}

        {/* User */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '.75rem .75rem 0', marginTop: '.5rem',
          borderTop: '1px solid rgba(255,255,255,0.04)',
        }}>
          <div style={{
            width: 28, height: 28, borderRadius: '50%',
            background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 12, fontWeight: 700, color: '#ef4444', flexShrink: 0,
          }}>
            {user?.name?.[0] ?? 'U'}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#d1d5db', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.name}
            </div>
            <div style={{ fontSize: 10, color: '#334155', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.email}
            </div>
          </div>
          <button onClick={logout} title="Sign out" style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: '#334155', padding: 4, fontSize: 14,
            transition: 'color .15s',
          }}>⎋</button>
        </div>
      </aside>

      {/* Main */}
      <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Outlet />
      </main>

      <style>{`
        @keyframes pulse2 { 0%,100%{opacity:1} 50%{opacity:0.3} }
      `}</style>
    </div>
  )
}