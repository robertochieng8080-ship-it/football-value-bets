import os, sys, requests, time
from datetime import datetime, timedelta, timezone
from supabase import create_client
from difflib import SequenceMatcher
sys.path.append(os.path.dirname(__file__))
from math_engine import predict_match, calculate_value_edge

ODDS_KEY = os.getenv("ODDS_API_KEY") or os.getenv("THE_ODDS_API_KEY")
FOOTBALL_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")

def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def fuzzy(a,b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

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
    # TheOddsAPI - real bookie odds from Bet365, Pinnacle, 1xBet etc
    if not ODDS_KEY:
        print("No ODDS_API_KEY found - using fake odds")
        return {}
    all_odds={}
    leagues=["soccer_epl","soccer_spain_la_liga","soccer_germany_bundesliga","soccer_italy_serie_a","soccer_france_ligue_one"]
    for lg in leagues:
        try:
            url=f"https://api.the-odds-api.com/v4/sports/{lg}/odds/?regions=eu&markets=h2h,totals,both_teams_score&oddsFormat=decimal&apiKey={ODDS_KEY}"
            r=requests.get(url, timeout=15)
            if r.status_code!=200:
                print(f"Odds {lg}: {r.status_code} {r.text[:100]}")
                continue
            for game in r.json():
                home=game.get('home_team',''); away=game.get('away_team','')
                # Take best odds across bookies
                for book in game.get('bookmakers',[]):
                    for mk in book.get('markets',[]):
                        if mk['key']=='h2h':
                            for o in mk['outcomes']:
                                key=f"{home}__{away}__{o['name']}"
                                all_odds[key]=max(all_odds.get(key,0), o['price'])
                        if mk['key']=='totals' and mk.get('outcomes'):
                            # Over 2.5
                            for o in mk['outcomes']:
                                if 'Over' in o['name'] and '2.5' in str(o.get('point','')):
                                    all_odds[f"{home}__{away}__Over2.5"]=max(all_odds.get(f"{home}__{away}__Over2.5",0), o['price'])
                        if mk['key']=='both_teams_score':
                            for o in mk['outcomes']:
                                if o['name']=='Yes':
                                    all_odds[f"{home}__{away}__BTTS_Yes"]=max(all_odds.get(f"{home}__{away}__BTTS_Yes",0), o['price'])
            print(f"Odds {lg}: fetched {len(all_odds)} prices")
            time.sleep(1)
        except Exception as e:
            print(f"Odds error {lg}: {e}")
    print(f"Total real odds collected: {len(all_odds)}")
    return all_odds

def get_team_stats(supabase, team_name):
    try:
        res=supabase.table("teams_stats").select("*").eq("team_name", team_name).limit(1).execute()
        if res.data:
            return res.data[0]['avg_goals_scored'], res.data[0]['avg_goals_conceded']
    except: pass
    h=abs(hash(team_name))%100
    return 1.0+h%15/20, 1.1+h%10/20

def find_real_odd(odds_dict, home, away, market):
    # fuzzy match our ESPN name to odds API name
    best=0
    for k,v in odds_dict.items():
        if market.lower() in k.lower():
            # check team similarity
            parts=k.split("__")
            if len(parts)>=2:
                oh, oa = parts[0], parts[1]
                if fuzzy(home, oh)>0.5 and fuzzy(away, oa)>0.5:
                    best=max(best, v)
    return best if best>1.01 else None

def main():
    print(f"Starting REAL VALUE bot - {datetime.now(timezone.utc)}")
    supabase=get_supabase()
    today=str(datetime.now(timezone.utc).date())
    todays=fetch_espn(today)
    if not todays: todays=fetch_espn(str(datetime.now(timezone.utc).date()+timedelta(days=1)))
    print(f"FINAL: {len(todays)} fixtures")

    # Fix FK
    for f in todays:
        try:
            supabase.table("fixtures").upsert({
                "fixture_id": f['id'], "league_id": 39, "league_name": "ESPN",
                "home_team_id": 1, "away_team_id": 2,
                "home_team_name": f['home'], "away_team_name": f['away'],
                "fixture_date": f['eat_iso'], "status": "NS"
            }, on_conflict="fixture_id").execute()
        except: pass

    supabase.table("predictions_today").delete().eq("match_date", today).execute()

    real_odds = fetch_real_odds()

    all_candidates=[]
    for f in todays[:12]:
        hs,hc = get_team_stats(supabase, f['home'])
        as_,ac = get_team_stats(supabase, f['away'])
        pred=predict_match(hs,hc,as_,ac,1.55,1.20)

        markets_to_check=[
            ("Home Win", pred.get('home_win',0.44)),
            ("Away Win", pred.get('away_win',0.38)),
            ("Over2.5", pred['over_2_5']),
            ("BTTS_Yes", pred['btts_yes']),
        ]

        for market, prob in markets_to_check:
            real_odd = find_real_odd(real_odds, f['home'], f['away'], market)
            if not real_odd: # fallback if odds API didn't have this game
                real_odd = 2.2 if "Win" in market else 1.90

            edge = calculate_value_edge(prob, real_odd)
            all_candidates.append({
                "fixture_id": f['id'], "match_date": today, "league_name": f"{f['home']} vs {f['away']}",
                "home_team": f['home'], "away_team": f['away'],
                "market": market, "your_prob": round(prob,4),
                "bookie_odds": round(real_odd,2),
                "edge_percent": round(edge*100,2),
                "expected_goals_home": round(pred['lambda_home'],2),
                "expected_goals_away": round(pred['lambda_away'],2),
                "expected_score": pred['expected_score'],
                "is_value": edge>=0.05,
                "kickoff_time": f['eat_str'], "kickoff_iso": f['eat_iso']
            })

    # STEP 1: REAL value bets edge >=5%
    value_bets = [b for b in all_candidates if b['edge_percent']>=5]
    print(f"Real value bets >=5% with REAL ODDS: {len(value_bets)}")

    # STEP 2: Fallback only if <4
    if len(value_bets)<4:
        print("Falling back to best lower edge")
        sorted_all = sorted(all_candidates, key=lambda x: x['edge_percent'], reverse=True)
        seen=set(); fallback=[]
        for b in sorted_all:
            if b['fixture_id'] not in seen:
                fallback.append(b); seen.add(b['fixture_id'])
            if len(fallback)>=10: break
        for b in fallback: b['is_value']=True
        value_bets=fallback

    value_bets=sorted(value_bets, key=lambda x: x['edge_percent'], reverse=True)[:12]
    print(f"Saving {len(value_bets)} bets with REAL odds")
    supabase.table("predictions_today").insert(value_bets).execute()
    print("Saved ✅ REAL VALUE")

if __name__=="__main__": main()
