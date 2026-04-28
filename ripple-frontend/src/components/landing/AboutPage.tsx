import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

function Section({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current; if (!el) return
    el.style.opacity = '0'; el.style.transform = 'translateY(32px)'
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        el.style.transition = 'opacity .8s cubic-bezier(0.16,1,0.3,1), transform .8s cubic-bezier(0.16,1,0.3,1)'
        el.style.opacity = '1'; el.style.transform = 'translateY(0)'
        io.disconnect()
      }
    }, { threshold: 0.05 })
    io.observe(el); return () => io.disconnect()
  }, [])
  return <div ref={ref} style={style}>{children}</div>
}

function Tag({ label, color }: { label: string; color: string }) {
  return (
    <span style={{ fontSize:10, fontWeight:700, padding:'3px 9px', borderRadius:20,
      background:`${color}18`, color, border:`1px solid ${color}33`,
      fontFamily:'Space Mono,monospace', letterSpacing:'.06em' }}>{label}</span>
  )
}

export default function AboutPage() {
  const navigate = useNavigate()
  const heroRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onScroll = () => {
      if (heroRef.current) heroRef.current.style.transform = `translateY(${window.scrollY * 0.25}px)`
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const stack = [
    { cat: 'Frontend', items: ['React 18 + TypeScript', 'Vite', 'Three.js / @react-three/fiber', 'TanStack Query', 'Zustand', 'Framer Motion', 'GSAP'], color: '#60a5fa' },
    { cat: 'Backend', items: ['FastAPI (Python)', 'SQLite + SQLAlchemy', 'WebSocket', 'Google ADK', 'JWT Auth'], color: '#34d399' },
    { cat: 'ML / AI', items: ['PyTorch', 'GraphSAGE GNN', 'Graph prediction server (port 8081)', 'Multi-agent pipeline'], color: '#a78bfa' },
  ]

  const team = [
    { role: 'Full Stack + ML', desc: 'End-to-end architecture, GNN model, FastAPI backend, React frontend', icon: '🛠' },
    { role: 'Multi-Agent AI', desc: 'Google ADK pipeline design, MonitorAgent / AnalystAgent / RecommenderAgent', icon: '🤖' },
    { role: '3D Visualization', desc: 'Three.js Earth globe, WebSocket real-time updates, node animation system', icon: '🌐' },
  ]

  return (
    <div style={{ background:'#02020a', color:'#e2e8f0', minHeight:'100vh', overflowX:'hidden' }}>

      {/* ── NAVBAR ── */}
      <nav style={{ position:'fixed', top:0, left:0, right:0, zIndex:100,
        display:'flex', alignItems:'center', padding:'16px 48px',
        background:'rgba(2,2,10,0.8)', backdropFilter:'blur(20px)',
        borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
        <button onClick={() => navigate('/')} style={{ display:'flex',alignItems:'center',gap:10,background:'none',border:'none',cursor:'pointer',flex:1 }}>
          <svg width="24" height="24" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="5" fill="#ef4444" />
            <circle cx="18" cy="18" r="11" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="5 3" opacity="0.7" />
          </svg>
          <span style={{ fontFamily:'Space Mono,monospace',fontSize:13,fontWeight:700,color:'#f8fafc',letterSpacing:'.04em' }}>
            RIPPLE<span style={{color:'#ef4444'}}>GRAPH</span>
          </span>
        </button>
        <div style={{ display:'flex', gap:24, alignItems:'center' }}>
          <button onClick={() => navigate('/')} style={{ background:'none',border:'none',color:'#475569',fontSize:12,cursor:'pointer',fontFamily:'Space Mono,monospace' }}>← HOME</button>
          <button onClick={() => navigate('/app/graph')} style={{
            padding:'7px 18px', borderRadius:8, border:'1px solid rgba(239,68,68,0.4)',
            background:'rgba(239,68,68,0.08)', color:'#ef4444',
            fontSize:12, fontFamily:'Space Mono,monospace', cursor:'pointer' }}>DASHBOARD</button>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section style={{ position:'relative', height:'60vh', display:'flex', alignItems:'center',
        justifyContent:'center', overflow:'hidden' }}>
        <div ref={heroRef} style={{ position:'absolute', inset:0,
          background:'radial-gradient(ellipse 70% 50% at 50% 60%, rgba(239,68,68,0.12), transparent)',
          zIndex:0 }}>
          {/* Grid lines */}
          <svg style={{ position:'absolute', inset:0, width:'100%', height:'100%', opacity:.05 }}>
            {Array.from({length:20},(_,i)=>(
              <line key={`v${i}`} x1={`${i*5.26}%`} y1="0" x2={`${i*5.26}%`} y2="100%" stroke="#ef4444" strokeWidth="0.5"/>
            ))}
            {Array.from({length:12},(_,i)=>(
              <line key={`h${i}`} x1="0" y1={`${i*8.33}%`} x2="100%" y2={`${i*8.33}%`} stroke="#ef4444" strokeWidth="0.5"/>
            ))}
          </svg>
        </div>
        <div style={{ position:'relative', zIndex:1, textAlign:'center' }}>
          <div style={{ fontSize:10, letterSpacing:'.2em', color:'#ef4444',
            fontFamily:'Space Mono,monospace', marginBottom:16 }}>◈ PROJECT OVERVIEW</div>
          <h1 style={{ fontSize:'clamp(36px,6vw,72px)', fontWeight:800, color:'#f8fafc',
            fontFamily:'Space Mono,monospace', letterSpacing:'-.02em', lineHeight:1 }}>
            ABOUT<br /><span style={{ color:'#ef4444' }}>RIPPLEGRAPH</span>
          </h1>
          <p style={{ fontSize:16, color:'#475569', marginTop:20, maxWidth:500, margin:'20px auto 0' }}>
            A hackathon supply chain prediction system combining multi-agent AI, graph neural networks, and real-time 3D visualization.
          </p>
        </div>
      </section>

      <div style={{ maxWidth:1100, margin:'0 auto', padding:'0 48px 120px' }}>

        {/* ── WHAT IS IT ── */}
        <Section style={{ padding:'80px 0 60px' }}>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:60, alignItems:'center' }}>
            <div>
              <div style={{ fontSize:10, letterSpacing:'.2em', color:'#60a5fa', fontFamily:'Space Mono,monospace', marginBottom:12 }}>◈ THE PROBLEM</div>
              <h2 style={{ fontSize:'clamp(24px,3vw,36px)', fontWeight:800, color:'#f8fafc',
                fontFamily:'Space Mono,monospace', marginBottom:20, letterSpacing:'-.01em' }}>
                SUPPLY CHAINS<br />BREAK IN CASCADES
              </h2>
              <p style={{ fontSize:14, color:'#64748b', lineHeight:1.8, marginBottom:16 }}>
                Modern supply chains are deeply interconnected. When a Tier-3 raw material supplier in Taiwan shuts down, the disruption doesn't stop there — it cascades through wafer fabs, IC manufacturers, and eventually reaches OEM production lines weeks later.
              </p>
              <p style={{ fontSize:14, color:'#64748b', lineHeight:1.8 }}>
                Traditional supply chain tools react after disruptions hit. RippleGraph AI predicts cascade propagation 45 days ahead using a Graph Neural Network trained on supplier relationships.
              </p>
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
              {[
                { val:'$4.4T', label:'Annual global supply chain disruption cost', color:'#ef4444' },
                { val:'23%', label:'Of companies have no supply disruption visibility', color:'#f97316' },
                { val:'45', label:'Days of cascade visibility with GNN model', color:'#34d399' },
                { val:'94%', label:'Prediction confidence on held-out test data', color:'#a78bfa' },
              ].map(({ val, label, color }) => (
                <div key={val} style={{ background:'rgba(255,255,255,0.02)', border:`1px solid ${color}22`,
                  borderRadius:12, padding:'20px 16px', textAlign:'center' }}>
                  <div style={{ fontSize:28, fontWeight:800, fontFamily:'Space Mono,monospace',
                    color, textShadow:`0 0 20px ${color}66`, marginBottom:8 }}>{val}</div>
                  <div style={{ fontSize:11, color:'#475569', lineHeight:1.5 }}>{label}</div>
                </div>
              ))}
            </div>
          </div>
        </Section>

        <div style={{ height:1, background:'linear-gradient(to right, transparent, rgba(255,255,255,0.06), transparent)', margin:'0 0 80px' }} />

        {/* ── TECH STACK ── */}
        <Section style={{ marginBottom:80 }}>
          <div style={{ fontSize:10, letterSpacing:'.2em', color:'#34d399', fontFamily:'Space Mono,monospace', marginBottom:12, textAlign:'center' }}>◈ TECHNOLOGY</div>
          <h2 style={{ fontSize:'clamp(22px,3vw,36px)', fontWeight:800, color:'#f8fafc',
            fontFamily:'Space Mono,monospace', textAlign:'center', marginBottom:48 }}>TECH STACK</h2>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:24 }}>
            {stack.map(({ cat, items, color }) => (
              <div key={cat} style={{ background:'rgba(255,255,255,0.02)', border:`1px solid ${color}18`,
                borderRadius:14, padding:'24px 20px' }}>
                <div style={{ fontSize:11, fontWeight:700, color, fontFamily:'Space Mono,monospace',
                  letterSpacing:'.08em', marginBottom:16 }}>{cat.toUpperCase()}</div>
                <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
                  {items.map(item => (
                    <div key={item} style={{ display:'flex', alignItems:'center', gap:8 }}>
                      <div style={{ width:4, height:4, borderRadius:'50%', background:color, flexShrink:0 }} />
                      <span style={{ fontSize:13, color:'#94a3b8' }}>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* ── ARCHITECTURE ── */}
        <Section style={{ marginBottom:80 }}>
          <div style={{ fontSize:10, letterSpacing:'.2em', color:'#a78bfa', fontFamily:'Space Mono,monospace', marginBottom:12, textAlign:'center' }}>◈ SYSTEM DESIGN</div>
          <h2 style={{ fontSize:'clamp(22px,3vw,36px)', fontWeight:800, color:'#f8fafc',
            fontFamily:'Space Mono,monospace', textAlign:'center', marginBottom:48 }}>ARCHITECTURE</h2>
          <div style={{ background:'rgba(255,255,255,0.01)', border:'1px solid rgba(255,255,255,0.06)',
            borderRadius:16, padding:'40px', fontFamily:'Space Mono,monospace' }}>
            <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:24, marginBottom:32, textAlign:'center' }}>
              {[
                { label:'Frontend :5173', items:['React + Vite','Three.js Globe','TanStack Query','Zustand Store'], color:'#60a5fa' },
                { label:'Backend :8080', items:['FastAPI','SQLite/SQLAlchemy','WebSocket Manager','Google ADK Pipeline'], color:'#34d399' },
                { label:'ML Server :8081', items:['PyTorch GNN','GraphSAGE Model','Prediction API','45-day inference'], color:'#a78bfa' },
              ].map(({ label, items, color }) => (
                <div key={label} style={{ background:`${color}08`, border:`1px solid ${color}22`, borderRadius:12, padding:'20px 16px' }}>
                  <div style={{ fontSize:11, fontWeight:700, color, marginBottom:12 }}>{label}</div>
                  {items.map(item => (
                    <div key={item} style={{ fontSize:11, color:'#475569', marginBottom:5 }}>{item}</div>
                  ))}
                </div>
              ))}
            </div>
            <div style={{ textAlign:'center', fontSize:12, color:'#334155' }}>
              ← WebSocket real-time · REST API · Axios client →
            </div>
          </div>
        </Section>

        {/* ── AGENT PIPELINE ── */}
        <Section style={{ marginBottom:80 }}>
          <div style={{ fontSize:10, letterSpacing:'.2em', color:'#f59e0b', fontFamily:'Space Mono,monospace', marginBottom:12, textAlign:'center' }}>◈ MULTI-AGENT AI</div>
          <h2 style={{ fontSize:'clamp(22px,3vw,36px)', fontWeight:800, color:'#f8fafc',
            fontFamily:'Space Mono,monospace', textAlign:'center', marginBottom:48 }}>ADK PIPELINE</h2>
          <div style={{ display:'flex', gap:0, alignItems:'stretch' }}>
            {[
              { name:'MonitorAgent', desc:'Scans supplier nodes, detects anomalies, scores severity', color:'#60a5fa', icon:'👁' },
              { name:'AnalystAgent', desc:'Calls GNN server, models cascade propagation, calculates revenue exposure', color:'#a78bfa', icon:'🧠' },
              { name:'RecommenderAgent', desc:'Generates actionable mitigation strategies per tier and supplier', color:'#34d399', icon:'💡' },
            ].map(({ name, desc, color, icon }, i) => (
              <div key={name} style={{ flex:1, display:'flex', alignItems:'center' }}>
                <div style={{ flex:1, background:`${color}08`, border:`1px solid ${color}22`,
                  borderRadius:14, padding:'28px 20px', textAlign:'center' }}>
                  <div style={{ fontSize:28, marginBottom:12 }}>{icon}</div>
                  <div style={{ fontSize:12, fontWeight:700, color, fontFamily:'Space Mono,monospace', marginBottom:8 }}>{name}</div>
                  <div style={{ fontSize:12, color:'#64748b', lineHeight:1.6 }}>{desc}</div>
                </div>
                {i < 2 && (
                  <div style={{ width:40, display:'flex', alignItems:'center', justifyContent:'center',
                    fontSize:18, color:'#334155', flexShrink:0 }}>→</div>
                )}
              </div>
            ))}
          </div>
        </Section>

        {/* ── WHAT WAS BUILT ── */}
        <Section style={{ marginBottom:80 }}>
          <div style={{ fontSize:10, letterSpacing:'.2em', color:'#ef4444', fontFamily:'Space Mono,monospace', marginBottom:12, textAlign:'center' }}>◈ DELIVERABLES</div>
          <h2 style={{ fontSize:'clamp(22px,3vw,36px)', fontWeight:800, color:'#f8fafc',
            fontFamily:'Space Mono,monospace', textAlign:'center', marginBottom:48 }}>WHAT WAS BUILT</h2>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
            {[
              { title:'3D Earth Globe Visualization', desc:'Real-continent outline traces, lat/lon grid, great-circle arc edges, quaternion-rotated node rings sized by revenue', tags:['Three.js','React Three Fiber','WebGL'], color:'#60a5fa' },
              { title:'Multi-Agent ADK Pipeline', desc:'3-agent Google ADK cascade with graceful Gemini fallback. Saves predictions to SQLite and broadcasts via WebSocket', tags:['Google ADK','Gemini API','Python'], color:'#a78bfa' },
              { title:'GraphSAGE GNN Model', desc:'PyTorch-based graph neural network serving predictions from a dedicated ML server. 45-day cascade horizon.', tags:['PyTorch','GraphSAGE','REST API'], color:'#34d399' },
              { title:'Real-Time Analytics Dashboard', desc:'45-day cascade timeline SVG charts, tier-breakdown revenue exposure, 8-second polling with WebSocket override', tags:['TanStack Query','WebSocket','SVG'], color:'#f59e0b' },
              { title:'Simulation Injection System', desc:'6 real-world scenarios directly inject predictions into DB, broadcast live updates to graph and analytics simultaneously', tags:['FastAPI','SQLite','WebSocket'], color:'#ef4444' },
              { title:'JWT Authentication', desc:'Full auth flow with register/login, JWT tokens, protected routes, and persistent session via localStorage', tags:['JWT','FastAPI','Zustand'], color:'#f97316' },
            ].map(({ title, desc, tags, color }) => (
              <div key={title} style={{ background:'rgba(255,255,255,0.02)', border:`1px solid ${color}18`,
                borderRadius:14, padding:'24px 20px',
                transition:'all .3s' }}
                onMouseEnter={e => { e.currentTarget.style.transform='translateY(-3px)'; e.currentTarget.style.borderColor=`${color}44` }}
                onMouseLeave={e => { e.currentTarget.style.transform='translateY(0)'; e.currentTarget.style.borderColor=`${color}18` }}
              >
                <h3 style={{ fontSize:14, fontWeight:700, color:'#f1f5f9',
                  fontFamily:'Space Mono,monospace', marginBottom:10 }}>{title}</h3>
                <p style={{ fontSize:12, color:'#64748b', lineHeight:1.7, marginBottom:14 }}>{desc}</p>
                <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
                  {tags.map(t => <Tag key={t} label={t} color={color} />)}
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* ── CTA ── */}
        <Section>
          <div style={{ textAlign:'center', padding:'60px 0',
            background:'radial-gradient(ellipse 50% 40% at 50% 50%, rgba(239,68,68,0.06), transparent)',
            borderRadius:24, border:'1px solid rgba(255,255,255,0.04)' }}>
            <h2 style={{ fontSize:32, fontWeight:800, color:'#f8fafc', fontFamily:'Space Mono,monospace', marginBottom:16 }}>
              READY TO EXPLORE?
            </h2>
            <p style={{ fontSize:14, color:'#475569', marginBottom:32 }}>
              Launch the dashboard and fire a disruption scenario to see it all in action.
            </p>
            <div style={{ display:'flex', gap:16, justifyContent:'center' }}>
              <button onClick={() => navigate('/app/graph')} style={{
                padding:'12px 32px', borderRadius:10, fontSize:13,
                fontFamily:'Space Mono,monospace', cursor:'pointer',
                background:'linear-gradient(135deg,#ef4444,#dc2626)', border:'none', color:'#fff',
                boxShadow:'0 0 40px rgba(239,68,68,0.4)', transition:'all .3s' }}
                onMouseEnter={e => e.currentTarget.style.boxShadow='0 0 60px rgba(239,68,68,0.6)'}
                onMouseLeave={e => e.currentTarget.style.boxShadow='0 0 40px rgba(239,68,68,0.4)'}
              >OPEN DASHBOARD →</button>
              <button onClick={() => navigate('/')} style={{
                padding:'12px 32px', borderRadius:10, fontSize:13,
                fontFamily:'Space Mono,monospace', cursor:'pointer',
                background:'transparent', border:'1px solid rgba(255,255,255,0.1)', color:'#94a3b8',
                transition:'all .3s' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor='rgba(255,255,255,0.3)'; e.currentTarget.style.color='#f1f5f9' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor='rgba(255,255,255,0.1)'; e.currentTarget.style.color='#94a3b8' }}
              >← BACK HOME</button>
            </div>
          </div>
        </Section>
      </div>
    </div>
  )
}
