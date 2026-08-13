import { useDemoStore } from '../../store/useDemoStore'
import { useSimulationStore } from '../../store/useSimulationStore'

export default function EventLog() {
  const isSim = useSimulationStore(s => s.isRunning)
  const store = isSim ? useSimulationStore() : useDemoStore()
  const events = store.events

  return (
    <div style={{
      width: '100%',
      height: '100%',
      background: '#FFFFFF',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 18px',
        borderBottom: '1px solid #E9E9E5',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: '#FFFFFF',
      }}>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.65rem',
          letterSpacing: '0.12em',
          color: '#2C2D30',
          fontWeight: 800,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          REAL-TIME AUDIT LOG
          <span style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: '#D9534F',
            display: 'inline-block',
            boxShadow: '0 0 6px rgba(217,83,79,0.5)',
          }} />
        </div>
      </div>

      {/* Events List */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
        background: '#FAFAFA',
      }}>
        {events.length === 0 && (
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.68rem',
            color: '#A0A2A8',
            textAlign: 'center',
            marginTop: '40px',
          }}>
            Awaiting telemetry & voice events...
          </div>
        )}

        {events.map((evt: any) => {
          const isCritical = evt.risk === 'critical'
          const timeStr = new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          return (
            <div
              key={evt.id}
              style={{
                background: '#FFFFFF',
                border: `1px solid ${isCritical ? '#FCDAD7' : '#E9E9E5'}`,
                borderRadius: '6px',
                padding: '10px 12px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
                animation: 'fade-up 0.3s ease both',
              }}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '6px',
              }}>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '0.55rem',
                  color: '#8E9096',
                }}>
                  {timeStr}
                </span>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: '0.5rem',
                  color: isCritical ? '#C84B42' : '#D9534F',
                  background: isCritical ? '#FDE8E8' : '#FFF3EE',
                  border: `1px solid ${isCritical ? '#F8B4B4' : '#FCDAD7'}`,
                  padding: '2px 6px',
                  borderRadius: '3px',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}>
                  {evt.type || 'NOVA-ACTION'}
                </span>
              </div>

              <div style={{
                fontFamily: "'Inter', -apple-system, sans-serif",
                fontSize: '0.72rem',
                color: '#2C2D30',
                lineHeight: 1.4,
                fontWeight: 500,
              }}>
                {evt.message}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
