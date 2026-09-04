'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

export default function ProfitTracker() {
  const [daily, setDaily] = useState<any>(null)
  const [bets, setBets] = useState<any[]>([])

  useEffect(() => {
    async function load() {
      const { data: d } = await supabase.from('profit_daily').select('*').order('date', { ascending: false }).limit(1).single()
      setDaily(d)
      const { data: b } = await supabase.from('predictions_today').select('*').not('is_won', 'is', null).order('match_date', { ascending: false }).limit(20)
      setBets(b || [])
    }
    load()
  }, [])

  if (!daily) return <div>No P&L yet - run profit_tracker.py after games finish</div>

  return (
    <div className="grid grid-cols-4 gap-4">
      <div className="bg-green-900 p-4 rounded">Profit: {daily.total_profit} units</div>
      <div className="bg-zinc-800 p-4 rounded">Yield: {daily.yield_percent}%</div>
      <div className="bg-zinc-800 p-4 rounded">Hit Rate: {daily.hit_rate}%</div>
      <div className="bg-zinc-800 p-4 rounded">{daily.wins}/{daily.settled_bets} Won</div>
      
      <table className="col-span-4 w-full mt-4">
        <thead><tr><th>Match</th><th>Market</th><th>Odds</th><th>Score</th><th>Result</th><th>Profit</th></tr></thead>
        <tbody>
          {bets.map((bet,i) => (
            <tr key={i} className={bet.is_won ? 'text-green-400' : 'text-red-400'}>
              <td>{bet.home_team} vs {bet.away_team}</td>
              <td>{bet.market}</td>
              <td>{bet.bookie_odds}</td>
              <td>{bet.result_home_score}-{bet.result_away_score}</td>
              <td>{bet.is_won ? 'WON ✅' : 'LOST ❌'}</td>
              <td>{bet.profit}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
