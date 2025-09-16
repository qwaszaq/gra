import React, { useState, useRef, useEffect } from 'react'
import { useWebSocket } from './useWebSocket'
import type { ServerMsg, ClientAction } from './types'
import CaseBoard from './CaseBoard'
import Gallery from './Gallery'

const TITLE = "Partnerzy w Zbrodni - WEB"

export default function App() {
  // WebSocket state
  const [wsUrl, setWsUrl] = useState('ws://localhost:65432/ws')
  const [player, setPlayer] = useState('Marlow')
  const [sessionId, setSessionId] = useState('demo-1')
  const [singlePlayer, setSinglePlayer] = useState(true)
  const [showGallery, setShowGallery] = useState(false)

  // Game state
  const [turn, setTurn] = useState(0)
  const [currentNarration, setCurrentNarration] = useState('')
  const [currentImage, setCurrentImage] = useState('')
  const [text, setText] = useState('')
  const [logs, setLogs] = useState<string[]>([])
  const [whispers, setWhispers] = useState<string[]>([])
  const [metrics, setMetrics] = useState<{time:number, suspicion:number, reputation:number}>({time:20,suspicion:0,reputation:0})
  const [shot, setShot] = useState<string|undefined>(undefined)
  const [reframed, setReframed] = useState<{from?:string,to?:string}|null>(null)
  const [inventory, setInventory] = useState<any>({})
  const [location, setLocation] = useState<string>('office')
  const [relations, setRelations] = useState<any>({})
  const [sfxEnabled, setSfxEnabled] = useState(true)
  const [caseGraph, setCaseGraph] = useState<{nodes:any[], edges:any[]}>({nodes:[], edges:[]})
  const [showBoard, setShowBoard] = useState(false)
  const [verdict, setVerdict] = useState<{verdict?:string, epilogue?:string}|null>(null)

  // Audio controls
  const [voiceEnabled, setVoiceEnabled] = useState(true)
  const [musicEnabled, setMusicEnabled] = useState(true)
  const [backgroundMusicEnabled, setBackgroundMusicEnabled] = useState(true)

  // audio refs
  const voiceRef = useRef<HTMLAudioElement|null>(null)
  const musicRef = useRef<HTMLAudioElement|null>(null)
  const sfxRef = useRef<HTMLAudioElement|null>(null)
  const sfxQueue = useRef<string[]>([])
  const sfxPlaying = useRef(false)
  const backgroundMusicRef = useRef<HTMLAudioElement|null>(null)

  const { connect, disconnect, connected, sendAction, onMessage, sendRaw } = useWebSocket(wsUrl)

  const connectionLabel = connected ? 'Połączony' : 'Rozłączony'

  const playSfxQueue = (urls: string[]) => {
    if (!sfxEnabled || !urls?.length) return
    sfxQueue.current.push(...urls)
    const playNext = () => {
      if (!sfxEnabled) { sfxQueue.current = []; sfxPlaying.current = false; return }
      const url = sfxQueue.current.shift()
      if (!url) { sfxPlaying.current = false; return }
      if (sfxRef.current) {
        sfxRef.current.src = url
        sfxRef.current.currentTime = 0
        sfxRef.current.onended = () => playNext()
        sfxRef.current.onerror = () => playNext()
        sfxPlaying.current = true
        sfxRef.current.play().catch(()=> playNext())
      }
    }
    if (!sfxPlaying.current) playNext()
  }

  useEffect(() => {
    if (connected) {
      pushLog(`Połączono z ${wsUrl}`)
    } else {
      pushLog('Rozłączono')
    }
  }, [connected, wsUrl])

  // Start background music on component mount
  useEffect(() => {
    const startBackgroundMusic = () => {
      if (backgroundMusicRef.current && backgroundMusicEnabled) {
        backgroundMusicRef.current.volume = 0.3 // 30% volume
        backgroundMusicRef.current.loop = true
        backgroundMusicRef.current.play().catch(console.error)
      }
    }

    // Start music after a short delay to ensure user interaction
    const timer = setTimeout(startBackgroundMusic, 1000)
    return () => clearTimeout(timer)
  }, [backgroundMusicEnabled])

  // Control background music
  useEffect(() => {
    if (backgroundMusicRef.current) {
      if (backgroundMusicEnabled) {
        backgroundMusicRef.current.play().catch(console.error)
      } else {
        backgroundMusicRef.current.pause()
      }
    }
  }, [backgroundMusicEnabled])

  const pushLog = (msg: string) => {
    setLogs(prev => [...prev.slice(-9), `${new Date().toLocaleTimeString()}: ${msg}`])
  }

  const connectNow = () => {
    connect(player, sessionId, singlePlayer)
    onMessage(handleMessage)
  }

  const disconnectNow = () => {
    disconnect()
  }

  const sendNow = () => {
    if (!connected || !text.trim()) return
    const action: ClientAction = {
      type: 'action',
      player,
      session_id: sessionId,
      turn_id: turn,
      text_raw: text.trim()
    }
    sendAction(action)
    setText('')
  }

  const handleMessage = (msg: ServerMsg) => {
    console.log('Received:', msg)
    
    switch (msg.type) {
      case 'info':
        pushLog(`INFO: ${msg.message}`)
        break
      case 'error':
        pushLog(`ERROR: ${(msg as any).message || (msg as any).reason || 'undefined'}`)
        break
      case 'story_update':
        applyStoryUpdate(msg)
        break
      case 'image_update':
        console.log('[DEBUG] Handling image_update')
        applyImageUpdate(msg)
        break
      case 'graph_update':
        const delta = (msg as any).graph_delta
        setCaseGraph((g:any)=> ({
          nodes: [...(g.nodes||[]), ...(delta?.nodes_add || [])],
          edges: [...(g.edges||[]), ...(delta?.edges_add || [])]
        }))
        return
      case 'verdict_update':
        const m = msg as any
        setVerdict({verdict: m.verdict, epilogue: m.epilogue})
        if (m.sfx?.length) playSfxQueue(m.sfx as string[])
        return
      case 'narrative_update':
        applyNarrative(msg)
        break
      case 'override_update':
        applyOverride(msg)
        break
    }
  }

  const applyStoryUpdate = (s: any) => {
    setTurn(s.turn_id)
    setCurrentNarration(s.text || '')
    setWhispers(Array.isArray(s.whispers)? s.whispers : [])
    if (s.metrics) setMetrics(s.metrics)
    if (s.image) setCurrentImage(s.image)
    if (s.voice_audio) playVoice(s.voice_audio)
    if (s.music) playMusic(s.music)
    setShot(s.shot)
    
    if (s.reframed) {
      setReframed({ from: s.reframed_from, to: s.reframed_to })
    } else {
      setReframed(null)
    }
    
    if ((s as any).inventory) setInventory((s as any).inventory)
    if ((s as any).location) setLocation((s as any).location)
    if ((s as any).relations) setRelations((s as any).relations)
    if ((s as any).sfx) playSfxQueue((s as any).sfx as string[])
    
    pushLog(`TURN ${s.turn_id}: ${s.text?.slice(0, 140) || ''}...`)
  }

  const applyImageUpdate = (msg: any) => {
    const url = msg.image
    console.log('[DEBUG] applyImageUpdate called with:', msg)
    console.log('[DEBUG] Current image before swap:', currentImage)
    
    if (url) {
      console.log('[DEBUG] Setting new image to:', url)
      const imgEl = document.querySelector('.scene-image img') as HTMLImageElement | null
      if (imgEl) {
        console.log('[DEBUG] Found img element, starting fade transition')
        imgEl.classList.add('fading')
        setTimeout(()=> {
          console.log('[DEBUG] Setting new image after fade')
          setCurrentImage(url)
          setTimeout(()=> {
            console.log('[DEBUG] Removing fade class')
            imgEl?.classList.remove('fading')
          }, 50)
        }, 200)
      } else {
        console.log('[DEBUG] No img element found, setting directly')
        setCurrentImage(url)
      }
      pushLog(`[SWAP] image_update -> ${url}`)
    } else {
      console.log('[DEBUG] No URL provided in image_update')
    }
  }

  const applyNarrative = (n: any) => {
    setTurn(n.turn_id)
    setCurrentNarration(n.text || '')
    if (n.image) setCurrentImage(n.image)
    if (n.voice_audio) playVoice(n.voice_audio)
    if (n.music) playMusic(n.music)
    pushLog(`TURN ${n.turn_id}: ${n.text?.slice(0, 140) || ''}...`)
  }

  const applyOverride = (o: any) => {
    if (o.text) {
      setCurrentNarration(o.text)
      pushLog(`[OVERRIDE] text: ${o.text.slice(0, 140)}...`)
    }
    if (o.image) {
      setCurrentImage(o.image)
      pushLog(`[OVERRIDE] image: ${o.image}`)
    }
    if (o.voice_audio) {
      playVoice(o.voice_audio)
      pushLog(`[OVERRIDE] voice: ${o.voice_audio}`)
    }
    if (o.music) {
      playMusic(o.music)
      pushLog(`[OVERRIDE] music: ${o.music}`)
    }
  }

  const playVoice = (url: string) => {
    if (!voiceEnabled || !voiceRef.current) return
    voiceRef.current.src = url
    voiceRef.current.play().catch(console.error)
  }

  const playMusic = (url: string) => {
    if (!musicEnabled || !musicRef.current) return
    musicRef.current.src = url
    musicRef.current.play().catch(console.error)
  }

  return (
    <div className="noir-app">
      {/* Background with rain effect */}
      <div className="rain-background">
        <div className="neon-lights"></div>
      </div>

      {/* Header */}
      <header className="noir-header">
        <h1 className="game-title">{TITLE}</h1>
        
        <div className="connection-info">
          <div className="connection-field">
            <label>WS URL:</label>
            <input 
              data-testid="ws-url" 
              value={wsUrl} 
              onChange={e => setWsUrl(e.target.value)}
              className="connection-input"
            />
          </div>
          
          <div className="connection-field">
            <label>Kryptonim:</label>
            <input 
              data-testid="player" 
              value={player} 
              onChange={e => setPlayer(e.target.value)}
              className="connection-input"
            />
          </div>
          
          <div className="connection-field">
            <label>Session ID:</label>
            <input 
              data-testid="session-id" 
              value={sessionId} 
              onChange={e => setSessionId(e.target.value)}
              className="connection-input"
            />
            <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}></div>
          </div>
        </div>

        <div className="header-controls">
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              data-testid="single-player-checkbox"
              checked={singlePlayer} 
              onChange={e => setSinglePlayer(e.target.checked)} 
            />
            Single Player
          </label>
          
          <label className="checkbox-label">
            <input 
              type="checkbox" 
              checked={backgroundMusicEnabled} 
              onChange={e => setBackgroundMusicEnabled(e.target.checked)} 
            />
            Muzyka w tle
          </label>
          
          <button 
            className="gallery-btn"
            onClick={() => setShowGallery(!showGallery)}
          >
            {showGallery ? 'Ukryj galerię' : 'Pokaż galerię'}
          </button>
          
          <button onClick={()=> setShowBoard(s=>!s)}>{showBoard ? 'Ukryj Case Board' : 'Pokaż Case Board'}</button>
          {!connected ? (
            <button data-testid="connect-btn" onClick={connectNow} className="connect-btn">
              Połącz
            </button>
          ) : (
            <button onClick={disconnectNow} className="disconnect-btn">
              Rozłącz
            </button>
          )}
        </div>
      </header>

      {/* Main Game Area */}
      <main className="game-area">
        <div className="dialog-window">
          <div className="dialog-header">
            <h2 className="turn-title">TURA: {turn}</h2>
            <label className="checkbox-label">
              <input 
                type="checkbox" 
                checked={voiceEnabled} 
                onChange={e => setVoiceEnabled(e.target.checked)} 
              />
              Głos narratora
            </label>
          </div>
          
          <div className="dialog-content">
            {reframed && (
              <div style={{background:'rgba(229,9,20,.08)', border:'1px solid #e50914', color:'#e50914', padding:8, borderRadius:6, marginBottom:8}}>
                Zreinterpretowano wejście: „{reframed.from}” → „{reframed.to}”
              </div>
            )}
            <div className="narration-text">
              {currentNarration || 'Czekam na narrację...'}
            </div>
            
            <div className="scene-image">
              <img src={currentImage || 'http://localhost:8004/assets/images/case_zero/turn1.png'} alt="scene" />
              {shot && <div className="shot-badge">{shot}</div>}
            </div>
          </div>
          
          {/* Toggle SFX */}
          <div style={{display:'flex', gap:16, alignItems:'center', margin:'6px 0 10px'}}>
            <label><input type="checkbox" checked={sfxEnabled} onChange={e=>setSfxEnabled(e.target.checked)} /> Efekty SFX</label>
          </div>

          {/* Panel NPC */}
          {Object.keys(relations || {}).length > 0 && (
            <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(220px,1fr))', gap:12, margin:'8px 0'}}>
              {Object.entries(relations).map(([name, r]: any) => (
                <div key={name} style={{background:'rgba(255,255,255,.04)', padding:8, borderRadius:6}}>
                  <div style={{fontWeight:700, marginBottom:6}}>{name}</div>
                  <div style={{fontSize:13}}>Nastrój: <b>{r.mood}</b></div>
                  <div style={{fontSize:13}}>Zaufanie: <b>{r.trust}</b></div>
                  <div style={{fontSize:13}}>Strach: <b>{r.fear}</b></div>
                </div>
              ))}
            </div>
          )}
          
          {/* Chip'y stanu */}
          <div style={{display:'flex', gap:12, margin:'8px 0', fontSize:13}}>
            <div>📍 {location}</div>
            <div>🔫 {inventory.pistol_loaded ? 'Magazynek pełny' : 'Pusty'} ({inventory.ammo ?? 0})</div>
            <div>🚬 {inventory.cigarettes ?? 0}</div>
          </div>

          {/* HUD metryk */}
          <div style={{display:'flex', gap:12, margin:'8px 0'}}>
            <div>🕒 Czas: <b data-testid="m-time">{metrics.time}</b></div>
            <div>👁 Podejrzenie: <b data-testid="m-susp">{metrics.suspicion}</b></div>
            <div>🤝 Reputacja: <b data-testid="m-rep">{metrics.reputation}</b></div>
          </div>

          {/* Podszepty */}
          {whispers.length > 0 && (
            <div>
              <div style={{fontSize:12, opacity:.7, marginBottom:4}}>Podszepty:</div>
              <ul data-testid="whispers-list" style={{marginTop:0}}>
                {whispers.map((w,i)=>(<li key={i}>{w}</li>))}
              </ul>
            </div>
          )}
          
          <div className="action-input">
            <input
              data-testid="action-input"
              placeholder="Wpisz swoją akcję (np. Przesłuchuję świadka)"
              value={text}
              onChange={e => setText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' ? sendNow() : undefined}
              className="action-field"
            />
            <button 
              data-testid="send-btn" 
              onClick={sendNow} 
              disabled={!connected}
              className="send-btn"
            >
              ⚛
            </button>
          </div>
        </div>
      </main>

      {/* Gallery */}
      {showGallery && (
        <section className="gallery-section">
          <Gallery />
        </section>
      )}

      {showBoard && (
        <section className="log">
          <h3>Case Board</h3>
          <CaseBoard graph={caseGraph as any} onLink={(from,to,rel)=> {
            sendRaw({ type: 'link', player, session_id: sessionId, from, to, relation: rel })
          }} />
          <button onClick={()=> {
            const suspect = prompt('Kogo oskarżasz? (label podejrzanego)')
            if (suspect) sendRaw({ type:'accuse', player, session_id: sessionId, suspect })
          }}>Oskarż</button>
        </section>
      )}

      {/* Logs */}
      <section className="logs-section">
        <h3>Log</h3>
        <div className="logs-content">
          {logs.map((log, i) => (
            <div key={i} className="log-entry">{log}</div>
          ))}
        </div>
      </section>

      {/* Audio elements */}
      <audio data-testid="voice-audio" ref={voiceRef} preload="auto" />
      <audio data-testid="music-audio" ref={musicRef} preload="auto" />
      <audio data-testid="sfx-audio" ref={sfxRef} preload="auto" />

      {/* Verdict Modal */}
      {verdict && (
        <div style={{position:'fixed', inset:0, background:'rgba(0,0,0,.6)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:9999}}>
          <div style={{background:'#111', padding:16, border:'1px solid #333', maxWidth:700}}>
            <h3>Werdykt: {verdict.verdict}</h3>
            <p style={{whiteSpace:'pre-wrap'}}>{verdict.epilogue}</p>
            <button onClick={()=> setVerdict(null)}>Zamknij</button>
          </div>
        </div>
      )}
      <audio 
        ref={backgroundMusicRef} 
        preload="auto"
        src="/Shadows in the Rain.mp3"
        loop
      />
    </div>
  )
}