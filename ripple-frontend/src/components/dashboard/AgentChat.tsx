import { useState, useRef, useEffect } from 'react'
import { api } from '../../services/api'

interface Msg { role: 'user' | 'agent'; text: string; ts: string }

export default function AgentChat() {
  const [msgs, setMsgs]       = useState<Msg[]>([])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus]   = useState<any>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get('/agent/status').then(r => setStatus(r.data)).catch(() => {})
    // Welcome message
    setMsgs([{
      role: 'agent',
      text: "Hi! I'm the RippleGraph AI orchestrator. I coordinate three specialist agents:\n\n" +
            "• MonitorAgent — validates events, maps supplier context\n" +
            "• AnalystAgent — runs GNN predictions, quantifies cascade risk\n" +
            "• RecommenderAgent — generates rerouting strategies\n\n" +
            "Ask me anything about your supply chain. Try:\n" +
            "\"What is the current risk status?\"\n" +
            "\"Which suppliers are most critical?\"\n" +
            "\"What should we do if our Taiwan fab shuts down?\"",
      ts: new Date().toLocaleTimeString(),
    }])
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:'smooth' }) }, [msgs])

  const send = async () => {
    if (!input.trim() || loading) return
    const text = input.trim()
    setInput('')
    setMsgs(m => [...m, { role:'user', text, ts: new Date().toLocaleTimeString() }])
    setLoading(true)
    try {
      const r = await api.post('/agent/chat', { message: text, session_id: 'ui-session' })
      setMsgs(m => [...m, {
        role: 'agent',
        text: r.data.response ?? 'No response.',
        ts: new Date().toLocaleTimeString(),
      }])
    } catch (e: any) {
      setMsgs(m => [...m, { role:'agent', text:`Error: ${e.message}`, ts: new Date().toLocaleTimeString() }])
    }
    setLoading(false)
  }

  const PRESETS = [
    "What is the current risk status?",
    "Which Tier-3 suppliers are most critical?",
    "What happens if our Taiwan supplier shuts down?",
    "Give me rerouting recommendations for semiconductor shortage",
  ]

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', background:'#080810' }}>
      {/* Header */}
      <div style={{ padding:'12px 16px', borderBottom:'1px solid #1e1e3a', display:'flex', alignItems:'center', gap:10 }}>
        <div style={{ width:32, height:32, borderRadius:'50%', background:'rgba(239,68,68,.15)', border:'1px solid rgba(239,68,68,.3)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:16 }}>🤖</div>
        <div>
          <div style={{ fontSize:14, fontWeight:600, color:'#f9fafb' }}>RippleGraph Orchestrator</div>
          <div style={{ fontSize:11, color: status?.adk_ready ? '#22c55e' : '#f59e0b' }}>
            {status?.adk_ready ? '● ADK + Gemini active' : '● Fallback mode — add GEMINI_API_KEY for full ADK'}
          </div>
        </div>
        {status && (
          <div style={{ marginLeft:'auto', fontSize:11, color:'#6b7280', textAlign:'right' }}>
            <div>Mode: <span style={{ color:'#d1d5db' }}>{status.mode}</span></div>
          </div>
        )}
      </div>

      {/* Messages */}
      <div style={{ flex:1, overflowY:'auto', padding:'16px', display:'flex', flexDirection:'column', gap:12 }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ display:'flex', justifyContent: m.role==='user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              maxWidth:'80%',
              background: m.role==='user' ? 'rgba(239,68,68,.15)' : '#0f0f1a',
              border: `1px solid ${m.role==='user' ? 'rgba(239,68,68,.3)' : '#1e1e3a'}`,
              borderRadius: m.role==='user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
              padding:'10px 14px',
            }}>
              <div style={{ fontSize:13, color:'#e2e8f0', lineHeight:1.6, whiteSpace:'pre-wrap' }}>{m.text}</div>
              <div style={{ fontSize:10, color:'#4b5563', marginTop:4 }}>{m.ts}</div>
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display:'flex', gap:5, padding:'10px 14px' }}>
            {[0,1,2].map(i => (
              <div key={i} style={{
                width:7, height:7, borderRadius:'50%', background:'#ef4444',
                animation:`bounce 1s ease ${i*0.15}s infinite`,
              }} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Preset chips */}
      <div style={{ padding:'0 16px 8px', display:'flex', gap:6, flexWrap:'wrap' }}>
        {PRESETS.map(p => (
          <button key={p} onClick={() => { setInput(p) }}
            style={{ fontSize:11, padding:'4px 10px', borderRadius:20, border:'1px solid #2d2d4e', background:'#0f0f1a', color:'#9ca3af', cursor:'pointer' }}>
            {p}
          </button>
        ))}
      </div>

      {/* Input */}
      <div style={{ padding:'12px 16px', borderTop:'1px solid #1e1e3a', display:'flex', gap:8 }}>
        <input
          style={{ flex:1, background:'#0f0f1a', border:'1px solid #2d2d4e', borderRadius:10, color:'#e2e8f0', fontSize:13, padding:'10px 14px', outline:'none', fontFamily:'inherit' }}
          placeholder="Ask about supply chain risk…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
        />
        <button onClick={send} disabled={loading || !input.trim()}
          style={{ background:'#ef4444', color:'#fff', border:'none', borderRadius:10, padding:'10px 16px', fontSize:13, fontWeight:600, cursor:'pointer', opacity: loading||!input.trim() ? 0.5 : 1 }}>
          Send
        </button>
      </div>

      <style>{`
        @keyframes bounce {
          0%,100%{transform:translateY(0)} 50%{transform:translateY(-5px)}
        }
      `}</style>
    </div>
  )
}
