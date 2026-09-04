'use client'
import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabase'
function shuffle(a){ for(let i=a.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [a[i],a[j]]=[a[j],a[i]] } return a }
export default function Acca(){
  const [pool,setPool]=useState([]); const [accas,setAccas]=useState([])
  useEffect(()=>{ supabase.from('predictions_today').select('*').gte('edge',5).gte('your_prob',0.55).then(r=>setPool(r.data||[])) },[])
  const gen=()=>{
    if(pool.length<2){ setAccas([]); return }
    const makeOne=(n,label)=>{
      let tries=0; while(tries<30){
        const sh=shuffle([...pool]); const picked=[]; const leagues=new Set()
        for(let p of sh){ if(picked.length>=n) break; if(leagues.has(p.league)) continue; leagues.add(p.league); picked.push(p) }
        if(picked.length<n){ tries++; continue }
        const o=picked.reduce((s,p)=>s*Number(p.bookie_odds),1); const pr=picked.reduce((s,p)=>s*Number(p.your_prob),1)
        if(pr>=0.15&&pr<=0.40) return {type:label, legs:picked, totalOdds:o, totalProb:pr, totalEdge:picked.reduce((s,p)=>s+Number(p.edge),0)/n}; tries++
      } return null
    }
    const r=[]; const a2=makeOne(2,'Safe • 2 Legs'); const a3=makeOne(3,'Medium • 3 Legs'); const a4=makeOne(4,'VIP • 4 Legs'); if(a2) r.push(a2); if(a3) r.push(a3); if(a4) r.push(a4); setAccas(r)
  }
  useEffect(()=>{ if(pool.length) gen() },[pool])
  if(pool.length===0) return <main className="max-w-3xl mx-auto p-6"><div className="glass rounded-[24px] p-12 text-center">No Value Pool Today - We don't force ACCA</div></main>

  return(
    <main className="max-w-3xl mx-auto p-4">
      <div className="flex justify-between items-center mb-6"><h1 className="text-2xl font-black">VIP ACCA LAB</h1><button onClick={gen} className="bg-white text-black px-4 py-2 rounded-full text-xs font-bold">Regenerate</button></div>
      <div className="grid gap-5">
        {accas.map((a,i)=>{
          const isVip=a.type.includes('VIP')
          return(
            <div key={i} className={`${isVip?'relative overflow-hidden rounded-[24px] border border-green-400/20':'glass rounded-[24px]'} p-5`}>
              {isVip && <><img src="/vip-acca.webp" className="absolute inset-0 w-full h-full object-cover opacity-60" alt="vip"/><div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-transparent"/></>}
              <div className="relative flex justify-between"><span className={`${isVip?'bg-white text-black':'glass'} text-[11px] font-black px-3 py-1 rounded-full`}>{a.type}</span><span className="bg-black/60 backdrop-blur text-xs px-3 py-1 rounded-full border border-white/10">{a.totalOdds.toFixed(2)} @ {(a.totalProb*100).toFixed(1)}%</span></div>
              <div className="relative mt-4 space-y-2">{a.legs.map((l,j)=><div key={j} className="flex justify-between bg-black/40 backdrop-blur border border-white/5 p-3 rounded-xl text-sm"><span>{l.home_team} vs {l.away_team} • {l.market}</span><span className="font-bold">{l.bookie_odds}</span></div>)}</div>
              {isVip && <p className="relative mt-4 text-[11px] text-green-300/80">👑 VIP 4-leg from value pool only. Different leagues. High risk, for fun.</p>}
            </div>
          )
        })}
      </div>
    </main>
  )
}
