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
    if (filterMarket!== 'All' && r.market!== filterMarket) return false
    if (parseFloat(r.edge_percent) < parseFloat(filterEdge)) return false
    return true
  })

  return (
    <main className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-6xl mx-auto p-4 md:p-6">
        {/* Header */}
        <div className="flex flex-wrap justify-between items-center gap-3 mb-6">
          <h1 className="text-2xl md:text-3xl font-black tracking-tight">FOOTBALL<span className="text-green-400">VALUE</span>.BETS</h1>
          <div className="flex gap-2 text-xs">
            <a href="/" className="bg-white text-black px-3 py-1.5 rounded-full font-bold">Today</a>
            <a href="/history" className="bg-zinc-800 border border-zinc-700 px-3 py-1.5 rounded-full hover:bg-zinc-700">History P/L</a>
            <a href="/acca" className="bg-zinc-800 border border-zinc-700 px-3 py-1.5 rounded-full hover:bg-zinc-700">ACCA Generator</a>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4 mb-6">
          <div className="flex flex-wrap gap-3 items-center justify-between">
            <div className="flex flex-wrap gap-3">
              <select value={filterMarket} onChange={e=>setFilterMarket(e.target.value)} className="bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-white">
                <option value="All">All Markets</option>
                <option value="Over2.5">Over 2.5 Goals</option>
                <option value="BTTS_Yes">BTTS Yes</option>
                <option value="1_Over2.5">1 & Over 2.5</option>
                <option value="2_Over2.5">2 & Over 2.5</option>
              </select>
              <select value={filterEdge} onChange={e=>setFilterEdge(e.target.value)} className="bg-zinc-800 border border-zinc-700 rounded-xl px-4 py-2.5 text-sm text-white">
                <option value="5">Edge 5%+ (Quality)</option>
                <option value="10">Edge 10%+ (High Value)</option>
              </select>
            </div>
            <span className="text-xs bg-green-500/10 text-green-400 border border-green-500/20 px-3 py-1.5 rounded-full font-bold">{filtered.length} VALUE BETS</span>
          </div>
          <p className="text-xs text-zinc-500 mt-3">Quality {'>'} Quantity. If Edge {'<'} 5%, we hide it. Pro trading style. Bot runs daily 6 AM EAT.</p>
        </div>

        {/* Content */}
        {loading? (
          <p className="text-zinc-400 text-center py-16">Loading today's value...</p>
        ) : filtered.length === 0? (
          <div className="text-center py-16 border border-dashed border-zinc-800 rounded-2xl bg-zinc-900/50">
            <p className="text-zinc-200 font-bold text-lg">No Value Bets Today</p>
            <p className="text-sm text-zinc-500 mt-2">We don't force predictions. When there is no Edge {'>'}5%, we show nothing.</p>
            <p className="text-xs text-zinc-600 mt-1">Bot checks again at 6 AM EAT. Check History for past P/L transparency.</p>
            <div className="mt-6 flex justify-center gap-2">
              <a href="/history" className="bg-zinc-800 border border-zinc-700 px-4 py-2 rounded-xl text-sm">View History P/L →</a>
              <a href="/acca" className="bg-zinc-800 border border-zinc-700 px-4 py-2 rounded-xl text-sm">Try ACCA Generator →</a>
            </div>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {filtered.map(b => (
              <div key={b.id} className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 hover:border-zinc-700 transition">
                <div className="flex justify-between text-xs mb-2"><span className="text-zinc-500">{b.league_name}</span><span className="text-green-400 font-bold bg-green-500/10 border border-green-500/20 px-2 py-0.5 rounded-full">Edge +{b.edge_percent}%</span></div>
                <div className="font-bold text-lg text-white">{b.home_team} vs {b.away_team}</div>
                <div className="flex gap-2 mt-3">
                  <span className="bg-white text-black px-2.5 py-1 rounded-full text-xs font-black">{b.market}</span>
                  <span className="bg-zinc-800 border border-zinc-700 px-2.5 py-1 rounded-full text-xs text-zinc-300">Exp: {b.expected_score}</span>
                </div>
                <div className="grid grid-cols-3 gap-3 mt-5 bg-zinc-950 border border-zinc-800 rounded-xl p-3">
                  <div><p className="text-zinc-500 text-[10px] uppercase tracking-wide">Our Prob</p><p className="font-bold text-white mt-1">{(b.your_prob*100).toFixed(1)}%</p></div>
                  <div><p className="text-zinc-500 text-[10px] uppercase tracking-wide">Bookie Odds</p><p className="font-bold text-white mt-1">{b.bookie_odds}</p></div>
                  <div><p className="text-zinc-500 text-[10px] uppercase tracking-wide">Value</p><p className="font-bold text-green-400 mt-1">+{b.edge_percent}%</p></div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="mt-12 text-[11px] text-zinc-600 border-t border-zinc-900 pt-4 leading-relaxed">
          <p>Responsible Gambling: Stats not fixed games. Even 10% edge loses sometimes. Flat 100 KES staking for honest tracking. Never bet more than you can afford. 18+. Kenya BCLB helpline for help.</p>
          <p className="mt-2">Free tips + Premium: We give best value matches only. No forced bets.</p>
        </div>
      </div>
    </main>
  )
          }
