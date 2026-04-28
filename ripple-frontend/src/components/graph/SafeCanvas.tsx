// Replace the <Canvas> block in GraphPage.tsx with this component.
// Handles WebGL context loss gracefully on Windows.

import { useEffect, useRef, useState } from 'react'

export function SafeCanvas({ children, ...props }: any) {
  const [lost, setLost]       = useState(false)
  const [retries, setRetries] = useState(0)
  const containerRef          = useRef<HTMLDivElement>(null)

  // Listen for WebGL context loss on any canvas in this container
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleLost = (e: Event) => {
      e.preventDefault()
      console.warn('WebGL context lost — will retry in 2s')
      setLost(true)
      setTimeout(() => {
        setRetries(r => r + 1)
        setLost(false)
      }, 2000)
    }

    const canvas = container.querySelector('canvas')
    canvas?.addEventListener('webglcontextlost', handleLost)
    return () => canvas?.removeEventListener('webglcontextlost', handleLost)
  }, [retries])   // re-attach after each retry (new canvas element)

  return (
    <div ref={containerRef} style={{ flex:1, position:'relative' }}>
      {lost ? (
        <div style={{
          position:'absolute', inset:0, display:'flex', flexDirection:'column',
          alignItems:'center', justifyContent:'center', gap:12,
          color:'#6b7280', fontSize:13, background:'#080810',
        }}>
          <div className="spin" style={{ width:28, height:28, border:'2px solid #1e1e3a', borderTopColor:'#ef4444', borderRadius:'50%' }} />
          Recovering 3D context…
        </div>
      ) : (
        // key={retries} forces React to remount Canvas after context loss
        <div key={retries} style={{ height:'100%' }}>
          {children}
        </div>
      )}
    </div>
  )
}
