import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

// ── Particle field ──────────────────────────────────────────────────────────
function ParticleField() {
  const meshRef = useRef<THREE.Points>(null!)
  const count = 1800
  const positions = new Float32Array(count * 3)
  const velocities = new Float32Array(count)

  for (let i = 0; i < count; i++) {
    positions[i * 3]     = (Math.random() - 0.5) * 28
    positions[i * 3 + 1] = (Math.random() - 0.5) * 18
    positions[i * 3 + 2] = (Math.random() - 0.5) * 10
    velocities[i] = Math.random() * 0.002 + 0.001
  }

  useFrame(({ clock }) => {
    if (!meshRef.current) return
    const pos = meshRef.current.geometry.attributes.position.array as Float32Array
    for (let i = 0; i < count; i++) {
      pos[i * 3 + 1] -= velocities[i]
      if (pos[i * 3 + 1] < -9) pos[i * 3 + 1] = 9
    }
    meshRef.current.geometry.attributes.position.needsUpdate = true
    meshRef.current.rotation.y = clock.elapsedTime * 0.04
  })

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))

  return (
    <points ref={meshRef} geometry={geo}>
      <pointsMaterial color="#ef4444" size={0.045} transparent opacity={0.35} />
    </points>
  )
}

function NetworkLines() {
  const lineRef = useRef<THREE.Group>(null!)
  useFrame(({ clock }) => {
    if (lineRef.current) lineRef.current.rotation.y = clock.elapsedTime * 0.07
  })

  const nodes = Array.from({ length: 22 }, () => ({
    x: (Math.random() - 0.5) * 16,
    y: (Math.random() - 0.5) * 10,
    z: (Math.random() - 0.5) * 6,
  }))

  const edges: [number, number][] = []
  nodes.forEach((_, i) => {
    const j = (i + 1) % nodes.length
    const k = (i + 3) % nodes.length
    edges.push([i, j], [i, k])
  })

  return (
    <group ref={lineRef}>
      {edges.map(([a, b], idx) => {
        const start = new THREE.Vector3(nodes[a].x, nodes[a].y, nodes[a].z)
        const end   = new THREE.Vector3(nodes[b].x, nodes[b].y, nodes[b].z)
        return (
          <line key={idx}>
            <bufferGeometry>
              <bufferAttribute
                attach="attributes-position"
                args={[new Float32Array([start.x,start.y,start.z,end.x,end.y,end.z]),3]}
              />
            </bufferGeometry>
            <lineBasicMaterial color="#ef4444" transparent opacity={0.08} />
          </line>
        )
      })}
      {nodes.map((n, i) => (
        <mesh key={i} position={[n.x, n.y, n.z]}>
          <sphereGeometry args={[0.06, 8, 8]} />
          <meshBasicMaterial color={i % 4 === 0 ? '#ef4444' : i % 4 === 1 ? '#f97316' : i % 4 === 2 ? '#a78bfa' : '#34d399'} />
        </mesh>
      ))}
    </group>
  )
}

// ── Typewriter hook ──────────────────────────────────────────────────────────
function useTypewriter(text: string, speed = 40) {
  const [displayed, setDisplayed] = useRef(['', 0]) as unknown as [{ current: [string, number] }, null]
  const [, forceUpdate] = useRef(0) as unknown as [{ current: number }, null]

  useEffect(() => {
    let i = 0
    const interval = setInterval(() => {
      if (i <= text.length) {
        displayed.current = [text.slice(0, i), i]
        forceUpdate.current++
        i++
      } else {
        clearInterval(interval)
      }
    }, speed)
    return () => clearInterval(interval)
  }, [text])
}

// Simple typewriter component
function Typewriter({ text, speed = 35 }: { text: string; speed?: number }) {
  const [displayed, setDisplayed] = useRef('')  as unknown as [{ current: string }, null]
  const [tick, setTick] = useRef(0) as unknown as [{ current: number }, null]
  const [, forceRender] = useRef(false) as unknown as [{ current: boolean }, null]
  const [displayedText, setDisplayedText] = useRef<string>('') as unknown as [{ current: string }, null]
  const [_displayed, _setDisplayed] = useRef(0) as unknown as [{ current: number }, null]

  // Use actual state
  const [chars, setChars] = useRef(0) as unknown as [{ current: number }, null]
  useEffect(() => {
    let i = 0
    const iv = setInterval(() => {
      i++
      const el = document.getElementById('tw-' + text.slice(0,5))
      if (el) el.textContent = text.slice(0, i)
      if (i >= text.length) clearInterval(iv)
    }, speed)
    return () => clearInterval(iv)
  }, [text])

  return <span id={'tw-' + text.slice(0,5)}></span>
}

// ── Feature Card ─────────────────────────────────────────────────────────────
function FeatureCard({ icon, title, desc, color, delay }: { icon: string; title: string; desc: string; color: string; delay: number }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current; if (!el) return
    el.style.opacity = '0'; el.style.transform = 'translateY(40px)'
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          el.style.transition = 'opacity .7s ease, transform .7s ease'
          el.style.opacity = '1'; el.style.transform = 'translateY(0)'
        }, delay)
        observer.disconnect()
      }
    }, { threshold: 0.1 })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={ref} style={{
      background: 'rgba(255,255,255,0.02)', border: `1px solid ${color}22`,
      borderRadius: 16, padding: '28px 24px', position: 'relative', overflow: 'hidden',
      transition: 'all .3s',
    }}
    onMouseEnter={e => {
      const el = e.currentTarget
      el.style.transform = 'translateY(-4px)'
      el.style.background = `${color}08`
      el.style.borderColor = `${color}44`
      el.style.boxShadow = `0 20px 40px ${color}15`
    }}
    onMouseLeave={e => {
      const el = e.currentTarget
      el.style.transform = 'translateY(0)'
      el.style.background = 'rgba(255,255,255,0.02)'
      el.style.borderColor = `${color}22`
      el.style.boxShadow = 'none'
    }}
    >
      <div style={{ position:'absolute', top:0, right:0, width:100, height:100,
        background: `radial-gradient(circle at top right, ${color}10, transparent 70%)` }} />
      <div style={{ fontSize: 32, marginBottom: 14 }}>{icon}</div>
      <h3 style={{ fontSize: 15, fontWeight: 700, color: '#f1f5f9', fontFamily: 'Space Mono, monospace',
        marginBottom: 8, letterSpacing: '.02em' }}>{title}</h3>
      <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.7 }}>{desc}</p>
    </div>
  )
}

// ── Stat ──────────────────────────────────────────────────────────────────────
function StatItem({ value, label, color }: { value: string; label: string; color: string }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current; if (!el) return
    el.style.opacity = '0'
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { el.style.transition = 'opacity .8s'; el.style.opacity = '1'; io.disconnect() }
    }, { threshold: 0.2 })
    io.observe(el); return () => io.disconnect()
  }, [])
  return (
    <div ref={ref} style={{ textAlign:'center', padding:'24px 16px' }}>
      <div style={{ fontSize: 40, fontWeight: 800, fontFamily: 'Space Mono, monospace',
        color, textShadow: `0 0 30px ${color}88`, marginBottom: 8 }}>{value}</div>
      <div style={{ fontSize: 12, color: '#475569', letterSpacing: '.1em', textTransform: 'uppercase' }}>{label}</div>
    </div>
  )
}

// ── Main HomePage ─────────────────────────────────────────────────────────────
export default function HomePage() {
  const navigate = useNavigate()
  const heroRef = useRef<HTMLDivElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const subtitleRef = useRef<HTMLParagraphElement>(null)
  const ctaRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // GSAP-like staggered entrance using Web Animations API
    const elements = [titleRef.current, subtitleRef.current, ctaRef.current].filter(Boolean)
    elements.forEach((el, i) => {
      if (!el) return
      el.animate([
        { opacity: '0', transform: 'translateY(30px)' },
        { opacity: '1', transform: 'translateY(0)' },
      ], { duration: 900, delay: 300 + i * 200, fill: 'forwards', easing: 'cubic-bezier(0.16,1,0.3,1)' })
    })

    // Parallax on scroll
    const onScroll = () => {
      const y = window.scrollY
      if (heroRef.current) {
        heroRef.current.style.transform = `translateY(${y * 0.3}px)`
      }
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const features = [
    { icon: '🌐', title: 'Real-Time 3D Globe', desc: 'Interactive Earth visualization with 29 supplier nodes plotted at real lat/lon coordinates. Great-circle arcs show supply chain flows.', color: '#60a5fa', delay: 0 },
    { icon: '🤖', title: 'Multi-Agent AI Pipeline', desc: 'Google ADK-powered MonitorAgent → AnalystAgent → RecommenderAgent cascade. Autonomous disruption detection and mitigation.', color: '#a78bfa', delay: 150 },
    { icon: '🧠', title: 'GraphSAGE GNN Model', desc: 'PyTorch-based Graph Neural Network for 45-day supply chain cascade prediction. 94%+ confidence on tier propagation models.', color: '#34d399', delay: 300 },
    { icon: '⚡', title: 'Live WebSocket Updates', desc: 'Real-time risk score broadcasting. Node colors, analytics KPIs, and sidebar alerts all update simultaneously via WebSocket.', color: '#f59e0b', delay: 450 },
    { icon: '🎯', title: '6 Crisis Scenarios', desc: 'From TSMC shutdowns to rare earth bans — inject any scenario and watch the full cascade propagate across tiers in real-time.', color: '#ef4444', delay: 600 },
    { icon: '📊', title: 'Analytics Dashboard', desc: '45-day cascade timeline, tier-by-tier revenue exposure, KPI tracking with 8-second refresh, and ADK pipeline recommendations.', color: '#f97316', delay: 750 },
  ]

  return (
    <div style={{ background: '#02020a', color: '#e2e8f0', minHeight: '100vh', overflowX: 'hidden' }}>

      {/* ── NAVBAR ── */}
      <nav style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        display: 'flex', alignItems: 'center', padding: '16px 48px',
        background: 'rgba(2,2,10,0.7)', backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}>
        <div style={{ display:'flex', alignItems:'center', gap:10, flex:1 }}>
          <svg width="28" height="28" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="5" fill="#ef4444" filter="url(#glow2)" />
            <circle cx="18" cy="18" r="11" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="5 3" opacity="0.7" />
            <circle cx="18" cy="18" r="17" fill="none" stroke="#ef4444" strokeWidth="0.75" strokeDasharray="3 4" opacity="0.25" />
            <defs><filter id="glow2"><feGaussianBlur stdDeviation="2" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
          </svg>
          <span style={{ fontFamily:'Space Mono,monospace', fontSize:14, fontWeight:700, color:'#f8fafc', letterSpacing:'.04em' }}>
            RIPPLE<span style={{ color:'#ef4444' }}>GRAPH</span>
          </span>
          <span style={{ fontSize:10, color:'#334155', letterSpacing:'.1em', marginLeft:4 }}>AI</span>
        </div>
        <div style={{ display:'flex', gap:32, alignItems:'center' }}>
          {['Features','About'].map(label => (
            <a key={label} href={label === 'About' ? '/about' : '#features'}
              onClick={label === 'About' ? (e) => { e.preventDefault(); navigate('/about') } : undefined}
              style={{ fontSize:13, color:'#475569', textDecoration:'none', fontFamily:'Space Mono,monospace',
                letterSpacing:'.05em', transition:'color .2s' }}
              onMouseEnter={e => (e.currentTarget.style.color = '#f1f5f9')}
              onMouseLeave={e => (e.currentTarget.style.color = '#475569')}
            >{label}</a>
          ))}
          <button onClick={() => navigate('/app/graph')} style={{
            padding:'8px 20px', borderRadius:8, border:'1px solid rgba(239,68,68,0.4)',
            background:'rgba(239,68,68,0.08)', color:'#ef4444',
            fontSize:12, fontFamily:'Space Mono,monospace', cursor:'pointer',
            transition:'all .2s', letterSpacing:'.05em',
          }}
          onMouseEnter={e => { e.currentTarget.style.background='rgba(239,68,68,0.18)'; e.currentTarget.style.boxShadow='0 0 20px rgba(239,68,68,0.3)' }}
          onMouseLeave={e => { e.currentTarget.style.background='rgba(239,68,68,0.08)'; e.currentTarget.style.boxShadow='none' }}
          >LAUNCH APP →</button>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section style={{ position:'relative', height:'100vh', display:'flex', alignItems:'center',
        justifyContent:'center', overflow:'hidden' }}>
        {/* Three.js background */}
        <div ref={heroRef} style={{ position:'absolute', inset:0, zIndex:0 }}>
          <Canvas camera={{ fov:60, position:[0,0,10] }} style={{ background:'transparent' }}>
            <ambientLight intensity={0.2} />
            <ParticleField />
            <NetworkLines />
          </Canvas>
        </div>
        {/* Radial gradient overlay */}
        <div style={{ position:'absolute', inset:0, zIndex:1,
          background:'radial-gradient(ellipse 80% 60% at 50% 50%, transparent 30%, #02020a 80%)' }} />

        {/* Hero content */}
        <div style={{ position:'relative', zIndex:2, textAlign:'center', maxWidth:800, padding:'0 24px' }}>
          <div style={{ fontSize:10, letterSpacing:'.2em', color:'#ef4444', fontFamily:'Space Mono,monospace',
            marginBottom:24, opacity:0 }} ref={el => {
            if (el) el.animate([{opacity:0},{opacity:1}],{duration:600,delay:100,fill:'forwards'})
          }}>
            ◉ HACKATHON PROJECT · SUPPLY CHAIN AI
          </div>
          <h1 ref={titleRef} style={{ fontSize:'clamp(42px,7vw,88px)', fontWeight:800, lineHeight:1.0,
            letterSpacing:'-.03em', color:'#f8fafc', marginBottom:24, fontFamily:'Space Mono,monospace',
            opacity:0 }}>
            RIPPLE<br />
            <span style={{ color:'#ef4444', textShadow:'0 0 60px rgba(239,68,68,0.6)' }}>GRAPH</span>
            <span style={{ color:'rgba(255,255,255,0.15)', fontSize:'0.5em', verticalAlign:'super' }}>AI</span>
          </h1>
          <p ref={subtitleRef} style={{ fontSize:'clamp(14px,2vw,18px)', color:'#64748b', lineHeight:1.8,
            maxWidth:560, margin:'0 auto 40px', opacity:0 }}>
            Predict supply chain disruptions before they cascade.
            Multi-agent AI · GraphSAGE GNN · Real-time 3D visualization.
          </p>
          <div ref={ctaRef} style={{ display:'flex', gap:16, justifyContent:'center', flexWrap:'wrap', opacity:0 }}>
            <button onClick={() => navigate('/app/graph')} style={{
              padding:'14px 36px', borderRadius:10, fontSize:14,
              fontFamily:'Space Mono,monospace', letterSpacing:'.06em', cursor:'pointer',
              background:'linear-gradient(135deg, #ef4444, #dc2626)',
              border:'none', color:'#fff',
              boxShadow:'0 0 40px rgba(239,68,68,0.4)',
              transition:'all .3s',
            }}
            onMouseEnter={e => { e.currentTarget.style.transform='translateY(-2px)'; e.currentTarget.style.boxShadow='0 8px 50px rgba(239,68,68,0.6)' }}
            onMouseLeave={e => { e.currentTarget.style.transform='translateY(0)'; e.currentTarget.style.boxShadow='0 0 40px rgba(239,68,68,0.4)' }}
            >OPEN DASHBOARD</button>
            <button onClick={() => navigate('/about')} style={{
              padding:'14px 36px', borderRadius:10, fontSize:14,
              fontFamily:'Space Mono,monospace', letterSpacing:'.06em', cursor:'pointer',
              background:'transparent', color:'#94a3b8',
              border:'1px solid rgba(255,255,255,0.1)', transition:'all .3s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor='rgba(255,255,255,0.3)'; e.currentTarget.style.color='#f1f5f9' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor='rgba(255,255,255,0.1)'; e.currentTarget.style.color='#94a3b8' }}
            >ABOUT PROJECT</button>
          </div>
        </div>

        {/* Scroll indicator */}
        <div style={{ position:'absolute', bottom:40, left:'50%', transform:'translateX(-50%)',
          display:'flex', flexDirection:'column', alignItems:'center', gap:8, zIndex:2 }}>
          <div style={{ fontSize:10, color:'#334155', letterSpacing:'.15em', fontFamily:'Space Mono,monospace' }}>SCROLL</div>
          <div style={{ width:1, height:40, background:'linear-gradient(to bottom, #334155, transparent)', animation:'scrollPulse 2s ease-in-out infinite' }} />
        </div>
      </section>

      {/* ── STATS BAND ── */}
      <section style={{ padding:'60px 48px', borderTop:'1px solid rgba(255,255,255,0.04)',
        borderBottom:'1px solid rgba(255,255,255,0.04)',
        background:'linear-gradient(to right, rgba(239,68,68,0.03), transparent, rgba(167,139,250,0.03))',
        display:'grid', gridTemplateColumns:'repeat(4,1fr)' }}>
        <StatItem value="29" label="Supplier Nodes" color="#60a5fa" />
        <StatItem value="6" label="Crisis Scenarios" color="#ef4444" />
        <StatItem value="45" label="Day Cascade Model" color="#a78bfa" />
        <StatItem value="94%" label="GNN Confidence" color="#34d399" />
      </section>

      {/* ── FEATURES ── */}
      <section id="features" style={{ padding:'100px 48px', maxWidth:1200, margin:'0 auto' }}>
        <div style={{ textAlign:'center', marginBottom:64 }}>
          <div style={{ fontSize:10, letterSpacing:'.2em', color:'#ef4444',
            fontFamily:'Space Mono,monospace', marginBottom:12 }}>◈ CAPABILITIES</div>
          <h2 style={{ fontSize:'clamp(28px,4vw,48px)', fontWeight:800, color:'#f8fafc',
            fontFamily:'Space Mono,monospace', letterSpacing:'-.02em' }}>
            BUILT FOR THE<br />
            <span style={{ color:'#ef4444' }}>REAL WORLD</span>
          </h2>
        </div>
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(340px,1fr))', gap:20 }}>
          {features.map(f => <FeatureCard key={f.title} {...f} />)}
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section style={{ padding:'80px 48px', background:'rgba(255,255,255,0.01)',
        borderTop:'1px solid rgba(255,255,255,0.04)' }}>
        <div style={{ maxWidth:900, margin:'0 auto' }}>
          <div style={{ textAlign:'center', marginBottom:60 }}>
            <div style={{ fontSize:10, letterSpacing:'.2em', color:'#a78bfa',
              fontFamily:'Space Mono,monospace', marginBottom:12 }}>◈ ARCHITECTURE</div>
            <h2 style={{ fontSize:'clamp(24px,3vw,40px)', fontWeight:800, color:'#f8fafc',
              fontFamily:'Space Mono,monospace' }}>HOW IT WORKS</h2>
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:0 }}>
            {[
              { step:'01', title:'Disruption Event Detected', desc:'MonitorAgent continuously polls global supply chain signals. Natural disasters, port strikes, geopolitical events — all scored for severity.', color:'#ef4444' },
              { step:'02', title:'GNN Cascade Prediction', desc:'GraphSAGE model runs inference across the supplier graph. Predicts risk propagation: Tier-3 → Tier-2 → Tier-1 → OEM over 45 days.', color:'#a78bfa' },
              { step:'03', title:'AI Recommendations', desc:'RecommenderAgent generates specific mitigation strategies: rerouting suppliers, pre-positioning inventory, activating backup contracts.', color:'#34d399' },
              { step:'04', title:'Live Dashboard Update', desc:'WebSocket broadcasts push risk scores to the 3D globe in real-time. All nodes recolor, analytics KPIs update, sidebar alerts fire.', color:'#60a5fa' },
            ].map((item, i) => (
              <PipelineStep key={item.step} {...item} isLast={i === 3} />
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={{ padding:'120px 48px', textAlign:'center',
        background:'radial-gradient(ellipse 60% 40% at 50% 50%, rgba(239,68,68,0.08), transparent)' }}>
        <h2 style={{ fontSize:'clamp(32px,5vw,64px)', fontWeight:800, color:'#f8fafc',
          fontFamily:'Space Mono,monospace', letterSpacing:'-.02em', marginBottom:24 }}>
          PREDICT THE<br />
          <span style={{ color:'#ef4444', textShadow:'0 0 40px rgba(239,68,68,0.5)' }}>NEXT RIPPLE</span>
        </h2>
        <p style={{ fontSize:16, color:'#475569', marginBottom:48, maxWidth:500, margin:'0 auto 48px' }}>
          Launch the dashboard and fire a crisis scenario to see the full multi-agent AI pipeline in action.
        </p>
        <button onClick={() => navigate('/app/graph')} style={{
          padding:'18px 56px', borderRadius:12, fontSize:16,
          fontFamily:'Space Mono,monospace', letterSpacing:'.08em', cursor:'pointer',
          background:'linear-gradient(135deg, #ef4444, #dc2626)',
          border:'none', color:'#fff',
          boxShadow:'0 0 60px rgba(239,68,68,0.5)',
          transition:'all .3s',
        }}
        onMouseEnter={e => { e.currentTarget.style.transform='scale(1.04)'; e.currentTarget.style.boxShadow='0 0 80px rgba(239,68,68,0.7)' }}
        onMouseLeave={e => { e.currentTarget.style.transform='scale(1)'; e.currentTarget.style.boxShadow='0 0 60px rgba(239,68,68,0.5)' }}
        >LAUNCH RIPPLGRAPH →</button>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ padding:'32px 48px', borderTop:'1px solid rgba(255,255,255,0.04)',
        display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <span style={{ fontFamily:'Space Mono,monospace', fontSize:12, color:'#1e293b' }}>
          RIPPLE<span style={{ color:'#ef4444' }}>GRAPH</span> AI · Hackathon 2024
        </span>
        <div style={{ display:'flex', gap:24 }}>
          <button onClick={() => navigate('/about')} style={{ background:'none',border:'none',color:'#334155',fontSize:12,cursor:'pointer',fontFamily:'Space Mono,monospace' }}>About</button>
          <button onClick={() => navigate('/app/graph')} style={{ background:'none',border:'none',color:'#334155',fontSize:12,cursor:'pointer',fontFamily:'Space Mono,monospace' }}>Dashboard</button>
        </div>
      </footer>

      <style>{`
        @keyframes scrollPulse { 0%,100%{opacity:.3} 50%{opacity:1} }
      `}</style>
    </div>
  )
}

function PipelineStep({ step, title, desc, color, isLast }: { step:string; title:string; desc:string; color:string; isLast:boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const el = ref.current; if (!el) return
    el.style.opacity = '0'; el.style.transform = 'translateX(-20px)'
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        el.style.transition = 'opacity .7s ease, transform .7s ease'
        el.style.opacity = '1'; el.style.transform = 'translateX(0)'
        io.disconnect()
      }
    }, { threshold: 0.1 })
    io.observe(el); return () => io.disconnect()
  }, [])

  return (
    <div ref={ref} style={{ display:'flex', gap:32, padding:'32px 0', position:'relative' }}>
      {!isLast && <div style={{ position:'absolute', left:28, top:64, bottom:0, width:1,
        background:`linear-gradient(to bottom, ${color}44, transparent)` }} />}
      <div style={{ width:56, height:56, borderRadius:'50%', border:`2px solid ${color}44`,
        display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
        background:`${color}10`, fontFamily:'Space Mono,monospace', fontSize:13,
        fontWeight:700, color, boxShadow:`0 0 20px ${color}20` }}>{step}</div>
      <div style={{ paddingTop:12 }}>
        <h3 style={{ fontSize:16, fontWeight:700, color:'#f1f5f9', fontFamily:'Space Mono,monospace', marginBottom:8 }}>{title}</h3>
        <p style={{ fontSize:14, color:'#64748b', lineHeight:1.7 }}>{desc}</p>
      </div>
    </div>
  )
}
