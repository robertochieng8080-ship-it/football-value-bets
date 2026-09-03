'use client'
import { useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'

export default function Home() {
  const [data, setData] = useState([])
  const [filterMarket, setFilterMarket] = useState('All')
  const [filterEdge, setFilterEdge] = useState('5')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const { data } = await supabase.from('predictions_today').select('*').order('edge_percent', { ascending: false })
      setData(data || [])
      setLoading(false)
    }
    load()
  }, [])

  const filtered = data.filter(r => {
    if (filterMarket !== 'All' && r.market !== filterMarket) return false
    if (parseFloat(r.edge_percent) < parseFloat(filterEdge)) return false
    return true
  })

  return (
    <main className="max-w-6xl mx-auto p-4 md:p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">FOOTBALL<span className="text-green-400">VALUE</span>.BETS</h1>
        <span className="text-xs bg-zinc-800 px-3 py-1 rounded-full">{filtered.length} VALUE BETS</span>
      </div>

      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 mb-6">
        <div className="flex flex-wrap gap-3">
          <select value={filterMarket} onChange={e=>setFilterMarket(e.target.value)} className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
            <option value="All">All Markets</option>
            <option value="Over2.5">Over 2.5 Goals</option>
            <option value="BTTS_Yes">BTTS Yes</option>
            <option value="1_Over2.5">1 & Over 2.5</option>
            <option value="2_Over2.5">2 & Over 2.5</option>
          </select>
          <select value={filterEdge} onChange={e=>setFilterEdge(e.target.value)} className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm">
            <option value="5">Edge 5%+ (Quality)</option>
            <option value="10">Edge 10%+ (High Value)</option>
          </select>
        </div>
        <p className="text-xs text-zinc-500 mt-3">Quality {'>'} Quantity. If Edge {'<'} 5%, we hide it. Pro trading style.</p>
      </div>

      {loading ? <p className="text-zinc-500">Loading today's value...</p> : filtered.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-zinc-800 rounded-xl">
          <p className="text-zinc-400">No Value Bets Today</p>
          <p className="text-xs text-zinc-600 mt-2">We don't force bets. Bot checks again at 6 AM EAT.</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {filtered.map(b => (
            <div key={b.id} className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition">
              <div className="flex justify-between text-xs text-zinc-500 mb-2"><span>{b.league_name}</span><span className="text-green-400 font-bold">Edge {b.edge_percent}%</span></div>
              <div className="font-bold text-lg">{b.home_team} vs {b.away_team}</div>
              <div className="flex gap-2 mt-3">
                <span className="bg-green-500/10 text-green-400 border border-green-500/20 px-2 py-1 rounded text-xs font-bold">{b.market}</span>
                <span className="bg-zinc-800 px-2 py-1 rounded text-xs">Exp: {b.expected_score} (xG {b.expected_goals_home}-{b.expected_goals_away})</span>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-4 text-sm">
                <div><p className="text-zinc-500 text-xs">Our Prob</p><p className="font-bold">{(b.your_prob*100).toFixed(1)}%</p></div>
                <div><p className="text-zinc-500 text-xs">Bookie Odds</p><p className="font-bold">{b.bookie_odds}</p></div>
                <div><p className="text-zinc-500 text-xs">Value</p><p className="font-bold text-green-400">+{b.edge_percent}%</p></div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-12 text-xs text-zinc-600 border-t border-zinc-900 pt-4">
        <p>Responsible Gambling: Stats not fixed games. Even 10% edge loses. Never bet more than you can afford. 18+. Kenya BCLB helpline for help.</p>
      </div>
    </main>
  )
  }
