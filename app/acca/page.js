'use client'
import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabase'

function shuffle(a){ for(let i=a.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [a[i],a[j]]=[a[j],a[i]] } return a }

export default function Acca(){
  const [pool,setPool]=useState([])
  const [accas,setAccas]=useState([])
  useEffect(()=>{ supabase.from('predictions_today').select('*').gte('edge',5).gte('your_prob',0.55).then(r=>setPool(r.data||[])) },[])

  const generate = ()=>{
    if(pool.length<2){ setAccas([]); return }
    const makeOne = (n, label)=>{
      let tries=0, best=null
      while(tries<30){
        const shuffled = shuffle([...pool])
        const picked=[]
        const leagues=new Set()
        for(let p of shuffled){
          if(picked.length>=n) break
          if(leagues.has(p.league)) continue
          leagues.add(p.league); picked.push(p)
        }
        if(picked.length<n) { tries++; continue }
        const totalOdds = picked.reduce((s,p)=>s*Number(p.bookie_odds),1)
        const totalProb = picked.reduce((s,p)=>s*Number(p.your_prob),1)
        const totalEdge = picked.reduce((s,p)=>s+Number(p.edge),0)/n
        if(totalProb>=0.15 && totalProb<=0.40){ best={type:label, legs:picked, totalOdds, totalProb, totalEdge}; break }
        tries++
      }
      return best
    }
    const res=[]
    const s2=makeOne(2,'Safe Acca (2 legs)')
    const s3=makeOne(3,'Medium Acca (3 legs)')
    const s4=makeOne(4,'Risky Acca (4 legs)')
    if(s2) res.push(s2); if(s3) res.push(s3); if(s4) res.push(s4)
    setAccas(res)
  }

  useEffect(()=>{ if(pool.length) generate() },[pool])

  const copyText = (a)=>{
    const txt = `${a.type}\n`+a.legs.map(l=>`${l.home_team} vs ${l.away_team} - ${l.market} @${l.bookie_odds}`).join('\n')+`\nTotal Odds: ${a.totalOdds.toFixed(2)} | Prob: ${(a.totalProb*100).toFixed(1)}%`
    navigator.clipboard.writeText(txt); alert('Copied for Telegram/WhatsApp')
  }

  if(pool.length===0) return <main className="max-w-3xl mx-auto p-6 text-center"><p className="bg-zinc-900 border border-zinc-800 rounded-xl p-8">No Value Bets Today - We don't force predictions. Acca generator needs Edge {'>'}5% pool.</p></main>

  return(
    <main className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-2">VALUE ACCA GENERATOR</h1>
      <p className="text-xs text-zinc-500 mb-4">Smart random from value pool only. Different leagues, 15-40% total prob only. High risk for fun.</p>
      <button onClick={generate} className="bg-white text-black px-4 py-2 rounded-lg text-sm font-bold mb-6">Regenerate ACCA</button>
      <div className="grid gap-4">
        {accas.map((a,i)=><div key={i} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <div className="flex justify-between"><h2 className="font-bold">{a.type}</h2><span className="text-xs bg-zinc-800 px-2 py-1 rounded">Total {a.totalOdds.toFixed(2)} | {(a.totalProb*100).toFixed(1)}% | Edge {a.totalEdge.toFixed(1)}%</span></div>
          <div className="mt-3 space-y-2 text-sm">{a.legs.map((l,j)=><div key={j} className="flex justify-between bg-zinc-800/50 p-2 rounded"><span>{l.home_team} vs {l.away_team} - {l.market}</span><span>{l.bookie_odds}</span></div>)}</div>
          <button onClick={()=>copyText(a)} className="mt-3 w-full bg-zinc-800 border border-zinc-700 py-2 rounded text-sm">Copy for Telegram / WhatsApp</button>
          <p className="text-xs text-amber-500/70 mt-2">⚠️ ACCA is high risk, for fun. Stake small.</p>
        </div>)}
      </div>
    </main>
  )
                                         }
