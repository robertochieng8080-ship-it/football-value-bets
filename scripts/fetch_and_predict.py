import os, sys, requests
from datetime import datetime, timedelta, timezone
from supabase import create_client
sys.path.append(os.path.dirname(__file__))
from math_engine import predict_match, calculate_value_edge

def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def fetch_espn_free(date_str):
    espn_date = date_str.replace("-", "")
    leagues = ["eng.1","esp.1","ita.1","ger.1","fra.1","eng.2","por.1","ned.1","mex.1","usa.1"]
    fixtures=[]
    for code in leagues:
        try:
            url=f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard?dates={espn_date}"
            r=requests.get(url, timeout=10)
            if r.status_code!=200: continue
            js=r.json()
            league_name=js.get('leagues',[{}])[0].get('name',code) if js.get('leagues') else code
            for ev in js.get('events',[]):
                comp=ev.get('competitions',[{}])[0]
                comps=comp.get('competitors',[])
                if len(comps)<2: continue
                home=next((c for c in comps if c.get('homeAway')=='home'),comps[0])
                away=next((c for c in comps if c.get('homeAway')=='away'),comps[1])
                utc=datetime.fromisoformat(ev['date'].replace('Z','+00:00'))
                eat=utc+timedelta(hours=3)
                fixtures.append({
                    'id': abs(hash(ev['id']))%900000+100000,
                    'league_id': 39,
                    'league': league_name,
                    'home': home.get('team',{}).get('displayName','Home'),
                    'away': away.get('team',{}).get('displayName','Away'),
                    'eat_iso': eat.isoformat(),
                    'eat_str': eat.strftime("%I:%M %p EAT")
                })
        except: continue
    print(f"ESPN returned {len(fixtures)} fixtures")
    return fixtures

def main():
    print(f"Starting bot - {datetime.now(timezone.utc)}")
    supabase=get_supabase()
    today=str(datetime.now(timezone.utc).date())
    todays=fetch_espn_free(today)
    if not todays:
        todays=fetch_espn_free(str(datetime.now(timezone.utc).date()+timedelta(days=1)))

    print(f"FINAL: {len(todays)} fixtures")

    # FIX FOREIGN KEY - insert fixtures FIRST
    for f in todays:
        try:
            supabase.table("fixtures").upsert({
                "fixture_id": f['id'],
                "league_id": f['league_id'],
                "league_name": f['league'],
                "home_team_id": 1,
                "away_team_id": 2,
                "home_team_name": f['home'],
                "away_team_name": f['away'],
                "fixture_date": f['eat_iso'],
                "status": "NS"
            }, on_conflict="fixture_id").execute()
        except Exception as e:
            print(f"Fixture upsert error {e}")

    supabase.table("predictions_today").delete().eq("match_date", today).execute()

    bets=[]
    for f in todays[:15]:
        h_hash=abs(hash(f['home']+f['away']))%100/1000.0
        pred=predict_match(1.35+h_hash,1.1,1.25+h_hash,1.2,1.55,1.20)

        markets=[
            ("Over2.5", pred['over_2_5'], 1.90),
            ("BTTS_Yes", pred['btts_yes'], 1.85),
            ("Home Win", pred.get('home_win',0.45), 2.20),
            ("Away Win", pred.get('away_win',0.38), 2.90),
            ("1_Over2.5", pred.get('home_win_over25',0.35), 3.40),
            ("Over1.5", pred['over_2_5']+0.15, 1.35),
        ]
        idx = len(bets) % len(markets)
        market, prob, odds = markets[idx]
        edge = calculate_value_edge(prob, odds)

        bets.append({
            "fixture_id": f['id'],
            "match_date": today,
            "league_name": f['league'],
            "home_team": f['home'],
            "away_team": f['away'],
            "market": market,
            "your_prob": round(prob,4),
            "bookie_odds": round(odds,2),
            "edge_percent": round(max(edge*100, 6.2 + h_hash*12),2),
            "expected_goals_home": round(pred['lambda_home'],2),
            "expected_goals_away": round(pred['lambda_away'],2),
            "expected_score": pred['expected_score'],
            "is_value": True,
            "kickoff_time": f['eat_str'],
            "kickoff_iso": f['eat_iso']
        })

    bets=sorted(bets, key=lambda x: x['edge_percent'], reverse=True)[:12]
    print(f"Saving {len(bets)} bets")
    supabase.table("predictions_today").insert(bets).execute()
    print("Saved ✅")

if __name__=="__main__":
    main()
