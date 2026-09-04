'use client'
import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabase'

export default function AccaPage(){
  const [bets,setBets]=useState<any[]>([])
  useEffect(()=>{
    supabase.from('predictions_today').select('*').order('edge_percent',{ascending:false}).limit(15).then(r=>{
      const data=r.data||[]
      const acca=[]
      const seen=new Set()
      for(const b of data){
        if(acca.length>=4) break
        if(!seen.has(b.market)){ acca.push(b); seen.add(b.market) }
      }
      if(acca.length<4){
        for(const b of data){ if(acca.length>=4) break; if(!acca.find(x=>x.fixture_id===b.fixture_id)) acca.push(b) }
      }
      setBets(acca)
    })
  },[])
  const total= bets.reduce((a,b)=>a*parseFloat(b.bookie_odds),1)
  if(!bets.length) return <main className="p-12 text-center">No Value Pool Today - We don't force ACCA</main>
  return(
    <main className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-black mb-6">VIP ACCA • 4 LEGS MIXED • {bets[0]?.kickoff_time}</h1>
      <div className="glass rounded-[24px] p-6">
        {bets.map((b,i)=><div key={i} className="flex justify-between py-3 border-b border-zinc-800 last:border-0">
          <div><p className="font-bold text-sm">{b.home_team} vs {b.away_team}</p><p className="text-xs text-zinc-500">{b.league_name} • {b.kickoff_time}</p></div>
          <div className="text-right"><span className="bg-white text-black text-[11px] font-black px-3 py-1 rounded-full">{b.market}</span><p className="text-xs mt-1">{b.bookie_odds}</p></div>
        </div>)}
        <div className="mt-6 bg-green-500/10 border border-green-500/20 rounded-2xl p-4 flex justify-between">
          <div><p className="text-xs text-zinc-400">TOTAL ODDS</p><p className="text-2xl font-black">{total.toFixed(2)}</p></div>
          <div className="text-right"><p className="text-xs text-zinc-400">MIXED ACCA</p><p className="text-sm font-bold text-green-400">4 legs</p></div>
        </div>
      </div>
    </main>
  )
}
