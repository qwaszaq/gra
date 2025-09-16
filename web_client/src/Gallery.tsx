import React, { useEffect, useState } from 'react'

const VISION_BASE = import.meta.env.VITE_VISION_BASE || 'http://localhost:8004'

export default function Gallery() {
  const [gen, setGen] = useState<string[]>([])
  const [cz, setCz] = useState<string[]>([])

  useEffect(() => {
    fetch(`${VISION_BASE}/list?collection=generated`).then(r=>r.json()).then(d=> setGen(d.images || []))
    fetch(`${VISION_BASE}/list?collection=case_zero`).then(r=>r.json()).then(d=> setCz(d.images || []))
  }, [])

  const renderGrid = (title: string, items: string[]) => (
    <>
      <h3>{title}</h3>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill, minmax(200px,1fr))', gap: 12}}>
        {items.map((u, i) => <img key={i} src={`${u.startsWith('/assets') ? VISION_BASE+u : u}`} style={{width:'100%',borderRadius:6}} />)}
      </div>
    </>
  )

  return (
    <div style={{padding:12}}>
      {renderGrid("Generated", gen)}
      <div style={{height:24}}/>
      {renderGrid("Case Zero", cz)}
    </div>
  )
}
