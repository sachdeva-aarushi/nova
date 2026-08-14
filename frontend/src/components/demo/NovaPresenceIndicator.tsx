import { useEffect } from 'react'
import { useDemoStore } from '../../store/useDemoStore'
import { useSimulationStore } from '../../store/useSimulationStore'
import { startRealVoiceListener, stopRealVoiceListener } from '../../engine/realSystemEngine'
import { stopCurrentTTS } from '../../engine/deepgramVoice'

export default function NovaPresenceIndicator() {
  const isSim = useSimulationStore(s => s.isRunning)
  const store = isSim ? useSimulationStore() : useDemoStore()

  const { novaState, novaCaption, setNovaCaption } = store as any

  // Auto-dismiss the caption speech bubble 3.5 seconds after NOVA finishes speaking
  useEffect(() => {
    if (novaState === 'idle' && novaCaption && !novaCaption.startsWith('🎙')) {
      const timer = setTimeout(() => {
        if (setNovaCaption) {
          setNovaCaption('')
        }
      }, 3500)
      return () => clearTimeout(timer)
    }
  }, [novaState, novaCaption, setNovaCaption])

  const stateColors: Record<string, string> = {
    speaking: '#2563EB',
    processing: '#D98A3A',
    listening: '#0D9488',
    idle: '#62636A',
  }

  const stateLabels: Record<string, string> = {
    speaking: 'NOVA · SPEAKING (TAP TO STOP)',
    processing: 'NOVA · THINKING',
    listening: 'NOVA · LISTENING (TAP TO STOP)',
    idle: 'TAP TO SPEAK TO NOVA',
  }

  const dotColor = stateColors[novaState] || '#0D9488'
  const isUserSpeech = novaCaption?.startsWith('[USER]') || novaCaption?.startsWith('🎙')
  const displayText = isUserSpeech ? novaCaption.replace(/^(\[USER\]|🎙)\s*/, '') : novaCaption

  const handleMicToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (novaState === 'speaking') {
      stopCurrentTTS()
    } else if (novaState === 'listening') {
      stopRealVoiceListener()
      if (store.setNovaState) store.setNovaState('idle')
    } else {
      if (store.setNovaState) store.setNovaState('listening')
      startRealVoiceListener()
    }
  }

  return (
    <div style={{
      position: 'absolute',
      bottom: '24px',
      right: '24px',
      zIndex: 40,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-end',
      gap: '12px',
      pointerEvents: 'none',
    }}>
      {/* Caption / transcript bubble */}
      {novaCaption && (
        <div style={{
          background: '#FFFFFF',
          border: `2px solid ${isUserSpeech ? '#0D9488' : '#2563EB'}`,
          borderRadius: '12px',
          padding: '14px 20px',
          maxWidth: '460px',
          color: '#0E0D1F',
          fontFamily: "'Titillium Web', sans-serif",
          fontSize: '0.92rem',
          lineHeight: 1.5,
          boxShadow: '0 8px 24px rgba(0,0,0,0.1)',
          animation: 'fade-up 0.3s ease both',
          transition: 'all 0.2s ease',
          pointerEvents: 'auto',
        }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.58rem',
            color: isUserSpeech ? '#0D9488' : '#2563EB',
            letterSpacing: '0.12em',
            marginBottom: '6px',
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <span style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: isUserSpeech ? '#0D9488' : '#2563EB',
            }} />
            {isUserSpeech ? 'OPERATOR VOICE INPUT' : 'NOVA VOICE INTELLIGENCE'}
          </div>
          "{displayText}"
        </div>
      )}

      {/* Interactive Tap-to-Talk Mic Toggle Button */}
      <button
        onClick={handleMicToggle}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          background: '#FFFFFF',
          border: `2px solid ${novaState === 'speaking' ? '#2563EB' : novaState === 'processing' ? '#D98A3A' : novaState === 'listening' ? '#0D9488' : '#8E9096'}`,
          borderRadius: '30px',
          padding: '10px 22px',
          boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
          cursor: 'pointer',
          pointerEvents: 'auto',
          transition: 'all 0.2s ease',
          outline: 'none',
        }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.04)' }}
        onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1.0)' }}
      >
        {/* Animated bars for listening/speaking */}
        {(novaState === 'listening' || novaState === 'speaking') ? (
          <div style={{ display: 'flex', gap: 2, alignItems: 'center', height: 14 }}>
            {[0, 1, 2, 3].map(i => (
              <div key={i} style={{
                width: 3,
                background: dotColor,
                borderRadius: 2,
                animation: `waveform-bar ${0.6 + i * 0.15}s ease-in-out infinite alternate`,
                height: '100%',
              }} />
            ))}
          </div>
        ) : (
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            background: dotColor,
          }} />
        )}

        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.68rem',
          letterSpacing: '0.1em',
          color: dotColor,
          fontWeight: 800,
        }}>
          {stateLabels[novaState] || 'TAP TO SPEAK TO NOVA'}
        </span>

        {/* Deepgram badge */}
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '0.48rem',
          color: '#8E9096',
          letterSpacing: '0.05em',
          borderLeft: '1px solid #C8C9C6',
          paddingLeft: 8,
          fontWeight: 700,
        }}>
          DEEPGRAM
        </span>
      </button>

      <style>{`
        @keyframes waveform-bar {
          from { height: 4px; }
          to   { height: 14px; }
        }
      `}</style>
    </div>
  )
}
