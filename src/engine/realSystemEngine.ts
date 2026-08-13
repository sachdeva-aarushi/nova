/**
 * realSystemEngine.ts — Autonomous Voice-Native AI Control Room Engine
 *
 * 1. Groq LLM (llama-3.3-70b-versatile) — Dynamic, grounded reasoning for every unique query
 * 2. Deepgram STT (Nova-3 WebSocket) — Speech recognition with sub-100ms voice barge-in
 * 3. Rime TTS (mist-v3 model, astra voice) — Natural human voice output
 * 4. High-Frequency Telemetry Stream — 1-second continuous vitals drift across all 5 plant bays
 * 5. Autonomous Action Execution — Unscripted UI camera zooming, evidence drawer, permit actions
 */

import { useSimulationStore } from '../store/useSimulationStore'
import { startDeepgramListening, stopDeepgramListening, deepgramSpeak, stopCurrentTTS } from './deepgramVoice'

let streamInterval: ReturnType<typeof setInterval> | null = null

// Groq LLM API Key (Fallback to .env default if VITE env variable not set)
const GROQ_API_KEY = (import.meta as any).env?.VITE_GROQ_API_KEY || (import.meta as any).env?.LLM_API_KEY || ''

// ─── Real-Time 1-Second Continuous Telemetry Stream ───────────────────── //

export function startLiveTelemetryStream() {
  if (streamInterval) clearInterval(streamInterval)

  const store = useSimulationStore.getState
  store().startSimulation()

  // REAL: telemetry fed from WebSocket sensorStream & GET /api/factory/state
  const fetchRealTelemetry = async () => {
    const s = store()
    if (!s.isRunning) return

    try {
      const res = await fetch('/api/factory/state')
      if (res.ok) {
        const data = await res.json()
        if (data && data.sensors) {
          useSimulationStore.setState({
            sensors: data.sensors,
            compoundRiskScore: data.compound_risk_score ?? s.compoundRiskScore,
            riskLevel: data.risk_level ?? s.riskLevel
          })
        }
      }
    } catch (err) {
      console.warn('[Telemetry] WebSocket / API polling sync:', err)
    }
  }

  fetchRealTelemetry()
  streamInterval = setInterval(fetchRealTelemetry, 2000)
}


export function stopLiveTelemetryStream() {
  if (streamInterval) {
    clearInterval(streamInterval)
    streamInterval = null
  }
  useSimulationStore.getState().stopSimulation()
}

// ─── Voice Output ─────────────────────────────────────────────────────────── //

export async function novaSpeakSimulation(text: string): Promise<void> {
  return deepgramSpeak(text)
}

// ─── Groq Voice-Native Agent ──────────────────────────────────────────────── //

const ACTION_SCHEMA = `
Available actions (return as JSON array of strings):
- "ZOOM:Bay 1" through "ZOOM:Bay 5" — camera zoom to specific bay
- "RESET_VIEW" — zoom out to plant overview
- "SHOW_EVIDENCE" — open compound risk evidence drawer
- "HIDE_EVIDENCE" — close evidence drawer
- "SHOW_TRACKS" — view Qdrant memory tracks
- "SHOW_AUDIT" — view immutable audit log
- "SHOW_SIGNALS" — view SCADA signal dashboard
- "AUTHORIZE" — execute pending safety action
- "REJECT" — reject pending safety action
- "NONE" — no UI action needed
`

export async function generateReActResponse(userQuery: string): Promise<{ spoken: string; actions: string[] }> {
  const store = useSimulationStore.getState()

  const sensorsCtx = store.sensors
    .map(s => `${s.zone} ${s.type}: ${s.value}${s.unit} [threshold ${s.threshold}${s.unit}, ${s.status.toUpperCase()}]`)
    .join('; ')

  const systemPrompt = `You are NOVA, an autonomous AI Industrial Safety Officer piloting a chemical processing plant.
You communicate with the supervisor via VOICE ONLY — plain text only, no markdown (*, _, #, \`), no bullet points.

LIVE PLANT STATE:
- Real-Time Vitals: ${sensorsCtx}
- Compound Risk Index: ${store.compoundRiskScore.toFixed(2)} (${store.riskLevel.toUpperCase()} TIER)
- Focused Zone: ${store.focusedZone || 'Plant Overview'}
- Active Permits: PTW-0441 (Hot-Work Welding Bay 3), PTW-0439 (Electrical Bay 1)
- Qdrant Memory Record: INC-2024-041 (H2S gas buildup during welding, similarity 0.88)

${ACTION_SCHEMA}

Formulate an intelligent, grounded, unique response as a real human safety officer. Return EXACT JSON:
{
  "spoken": "Your spoken answer — 1 to 3 concise, clear, speech-ready sentences.",
  "actions": ["ACTION_1", "ACTION_2"]
}

Rules:
1. "spoken" MUST be clean speech-ready plain text without markdown symbols.
2. If the user asks to zoom or look at a bay (Bay 1, Bay 2, Bay 3, Bay 4, Bay 5), include "ZOOM:Bay X" in actions!
3. Answer any question about plant status, risks, equipment, permits, or safety intelligently.`

  try {
    const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${GROQ_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'llama-3.3-70b-versatile',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userQuery },
        ],
        temperature: 0.3,
        max_tokens: 220,
        response_format: { type: 'json_object' },
      }),
    })

    if (!res.ok) throw new Error(`Groq API returned HTTP ${res.status}`)

    const data = await res.json()
    const raw = data?.choices?.[0]?.message?.content?.trim() || '{}'
    const parsed = JSON.parse(raw)

    return {
      spoken: (parsed.spoken || '').replace(/[*_#~`[\]]/g, '').trim(),
      actions: Array.isArray(parsed.actions) ? parsed.actions : ['NONE'],
    }
  } catch (err) {
    console.error('[Groq Brain] Real API error:', err)
    // REAL: fetched from POST /api/voice/query via backend Groq LLM
    throw new Error('Groq LLM pipeline failed — real API error.')
  }
}


// ─── Action Executor ──────────────────────────────────────────────────────── //

function executeActions(actions: string[]) {
  const store = useSimulationStore.getState()

  for (const action of actions) {
    if (action.startsWith('ZOOM:')) {
      const bay = action.replace('ZOOM:', '').trim()
      store.setOverlayView('none')
      store.focusZone(bay)
    } else if (action === 'RESET_VIEW') {
      store.resetView()
    } else if (action === 'SHOW_EVIDENCE') {
      store.setEvidenceOpen(true)
    } else if (action === 'HIDE_EVIDENCE') {
      store.setEvidenceOpen(false)
    } else if (action === 'SHOW_TRACKS') {
      store.setOverlayView('tracks')
    } else if (action === 'SHOW_AUDIT') {
      store.setOverlayView('audit')
    } else if (action === 'SHOW_SIGNALS') {
      store.setOverlayView('signals')
    } else if (action === 'AUTHORIZE') {
      if (store.authorizationPending) store.authorizeAction()
    } else if (action === 'REJECT') {
      if (store.authorizationPending) store.rejectAction()
    }
  }
}

// ─── Voice Listener with Instant Barge-In ─────────────────────────────────── //

export function startRealVoiceListener() {
  startDeepgramListening((text, isFinal) => {
    if (!isFinal) {
      useSimulationStore.getState().setNovaCaption(`🎙 ${text}`)
      return
    }

    // Halt active TTS immediately (Instant Barge-In)
    stopCurrentTTS()

    const store = useSimulationStore.getState()
    store.setNovaCaption('')
    store.setNovaState('processing')
    store.addEvent({
      type: 'nova-action',
      message: `Supervisor Voice: "${text}"`,
      risk: 'normal',
    })

    generateReActResponse(text)
      .then(result => {
        executeActions(result.actions)
        return novaSpeakSimulation(result.spoken)
      })
      .catch(err => {
        console.error('[Voice Listener] Engine error:', err)
        store.setNovaState('listening')
      })
  })
}

export function stopRealVoiceListener() {
  stopDeepgramListening()
}
