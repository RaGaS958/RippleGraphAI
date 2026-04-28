import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8080/ws/live'

export interface RiskScore {
  score: number
  level: 'low' | 'medium' | 'high' | 'critical'
  peak_day: number
}

export interface PredictionComplete {
  event_id: string
  urgency: string
  critical: number
  high: number
  revenue: number
  model: string
  summary: string
  recommendations: string[]
}

interface WSState {
  scores: Record<string, RiskScore>
  connected: boolean
  lastPrediction: PredictionComplete | null
  newEvent: any | null
}

export function useRealtimeRisk() {
  const [state, setState] = useState<WSState>({
    scores: {}, connected: false, lastPrediction: null, newEvent: null,
  })

  const wsRef    = useRef<WebSocket | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout>>()
  const deadRef  = useRef(false)   // prevents reconnect after unmount

  const connect = useCallback(() => {
    // Don't connect if component unmounted or already open
    if (deadRef.current) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return

    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setState(s => ({ ...s, connected: true }))
      }

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.type === 'snapshot') {
            setState(s => ({ ...s, scores: msg.data ?? {} }))
          } else if (msg.type === 'risk_update') {
            setState(s => ({ ...s, scores: { ...s.scores, ...msg.data } }))
          } else if (msg.type === 'prediction_complete') {
            setState(s => ({ ...s, lastPrediction: msg.data }))
          } else if (msg.type === 'new_event') {
            setState(s => ({ ...s, newEvent: msg.data }))
          }
        } catch {}
      }

      ws.onclose = (e) => {
        setState(s => ({ ...s, connected: false }))
        wsRef.current = null
        // Only retry if not intentionally closed (code 1000) and not unmounted
        if (!deadRef.current && e.code !== 1000) {
          retryRef.current = setTimeout(connect, 4000)
        }
      }

      ws.onerror = () => {
        // Let onclose handle the retry
        ws.close()
      }
    } catch {
      if (!deadRef.current) {
        retryRef.current = setTimeout(connect, 4000)
      }
    }
  }, [])

  useEffect(() => {
    deadRef.current = false
    connect()
    return () => {
      deadRef.current = true
      clearTimeout(retryRef.current)
      if (wsRef.current) {
        wsRef.current.close(1000, 'component unmounted')
        wsRef.current = null
      }
    }
  }, [connect])

  return state
}