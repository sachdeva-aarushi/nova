import { useDemoStore } from '../../store/useDemoStore'
import { useSimulationStore } from '../../store/useSimulationStore'

export default function EvidencePanel() {
  const isSim = useSimulationStore(s => s.isRunning)
  const store = isSim ? useSimulationStore() : useDemoStore()

  const { evidenceOpen, setEvidenceOpen, compoundRiskScore, riskLevel, novaState, novaCaption, novaMessage } = store as any

  if (!evidenceOpen) return null

  const spokenText = novaCaption || novaMessage || "Supervisor, I'm monitoring the live plant state, and Bay 3's oxygen level is at 21.8%, which is above threshold, but I'm concerned about the H₂S level at 5.2ppm, considering the active permit PTW-0441 for hot-work welding in Bay 3, and the Qdrant historical match INC-2024-04-1 shows a similar H₂S gas buildup incident. I recommend we take a closer look."

  return (
    <div style={{
      position: 'absolute',
      top: 0,
      right: 0,
      width: '380px',
      height: '100%',
      background: '#FFFFFF',
      borderLeft: '1px solid #C8C9C6',
      boxShadow: '-4px 0 16px rgba(0,0,0,0.06)',
      zIndex: 35,
      display: 'flex',
      flexDirection: 'column',
      animation: 'fade-up 0.4s ease both',
      padding: '20px 24px',
    }}>
      {/* Drawer Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '18px',
        borderBottom: '1px solid #E9E9E5',
        paddingBottom: '14px',
      }}>
        <div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.6rem', color: '#2C2D30', letterSpacing: '0.12em', fontWeight: 800 }}>
            COMPOUND RISK EVIDENCE DRAWER
          </div>
          <div style={{ fontFamily: "'Inter', -apple-system, sans-serif", fontSize: '1.25rem', color: '#0E0D1F', fontWeight: 800, marginTop: '2px' }}>
            Bay 3 Safety Analysis
          </div>
        </div>

        <button
          onClick={() => setEvidenceOpen(false)}
          style={{
            background: '#F7F6F2',
            border: '1px solid #C8C9C6',
            color: '#62636A',
            padding: '4px 10px',
            borderRadius: '4px',
            cursor: 'pointer',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.6rem',
            fontWeight: 700,
          }}
        >
          ✕ CLOSE
        </button>
      </div>

      {/* Drawer Body Scroll */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '14px', paddingRight: '4px' }}>
        {/* Score Evaluation */}
        <div style={{
          background: '#F9F9F8',
          border: '1px solid #E9E9E5',
          borderRadius: '8px',
          padding: '16px',
        }}>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.58rem', color: '#8E9096', letterSpacing: '0.1em', fontWeight: 700 }}>
            COMPOUND RISK EVALUATION
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginTop: '6px' }}>
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '2.4rem', fontWeight: 800, color: compoundRiskScore > 0.7 ? '#C84B42' : '#D98A3A', lineHeight: 1 }}>
              {(compoundRiskScore || 0.47).toFixed(2)}
            </span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.7rem', color: compoundRiskScore > 0.7 ? '#C84B42' : '#D98A3A', fontWeight: 800 }}>
              {(riskLevel || 'ELEVATED').toUpperCase()} TIER
            </span>
          </div>
        </div>

        {/* Signal 1 */}
        <div style={{
          background: '#FFFFFF',
          border: '1px solid #E9E9E5',
          borderRadius: '8px',
          padding: '14px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
        }}>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.55rem', color: '#D98A3A', letterSpacing: '0.1em', fontWeight: 800, marginBottom: '6px' }}>
            CONVERGING SIGNAL FACTOR 1
          </div>
          <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.82rem', color: '#0E0D1F', fontWeight: 700 }}>
            SCADA Gas Sensor Spike (+8.2 ppm H₂S)
          </div>
          <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.72rem', color: '#62636A', marginTop: '4px', lineHeight: 1.4 }}>
            Telemetry feed shows 2-second upward trajectory near compressor C-14 intake.
          </div>
        </div>

        {/* Signal 2 */}
        <div style={{
          background: '#FFFFFF',
          border: '1px solid #E9E9E5',
          borderRadius: '8px',
          padding: '14px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
        }}>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.55rem', color: '#D98A3A', letterSpacing: '0.1em', fontWeight: 800, marginBottom: '6px' }}>
            CONVERGING SIGNAL FACTOR 2
          </div>
          <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.82rem', color: '#0E0D1F', fontWeight: 700 }}>
            Active Hot-Work Permit (PTW-0441)
          </div>
          <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.72rem', color: '#62636A', marginTop: '4px', lineHeight: 1.4 }}>
            Welding torch operation authorized in Zone B3 until 16:00.
          </div>
        </div>

        {/* Signal 3 */}
        <div style={{
          background: '#FFFFFF',
          border: '1px solid #E9E9E5',
          borderRadius: '8px',
          padding: '14px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
        }}>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.55rem', color: '#D98A3A', letterSpacing: '0.1em', fontWeight: 800, marginBottom: '6px' }}>
            CONVERGING SIGNAL FACTOR 3
          </div>
          <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.82rem', color: '#0E0D1F', fontWeight: 700 }}>
            Historical Match (INC-2024-04-1)
          </div>
          <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.72rem', color: '#62636A', marginTop: '4px', lineHeight: 1.4 }}>
            Similar H₂S buildup incident in Bay 3 with hot-work active and ventilation compromised.
          </div>
        </div>

        {/* Bottom NOVA Voice Intelligence Box */}
        <div style={{
          background: '#FFF9F5',
          border: '1px solid #FCDAD7',
          borderRadius: '8px',
          padding: '14px',
          marginTop: 'auto',
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px',
          }}>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '0.55rem', color: '#D9534F', letterSpacing: '0.1em', fontWeight: 800 }}>
              NOVA VOICE INTELLIGENCE
            </span>
            {/* Waveform indicator */}
            <div style={{ display: 'flex', gap: '2px', alignItems: 'center', height: '12px' }}>
              {[8, 14, 6, 12, 16, 10, 5].map((h, i) => (
                <div key={i} style={{
                  width: '2px',
                  height: `${h}px`,
                  background: '#D9534F',
                  borderRadius: '1px',
                  animation: novaState === 'speaking' ? `pulse-ring 1.${i+2}s ease-in-out infinite` : 'none',
                }} />
              ))}
            </div>
          </div>

          <div style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: '0.72rem',
            color: '#2C2D30',
            lineHeight: 1.45,
            fontWeight: 400,
            maxHeight: '100px',
            overflowY: 'auto',
          }}>
            {spokenText}
          </div>

          <div style={{
            marginTop: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            background: '#FFFFFF',
            border: '1px solid #F8B4B4',
            padding: '4px 10px',
            borderRadius: '20px',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.55rem',
            color: '#D9534F',
            fontWeight: 800,
            letterSpacing: '0.08em',
          }}>
            <span>●</span> NOVA • {novaState === 'speaking' ? 'SPEAKING' : novaState === 'listening' ? 'LISTENING' : 'ONLINE'}
          </div>
        </div>
      </div>
    </div>
  )
}
