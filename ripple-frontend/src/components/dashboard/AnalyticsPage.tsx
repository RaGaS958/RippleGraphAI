import { useQuery, useQueryClient } from '@tanstack/react-query'
import { predictionsApi } from '../../services/api'
import { useRealtimeRisk } from '../../hooks/useRealtimeRisk'
import { useMemo, useEffect } from 'react'

// ── Tiny bar/line chart — no external deps ────────────────────────────────────
function MiniTimeline({ days, color }: { days: number[]; color: string }) {
  const max = Math.max(...days, 0.01)
  const w = 320, h = 60
  const pts = days.map((v, i) => {
    const x = (i / (days.length - 1)) * w
    const y = h - (v / max) * (h - 4)
    return `${x},${y}`
  }).join(' ')

  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width:'100%', height:h, display:'block' }}>
      <defs>
        <linearGradient id={`grad-${color}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.4" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* Area fill */}
      <polygon
        points={`0,${h} ${pts} ${w},${h}`}
        fill={`url(#grad-${color})`}
      />
      {/* Line */}
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5"
        style={{ filter:`drop-shadow(0 0 4px ${color})` }} />
    </svg>
  )
}

function KPI({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  const c = color ?? '#ef4444'
  return (
    <div style={{
      background:'rgba(255,255,255,0.02)', border:`1px solid ${c}22`,
      borderRadius:10, padding:'14px 16px', boxShadow:`0 0 20px ${c}08`,
      position:'relative', overflow:'hidden',
    }}>
      <div style={{
        position:'absolute', top:0, left:0, right:0, height:2,
        background:`linear-gradient(90deg,transparent,${c}88,transparent)`,
      }} />
      <div style={{ fontSize:10, fontWeight:500, color:'#334155', textTransform:'uppercase', letterSpacing:'.1em', marginBottom:6, fontFamily:'Space Mono,monospace' }}>
        {label}
      </div>
      <div style={{ fontSize:26, fontWeight:700, color:c, fontFamily:'Space Mono,monospace', lineHeight:1, marginBottom:4, textShadow:`0 0 20px ${c}66` }}>
        {value}
      </div>
      {sub && <div style={{ fontSize:11, color:'#334155' }}>{sub}</div>}
    </div>
  )
}

// Generate a realistic 45-day risk cascade curve based on severity
function riskCurve(peakDay: number, peakValue: number, length = 45): number[] {
  return Array.from({ length }, (_, i) => {
    const d = i + 1
    if (d <= peakDay) {
      // Ramp up
      return peakValue * Math.pow(d / peakDay, 1.8)
    } else {
      // Slow decay
      const decay = (d - peakDay) / (length - peakDay)
      return peakValue * Math.pow(1 - decay * 0.7, 1.4)
    }
  })
}

export default function AnalyticsPage() {
  const { lastPrediction } = useRealtimeRisk()

  const { data: summary } = useQuery({ queryKey: ['summary'], queryFn: predictionsApi.summary, refetchInterval: 8_000 })
  const { data: tiers = [] } = useQuery({ queryKey: ['tiers'], queryFn: predictionsApi.tierBreakdown, refetchInterval: 8_000 })

  const qc = useQueryClient()

  // Force-refetch DB data whenever WebSocket fires a new prediction
  useEffect(() => {
    if (lastPrediction) {
      qc.invalidateQueries({ queryKey: ['summary'] })
      qc.invalidateQueries({ queryKey: ['tiers'] })
    }
  }, [lastPrediction])

  const rev  = parseFloat(summary?.total_revenue_at_risk_usd ?? 0)
  const aff  = parseInt(summary?.affected_suppliers ?? 0)
  const avg  = parseFloat(summary?.avg_risk_score ?? 0)
  const crit = parseInt(summary?.critical_count ?? 0)

  // Build cascade timeline from last prediction
  const cascadeData = useMemo(() => {
    if (!lastPrediction) return null
    const peak = Math.min(0.95, lastPrediction.revenue / 3e9)
    const peakDay = 7
    return {
      tier3: riskCurve(peakDay, peak * 1.0),
      tier2: riskCurve(peakDay + 3, peak * 0.82),
      tier1: riskCurve(peakDay + 7, peak * 0.61),
      oem:   riskCurve(peakDay + 12, peak * 0.42),
    }
  }, [lastPrediction])

  const urgencyColor = lastPrediction
    ? ({ CRITICAL:'#ef4444', HIGH:'#f97316', MEDIUM:'#eab308', LOW:'#22c55e' }[lastPrediction.urgency] ?? '#64748b')
    : '#64748b'

  return (
    <div style={{ padding:'1.5rem', height:'100%', overflowY:'auto', background:'#02020a' }}>
      <div style={{ marginBottom:'1.25rem', display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <div>
          <h2 style={{ fontSize:16, fontWeight:700, color:'#f8fafc', fontFamily:'Space Mono,monospace', letterSpacing:'.05em' }}>
            RISK ANALYTICS
          </h2>
          <p style={{ fontSize:11, color:'#334155', marginTop:3, letterSpacing:'.05em' }}>
            SQLITE-POWERED · LIVE VIA WEBSOCKET · AUTO-REFRESH 8s
          </p>
        </div>
        {lastPrediction && (
          <div style={{
            display:'flex', alignItems:'center', gap:8, fontSize:11,
            fontFamily:'Space Mono,monospace', color:urgencyColor,
            background:`${urgencyColor}11`, border:`1px solid ${urgencyColor}33`,
            borderRadius:8, padding:'6px 12px',
          }}>
            <div style={{ width:6, height:6, borderRadius:'50%', background:urgencyColor, animation:'pulse 1s infinite' }} />
            {lastPrediction.urgency} ACTIVE
          </div>
        )}
      </div>

      {/* KPI row */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:10, marginBottom:'1.25rem' }}>
        <KPI label="Revenue at Risk"    value={`$${(rev/1e9).toFixed(2)}B`} sub="next 45 days" color="#ef4444" />
        <KPI label="Affected Suppliers" value={String(aff || '—')} sub="across all tiers" color="#f97316" />
        <KPI label="Avg Risk Score"     value={avg ? `${(avg*100).toFixed(1)}%` : '—'} sub="portfolio-wide" color="#eab308" />
        <KPI label="Critical Nodes"     value={String(crit || '—')} sub="require action" color="#ef4444" />
      </div>

      {/* Cascade Timeline — shows when sim data exists */}
      {cascadeData && (
        <div style={{
          background:'rgba(255,255,255,0.01)', border:'1px solid rgba(255,255,255,0.05)',
          borderRadius:12, padding:'1.25rem', marginBottom:'1rem',
        }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'1rem' }}>
            <h3 style={{ fontSize:12, fontWeight:600, color:'#f9fafb', fontFamily:'Space Mono,monospace', letterSpacing:'.06em' }}>
              CASCADE RISK TIMELINE — 45 DAYS
            </h3>
            <div style={{ display:'flex', gap:12, fontSize:10, fontFamily:'Space Mono,monospace' }}>
              {[['#f59e0b','Tier-3'],['#34d399','Tier-2'],['#a78bfa','Tier-1'],['#60a5fa','OEM']].map(([c,l]) => (
                <span key={l} style={{ color:c as string, display:'flex', alignItems:'center', gap:4 }}>
                  <span style={{ width:16, height:2, background:c as string, display:'inline-block', borderRadius:1 }} />
                  {l}
                </span>
              ))}
            </div>
          </div>
          {/* Stacked mini-charts */}
          <div style={{ display:'grid', gridTemplateColumns:'repeat(2,1fr)', gap:12 }}>
            {([
              { tier:'TIER-3', data:cascadeData.tier3, color:'#f59e0b', label:'Raw Materials / Silicon' },
              { tier:'TIER-2', data:cascadeData.tier2, color:'#34d399', label:'Wafers / Components' },
              { tier:'TIER-1', data:cascadeData.tier1, color:'#a78bfa', label:'Semiconductors / ICs' },
              { tier:'OEM',    data:cascadeData.oem,   color:'#60a5fa', label:'Final Assemblers' },
            ]).map(({ tier, data, color, label }) => (
              <div key={tier} style={{ background:'rgba(255,255,255,0.02)', borderRadius:8, padding:'10px 12px', border:`1px solid ${color}18` }}>
                <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
                  <span style={{ fontSize:10, fontWeight:700, color, fontFamily:'Space Mono,monospace' }}>{tier}</span>
                  <span style={{ fontSize:10, color:'#475569' }}>{label}</span>
                </div>
                <MiniTimeline days={data} color={color} />
                <div style={{ display:'flex', justifyContent:'space-between', fontSize:9, color:'#334155', marginTop:4, fontFamily:'Space Mono,monospace' }}>
                  <span>Day 1</span>
                  <span style={{ color, fontWeight:700 }}>Peak: {(Math.max(...data)*100).toFixed(1)}%</span>
                  <span>Day 45</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tier breakdown */}
      <div style={{
        background:'rgba(255,255,255,0.01)', border:'1px solid rgba(255,255,255,0.05)',
        borderRadius:12, padding:'1.25rem', marginBottom:'1rem',
      }}>
        <h3 style={{ fontSize:12, fontWeight:600, color:'#f9fafb', marginBottom:'1rem', fontFamily:'Space Mono,monospace', letterSpacing:'.06em' }}>
          RISK BY SUPPLIER TIER
        </h3>
        {tiers.length === 0 ? (
          <div style={{ color:'#1e293b', fontSize:12, textAlign:'center', padding:'1.5rem', fontFamily:'Space Mono,monospace' }}>
            → Run a simulation to populate
          </div>
        ) : (
          <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
            {tiers.map((row: any) => {
              const risk  = parseFloat(row.avg_risk)
              const color = risk>0.7 ? '#ef4444' : risk>0.4 ? '#f97316' : '#22c55e'
              return (
                <div key={row.tier}>
                  <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:4 }}>
                    <span style={{ fontSize:11, fontWeight:600, color:'#475569', minWidth:64, fontFamily:'Space Mono,monospace' }}>
                      {row.tier?.replace('_',' ').toUpperCase()}
                    </span>
                    <div style={{ flex:1, height:8, background:'rgba(255,255,255,0.04)', borderRadius:4, overflow:'hidden' }}>
                      <div style={{
                        height:'100%', width:`${(risk*100).toFixed(0)}%`,
                        background:`linear-gradient(90deg,${color}88,${color})`,
                        borderRadius:4, boxShadow:`0 0 10px ${color}`,
                        transition:'width .8s ease',
                      }} />
                    </div>
                    <span style={{ fontSize:11, fontWeight:700, color, minWidth:42, textAlign:'right', fontFamily:'Space Mono,monospace', textShadow:`0 0 8px ${color}` }}>
                      {(risk*100).toFixed(1)}%
                    </span>
                    <span style={{ fontSize:10, color:'#334155', minWidth:110, textAlign:'right' }}>
                      ${(parseFloat(row.total_revenue_at_risk_usd)/1e6).toFixed(0)}M at risk
                    </span>
                  </div>
                  <div style={{ display:'flex', paddingLeft:76, gap:16, fontSize:10, color:'#334155' }}>
                    <span>{row.supplier_count} suppliers</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Last pipeline result */}
      {lastPrediction && (
        <div style={{
          background:`${urgencyColor}08`, border:`1px solid ${urgencyColor}22`,
          borderRadius:12, padding:'1.25rem',
          boxShadow:`0 0 40px ${urgencyColor}10`,
        }}>
          <h3 style={{ fontSize:12, fontWeight:600, color:urgencyColor, marginBottom:12, fontFamily:'Space Mono,monospace', display:'flex', alignItems:'center', gap:8 }}>
            <span style={{ width:6, height:6, borderRadius:'50%', background:urgencyColor, boxShadow:`0 0 8px ${urgencyColor}`, animation:'pulse 1s infinite' }} />
            LAST ADK PIPELINE — {lastPrediction.urgency}
          </h3>

          <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:10, marginBottom:12 }}>
            {[
              { l:'Revenue @ Risk', v:`$${(lastPrediction.revenue/1e9).toFixed(2)}B`, c:'#fca5a5' },
              { l:'Critical Nodes', v:String(lastPrediction.critical), c:'#ef4444' },
              { l:'High Nodes',     v:String(lastPrediction.high), c:'#f97316' },
            ].map(({ l,v,c }) => (
              <div key={l} style={{ background:'rgba(8,8,16,.7)', borderRadius:8, padding:'10px 12px', border:`1px solid ${c}18` }}>
                <div style={{ fontSize:10, color:'#334155', marginBottom:4, fontFamily:'Space Mono,monospace' }}>{l}</div>
                <div style={{ fontSize:22, fontWeight:700, color:c, fontFamily:'Space Mono,monospace', textShadow:`0 0 12px ${c}88` }}>{v}</div>
              </div>
            ))}
          </div>

          <div style={{ fontSize:12, color:'#64748b', marginBottom:10, lineHeight:1.6 }}>{lastPrediction.summary}</div>

          {lastPrediction.recommendations?.length > 0 && (
            <div>
              <div style={{ fontSize:10, color:'#334155', fontWeight:600, letterSpacing:'.08em', marginBottom:8, fontFamily:'Space Mono,monospace' }}>
                AI RECOMMENDATIONS
              </div>
              {lastPrediction.recommendations.slice(0,5).map((r, i) => (
                <div key={i} style={{ display:'flex', gap:8, fontSize:12, color:'#94a3b8', marginBottom:6, alignItems:'flex-start' }}>
                  <span style={{ color:urgencyColor, fontWeight:700, fontFamily:'Space Mono,monospace', flexShrink:0 }}>{i+1}.</span>
                  <span style={{ lineHeight:1.5 }}>{r}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
    </div>
  )
}