import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'
import LoginPage      from './components/auth/LoginPage'
import Layout         from './components/dashboard/Layout'
import GraphPage      from './components/graph/GraphPage'
import EventsPage     from './components/dashboard/EventsPage'
import AnalyticsPage  from './components/dashboard/AnalyticsPage'
import AgentChat      from './components/dashboard/AgentChat'
import SimulationPage from './components/dashboard/SimulationPage'
import HomePage       from './components/landing/HomePage'
import AboutPage      from './components/landing/AboutPage'

function Guard({ children }: { children: React.ReactNode }) {
  const { user, loading, restore } = useAuthStore()
  useEffect(() => { restore() }, [])
  if (loading) return (
    <div style={{ height:'100vh',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',background:'#02020a',gap:16 }}>
      <div style={{ width:40,height:40,borderRadius:'50%',border:'2px solid rgba(239,68,68,0.15)',borderTopColor:'#ef4444',animation:'spin .8s linear infinite',boxShadow:'0 0 20px rgba(239,68,68,0.3)' }} />
      <span style={{ fontFamily:'Space Mono,monospace',fontSize:11,color:'#334155',letterSpacing:'.1em' }}>INITIALIZING</span>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/"        element={<HomePage />} />
      <Route path="/about"   element={<AboutPage />} />
      <Route path="/login"   element={<LoginPage />} />
      <Route path="/app"     element={<Guard><Layout /></Guard>}>
        <Route index           element={<Navigate to="/app/graph" replace />} />
        <Route path="graph"      element={<GraphPage />} />
        <Route path="simulation" element={<SimulationPage />} />
        <Route path="events"     element={<EventsPage />} />
        <Route path="analytics"  element={<AnalyticsPage />} />
        <Route path="agent"      element={<AgentChat />} />
      </Route>
      {/* legacy redirect */}
      <Route path="/graph"      element={<Navigate to="/app/graph" replace />} />
      <Route path="/simulation" element={<Navigate to="/app/simulation" replace />} />
      <Route path="/analytics"  element={<Navigate to="/app/analytics" replace />} />
      <Route path="/events"     element={<Navigate to="/app/events" replace />} />
      <Route path="/agent"      element={<Navigate to="/app/agent" replace />} />
    </Routes>
  )
}