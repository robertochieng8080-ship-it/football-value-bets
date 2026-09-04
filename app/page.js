'use client'
import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

export default function Home(){
  const [data,setData]=useState([])
  const [fMarket,setFMarket]=useState('All')
  const [fEdge,setFEdge]=useState('5')
  useEffect(()=>{
    supabase.from('predictions_today').select('*').order('edge_percent',{ascending:false}).then(r=>setData(r.data||[]))
  },[])

  const filtered=data.filter(r=> (fMarket==='All'||r.market===fMarket) && parseFloat(r.edge_percent)>=parseFloat(fEdge))

  // Helper to format EAT time
  const formatEAT = (iso) => {
    if(!iso) return ''
    try {
      const d = new Date(iso)
      return d.toLocaleTimeString('en-KE', {hour: 'numeric', minute:'2-digit', hour12:true, timeZone:'Africa/Nairobi'}) + ' EAT'
    } catch { return iso }
  }

  return(
    <main className="max-w-6xl mx-auto p-4 md:p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-[28px] font-black tracking-tighter">FOOTBALL<span className="text-[#22c55e]">VALUE</span>.BETS</h1>
        <div className="flex gap-1.5 p-1 bg-zinc-900 rounded-full border border-zinc-800 text-xs">
          <span className="bg-white text-black px-4 py-1.5 rounded-full font-bold">Today</span>
          <a href="/history" className="px-4 py-1.5 text-zinc-400 hover:text-white">History P/L</a>
          <a href="/acca" className="px-4 py-1.5 text-zinc-400 hover:text-white">VIP ACCA</a>
        </div>
      </div>

      <div className="glass-green rounded-[24px] p-6 mb-6 flex justify-between items-center">
        <div><p className="text-xs tracking-widest text-green-400/70 uppercase">Live Value Pool</p><p className="text-3xl font-black mt-1">{filtered.length} BETS</p><p className="text-sm text-zinc-400 mt-1">Quality {'>'} Quantity. Edge {'<'}5% hidden. • Nairobi Time</p></div>
        <div className="hidden md:block w-24 h-24 rounded-full bg-gradient-to-br from-green-400/20 to-transparent border border-green-400/20" />
      </div>

      <div className="flex gap-2 mb-6 overflow-x-auto">
        {['All','Over2.5','BTTS_Yes','Over1.5','Home Win','Away Win','1_Over2.5','2_Over2.5'].map(m=><button key={m} onClick={()=>setFMarket(m)} className={`px-4 py-2 rounded-full text-xs border whitespace-nowrap ${fMarket===m?'bg-white text-black border-white font-bold':'glass text-zinc-400 border-zinc-800'}`}>{m}</button>)}
        <select value={fEdge} onChange={e=>setFEdge(e.target.value)} className="ml-auto glass rounded-full px-4 py-2 text-xs"><option value="5">Edge 5%+ Quality</option><option value="0">All Bets</option><option value="10">Edge 10%+ High</option></select>
      </div>

      {filtered.length===0? (
        <div className="glass rounded-[24px] p-12 text-center">
          <p className="font-black text-xl">No Value Bets Today</p>
          <p className="text-sm text-zinc-500 mt-2 max-w-md mx-auto">We don't force predictions. When no Edge {'>'}5% exists, we show nothing. This is pro trading discipline.</p>
          <div className="mt-6 flex justify-center gap-2"><a href="/history" className="bg-white text-black px-5 py-2.5 rounded-full text-sm font-bold">View Transparent P/L</a><a href="/acca" className="glass px-5 py-2.5 rounded-full text-sm">VIP ACCA →</a></div>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {filtered.map(b=><div key={b.id || b.fixture_id} className="glass rounded-[20px] p-5 hover:border-zinc-700 transition">
            <div className="flex justify-between text-[11px] items-center">
              <span className="text-zinc-500 uppercase tracking-wide">{b.league_name} • {b.kickoff_time || formatEAT(b.kickoff_iso) || formatEAT(b.fixture_date) || 'Today'}</span>
              <span className="bg-green-500/15 text-green-400 border border-green-500/20 px-2.5 py-0.5 rounded-full font-bold">+{b.edge_percent}% EDGE</span>
            </div>
            <p className="font-bold text-[18px] mt-3 tracking-tight">{b.home_team} vs {b.away_team}</p>
            <div className="flex gap-2 mt-3">
              <span className="bg-white text-black text-[11px] font-black px-3 py-1 rounded-full">{b.market}</span>
              <span className="glass text-[11px] px-3 py-1 rounded-full text-zinc-400">Exp {b.expected_score}</span>
              {b.kickoff_time && <span className="glass text-[11px] px-3 py-1 rounded-full text-green-300 border border-green-500/20">{b.kickoff_time}</span>}
            </div>
            <div className="grid grid-cols-3 gap-3 mt-4 bg-black/40 rounded-2xl p-3 border border-white/5"><div><p className="text-[10px] text-zinc-500 uppercase">Our Prob</p><p className="font-bold mt-1">{(b.your_prob*100).toFixed(1)}%</p></div><div><p className="text-[10px] text-zinc-500 uppercase">Odds</p><p className="font-bold mt-1">{b.bookie_odds}</p></div><div><p className="text-[10px] text-zinc-500 uppercase">Value</p><p className="font-bold mt-1 text-green-400">+{b.edge_percent}%</p></div></div>
          </div>)}
        </div>
      )}
    </main>
  )
                                                    }
