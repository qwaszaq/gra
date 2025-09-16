// web_client/src/CaseBoard.tsx
import React, { useMemo, useState } from 'react'

type Node = { id:string; type:'clue'|'suspect'|'location'|'witness'; label:string }
type Edge = { from:string; to:string; label:string; confidence:number }
type Graph = { nodes: Node[]; edges: Edge[] }

export default function CaseBoard({ graph, onLink }: { graph: Graph, onLink: (fromLabel:string, toLabel:string, relation:string)=>void }) {
  const [from, setFrom] = useState<string>(''); const [to, setTo] = useState<string>(''); const [rel, setRel] = useState<string>('implies')

  const clues    = useMemo(()=> (graph?.nodes||[]).filter(n=> n.type==='clue'), [graph])
  const suspects = useMemo(()=> (graph?.nodes||[]).filter(n=> n.type==='suspect' || n.type==='witness'), [graph])
  const locs     = useMemo(()=> (graph?.nodes||[]).filter(n=> n.type==='location'), [graph])

  return (
    <div style={{display:'grid', gridTemplateColumns:'2fr 1fr', gap:16}}>
      <div>
        <div style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:12}}>
          <div>
            <h4>Clues</h4>
            <ul>{clues.map(n=> <li key={n.id}>{n.label}</li>)}</ul>
          </div>
          <div>
            <h4>Suspects/Witnesses</h4>
            <ul>{suspects.map(n=> <li key={n.id}>{n.label}</li>)}</ul>
          </div>
          <div>
            <h4>Locations</h4>
            <ul>{locs.map(n=> <li key={n.id}>{n.label}</li>)}</ul>
          </div>
        </div>

        <h4 style={{marginTop:16}}>Edges</h4>
        <ul>
          {(graph?.edges||[]).map((e, i)=> <li key={i}>{e.label}: {e.from} → {e.to} ({Math.round(e.confidence*100)}%)</li>)}
        </ul>
      </div>

      <div>
        <h4>Szybkie łączenie</h4>
        <input placeholder="Z: np. świadek" value={from} onChange={e=>setFrom(e.target.value)} style={{width:'100%',marginBottom:6}} />
        <input placeholder="Do: np. zakrwawiony nóż" value={to} onChange={e=>setTo(e.target.value)} style={{width:'100%',marginBottom:6}} />
        <select value={rel} onChange={e=>setRel(e.target.value)} style={{width:'100%',marginBottom:6}}>
          <option value="implies">implies</option>
          <option value="found_at">found_at</option>
          <option value="seen_with">seen_with</option>
          <option value="contradicts">contradicts</option>
        </select>
        <button onClick={()=> (from && to) && onLink(from, to, rel)} style={{width:'100%'}}>Połącz</button>
      </div>
    </div>
  )
}
