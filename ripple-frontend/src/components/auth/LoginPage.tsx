import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

export default function LoginPage() {
  const { login, register, user, loading, error } = useAuthStore()
  const nav = useNavigate()
  const [mode, setMode]       = useState<'login' | 'register'>('login')
  const [email, setEmail]     = useState('')
  const [password, setPass]   = useState('')
  const [name, setName]       = useState('')
  const [localErr, setErr]    = useState('')
  const canvasRef             = useRef<HTMLCanvasElement>(null)

  useEffect(() => { if (user) nav('/graph', { replace: true }) }, [user])

  // Animated particle background
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    canvas.width  = window.innerWidth
    canvas.height = window.innerHeight

    const particles: { x: number; y: number; vx: number; vy: number; size: number; opacity: number }[] = []
    for (let i = 0; i < 80; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        size: Math.random() * 1.5 + 0.5,
        opacity: Math.random() * 0.4 + 0.1,
      })
    }

    let raf: number
    const draw = () => {
      ctx.fillStyle = 'rgba(2,2,10,0.92)'
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      // Draw connections
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x
          const dy = particles[i].y - particles[j].y
          const d  = Math.sqrt(dx*dx + dy*dy)
          if (d < 120) {
            ctx.beginPath()
            ctx.strokeStyle = `rgba(239,68,68,${0.06 * (1 - d/120)})`
            ctx.lineWidth   = 0.5
            ctx.moveTo(particles[i].x, particles[i].y)
            ctx.lineTo(particles[j].x, particles[j].y)
            ctx.stroke()
          }
        }
      }

      particles.forEach(p => {
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(239,68,68,${p.opacity})`
        ctx.shadowBlur = 6
        ctx.shadowColor = '#ef4444'
        ctx.fill()
        ctx.shadowBlur = 0
        p.x += p.vx; p.y += p.vy
        if (p.x < 0) p.x = canvas.width
        if (p.x > canvas.width) p.x = 0
        if (p.y < 0) p.y = canvas.height
        if (p.y > canvas.height) p.y = 0
      })

      raf = requestAnimationFrame(draw)
    }
    draw()
    return () => cancelAnimationFrame(raf)
  }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr('')
    try {
      if (mode === 'login') await login(email, password)
      else await register(email, password, name)
    } catch (e: any) { setErr(e.message) }
  }

  return (
    <div style={{ position: 'relative', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
      <canvas ref={canvasRef} style={{ position: 'absolute', inset: 0, zIndex: 0 }} />

      <div style={{
        position: 'relative', zIndex: 1,
        background: 'rgba(4,4,16,0.85)',
        border: '1px solid rgba(239,68,68,0.2)',
        borderRadius: 16, padding: '2.5rem 2rem',
        width: '100%', maxWidth: 420,
        backdropFilter: 'blur(20px)',
        boxShadow: '0 0 60px rgba(239,68,68,0.08), 0 0 120px rgba(239,68,68,0.04)',
      }}>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '1.5rem' }}>
          <div style={{ position: 'relative' }}>
            <svg width="40" height="40" viewBox="0 0 40 40">
              <circle cx="20" cy="20" r="6" fill="#ef4444" />
              <circle cx="20" cy="20" r="12" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="5 3" opacity="0.6" />
              <circle cx="20" cy="20" r="18" fill="none" stroke="#ef4444" strokeWidth="0.75" strokeDasharray="3 4" opacity="0.25" />
              <circle cx="20" cy="20" r="6" fill="none" stroke="#ef4444" strokeWidth="8" opacity="0.08" />
            </svg>
          </div>
          <div>
            <div style={{ fontFamily: 'Space Mono,monospace', fontWeight: 700, fontSize: 16, color: '#f8fafc', letterSpacing: '.03em' }}>
              RIPPLE<span style={{ color: '#ef4444' }}>GRAPH</span> AI
            </div>
            <div style={{ fontSize: 10, color: '#475569', letterSpacing: '.12em' }}>SUPPLY CHAIN INTELLIGENCE</div>
          </div>
        </div>

        <h1 style={{ fontSize: 20, fontWeight: 700, color: '#fff', marginBottom: 6 }}>
          Predict cascade failures
        </h1>
        <p style={{ fontSize: 13, color: '#475569', lineHeight: 1.6, marginBottom: '1.5rem' }}>
          45-day GNN risk forecasting across Tier-1/2/3 suppliers. Real-time 3D graph visualization.
        </p>

        {/* Mode tabs */}
        <div style={{ display: 'flex', background: 'rgba(255,255,255,0.03)', borderRadius: 10, padding: 4, marginBottom: 16, gap: 4 }}>
          {(['login','register'] as const).map(m => (
            <button key={m} onClick={() => setMode(m)} style={{
              flex: 1, padding: '7px 12px', borderRadius: 7,
              border: mode === m ? '1px solid rgba(239,68,68,0.3)' : '1px solid transparent',
              background: mode === m ? 'rgba(239,68,68,0.08)' : 'transparent',
              color: mode === m ? '#f1f5f9' : '#475569',
              fontSize: 13, fontWeight: 500, cursor: 'pointer',
              boxShadow: mode === m ? '0 0 12px rgba(239,68,68,0.1)' : 'none',
            }}>
              {m === 'login' ? 'Sign in' : 'Register'}
            </button>
          ))}
        </div>

        {(localErr || error) && (
          <div style={{
            background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
            borderRadius: 8, padding: '10px 14px', fontSize: 13, color: '#fca5a5', marginBottom: 12,
          }}>
            {localErr || error}
          </div>
        )}

        <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {mode === 'register' && (
            <input
              style={inputStyle} placeholder="Full name" value={name}
              onChange={e => setName(e.target.value)} required
            />
          )}
          <input
            style={inputStyle} type="email" placeholder="Email address"
            value={email} onChange={e => setEmail(e.target.value)} required
          />
          <input
            style={inputStyle} type="password" placeholder="Password (min 6 chars)"
            value={password} onChange={e => setPass(e.target.value)} required minLength={6}
          />
          <button type="submit" disabled={loading} style={{
            background: loading ? 'rgba(239,68,68,0.4)' : 'rgba(239,68,68,0.9)',
            color: '#fff', border: '1px solid rgba(239,68,68,0.5)',
            borderRadius: 10, padding: '12px 20px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
            boxShadow: loading ? 'none' : '0 0 20px rgba(239,68,68,0.3)',
            transition: 'all .15s', marginTop: 4,
          }}>
            {loading ? 'Loading…' : mode === 'login' ? 'Enter System' : 'Create Account'}
          </button>
        </form>

        {/* Feature pills */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid rgba(255,255,255,0.04)' }}>
          {[
            ['#ef4444','GNN Risk Propagation'],
            ['#f97316','45-Day Forecasting'],
            ['#a78bfa','3D Cascade View'],
            ['#34d399','ADK Multi-Agent'],
            ['#60a5fa','WebSocket Live'],
          ].map(([c, l]) => (
            <div key={l} style={{
              display: 'flex', alignItems: 'center', gap: 5,
              background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
              borderRadius: 20, padding: '3px 10px', fontSize: 11, color: '#64748b',
            }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: c, boxShadow: `0 0 4px ${c}` }} />
              {l}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 8, color: '#e2e8f0', fontSize: 14,
  padding: '11px 14px', outline: 'none', fontFamily: 'inherit', width: '100%',
  transition: 'border-color .15s',
}