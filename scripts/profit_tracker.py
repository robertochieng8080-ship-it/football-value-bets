import os, requests
from datetime import datetime, timedelta, timezone
from supabase import create_client
from difflib import SequenceMatcher

def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def fuzzy(a,b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() if a and b else 0

def fetch_espn_results(date_str):
    espn_date = date_str.replace("-", "")
    leagues = ["eng.1","esp.1","ita.1","ger.1","fra.1","por.1","ned.1","mex.1"]
    results = []
    for code in leagues:
        try:
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={espn_date}"
            r=requests.get(url, timeout=10)
            if r.status_code!=200: continue
            for ev in r.json().get('events',[]):
                comp=ev.get('competitions',[{}])[0]
                status=comp.get('status',{}).get('type',{}).get('name','')
                if status not in ['STATUS_FINAL','STATUS_FULL_TIME','STATUS_AFTER_EXTRA_TIME']:
                    continue
                comps=comp.get('competitors',[])
                if len(comps)<2: continue
                home=next((c for c in comps if c.get('homeAway')=='home'),comps[0])
                away=next((c for c in comps if c.get('homeAway')=='away'),comps[1])
                results.append({
                    'home': home.get('team',{}).get('displayName',''),
                    'away': away.get('team',{}).get('displayName',''),
                    'home_score': int(home.get('score','0')),
                    'away_score': int(away.get('score','0')),
                })
        except: continue
    return results

def is_won(market, home_score, away_score):
    if market=="Home Win": return home_score > away_score
    if market=="Away Win": return away_score > home_score
    if market=="Over2.5": return (home_score + away_score) > 2.5
    if market=="BTTS_Yes" or market=="BTTS Yes": return home_score>0 and away_score>0
    return False

def main():
    print(f"Profit Tracker - {datetime.now(timezone.utc)}")
    supabase=get_supabase()
    thirty_days_ago = str((datetime.now(timezone.utc).date() - timedelta(days=30)))
    try:
        preds = supabase.table("predictions_today").select("*").gte("match_date", thirty_days_ago).execute().data
    except:
        preds = supabase.table("predictions_today").select("*").execute().data

    if not preds:
        print("No predictions found")
        return

    print(f"Found {len(preds)} predictions to settle")
    total_staked = 0
    total_profit = 0.0
    wins = 0
    settled = 0
    by_market = {}
    dates = sorted(set([p['match_date'] for p in preds]))
    all_results = []
    for d in dates:
        res = fetch_espn_results(d)
        all_results.extend(res)
        print(f"{d}: {len(res)} finished matches")

    for p in preds:
        match = None
        best_score = 0
        for r in all_results:
            s = fuzzy(p['home_team'], r['home']) + fuzzy(p['away_team'], r['away'])
            if s > best_score:
                best_score = s
                match = r
        if not match or best_score < 0.8: continue

        settled+=1
        market = p['market']
        odds = float(p['bookie_odds'])
        won = is_won(market, match['home_score'], match['away_score'])
        profit = (odds - 1) if won else -1.0
        total_profit += profit
        total_staked += 1
        if won: wins+=1
        if market not in by_market:
            by_market[market] = {'staked':0,'profit':0.0,'wins':0}
        by_market[market]['staked']+=1
        by_market[market]['profit']+=profit
        if won: by_market[market]['wins']+=1
        try:
            supabase.table("predictions_today").update({
                "result_home_score": match['home_score'],
                "result_away_score": match['away_score'],
                "is_won": won,
                "profit": profit
            }).eq("fixture_id", p['fixture_id']).eq("market", market).execute()
        except: pass

    if settled==0:
        print("No settled bets yet")
        return

    hit_rate = wins/settled*100 if settled else 0
    yield_pct = total_profit/total_staked*100 if total_staked else 0
    avg_odds = sum([float(p['bookie_odds']) for p in preds[:settled]])/settled if settled else 0

    print("\n" + "="*50)
    print(f"SETTLED: {settled} bets")
    print(f"WINS: {wins} | LOSSES: {settled-wins}")
    print(f"HIT RATE: {hit_rate:.2f}%")
    print(f"TOTAL PROFIT: {total_profit:.2f} units")
    print(f"YIELD: {yield_pct:.2f}%")
    print(f"AVG ODDS: {avg_odds:.2f}")
    print("="*50)
    for m, d in by_market.items():
        hr = d['wins']/d['staked']*100 if d['staked'] else 0
        y = d['profit']/d['staked']*100 if d['staked'] else 0
        print(f"{m}: {d['staked']} bets, {hr:.1f}% hit, {y:.1f}% yield")

    try:
        today = str(datetime.now(timezone.utc).date())
        supabase.table("profit_daily").upsert({
            "date": today,
            "settled_bets": settled,
            "wins": wins,
            "total_staked": total_staked,
            "total_profit": float(round(total_profit,2)),
            "yield_percent": float(round(yield_pct,2)),
            "hit_rate": float(round(hit_rate,2)),
            "is_profitable": bool(yield_pct>0)
        }, on_conflict="date").execute()
        print(f"\nSaved daily P&L ✅ {today}")
    except Exception as e:
        print(f"P&L save error: {e}")

if __name__=="__main__": main()
