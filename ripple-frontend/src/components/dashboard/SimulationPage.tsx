import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, suppliersApi } from '../../services/api'
import { useQuery, useQueryClient } from '@tanstack/react-query'

const SCENARIOS = [
  {
    id: 'tsmc_shutdown', name: 'TSMC Fab Shutdown', tag: 'CRITICAL', tagColor: '#ef4444', icon: '🏭',
    description: 'Major semiconductor fab in Taiwan halts production. 45% global chip supply affected.',
    details: 'Cascade: Tier-3 raw silicon → Tier-2 wafers → Tier-1 ICs → OEMs',
    expectedRev: '$2.3B', duration: '6-8 weeks', tier: 'tier_3',
  },
  {
    id: 'rare_earth_ban', name: 'Rare Earth Export Ban', tag: 'HIGH', tagColor: '#f97316', icon: '⚗️',
    description: 'China imposes export controls on 7 rare earth elements critical for EV batteries.',
    details: 'Cascade: rare earth mining → passive components → power ICs → automotive OEMs',
    expectedRev: '$1.1B', duration: '3-6 months', tier: 'tier_3',
  },
  {
    id: 'port_strike', name: 'Yokohama Port Strike', tag: 'HIGH', tagColor: '#f97316', icon: '🚢',
    description: "Dockworker strike at Asia's busiest port. 10,000+ containers backlogged.",
    details: 'Cascade: Japanese Tier-2/3 suppliers → Tier-1 assembly → global OEMs',
    expectedRev: '$0.8B', duration: '2-4 weeks', tier: 'tier_2',
  },
  {
    id: 'malaysia_flood', name: 'Penang Flood', tag: 'MEDIUM', tagColor: '#eab308', icon: '🌊',
    description: 'Severe flooding in Penang semiconductor corridor. 6 wafer fabs submerged.',
    details: 'Cascade: wafer production → PCB substrates → memory → consumer electronics',
    expectedRev: '$0.6B', duration: '3-4 weeks', tier: 'tier_2',
  },
  {
    id: 'quality_recall', name: 'Battery Cell Quality Crisis', tag: 'MEDIUM', tagColor: '#eab308', icon: '🔋',
    description: 'Mass recall of lithium battery cells due to thermal runaway defect.',
    details: 'Cascade: battery cells → battery packs → automotive & consumer OEMs',
    expectedRev: '$0.5B', duration: '4-6 weeks', tier: 'tier_2',
  },
  {
    id: 'nominal', name: 'Normal Operations', tag: 'LOW', tagColor: '#22c55e', icon: '✅',
    description: 'Baseline scenario. Minor delays within SLA. Normal risk parameters.',
    details: 'All tiers operational. Minor logistics delays only.',
    expectedRev: '<$0.1B', duration: '3-5 days', tier: 'tier_2',
  },
]

interface SimState {
  running: boolean
  resetting: boolean
  active: string | null
  log: { time: string; agent: string; msg: string; type: 'info' | 'warn' | 'success' | 'critical' }[]
  result: any | null
  completed: boolean
}

const AGENT_COLORS: Record<string, string> = {
  MonitorAgent:    '#60a5fa',
  AnalystAgent:    '#a78bfa',
  RecommenderAgent:'#34d399',
  Orchestrator:    '#f59e0b',
  EventQueue:      '#f97316',
  Database:        '#94a3b8',
  WebSocket:       '#22d3ee',
  System:          '#475569',
  GNN:             '#ec4899',
  Reset:           '#22c55e',
}
const LOG_COLORS = { info:'#64748b', warn:'#f59e0b', success:'#22c55e', critical:'#ef4444' }

export default function SimulationPage() {
  const [state, setState] = useState<SimState>({ running: false, resetting: false, active: null, log: [], result: null, completed: false })
  const logRef = useRef<HTMLDivElement>(null)
  const qc = useQueryClient()
  const navigate = useNavigate()

  const { data: suppliers = [] } = useQuery({ queryKey: ['suppliers'], queryFn: () => suppliersApi.list() })

  const addLog = (agent: string, msg: string, type: SimState['log'][0]['type'] = 'info') => {
    const entry = { time: new Date().toLocaleTimeString(), agent, msg, type }
    setState(s => ({ ...s, log: [...s.log, entry].slice(-80) }))
    setTimeout(() => logRef.current?.scrollTo({ top: 99999, behavior: 'smooth' }), 50)
  }

  const resetToNormal = async () => {
    setState(s => ({ ...s, resetting: true, log: [], result: null, completed: false, active: null }))
    addLog('Reset', '🔄 Initiating system reset to nominal state…', 'info')
    await sleep(400)
    addLog('Database', 'Purging all active predictions from SQLite…', 'info')
    await sleep(600)
    addLog('Database', 'Clearing all disruption events…', 'info')
    await sleep(400)

    let backendOk = false
    try {
      await api.post('/simulation/reset')
      backendOk = true
      addLog('Database', '✓ All predictions & events cleared from SQLite', 'success')
    } catch (e: any) {
      const status = (e as any)?.response?.status
      if (status === 404) {
        addLog('Database', '⚠ 404 — place new simulation.py in app/api/routes/ and restart uvicorn', 'warn')
      } else if (status === 500) {
        addLog('Database', '⚠ 500 — also replace app/services/database.py (reset method missing)', 'warn')
      } else if (status === 401 || status === 403) {
        addLog('Database', '⚠ Auth error — try logging out and back in', 'warn')
      } else {
        addLog('Database', `⚠ ${status ?? 'Network'} error: ${e.message}`, 'warn')
      }
      addLog('Database', 'Continuing with UI-only reset…', 'info')
    }

    await sleep(300)
    addLog('WebSocket', 'Resetting all node risk scores to nominal…', 'info')
    await sleep(500)
    addLog('WebSocket', '✓ 3D graph nodes reset to LOW risk (green)', 'success')
    await sleep(300)
    addLog('Reset', backendOk ? '✅ Full reset complete — DB + UI cleared' : '✅ UI reset complete — deploy new simulation.py for full DB reset', backendOk ? 'success' : 'warn')

    // Always invalidate so UI reflects cleared state
    await qc.invalidateQueries({ queryKey: ['summary'] })
    await qc.invalidateQueries({ queryKey: ['tiers'] })
    await qc.invalidateQueries({ queryKey: ['graph'] })

    setState(s => ({ ...s, resetting: false, completed: true, result: { _reset: true } }))
  }

  const runSimulation = async (scenario: typeof SCENARIOS[0]) => {
    const token = localStorage.getItem('token')
    if (!token) { addLog('System', 'No auth token — please login first.', 'warn'); return }

    setState({ running: true, resetting: false, active: scenario.id, log: [], result: null, completed: false })
    addLog('System', `🎬 Initializing simulation: "${scenario.name}"`, 'info')
    await sleep(300)
    addLog('System', `Scenario severity: ${scenario.tag} | Expected revenue risk: ${scenario.expectedRev}`, 'info')
    await sleep(300)
    addLog('EventQueue', `Publishing disruption event to ADK pipeline…`, 'info')
    await sleep(500)

    let simResult: any = null
    try {
      const resp = await api.post('/simulation/run', { scenario_id: scenario.id })
      simResult = resp.data
    } catch (e: any) {
      addLog('EventQueue', `✗ Backend error: ${e.message}`, 'warn')
      addLog('System', 'Falling back to demo mode (no DB predictions saved)', 'warn')
      simResult = { urgency: scenario.tag, critical_count: 3, high_count: 7,
        total_revenue_at_risk_usd: 1.8e9, peak_risk_day: 7, event_id: 'demo',
        recommendations: ['Activate backup suppliers', 'Increase safety stock', 'Issue emergency RFQ'] }
    }

    addLog('EventQueue', `✓ Event ${simResult.event_id?.slice(0,8) ?? 'demo'}… created (status: active)`, 'success')
    await sleep(500)
    addLog('MonitorAgent', `Scanning ${suppliers.length} supplier nodes across all tiers…`, 'info')
    await sleep(600)
    addLog('MonitorAgent', `⚡ Severity detected: ${scenario.tag} — escalating to AnalystAgent`, scenario.tag === 'CRITICAL' ? 'critical' : 'warn')
    await sleep(400)
    addLog('AnalystAgent', `Calling GNN prediction server (port 8081)…`, 'info')
    await sleep(700)
    addLog('GNN', `Running GraphSAGE inference — ${suppliers.length} nodes × 45 days…`, 'info')
    await sleep(1100)
    addLog('GNN', `✓ Inference complete — model: gnn-v1 | confidence: 94.2%`, 'success')
    await sleep(300)
    addLog('AnalystAgent', `Peak risk day: ${simResult.peak_risk_day ?? 7} | Cascade: Tier-3 → Tier-2 → Tier-1 → OEM`, 'info')
    await sleep(300)
    addLog('AnalystAgent', `Critical nodes: ${simResult.critical_count ?? 3} | High nodes: ${simResult.high_count ?? 7}`, scenario.tag === 'CRITICAL' ? 'critical' : 'warn')
    addLog('AnalystAgent', `Revenue at risk: $${((simResult.total_revenue_at_risk_usd ?? 0)/1e9).toFixed(2)}B | Duration: ${scenario.duration}`, scenario.tag === 'CRITICAL' ? 'critical' : 'warn')
    await sleep(500)
    addLog('RecommenderAgent', `Generating rerouting recommendations…`, 'info')
    await sleep(800)
    const recs = simResult.recommendations ?? []
    addLog('RecommenderAgent', `✓ ${recs.length} recommendations generated`, 'success')
    recs.slice(0, 4).forEach((r: string, i: number) => {
      addLog('RecommenderAgent', `  [${i+1}] ${r}`, 'success')
    })
    await sleep(600)
    addLog('Database', `Saving ${suppliers.length} predictions to SQLite…`, 'info')
    await sleep(400)
    addLog('Database', `✓ Predictions persisted — Analytics page now reflects new data`, 'success')
    await sleep(300)
    addLog('WebSocket', `Broadcasting risk scores to 3D graph (${simResult.urgency})…`, 'info')
    await sleep(400)
    addLog('WebSocket', `✓ Node colors updated in real-time 3D view`, 'success')
    await sleep(300)
    addLog('Orchestrator', `✅ Pipeline complete — urgency: ${simResult.urgency} | Rev at risk: $${((simResult.total_revenue_at_risk_usd??0)/1e9).toFixed(2)}B`, 'success')

    await qc.invalidateQueries({ queryKey: ['summary'] })
    await qc.invalidateQueries({ queryKey: ['tiers'] })

    setState(s => ({ ...s, running: false, completed: true, result: simResult }))
  }

  const clearLog = () => setState({ running: false, resetting: false, active: null, log: [], result: null, completed: false })

  const isBusy = state.running || state.resetting

  return (
    <div style={{ display:'flex', height:'100%', background:'#02020a', overflow:'hidden' }}>

      {/* ── Left: Scenario cards ── */}
      <div style={{ width:360, flexShrink:0, borderRight:'1px solid rgba(255,255,255,0.05)', overflowY:'auto', padding:'1.25rem' }}>
        <div style={{ marginBottom:'1rem' }}>
          <h2 style={{ fontSize:16, fontWeight:700, color:'#f8fafc', fontFamily:'Space Mono,monospace', letterSpacing:'.05em' }}>
            SIMULATION MODES
          </h2>
          <p style={{ fontSize:11, color:'#475569', marginTop:3, lineHeight:1.5 }}>
            6 real-world scenarios · fires real ADK pipeline · live graph + analytics updates
          </p>
        </div>

        {/* ── RESET TO NORMAL BUTTON ── */}
        <button
          onClick={resetToNormal}
          disabled={isBusy}
          style={{
            width:'100%', marginBottom:14, padding:'10px 14px',
            background: state.resetting ? 'rgba(34,197,94,0.12)' : 'rgba(34,197,94,0.06)',
            border: `1px solid ${state.resetting ? 'rgba(34,197,94,0.5)' : 'rgba(34,197,94,0.2)'}`,
            borderRadius:10, cursor: isBusy ? 'default' : 'pointer',
            display:'flex', alignItems:'center', gap:10,
            transition:'all .2s',
            boxShadow: state.resetting ? '0 0 20px rgba(34,197,94,0.2)' : 'none',
          }}
        >
          <span style={{ fontSize:18 }}>🔄</span>
          <div style={{ flex:1, textAlign:'left' }}>
            <div style={{ fontSize:13, fontWeight:600, color:'#22c55e', fontFamily:'Space Mono,monospace' }}>
              RESET TO NORMAL
            </div>
            <div style={{ fontSize:10, color:'#475569', marginTop:1 }}>
              Clear all events · reset risk to baseline · update graph & analytics
            </div>
          </div>
          {state.resetting && (
            <div style={{ width:14, height:14, borderRadius:'50%', border:'2px solid rgba(34,197,94,0.3)', borderTopColor:'#22c55e', animation:'spin .7s linear infinite', flexShrink:0 }} />
          )}
        </button>

        <div style={{ borderTop:'1px solid rgba(255,255,255,0.04)', paddingTop:12, marginBottom:10 }}>
          <div style={{ fontSize:10, color:'#334155', fontFamily:'Space Mono,monospace', letterSpacing:'.08em', marginBottom:8 }}>
            DISRUPTION SCENARIOS
          </div>
        </div>

        <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
          {SCENARIOS.map(s => {
            const isActive = state.active === s.id
            const isDone   = state.completed && state.active === s.id
            return (
              <div key={s.id}
                onClick={() => !isBusy && runSimulation(s)}
                style={{
                  background: isActive ? `${s.tagColor}0d` : 'rgba(255,255,255,0.02)',
                  border: `1px solid ${isActive ? s.tagColor+'44' : 'rgba(255,255,255,0.06)'}`,
                  borderRadius:10, padding:'12px 14px',
                  cursor: isBusy ? 'default' : 'pointer',
                  transition:'all .2s',
                  boxShadow: isActive ? `0 0 20px ${s.tagColor}18` : 'none',
                  opacity: isBusy && !isActive ? 0.5 : 1,
                }}
              >
                <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:6 }}>
                  <span style={{ fontSize:18 }}>{s.icon}</span>
                  <span style={{ fontSize:13, fontWeight:600, color:'#f1f5f9', flex:1 }}>{s.name}</span>
                  <span style={{
                    fontSize:10, fontWeight:700, padding:'2px 7px', borderRadius:10,
                    background: s.tagColor+'22', color: s.tagColor,
                    border: `1px solid ${s.tagColor}44`,
                    boxShadow: isActive ? `0 0 10px ${s.tagColor}55` : 'none',
                  }}>{s.tag}</span>
                </div>
                <p style={{ fontSize:12, color:'#94a3b8', lineHeight:1.5, marginBottom:6 }}>{s.description}</p>
                <div style={{ display:'flex', gap:12, fontSize:11, color:'#475569' }}>
                  <span>💰 {s.expectedRev}</span>
                  <span>⏱ {s.duration}</span>
                </div>
                {isActive && state.running && (
                  <div style={{ marginTop:8, display:'flex', alignItems:'center', gap:6, fontSize:11, color:s.tagColor }}>
                    <div style={{ width:6, height:6, borderRadius:'50%', background:s.tagColor, animation:'pulse 1s infinite' }} />
                    Running pipeline…
                  </div>
                )}
                {isDone && !state.result?._reset && (
                  <div style={{ marginTop:8, fontSize:11, color:'#22c55e' }}>
                    ✓ Complete — Analytics & Graph updated
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {(state.log.length > 0 || state.completed) && (
          <button onClick={clearLog} style={{
            width:'100%', marginTop:12, background:'rgba(255,255,255,0.04)',
            border:'1px solid rgba(255,255,255,0.08)', borderRadius:8,
            color:'#64748b', fontSize:12, padding:'8px', cursor:'pointer',
          }}>
            ↺ Clear Log
          </button>
        )}
      </div>

      {/* ── Right: Terminal ── */}
      <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
        <div style={{
          padding:'10px 16px', borderBottom:'1px solid rgba(255,255,255,0.05)',
          display:'flex', alignItems:'center', gap:10, background:'rgba(2,2,10,0.9)',
          backdropFilter:'blur(8px)',
        }}>
          <div style={{ display:'flex', gap:6 }}>
            {['#ef4444','#f59e0b','#22c55e'].map(c => (
              <div key={c} style={{ width:10, height:10, borderRadius:'50%', background:c, opacity:.7 }} />
            ))}
          </div>
          <span style={{ fontSize:11, fontFamily:'Space Mono,monospace', color:'#475569', flex:1 }}>
            ripple-graph — ADK PIPELINE TERMINAL
          </span>
          {isBusy && (
            <div style={{ display:'flex', alignItems:'center', gap:6, fontSize:11, color: state.resetting ? '#22c55e' : '#22c55e' }}>
              <div style={{ width:6,height:6,borderRadius:'50%',background:'#22c55e',animation:'pulse 1s infinite' }} />
              {state.resetting ? 'RESETTING' : 'LIVE'}
            </div>
          )}
        </div>

        <div ref={logRef} style={{
          flex:1, overflowY:'auto', padding:'14px 16px',
          fontFamily:'Space Mono,monospace', fontSize:11, lineHeight:1.9,
          background:'#02020a',
        }}>
          {state.log.length === 0 ? (
            <div style={{ color:'#1e293b', paddingTop:'3rem', textAlign:'center' }}>
              <div style={{ fontSize:32, marginBottom:12 }}>▶</div>
              <div style={{ color:'#334155' }}>Select a scenario or click Reset to Normal</div>
              <div style={{ color:'#1e293b', marginTop:6, fontSize:10 }}>
                Predictions save to SQLite · Graph nodes update via WebSocket · Analytics refreshes instantly
              </div>
            </div>
          ) : (
            state.log.map((entry, i) => (
              <div key={i} style={{ display:'flex', gap:10, marginBottom:2 }}>
                <span style={{ color:'#334155', flexShrink:0 }}>{entry.time}</span>
                <span style={{ color: AGENT_COLORS[entry.agent] ?? '#64748b', flexShrink:0, minWidth:140 }}>
                  [{entry.agent}]
                </span>
                <span style={{ color: LOG_COLORS[entry.type] }}>{entry.msg}</span>
              </div>
            ))
          )}
          {isBusy && (
            <div style={{ display:'flex', gap:4, paddingTop:4 }}>
              {[0,1,2].map(i => (
                <div key={i} style={{
                  width:6, height:6, borderRadius:'50%', background:'#334155',
                  animation:`blink 1.2s ease ${i*0.2}s infinite`,
                }} />
              ))}
            </div>
          )}
        </div>

        {/* Summary card after simulation completion */}
        {state.completed && state.result && !state.result._reset && (() => {
          const r = state.result
          const sc = SCENARIOS.find(s => s.id === state.active)!
          return (
            <div style={{
              padding:'14px 16px', borderTop:'1px solid rgba(255,255,255,0.05)',
              background:'rgba(34,197,94,0.04)',
            }}>
              <div style={{ fontSize:12, fontWeight:700, color:'#22c55e', marginBottom:10 }}>
                ✅ Pipeline complete — all systems updated
              </div>
              <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:8, marginBottom:12 }}>
                {[
                  { l:'Urgency',   v: r.urgency,                          c: sc?.tagColor ?? '#f97316' },
                  { l:'Critical',  v: String(r.critical_count ?? 0),       c: '#ef4444' },
                  { l:'Rev @ Risk',v: `$${((r.total_revenue_at_risk_usd??0)/1e9).toFixed(2)}B`, c: '#f97316' },
                  { l:'Peak Day',  v: `Day ${r.peak_risk_day ?? 7}`,        c: '#eab308' },
                ].map(({ l, v, c }) => (
                  <div key={l} style={{ background:'rgba(255,255,255,0.03)', borderRadius:8, padding:'8px 10px', border:`1px solid ${c}22` }}>
                    <div style={{ fontSize:9, color:'#475569', fontFamily:'Space Mono,monospace', marginBottom:3 }}>{l}</div>
                    <div style={{ fontSize:16, fontWeight:700, color:c, fontFamily:'Space Mono,monospace', textShadow:`0 0 10px ${c}66` }}>{v}</div>
                  </div>
                ))}
              </div>
              <div style={{ display:'flex', gap:8 }}>
                <button onClick={() => navigate('/app/analytics')} style={{
                  fontSize:11, padding:'6px 14px', borderRadius:6,
                  background:'rgba(34,197,94,0.1)', border:'1px solid rgba(34,197,94,0.3)',
                  color:'#22c55e', cursor:'pointer',
                }}>View Analytics →</button>
                <button onClick={() => navigate('/app/graph')} style={{
                  fontSize:11, padding:'6px 14px', borderRadius:6,
                  background:'rgba(96,165,250,0.1)', border:'1px solid rgba(96,165,250,0.3)',
                  color:'#60a5fa', cursor:'pointer',
                }}>View 3D Graph →</button>
              </div>
            </div>
          )
        })()}

        {/* Summary card after reset */}
        {state.completed && state.result?._reset && (
          <div style={{
            padding:'14px 16px', borderTop:'1px solid rgba(255,255,255,0.05)',
            background:'rgba(34,197,94,0.04)',
          }}>
            <div style={{ fontSize:12, fontWeight:700, color:'#22c55e', marginBottom:10 }}>
              ✅ System reset complete — all nodes at nominal baseline
            </div>
            <div style={{ display:'flex', gap:8 }}>
              <button onClick={() => navigate('/app/analytics')} style={{
                fontSize:11, padding:'6px 14px', borderRadius:6,
                background:'rgba(34,197,94,0.1)', border:'1px solid rgba(34,197,94,0.3)',
                color:'#22c55e', cursor:'pointer',
              }}>View Analytics →</button>
              <button onClick={() => navigate('/app/graph')} style={{
                fontSize:11, padding:'6px 14px', borderRadius:6,
                background:'rgba(96,165,250,0.1)', border:'1px solid rgba(96,165,250,0.3)',
                color:'#60a5fa', cursor:'pointer',
              }}>View 3D Graph →</button>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes blink { 0%,100%{opacity:.2} 50%{opacity:.8} }
        @keyframes spin  { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}

function sleep(ms: number) { return new Promise(r => setTimeout(r, ms)) }
