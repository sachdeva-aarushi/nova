/**
 * frontend/src/hooks/useRimeAudio.ts
 *
 * Connects to WS /ws/audio/{case_id} and plays binary audio chunks.
 * Handles barge-in: when speaking and mic detects audio → call POST /api/voice/cancel.
 *
 * Usage:
 *   const { isPlaying, bargeIn } = useRimeAudio(caseId)
 */
import { getApiUrl } from '../services/api'

const getWsAudioBase = (): string => {
  if (import.meta.env.VITE_WS_URL) {
    return (import.meta.env.VITE_WS_URL as string).replace(/\/+$/, '')
  }
  const apiEnv = (import.meta.env.VITE_API_URL as string | undefined) || (import.meta.env.VITE_API_BASE_URL as string | undefined)
  if (apiEnv && /^https?:\/\//i.test(apiEnv)) {
    const wsProtocol = apiEnv.startsWith('https') ? 'wss:' : 'ws:'
    const host = apiEnv.replace(/^https?:\/\//i, '').replace(/\/+$/, '')
    return `${wsProtocol}//${host}`
  }
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost') {
    return 'wss://nova-2-z63a.onrender.com'
  }
  return 'ws://localhost:8000'
}

export interface UseRimeAudioOptions {
  caseId?: string | null
  onCaption?: (text: string) => void
  onAudioEnd?: () => void
}

export interface UseRimeAudioReturn {
  isPlaying: boolean
  isSpeaking: boolean
  caption: string
  bargeIn: () => Promise<void>
}

export function useRimeAudio(
  optsOrId: string | UseRimeAudioOptions | null
): UseRimeAudioReturn {
  const caseId = typeof optsOrId === 'string' || optsOrId === null ? optsOrId : optsOrId?.caseId ?? null
  const onCaption = typeof optsOrId === 'object' && optsOrId !== null ? optsOrId.onCaption : undefined
  const onAudioEnd = typeof optsOrId === 'object' && optsOrId !== null ? optsOrId.onAudioEnd : undefined

  const [isPlaying, setIsPlaying] = useState(false)
  const [caption, setCaption] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const sourceQueueRef = useRef<AudioBuffer[]>([])
  const playingRef = useRef(false)
  const scheduledAtRef = useRef(0)
  const activeSourcesRef = useRef(0)
  const rimeTimeoutRef = useRef<any>(null)

  // Get/init AudioContext
  const getAudioCtx = useCallback(() => {
    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      audioCtxRef.current = new AudioContext({ sampleRate: 22050 })
    }
    return audioCtxRef.current
  }, [])

  // Decode and schedule a chunk
  const scheduleChunk = useCallback(async (data: ArrayBuffer) => {
    try {
      const ctx = getAudioCtx()
      if (ctx.state === 'suspended') await ctx.resume()

      const buffer = await ctx.decodeAudioData(data)
      const now = ctx.currentTime
      const startAt = Math.max(scheduledAtRef.current, now)

      const source = ctx.createBufferSource()
      source.buffer = buffer
      source.connect(ctx.destination)
      source.start(startAt)

      scheduledAtRef.current = startAt + buffer.duration
      setIsPlaying(true)
      playingRef.current = true
      ;(window as any)._isRimeSpeaking = true

      activeSourcesRef.current = (activeSourcesRef.current || 0) + 1

      source.onended = () => {
        activeSourcesRef.current = Math.max(0, (activeSourcesRef.current || 1) - 1)
        if (activeSourcesRef.current === 0) {
          setIsPlaying(false)
          playingRef.current = false
          ;(window as any)._isRimeSpeaking = false
          onAudioEnd?.()
        }
      }

      // Safety fallback timer to guarantee _isRimeSpeaking is cleared
      if (rimeTimeoutRef.current) clearTimeout(rimeTimeoutRef.current)
      const dur = Math.max(1, (scheduledAtRef.current - ctx.currentTime) * 1000)
      rimeTimeoutRef.current = setTimeout(() => {
        activeSourcesRef.current = 0
        setIsPlaying(false)
        playingRef.current = false
        ;(window as any)._isRimeSpeaking = false
        onAudioEnd?.()
      }, dur + 500)
    } catch (err) {
      console.warn('[useRimeAudio] Decode error:', err)
      ;(window as any)._isRimeSpeaking = false
    }
  }, [getAudioCtx, onAudioEnd])

  // Connect WS audio socket
  useEffect(() => {
    if (!caseId) return

    const ws = new WebSocket(`${getWsAudioBase()}/ws/audio/${caseId}`)
    ws.binaryType = 'arraybuffer'
    wsRef.current = ws

    ws.onopen = () => {
      console.log('[useRimeAudio] Connected to audio stream:', caseId)
    }

    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        scheduleChunk(event.data)
      } else if (typeof event.data === 'string') {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'caption' || msg.caption || msg.text) {
            const text = msg.caption || msg.text || ''
            setCaption(text)
            onCaption?.(text)
          }
          if (msg.type === 'audio.stream_end') {
            // Stream complete
          } else if (msg.type === 'audio.cancelled') {
            // Cancel all pending audio
            scheduledAtRef.current = getAudioCtx().currentTime
            setIsPlaying(false)
            playingRef.current = false
          }
        } catch { /* ignore */ }
      }
    }

    ws.onclose = () => {
      console.log('[useRimeAudio] WS closed:', caseId)
    }

    ws.onerror = (err) => {
      console.warn('[useRimeAudio] WS error:', err)
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [caseId, scheduleChunk, getAudioCtx, onCaption])

  // Barge-in handler
  const bargeIn = useCallback(async () => {
    if (!caseId) return
    try {
      // Stop scheduled audio immediately
      scheduledAtRef.current = getAudioCtx().currentTime
      setIsPlaying(false)
      playingRef.current = false

      // Tell backend to cancel synthesis
      await fetch(getApiUrl('/api/voice/cancel'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: caseId }),
      })
    } catch (err) {
      console.warn('[useRimeAudio] Barge-in error:', err)
    }
  }, [caseId, getAudioCtx])

  return { isPlaying, isSpeaking: isPlaying, caption, bargeIn }
}
