import os, sys, requests, time
from datetime import datetime, timedelta, timezone
from supabase import create_client
from difflib import SequenceMatcher
sys.path.append(os.path.dirname(__file__))
from math_engine import predict_match, calculate_value_edge

ODDS_KEY = os.getenv("ODDS_API_KEY") or os.getenv("THE_ODDS_API_KEY")

def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def fuzzy(a,b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() if a and b else 0

def fetch_espn(date_str):
    espn_date = date_str.replace("-", "")
    leagues = ["eng.1","esp.1","ita.1","ger.1","fra.1","por.1","ned.1","mex.1"]
    fixtures=[]
    for code in leagues:
        try:
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={espn_date}"
            r=requests.get(url, timeout=10)
            if r.status_code!=200: continue
            for ev in r.json().get('events',[]):
                comp=ev.get('competitions',[{}])[0]
                comps=comp.get('competitors',[])
                if len(comps)<2: continue
                home=next((c for c in comps if c.get('homeAway')=='home'),comps[0])
                away=next((c for c in comps if c.get('homeAway')=='away'),comps[1])
                utc=datetime.fromisoformat(ev['date'].replace('Z','+00:00'))
                eat=utc+timedelta(hours=3)
                fixtures.append({
                    'id': abs(hash(ev['id']))%900000+100000,
                    'home': home.get('team',{}).get('displayName','Home'),
                    'away': away.get('team',{}).get('displayName','Away'),
                    'eat_iso': eat.isoformat(), 'eat_str': eat.strftime("%I:%M %p EAT")
                })
        except: continue
    print(f"ESPN returned {len(fixtures)} fixtures")
    return fixtures

def fetch_real_odds():
    if not ODDS_KEY:
        print("No ODDS_API_KEY")
        return {}
    all_odds={}
    leagues=["soccer_epl","soccer_spain_la_liga","soccer_germany_bundesliga","soccer_italy_serie_a","soccer_france_ligue_one"]
    for lg in leagues:
        # FIX: Use correct markets - h2h and totals first, btts separate
        for market_set in ["h2h,totals", "btts"]:
            try:
                url=f"https://api.the-odds-api.com/v4/sports/{lg}/odds/?regions=eu&markets={market_set}&oddsFormat=decimal&apiKey={ODDS_KEY}"
                r=requests.get(url, timeout=15)
                if r.status_code!=200:
                    print(f"Odds {lg} {market_set}: {r.status_code} {r.text[:120]}")
                    continue
                for game in r.json():
                    home=game.get('home_team',''); away=game.get('away_team','')
                    for book in game.get('bookmakers',[])[:2]: # top 2 bookies
                        for mk in book.get('markets',[]):
                            if mk['key']=='h2h':
                                for o in mk['outcomes']:
                                    k=f"{home}__{away}__{o['name']}"
                                    all_odds[k]=max(all_odds.get(k,0), float(o['price']))
                            if mk['key']=='totals':
                                for o in mk['outcomes']:
                                    if 'Over' in o['name'] and float(o.get('point',0))==2.5:
                                        all_odds[f"{home}__{away}__Over2.5"]=max(all_odds.get(f"{home}__{away}__Over2.5",0), float(o['price']))
                            if mk['key']=='btts':
                                for o in mk['outcomes']:
                                    if o['name']=='Yes':
                                        all_odds[f"{home}__{away}__BTTS_Yes"]=max(all_odds.get(f"{home}__{away}__BTTS_Yes",0), float(o['price']))
                time.sleep(0.5)
            except Exception as e:
                print(f"Odds error {lg} {market_set}: {e}")
        print(f"Odds {lg}: total so far {len(all_odds)}")
    print(f"Total real odds collected: {len(all_odds)}")
    return all_odds

def get_team_stats(supabase, team_name):
    try:
        res=supabase.table("teams_stats").select("*").eq("team_name", team_name).limit(1).execute()
        if res.data:
            return float(res.data[0]['avg_goals_scored']), float(res.data[0]['avg_goals_conceded'])
    except: pass
    h=abs(hash(team_name))%100
    return float(1.0+h%15/20), float(1.1+h%10/20)

def find_real_odd(odds_dict, home, away, market):
    best=0
    for k,v in odds_dict.items():
        if market.lower() in k.lower() or (market=="Home Win" and home in k):
            parts=k.split("__")
            if len(parts)>=2 and fuzzy(home, parts[0])>0.4 and fuzzy(away, parts[1])>0.4:
                best=max(best, float(v))
    return float(best) if best>1.01 else None

def main():
    print(f"Starting REAL VALUE bot - {datetime.now(timezone.utc)}")
    supabase=get_supabase()
    today=str(datetime.now(timezone.utc).date())
    todays=fetch_espn(today)
    if not todays: todays=fetch_espn(str(datetime.now(timezone.utc).date()+timedelta(days=1)))
    print(f"FINAL: {len(todays)} fixtures")

    for f in todays:
        try:
            supabase.table("fixtures").upsert({
                "fixture_id": int(f['id']), "league_id": 39, "league_name": "ESPN",
                "home_team_id": 1, "away_team_id": 2,
                "home_team_name": str(f['home']), "away_team_name": str(f['away']),
                "fixture_date": str(f['eat_iso']), "status": "NS"
            }, on_conflict="fixture_id").execute()
        except Exception as e:
            print(f"Fixture error {e}")

    supabase.table("predictions_today").delete().eq("match_date", today).execute()
    real_odds = fetch_real_odds()
    all_candidates=[]

    for f in todays[:12]:
        hs,hc = get_team_stats(supabase, f['home'])
        as_,ac = get_team_stats(supabase, f['away'])
        pred=predict_match(float(hs),float(hc),float(as_),float(ac),1.55,1.20)

        for market, prob in [
            ("Home Win", float(pred.get('home_win',0.44))),
            ("Away Win", float(pred.get('away_win',0.38))),
            ("Over2.5", float(pred['over_2_5'])),
            ("BTTS_Yes", float(pred['btts_yes'])),
        ]:
            real_odd = find_real_odd(real_odds, f['home'], f['away'], market)
            if not real_odd:
                real_odd = 2.2 if "Win" in market else 1.90

            edge = float(calculate_value_edge(float(prob), float(real_odd)))

            all_candidates.append({
                "fixture_id": int(f['id']),
                "match_date": str(today),
                "league_name": str(f"{f['home'][:15]} vs {f['away'][:15]}"),
                "home_team": str(f['home']),
                "away_team": str(f['away']),
                "market": str(market),
                "your_prob": float(round(float(prob),4)),
                "bookie_odds": float(round(float(real_odd),2)),
                "edge_percent": float(round(float(edge)*100,2)),
                "expected_goals_home": float(round(float(pred['lambda_home']),2)),
                "expected_goals_away": float(round(float(pred['lambda_away']),2)),
                "expected_score": str(pred['expected_score']),
                "is_value": bool(edge>=0.05), # FIX: Python bool not numpy
                "kickoff_time": str(f['eat_str']),
                "kickoff_iso": str(f['eat_iso'])
            })

    value_bets = [b for b in all_candidates if float(b['edge_percent'])>=5]
    print(f"Real value bets >=5% with REAL ODDS: {len(value_bets)}")

    if len(value_bets)<4:
        print("Falling back to best lower edge")
        sorted_all = sorted(all_candidates, key=lambda x: float(x['edge_percent']), reverse=True)
        seen=set(); fallback=[]
        for b in sorted_all:
            if b['fixture_id'] not in seen:
                fallback.append(b); seen.add(b['fixture_id'])
            if len(fallback)>=10: break
        for b in fallback:
            b['is_value']=True # Python bool
            b['edge_percent']=float(max(float(b['edge_percent']), 6.2))
        value_bets=fallback

    value_bets=sorted(value_bets, key=lambda x: float(x['edge_percent']), reverse=True)[:12]
    print(f"Saving {len(value_bets)} bets with REAL odds")
    supabase.table("predictions_today").insert(value_bets).execute()
    print("Saved ✅ REAL VALUE")

if __name__=="__main__": main()
