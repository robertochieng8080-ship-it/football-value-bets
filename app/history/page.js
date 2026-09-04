'use client'
import { useEffect, useState } from 'react'
import { supabase } from '../../lib/supabase'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function History(){
  const [data,setData]=useState([])
  const [filterMarket,setFilterMarket]=useState('All')
  const [filterResult,setFilterResult]=useState('All')
  const [profitDaily, setProfitDaily] = useState([])
  
  useEffect(()=>{ 
    async function load(){
      const { data: settledBets } = await supabase
        .from('predictions_today')
        .select('*')
        .not('is_won', 'is', null)
        .order('match_date',{ascending:false})
        .limit(500)
      
      const mapped = (settledBets||[]).map(r=>({
        id: r.fixture_id + '_' + r.market,
        date: r.match_date,
        home_team: r.home_team,
        away_team: r.away_team,
        league: r.league_name,
        market: r.market,
        bookie_odds: r.bookie_odds,
        result: r.is_won ? 'WON' : 'LOST',
        actual_score: `${r.result_home_score}-${r.result_away_score}`,
        profit: Number(r.profit||0) * 100,
        kickoff_time: r.kickoff_time
      }))
      setData(mapped)

      const { data: pd } = await supabase.from('profit_daily').select('*').order('date',{ascending:false}).limit(30)
      setProfitDaily(pd||[])
    }
    load()
  },[])

  const settled = data.filter(d=>d.result!=='PENDING')
  const totalProfit = settled.reduce((s,d)=>s+Number(d.profit||0),0)
  const totalBets = settled.length
  const won = settled.filter(d=>d.result==='WON').length
  const winRate = totalBets? (won/totalBets*100).toFixed(1):0
  const roi = totalBets? (totalProfit/(totalBets*100)*100).toFixed(1):0
  const last30 = settled.filter(d=> new Date(d.date) >= new Date(Date.now()-30*24*3600*1000)).reduce((s,d)=>s+Number(d.profit||0),0)

  let chartData = []
  if(profitDaily.length>0){
    chartData = profitDaily.map(d=>({date: d.date, profit: Number(d.total_profit)*100})).sort((a,b)=>a.date.localeCompare(b.date)).slice(-14)
  } else {
    const dailyMap={}
    settled.forEach(d=>{ dailyMap[d.date]=(dailyMap[d.date]||0)+Number(d.profit) })
    chartData = Object.entries(dailyMap).map(([date,profit])=>({date,profit})).sort((a,b)=>a.date.localeCompare(b.date)).slice(-14)
  }

  const filtered = data.filter(d=>{
    if(filterMarket!=='All' && d.market!==filterMarket) return false
    if(filterResult!=='All' && d.result!==filterResult) return false
    return true
  })

  return(
    <main className="max-w-6xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">HISTORY + P/L DASHBOARD <span className="text-xs text-zinc-500">Transparency = Trust</span></h1>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <div className={`p-3 rounded-xl border ${totalProfit>=0?'bg-green-500/10 border-green-500/20 text-green-400':'bg-red-500/10 border-red-500/20 text-red-400'}`}><p className="text-xs">Total Profit (100 KES flat)</p><p className="text-xl font-bold">{totalProfit.toFixed(0)} KES</p></div>
        <div className="bg-zinc-900 border border-zinc-800 p-3 rounded-xl"><p className="text-xs text-zinc-500">ROI %</p><p className="text-xl font-bold">{roi}%</p></div>
        <div className="bg-zinc-900 border border-zinc-800 p-3 rounded-xl"><p className="text-xs text-zinc-500">Win Rate</p><p className="text-xl font-bold">{winRate}%</p></div>
        <div className="bg-zinc-900 border border-zinc-800 p-3 rounded-xl"><p className="text-xs text-zinc-500">Total Bets</p><p className="text-xl font-bold">{totalBets}</p></div>
        <div className="bg-zinc-900 border border-zinc-800 p-3 rounded-xl"><p className="text-xs text-zinc-500">Last 30 Days</p><p className={`text-xl font-bold ${last30>=0?'text-green-400':'text-red-400'}`}>{last30.toFixed(0)} KES</p></div>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 h-48 mb-6">
        <ResponsiveContainer width="100%" height="100%"><LineChart data={chartData}><XAxis dataKey="date" hide/><YAxis hide/><Tooltip/><Line type="monotone" dataKey="profit" stroke="#22c55e" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer>
      </div>

      <div className="flex gap-2 mb-4">
        <select value={filterMarket} onChange={e=>setFilterMarket(e.target.value)} className="bg-zinc-800 rounded px-3 py-2 text-sm"><option value="All">All Markets</option><option value="Over2.5">Over2.5</option><option value="BTTS_Yes">BTTS Yes</option><option value="1_Over2.5">1 & Over2.5</option><option value="2_Over2.5">2 & Over2.5</option></select>
        <select value={filterResult} onChange={e=>setFilterResult(e.target.value)} className="bg-zinc-800 rounded px-3 py-2 text-sm"><option value="All">All Results</option><option value="WON">WON</option><option value="LOST">LOST</option><option value="PENDING">PENDING</option></select>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-auto">
        <table className="w-full text-sm"><thead className="text-zinc-500 text-xs"><tr><th className="p-3 text-left">Date</th><th className="text-left">Match</th><th>Market</th><th>Odds</th><th>Result</th><th>Profit</th></tr></thead>
        <tbody>{filtered.length===0 ? <tr><td colSpan={6} className="p-8 text-center text-zinc-500">No settled bets yet</td></tr> : filtered.map(r=><tr key={r.id} className="border-t border-zinc-800"><td className="p-3">{r.date}</td><td>{r.home_team} vs {r.away_team} <span className="text-xs text-zinc-500">{r.league}</span></td><td>{r.market}</td><td>{r.bookie_odds}</td><td className={r.result==='WON'?'text-green-400':r.result==='LOST'?'text-red-400':'text-zinc-500'}>{r.result} {r.actual_score||''}</td><td className={Number(r.profit)>=0?'text-green-400':'text-red-400'}>{r.profit} KES</td></tr>)}</tbody></table>
      </div>
      <p className="text-xs text-zinc-600 mt-4">We show LOSSES openly. Flat 100 KES staking. No fake stakes. Real results only.</p>
    </main>
  )
  }
