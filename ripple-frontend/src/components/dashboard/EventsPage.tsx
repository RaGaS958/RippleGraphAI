import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { eventsApi, suppliersApi } from '../../services/api'

const TYPES = ['factory_shutdown','natural_disaster','logistics_delay','quality_issue','geopolitical','capacity_constraint']
const STATUS_COLOR: Record<string,string> = { active:'#ef4444', monitoring:'#f59e0b', resolved:'#22c55e' }

export default function EventsPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    supplier_id:'', disruption_type:'factory_shutdown',
    severity:0.85, description:'', affected_capacity_pct:40,
  })

  const { data: events = [], isLoading } = useQuery({
    queryKey:['events'], queryFn: eventsApi.listActive, refetchInterval:10_000
  })

  const { data: suppliers = [] } = useQuery({
    queryKey:['suppliers'], queryFn: () => suppliersApi.list()
  })

  const createMut = useMutation({
    mutationFn: eventsApi.create,
    onSuccess: () => { qc.invalidateQueries({queryKey:['events']}); setShowForm(false) }
  })

  const resolveMut = useMutation({
    mutationFn: eventsApi.resolve,
    onSuccess: () => qc.invalidateQueries({queryKey:['events']})
  })

  const tier3 = suppliers.filter((s:any) => s.tier === 'tier_3')

  return (
    <div style={{ padding:'1.5rem', height:'100%', overflowY:'auto' }}>
      {/* Header */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'1.25rem' }}>
        <div>
          <h2 style={{ fontSize:18, fontWeight:700, color:'#f9fafb' }}>Disruption Events</h2>
          <p style={{ fontSize:13, color:'#6b7280', marginTop:2 }}>{events.length} active events</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} style={btn('#ef4444')}>
          + New Event
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div style={card}>
          <h3 style={{ fontSize:14, fontWeight:600, color:'#f9fafb', marginBottom:'1rem' }}>Create Disruption Event</h3>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 }}>
            <div style={fieldWrap}>
              <label style={label}>Supplier (Tier 3)</label>
              <select style={input} value={form.supplier_id} onChange={e => setForm({...form, supplier_id:e.target.value})}>
                <option value="">Select supplier…</option>
                {tier3.map((s:any) => <option key={s.id} value={s.id}>{s.name} — {s.country}</option>)}
              </select>
            </div>
            <div style={fieldWrap}>
              <label style={label}>Type</label>
              <select style={input} value={form.disruption_type} onChange={e => setForm({...form, disruption_type:e.target.value})}>
                {TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g,' ')}</option>)}
              </select>
            </div>
            <div style={fieldWrap}>
              <label style={label}>Severity: {(form.severity*100).toFixed(0)}%</label>
              <input type="range" min={0} max={1} step={0.01} value={form.severity}
                onChange={e => setForm({...form, severity:+e.target.value})}
                style={{ width:'100%', accentColor:'#ef4444' }} />
            </div>
            <div style={fieldWrap}>
              <label style={label}>Capacity affected: {form.affected_capacity_pct}%</label>
              <input type="range" min={1} max={100} step={1} value={form.affected_capacity_pct}
                onChange={e => setForm({...form, affected_capacity_pct:+e.target.value})}
                style={{ width:'100%', accentColor:'#ef4444' }} />
            </div>
            <div style={{ ...fieldWrap, gridColumn:'1/-1' }}>
              <label style={label}>Description</label>
              <textarea style={{ ...input, resize:'none' }} rows={2}
                placeholder="Describe the disruption…"
                value={form.description} onChange={e => setForm({...form, description:e.target.value})} />
            </div>
          </div>
          <div style={{ display:'flex', gap:8, justifyContent:'flex-end', marginTop:'1rem' }}>
            <button onClick={() => setShowForm(false)} style={btn('#374151')}>Cancel</button>
            <button
              disabled={createMut.isPending || !form.supplier_id}
              onClick={() => createMut.mutate(form)}
              style={btn('#ef4444')}>
              {createMut.isPending ? 'Creating…' : 'Create + Trigger ADK Pipeline'}
            </button>
          </div>
        </div>
      )}

      {/* List */}
      <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
        {isLoading && <div style={{ color:'#6b7280', textAlign:'center', padding:'2rem' }}>Loading…</div>}
        {!isLoading && events.length === 0 && (
          <div style={{ color:'#4b5563', textAlign:'center', padding:'3rem', fontSize:14 }}>
            No active events. System nominal.
          </div>
        )}
        {events.map((ev:any) => (
          <div key={ev.id} style={card}>
            <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:6 }}>
              <span style={{ fontSize:13, fontWeight:600, color:'#f9fafb', flex:1, textTransform:'capitalize' }}>
                {ev.disruption_type?.replace(/_/g,' ')}
              </span>
              <span style={{ fontSize:11, fontWeight:600, color: STATUS_COLOR[ev.status]??'#6b7280', textTransform:'capitalize' }}>
                {ev.status}
              </span>
              <span style={{ fontSize:11, color:'#6b7280', background:'#1e1e3a', padding:'2px 8px', borderRadius:5 }}>
                Severity: {(ev.severity*100).toFixed(0)}%
              </span>
            </div>
            <p style={{ fontSize:13, color:'#9ca3af', marginBottom:8, lineHeight:1.4 }}>{ev.description || '—'}</p>
            <div style={{ display:'flex', gap:12, flexWrap:'wrap', fontSize:11, color:'#6b7280', marginBottom:8 }}>
              <span>Capacity: {ev.affected_capacity_pct?.toFixed(0)}%</span>
              {ev.estimated_revenue_at_risk_usd > 0 && (
                <span style={{ color:'#fca5a5', fontWeight:600 }}>
                  ${(ev.estimated_revenue_at_risk_usd/1e6).toFixed(1)}M at risk
                </span>
              )}
            </div>
            {ev.status === 'active' && (
              <button onClick={() => resolveMut.mutate(ev.id)}
                style={{ ...btn('#374151'), fontSize:12, padding:'5px 10px' }}>
                Mark resolved
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

const card: React.CSSProperties = { background:'#0f0f1a', border:'1px solid #1e1e3a', borderRadius:10, padding:'14px 16px', marginBottom:8 }
const fieldWrap: React.CSSProperties = { display:'flex', flexDirection:'column', gap:5 }
const label: React.CSSProperties = { fontSize:12, color:'#6b7280', fontWeight:500 }
const input: React.CSSProperties = { background:'#080810', border:'1px solid #2d2d4e', borderRadius:7, color:'#e2e8f0', fontSize:13, padding:'8px 10px', outline:'none', fontFamily:'inherit', width:'100%' }
const btn = (bg: string): React.CSSProperties => ({ background:bg, color:'#fff', border:'none', borderRadius:8, padding:'8px 16px', fontSize:13, fontWeight:600, cursor:'pointer' })
