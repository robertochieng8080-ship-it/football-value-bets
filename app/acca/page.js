'use client'
import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabase'

export default function AccaPage(){
  const [bets,setBets]=useState([])
  useEffect(()=>{
    supabase.from('predictions_today').select('*').order('edge_percent',{ascending:false}).limit(15).then(r=>{
      const data=r.data||[]
      // simple ACCA: top 3
      setBets(data.slice(0,3))
    })
  },[])
  const totalOdds = bets.reduce((s,b)=>s*Number(b.bookie_odds),1)
  return(
    <main className="max-w-3xl mx-auto p-4">
      <h1 className="text-2xl font-bold">VIP ACCA</h1>
      <p className="text-zinc-500 text-sm mt-2">Top 3 value picks combined</p>
      <div className="mt-6 space-y-3">
        {bets.map(b=><div key={b.fixture_id} className="bg-zinc-900 p-3 rounded-xl border border-zinc-800">{b.home_team} vs {b.away_team} - {b.market} @ {b.bookie_odds} (+{b.edge_percent}%)</div>)}
      </div>
      <div className="mt-6 p-4 bg-green-500/10 border border-green-500/20 rounded-xl">Total Odds: {totalOdds.toFixed(2)}</div>
    </main>
  )
        }
