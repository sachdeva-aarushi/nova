/**
 * frontend/src/services/websocket.ts
 *
 * CaseWebSocket — native WebSocket wrapper with typed message envelopes,
 * exponential-backoff auto-reconnect (max 5 retries), and status callbacks.
 *
 * No `any`. All message parsing is done through WsEnvelope discriminated union.
 */
import type { WsEnvelope, WsStatus } from '../types/api'

type MessageHandler = (msg: WsEnvelope) => void
type StatusHandler = (status: WsStatus) => void

export const getWsUrl = (sessionId: string): string => {
  let rawWs = (import.meta.env.VITE_WS_URL as string | undefined)?.replace(/\/+$/, '')
  if (rawWs) {
    if (rawWs.includes('/ws/session')) return `${rawWs}/${sessionId}`
    return `${rawWs}/ws/session/${sessionId}`
  }

  const apiEnv = (import.meta.env.VITE_API_URL as string | undefined) || (import.meta.env.VITE_API_BASE_URL as string | undefined)
  if (apiEnv && /^https?:\/\//i.test(apiEnv)) {
    const wsProtocol = apiEnv.startsWith('https') ? 'wss:' : 'ws:'
    const host = apiEnv.replace(/^https?:\/\//i, '').replace(/\/+$/, '')
    return `${wsProtocol}//${host}/ws/session/${sessionId}`
  }

  if (import.meta.env.VITE_WS_HOST) {
    const host = import.meta.env.VITE_WS_HOST as string
    const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${host}/ws/session/${sessionId}`
  }

  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost') {
    return `wss://nova-2-z63a.onrender.com/ws/session/${sessionId}`
  }

  return `ws://localhost:8000/ws/session/${sessionId}`
}

const MAX_RETRIES = 5
const BASE_DELAY_MS = 1_000

function isWsEnvelope(raw: unknown): raw is WsEnvelope {
  return (
    typeof raw === 'object' &&
    raw !== null &&
    'type' in raw &&
    typeof (raw as Record<string, unknown>).type === 'string'
  )
}

export class CaseWebSocket {
  private readonly sessionId: string
  private ws: WebSocket | null = null
  private messageHandlers: MessageHandler[] = []
  private statusHandlers: StatusHandler[] = []
  private retryCount = 0
  private retryTimer: ReturnType<typeof setTimeout> | null = null
  private intentionalClose = false

  constructor(sessionId: string) {
    this.sessionId = sessionId
  }

  // ── Public API ──────────────────────────────────────────────────────── //

  connect(): void {
    this.intentionalClose = false
    this._open()
  }

  disconnect(): void {
    this.intentionalClose = true
    this._clearRetryTimer()
    this.ws?.close()
    this.ws = null
  }

  onMessage(handler: MessageHandler): void {
    this.messageHandlers.push(handler)
  }

  onStatus(handler: StatusHandler): void {
    this.statusHandlers.push(handler)
  }

  // ── Internal ────────────────────────────────────────────────────────── //

  private _open(): void {
    const url = getWsUrl(this.sessionId)
    const ws = new WebSocket(url)
    this.ws = ws

    ws.onopen = () => {
      this.retryCount = 0
      this._emitStatus('connected')
    }

    ws.onmessage = (event: MessageEvent<string>) => {
      let parsed: unknown
      try {
        parsed = JSON.parse(event.data) as unknown
      } catch {
        console.warn('[CaseWebSocket] non-JSON message received')
        return
      }
      if (isWsEnvelope(parsed)) {
        this.messageHandlers.forEach((h) => h(parsed as WsEnvelope))
      }
    }

    ws.onerror = () => {
      // onerror always precedes onclose — let onclose handle reconnect
    }

    ws.onclose = () => {
      if (this.intentionalClose) return
      this._scheduleReconnect()
    }
  }

  private _scheduleReconnect(): void {
    if (this.retryCount >= MAX_RETRIES) {
      this._emitStatus('disconnected')
      return
    }
    this._emitStatus('reconnecting')
    const delay = BASE_DELAY_MS * 2 ** this.retryCount
    this.retryCount += 1
    this.retryTimer = setTimeout(() => {
      this._open()
    }, delay)
  }

  private _clearRetryTimer(): void {
    if (this.retryTimer !== null) {
      clearTimeout(this.retryTimer)
      this.retryTimer = null
    }
  }

  private _emitStatus(status: WsStatus): void {
    this.statusHandlers.forEach((h) => h(status))
  }
}
