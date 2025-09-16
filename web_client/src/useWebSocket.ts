import { useRef, useState, useCallback } from 'react'
import type { ServerMsg, ClientAction } from './types'

export function useWebSocket(wsUrl: string) {
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)

  const connect = useCallback((player: string, sessionId: string, singlePlayer: boolean = false) => {
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return
    }
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      const login = { type: 'login', player, session_id: sessionId, single_player: singlePlayer, bot_style: 'ostrożny śledczy' }
      ws.send(JSON.stringify(login))
    }
    ws.onclose = () => { setConnected(false) }
    ws.onerror = () => { /* błędy ignorujemy tutaj; obsłuż w onmessage jeśli przyjdzie 'error' */ }

    return () => {
      ws.close()
      wsRef.current = null
      setConnected(false)
    }
  }, [wsUrl])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setConnected(false)
  }, [])

  const sendAction = useCallback((payload: ClientAction) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify(payload))
  }, [])

  const onMessage = useCallback((handler: (msg: ServerMsg) => void) => {
    if (!wsRef.current) return
    wsRef.current.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as ServerMsg
        handler(data)
      } catch {
        // ignore malformed
      }
    }
  }, [])

  const sendRaw = useCallback((payload:any) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify(payload))
  }, [])

  return { connect, disconnect, connected, sendAction, onMessage, sendRaw }
}
