'use client'
import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

export default function Home(){
  const [data,setData]=useState([])
  const [fMarket,setFMarket]=useState('All')
  const [fEdge,setFEdge]=useState('5')
  const [profitDaily, setProfitDaily] = useState(null)
  const [settled, setSettled] = useState([])

  useEffect(()=>{
    supabase.from('predictions_today').select('*').order('edge_percent',{ascending:false}).then(r=>setData(r.data||[]))

    // P/L TRACKER - REAL PROFIT
    supabase.from('profit_daily').select('*').order('date', {ascending:false}).limit(7).then(r=>{
      if(r.data && r.data.length>0) setProfitDaily(r.data[0])
    })
    supabase.from('predictions_today').select('*').not('is_won','is',null).order('match_date',{ascending:false}).limit(10).then(r=>{
      setSettled(r.data||[])
    })
  },[])

  const filtered=data.filter(r=> (fMarket==='All'||r.market===fMarket) && parseFloat(r.edge_percent)>=parseFloat(fEdge))

  const totalProfit = profitDaily? parseFloat(profitDaily.total_profit) : 0
  const yieldPct = profitDaily? parseFloat(profitDaily.yield_percent) : 0
  const hitRate = profitDaily? parseFloat(profitDaily.hit_rate) : 0

  return(
    <main className="max-w-6xl mx-auto p-4 md:p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-[28px] font-black tracking-tighter">FOOTBALL<span className="text-[#22c55e]">VALUE</span>.BETS</h1>
        <div className="flex gap-1.5 p-1 bg-zinc-900 rounded-full border border-zinc-800 text-xs">
          <span className="bg-white text-black px-4 py-1.5 rounded-full font-bold">Today</span>
          <a href="/history" className="px-4 py-1.5 text-zinc-400 hover:text-white">History</a>
          <a href="/acca" className="px-4 py-1.5 text-zinc-400 hover:text-white">VIP ACCA</a>
        </div>
      </div>

      {/* REAL P/L TRACKER - NEW */}
      {profitDaily? (
        <div className="glass rounded-[24px] p-5 mb-6 border border-green-500/20 bg-gradient-to-br from-green-500/[0.08] to-transparent">
          <div className="flex justify-between items-center mb-4">
            <p className="text-xs tracking-widest text-green-400/70 uppercase font-bold">REAL P&L • Last 7 Days Performance</p>
            <span className={`text-[11px] px-3 py-1 rounded-full font-black ${totalProfit>=0? 'bg-green-500/20 text-green-400 border border-green-500/20' : 'bg-red-500/20 text-red-400 border border-red-500/20'}`}>
              {totalProfit>=0? '+' : ''}{totalProfit.toFixed(2)} UNITS {yieldPct>=0? '▲':'▼'} {yieldPct.toFixed(1)}% YIELD
            </span>
          </div>
          <div className="grid grid-cols-4 gap-3">
            <div className="bg-black/40 rounded-2xl p-3 border border-white/5">
              <p className="text-[10px] text-zinc-500 uppercase">Profit</p>
              <p className={`font-black text-lg mt-1 ${totalProfit>=0? 'text-green-400' : 'text-red-400'}`}>{totalProfit>=0?'+':''}{totalProfit.toFixed(2)}</p>
              <p className="text-[10px] text-zinc-600 mt-1">{profitDaily.settled_bets} bets settled</p>
            </div>
            <div className="bg-black/40 rounded-2xl p-3 border border-white/5">
              <p className="text-[10px] text-zinc-500 uppercase">Yield</p>
              <p className="font-black text-lg mt-1 text-white">{yieldPct.toFixed(1)}%</p>
              <p className="text-[10px] text-zinc-600 mt-1">ROI per unit</p>
            </div>
            <div className="bg-black/40 rounded-2xl p-3 border border-white/5">
              <p className="text-[10px] text-zinc-500 uppercase">Hit Rate</p>
              <p className="font-black text-lg mt-1 text-white">{hitRate.toFixed(1)}%</p>
              <p className="text-[10px] text-zinc-600 mt-1">{profitDaily.wins}W - {profitDaily.settled_bets - profitDaily.wins}L</p>
            </div>
            <div className="bg-black/40 rounded-2xl p-3 border border-white/5">
              <p className="text-[10px] text-zinc-500 uppercase">Profitable</p>
              <p className={`font-black text-lg mt-1 ${profitDaily.is_profitable? 'text-green-400' : 'text-zinc-400'}`}>{profitDaily.is_profitable? 'YES ✅' : 'NO'}</p>
              <p className="text-[10px] text-zinc-600 mt-1">{profitDaily.date}</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="glass rounded-[24px] p-5 mb-6 border border-zinc-800 bg-zinc-900/30">
          <p className="text-xs tracking-widest text-zinc-500 uppercase">REAL P&L • Calculating...</p>
          <p className="text-sm text-zinc-400 mt-2">No settled bets yet - P&L appears tomorrow 7AM EAT after first games finish.</p>
        </div>
      )}

      <div className="glass-green rounded-[24px] p-6 mb-6 flex justify-between items-center">
        <div><p className="text-xs tracking-widest text-green-400/70 uppercase">Live Value Pool</p><p className="text-3xl font-black mt-1">{filtered.length} BETS</p></div>
      </div>

      <div className="flex gap-2 mb-6 overflow-x-auto">
        {['All','Over2.5','BTTS_Yes','Over1.5','Home Win','Away Win','1_Over2.5'].map(m=><button key={m} onClick={()=>setFMarket(m)} className={`px-4 py-2 rounded-full text-xs border whitespace-nowrap ${fMarket===m?'bg-white text-black border-white font-bold':'glass text-zinc-400 border-zinc-800'}`}>{m}</button>)}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {filtered.map(b=><div key={`${b.fixture_id}-${b.market}`} className="glass rounded-[20px] p-5">
          <div className="flex justify-between text-[11px]"><span className="text-zinc-500 uppercase">{b.league_name} • {b.kickoff_time || 'EAT'}</span><span className="bg-green-500/15 text-green-400 border border-green-500/20 px-2.5 py-0.5 rounded-full font-bold">+{b.edge_percent}% EDGE</span></div>
          <p className="font-bold text-[18px] mt-3">{b.home_team} vs {b.away_team}</p>
          <div className="flex gap-2 mt-3"><span className="bg-white text-black text-[11px] font-black px-3 py-1 rounded-full">{b.market}</span><span className="glass text-[11px] px-3 py-1 rounded-full">{b.expected_score}</span></div>
          <div className="grid grid-cols-3 gap-3 mt-4 bg-black/40 rounded-2xl p-3 border border-white/5"><div><p className="text-[10px] text-zinc-500 uppercase">Our Prob</p><p className="font-bold mt-1">{(b.your_prob*100).toFixed(1)}%</p></div><div><p className="text-[10px] text-zinc-500 uppercase">Odds</p><p className="font-bold mt-1">{b.bookie_odds}</p></div><div><p className="text-[10px] text-zinc-500 uppercase">Value</p><p className="font-bold mt-1 text-green-400">+{b.edge_percent}%</p></div></div>
        </div>)}
      </div>
    </main>
  )
}
