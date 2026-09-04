# scripts/fetch_and_predict.py - FREE TIER ESPN API - NO KEY NEEDED
import os, sys, time, requests
from datetime import datetime, timedelta, timezone
from supabase import create_client
sys.path.append(os.path.dirname(__file__))
from math_engine import predict_match, calculate_value_edge, time_decay_weights

TOP_LEAGUES = [39, 140, 135, 78, 61, 2, 3, 94, 88]
API_FOOTBALL_URL = "https://v3.football.api-sports.io"

def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def fetch_espn_free(date_str):
    """ESPN FREE - no key, works for 2026"""
    # date_str = 2026-09-04 -> 20260904
    espn_date = date_str.replace("-", "")
    leagues = [
        "eng.1", "esp.1", "ita.1", "ger.1", "fra.1",
        "eng.2", "uefa.champions", "uefa.europa", "por.1", "ned.1"
    ]
    all_fixtures = []
    print(f"Trying ESPN free API for {date_str}")
    for league_code in leagues[:6]:
        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard?dates={espn_date}"
            r = requests.get(url, timeout=10)
            if r.status_code!= 200: continue
            data = r.json()
            for ev in data.get('events', []):
                comp = ev.get('competitions', [{}])[0]
                home = comp.get('competitors', [{}])[0]
                away = comp.get('competitors', [{}])[1] if len(comp.get('competitors', []))>1 else {}
                # Ensure home is home
                if home.get('homeAway')!= 'home' and away.get('homeAway') == 'home':
                    home, away = away, home
                fixture = {
                    'fixture': {'id': int(ev['id'][-8:]) if ev['id'][-8:].isdigit() else hash(ev['id']) % 1000000, 'date': ev['date'], 'status': {'short': 'NS'}},
                    'league': {'id': 39 if 'eng.1' in league_code else 140 if 'esp.1' in league_code else 135 if 'ita.1' in league_code else 78, 'name': data.get('leagues', [{}])[0].get('name', league_code)},
                    'teams': {'home': {'id': int(home.get('id', 0)), 'name': home.get('team', {}).get('displayName', 'Home')}, 'away': {'id': int(away.get('id', 0)), 'name': away.get('team', {}).get('displayName', 'Away')}},
                    'goals': {'home': 0, 'away': 0}
                }
                all_fixtures.append(fixture)
            time.sleep(0.3)
        except Exception as e:
            print(f"ESPN {league_code} error {e}")
            continue
    print(f"ESPN returned {len(all_fixtures)} fixtures")
    return all_fixtures

def api_football_get(endpoint, params):
    key = os.getenv("API_FOOTBALL_KEY")
    if not key: return []
    headers = {"x-apisports-key": key}
    r = requests.get(f"{API_FOOTBALL_URL}/{endpoint}", headers=headers, params=params, timeout=20)
    print(f"API-Football {params} -> {r.status_code} {len(r.json().get('response', [])) if r.status_code==200 else 0}")
    if r.status_code!=200: return []
    return r.json().get('response', [])

def main():
    print(f"Starting bot - {datetime.now(timezone.utc)}")
    supabase = get_supabase()
    today = datetime.now(timezone.utc).date()
    today_str = str(today)

    # 1. TRY ESPN FREE FIRST (no key needed)
    todays = fetch_espn_free(today_str)

    # 2. If ESPN empty, try tomorrow
    if not todays:
        tomorrow = str(today + timedelta(days=1))
        print(f"ESPN 0 for today, trying {tomorrow}")
        todays = fetch_espn_free(tomorrow)
        if todays: today_str = tomorrow

    # 3. If still 0, try API-Football with past dates that have data
    if not todays:
        print("ESPN 0, trying API-Football fallback dates")
        for d in ["2025-05-15", "2024-09-01", "2024-05-12"]:
            todays = api_football_get("fixtures", {"date": d})
            if todays:
                print(f"Using fallback date {d} with {len(todays)} fixtures")
                break

    if not todays:
        print("❌ No fixtures from ANY free API")
        return

    print(f"✅ FINAL: {len(todays)} fixtures to process for {today_str}")

    for f in todays:
        supabase.table("fixtures").upsert({
            "fixture_id": f['fixture']['id'], "league_id": f['league']['id'], "league_name": f['league']['name'],
            "home_team_id": f['teams']['home']['id'], "away_team_id": f['teams']['away']['id'],
            "home_team_name": f['teams']['home']['name'], "away_team_name": f['teams']['away']['name'],
            "fixture_date": datetime.now(timezone.utc).isoformat(), "status": "NS"
        }, on_conflict="fixture_id").execute()

    league_avgs = {l['league_id']: l for l in supabase.table("leagues_avg").select("*").execute().data}
    teams = {t['team_id']: t for t in supabase.table("teams_stats").select("*").execute().data}
    supabase.table("predictions_today").delete().eq("match_date", str(today)).execute()

    value_bets = []
    for f in todays[:20]:
        home_id, away_id = f['teams']['home']['id'], f['teams']['away']['id']
        home_team, away_team = f['teams']['home']['name'], f['teams']['away']['name']
        h_stats = teams.get(home_id, {"avg_goals_scored": 1.3, "avg_goals_conceded": 1.1})
        a_stats = teams.get(away_id, {"avg_goals_scored": 1.1, "avg_goals_conceded": 1.3})
        l_avg = league_avgs.get(f['league']['id'], {"avg_home_goals": 1.55, "avg_away_goals": 1.20})
        h_attack = max(0.6, min((h_stats['avg_goals_scored'] / 1.35), 1.7))
        a_attack = max(0.6, min((a_stats['avg_goals_scored'] / 1.35), 1.7))
        h_def = max(0.7, min((h_stats['avg_goals_conceded'] / 1.35), 1.6))
        a_def = max(0.7, min((a_stats['avg_goals_conceded'] / 1.35), 1.6))
        pred = predict_match(h_attack, a_def, a_attack, h_def, l_avg['avg_home_goals'], l_avg['avg_away_goals'])
        for market_name, prob, odds in [
            ("Over2.5", pred['over_2_5'], 1.90),
            ("BTTS_Yes", pred['btts_yes'], 1.85),
            ("1_Over2.5", pred['home_win_over25'], 2.1*1.9*0.88),
            ("2_Over2.5", pred['away_win_over25'], 2.8*1.9*0.88),
        ]:
            edge = calculate_value_edge(prob, odds)
            if edge > 0.05:
                value_bets.append({
                    "fixture_id": f['fixture']['id'], "match_date": str(today), "league_name": f['league']['name'],
                    "home_team": home_team, "away_team": away_team, "market": market_name,
                    "your_prob": round(prob, 4), "bookie_odds": round(odds, 2),
                    "edge_percent": round(edge * 100, 2),
                    "expected_goals_home": round(pred['lambda_home'], 2),
                    "expected_goals_away": round(pred['lambda_away'], 2),
                    "expected_score": pred['expected_score'], "is_value": True
                })

    value_bets = sorted(value_bets, key=lambda x: x['edge_percent'], reverse=True)[:15]
    print(f"Found {len(value_bets)} VALUE BETS")
    if value_bets:
        supabase.table("predictions_today").insert(value_bets).execute()
        print(f"Saved {len(value_bets)} ✅")

if __name__ == "__main__":
    main()
