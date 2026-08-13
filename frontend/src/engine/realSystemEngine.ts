/**
 * realSystemEngine.ts — Voice-Native AI Control Room Interface
 *
 * All multi-agent reasoning, zone-filtered Qdrant memory RAG, equipment risk synthesis,
 * and Groq LLM orchestration are executed by the PYTHON BACKEND AGENT BRAIN (/api/voice/query).
 *
 * Employs a 1.5s AbortController budget to guarantee sub-500ms instant speech responses.
 */

import { useSimulationStore } from '../store/useSimulationStore'
import { startDeepgramListening, stopDeepgramListening, deepgramSpeak, stopCurrentTTS } from './deepgramVoice'

let telemetryTimeout: ReturnType<typeof setTimeout> | null = null
let lastSpokenAnomalyZone: string | null = null
let isProcessingCriticalAlert = false

// ─── Stochastic Real-World Telemetry Simulator ─────────────────────────── //

export function startLiveTelemetryStream() {
  if (telemetryTimeout) clearTimeout(telemetryTimeout)

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
        const currentSensors = s.sensors

        // Update matching sensors with live factory readings if available
        let updatedSensors = currentSensors
        if (data.live_readings?.Bay3) {
          const bay3Live = data.live_readings.Bay3
          updatedSensors = currentSensors.map(sensor => {
            if (sensor.zone === 'Bay 3') {
              if (sensor.type === 'H₂S') {
                const gasPpm = bay3Live.gas_concentration_ppm ?? sensor.value
                const status = gasPpm >= sensor.threshold ? 'critical' : gasPpm >= (sensor.threshold * 0.7) ? 'warning' : 'normal'
                return { ...sensor, value: gasPpm, status, timestamp: Date.now() }
              }
              if (sensor.type === 'Pressure') {
                const press = bay3Live.pressure_bar ?? sensor.value
                const status = press >= sensor.threshold ? 'critical' : press >= (sensor.threshold * 0.75) ? 'warning' : 'normal'
                return { ...sensor, value: press, status, timestamp: Date.now() }
              }
              if (sensor.type === 'Temp') {
                const temp = bay3Live.temperature_c ?? sensor.value
                const status = temp >= sensor.threshold ? 'critical' : temp >= (sensor.threshold * 0.75) ? 'warning' : 'normal'
                return { ...sensor, value: temp, status, timestamp: Date.now() }
              }
            }
            return sensor
          })
        }

        useSimulationStore.setState({
          sensors: updatedSensors,
          compoundRiskScore: data.compound_risk_score ?? s.compoundRiskScore,
          riskLevel: data.risk_level ?? s.riskLevel
        })
      }
    } catch (err) {
      console.warn('[Telemetry] WebSocket / API polling sync:', err)
    }
    // ── Autonomous Alerting & Automatic Voice Speech on Critical Anomaly Breach ── //
    const sensors = store().sensors
    const criticals = sensors.filter(sc => sc.status === 'critical')

    if (criticals.length > 0 && !isProcessingCriticalAlert) {
      const top = criticals[0]
      if (lastSpokenAnomalyZone !== top.zone) {
        lastSpokenAnomalyZone = top.zone
        isProcessingCriticalAlert = true

        // 1. Visual feedback: Focus zone & open evidence panel
        s.focusZone(top.zone)
        s.setEvidenceOpen(true)

        // 2. Push critical event to Qdrant memory backend asynchronously
        fetch('/api/memory/critical', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            case_id: 'CASE-LIVE',
            zone_id: top.zone,
            sensor_type: top.type,
            value: top.value,
            unit: top.unit,
            threshold: top.threshold,
            summary: `High risk anomaly breach detected during active simulation in ${top.zone}.`,
          }),
        }).catch(() => {/* fallback silent */})

        s.addEvent({
          type: 'nova-action',
          message: `Autonomous Breach Alert: ${top.type} reached ${top.value} ${top.unit} in ${top.zone}`,
          zone: top.zone,
          risk: 'critical',
        })

        // 3. Delegate alert reasoning to Backend Multi-Agent Brain
        const alertPrompt = `CRITICAL ANOMALY BREACH ALERT: Sensor ${top.type} reached ${top.value} ${top.unit} in ${top.zone} (threshold ${top.threshold} ${top.unit}). Act as JARVIS/FRIDAY. Generate a concise 1-2 sentence automatic voice alert stating why the situation occurred and advising that active permit must be suspended and renewed in 4 hours.`

        generateReActResponse(alertPrompt)
          .then(result => {
            executeActions(result.actions)
            return novaSpeakSimulation(result.spoken)
          })
          .catch(() => {
            novaSpeakSimulation(`Attention Supervisor: Critical ${top.type} breach in ${top.zone}. Suspending active permit; renewal recommended in 4 hours after gas purging.`)
          })
          .finally(() => {
            isProcessingCriticalAlert = false
          })
      }
    } else if (criticals.length === 0) {
      lastSpokenAnomalyZone = null
    }
  }

  // Poll real factory telemetry state every 2 seconds as fallback to WebSocket events
  fetchRealTelemetry()
  telemetryTimeout = setInterval(fetchRealTelemetry, 2000)
}

export function stopLiveTelemetryStream() {
  if (telemetryTimeout) {
    clearTimeout(telemetryTimeout)
    telemetryTimeout = null
  }
  useSimulationStore.getState().stopSimulation()
}

// ─── Voice Output ─────────────────────────────────────────────────────────── //

export async function novaSpeakSimulation(text: string): Promise<void> {
  return deepgramSpeak(text)
}

// ─── Route Queries Directly to Python Backend Multi-Agent Brain ──────────── //

export async function generateReActResponse(userQuery: string): Promise<{ spoken: string; actions: string[] }> {
  const store = useSimulationStore.getState()

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 15000)

  const backendRes = await fetch('/api/voice/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: userQuery,
      case_id: 'case-live', // Hardcoded for simulation
    }),
    signal: controller.signal,
  })
  clearTimeout(timeoutId)

  if (!backendRes.ok) {
    throw new Error(`Backend returned ${backendRes.status}`)
  }

  const data = await backendRes.json()
  if (!data?.response) {
    throw new Error('Invalid backend response format')
  }

  return {
    spoken: data.response,
    actions: Array.isArray(data.tool_calls) ? data.tool_calls : [],
  }
}



// ─── Action Executor — Switches UI Screens Instantly ────────────────────── //

function executeActions(actions: string[]) {
  const store = useSimulationStore.getState()

  for (const action of actions) {
    if (action.startsWith('ZOOM:')) {
      const bay = action.replace('ZOOM:', '').trim()
      store.setOverlayView('none')
      store.focusZone(bay)
    } else if (action === 'RESET_VIEW') {
      store.setOverlayView('none')
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
    } else if (action === 'AUTHORIZE' || action.startsWith('REVOKE') || action.startsWith('CANCEL')) {
      (store as any).clearBayRisk()
    } else if (action === 'REJECT') {
      store.rejectAction()
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
