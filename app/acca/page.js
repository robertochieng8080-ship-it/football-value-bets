'use client'
import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabase'

export default function AccaPage(){
  const [bets,setBets]=useState<any[]>([])
  useEffect(()=>{
    supabase.from('predictions_today').select('*').order('edge_percent',{ascending:false}).limit(20).then(r=>{
      const data=r.data||[]
      // Build 4-leg mixed market ACCA
      const usedMarkets=new Set()
      const acca=[]
      for(const b of data){
        if(acca.length>=4) break
        if(!usedMarkets.has(b.market)){
          acca.push(b)
          usedMarkets.add(b.market)
        }
      }
      // If still <4, fill with top edge regardless of market
      if(acca.length<4){
        for(const b of data){
          if(acca.length>=4) break
          if(!acca.find(x=>x.fixture_id===b.fixture_id)) acca.push(b)
        }
      }
      setBets(acca.slice(0,4))
    })
  },[])

  const totalOdds = bets.reduce((acc,b)=>acc*parseFloat(b.bookie_odds),1)

  if(bets.length===0) return <main className="max-w-3xl mx-auto p-6"><div className="glass rounded-[24px] p-12 text-center">No Value Pool Today - We don't force ACCA</div></main>

  return(
    <main className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-black mb-6">VIP ACCA • 4 LEGS • {bets[0]?.league_name?.split('•')[1] || 'Nairobi Time'}</h1>
      <div className="glass rounded-[24px] p-6">
        {bets.map((b,i)=><div key={i} className="flex justify-between py-3 border-b border-zinc-800 last:border-0">
          <div><p className="font-bold text-sm">{b.home_team} vs {b.away_team}</p><p className="text-xs text-zinc-500">{b.league_name} • {b.kickoff_time || b.expected_score?.split('•')[1] || ''}</p></div>
          <div className="text-right"><span className="bg-white text-black text-[11px] font-black px-3 py-1 rounded-full">{b.market}</span><p className="text-xs mt-1">{b.bookie_odds}</p></div>
        </div>)}
        <div className="mt-6 bg-green-500/10 border border-green-500/20 rounded-2xl p-4 flex justify-between">
          <div><p className="text-xs text-zinc-400">TOTAL ODDS</p><p className="text-2xl font-black">{totalOdds.toFixed(2)}</p></div>
          <div className="text-right"><p className="text-xs text-zinc-400">4 LEGS MIXED</p><p className="text-sm font-bold text-green-400">+{bets.reduce((a,b)=>a+parseFloat(b.edge_percent),0).toFixed(1)}% Total Edge</p></div>
        </div>
      </div>
    </main>
  )
            }
