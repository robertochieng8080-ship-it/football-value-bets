# scripts/fetch_and_predict.py - FULL WITH FALLBACK TO ALL LEAGUES
import os
import sys
import time
import requests
from datetime import datetime, timedelta, timezone
from supabase import create_client

sys.path.append(os.path.dirname(__file__))
from math_engine import predict_match, calculate_value_edge, time_decay_weights

TOP_LEAGUES = [39, 140, 135, 78, 61, 2, 3, 94, 88, 144]
API_FOOTBALL_URL = "https://v3.football.api-sports.io"

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise Exception("Missing SUPABASE_URL or SERVICE_KEY")
    return create_client(url, key)

def api_football_get(endpoint, params):
    key = os.getenv("API_FOOTBALL_KEY")
    print(f"DEBUG KEY present={bool(key)} len={len(key) if key else 0}")
    if not key:
        print("❌ API_FOOTBALL_KEY MISSING!")
        return None
    headers = {"x-apisports-key": key}
    r = requests.get(f"{API_FOOTBALL_URL}/{endpoint}", headers=headers, params=params, timeout=20)
    print(f"API status={r.status_code} remaining={r.headers.get('x-ratelimit-requests-remaining','?')}")
    if r.status_code!= 200:
        print(f"API error {r.status_code}: {r.text[:500]}")
        return None
    response = r.json().get('response', [])
    print(f"API returned {len(response)} fixtures for {params}")
    return response

def update_team_form(supabase, team_id, team_name, league_id, league_name, gf, ga, is_home):
    existing = supabase.table("teams_stats").select("*").eq("team_id", team_id).execute()
    form = existing.data[0].get('form_last_10', []) if existing.data else []
    new_entry = {"gf": gf, "ga": ga, "is_home": is_home, "date": datetime.now(timezone.utc).isoformat()}
    form = [new_entry] + form
    form = form[:10]
    weights = time_decay_weights(len(form), 0.88)
    avg_scored = sum(f['gf'] * w for f, w in zip(form, weights))
    avg_conceded = sum(f['ga'] * w for f, w in zip(form, weights))
    payload = {
        "team_id": team_id, "team_name": team_name, "league_id": league_id, "league_name": league_name,
        "avg_goals_scored": avg_scored, "avg_goals_conceded": avg_conceded,
        "form_last_10": form, "games_played": len(form),
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
    supabase.table("teams_stats").upsert(payload, on_conflict="team_id").execute()
    return payload

def fetch_odds_the_odds_api():
    key = os.getenv("THE_ODDS_API_KEY")
    if not key:
        print("No THE_ODDS_API_KEY, using fallback 1.90")
        return {}
    odds_map = {}
    for sport in ["soccer_epl", "soccer_spain_la_liga"]:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={key}&regions=eu,uk&markets=h2h,totals,btts&oddsFormat=decimal"
            r = requests.get(url, timeout=15)
            if r.status_code!=200: continue
            for match in r.json():
                home, away = match['home_team'], match['away_team']
                key_name = f"{home} vs {away}".lower()
                over25 = btts_yes = h2h_home = h2h_away = None
                for bm in match.get('bookmakers', [])[:2]:
                    for mk in bm.get('markets', []):
                        if mk['key']=='totals' and not over25:
                            for o in mk['outcomes']:
                                if o['name']=='Over' and o['point']==2.5: over25=o['price']
                        if mk['key']=='btts' and not btts_yes:
                            for o in mk['outcomes']:
                                if o['name']=='Yes': btts_yes=o['price']
                        if mk['key']=='h2h':
                            for o in mk['outcomes']:
                                if o['name']==home: h2h_home=o['price']
                                if o['name']==away: h2h_away=o['price']
                odds_map[key_name] = {"over25": over25 or 1.90, "btts_yes": btts_yes or 1.85, "home": h2h_home or 2.0, "away": h2h_away or 2.5}
            time.sleep(1)
        except Exception as e:
            print(f"Odds error: {e}")
    return odds_map

def main():
    print(f"Starting bot - {datetime.now(timezone.utc)}")
    supabase = get_supabase()
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    print(f"Fetching results for {yesterday}...")
    y_results = api_football_get("fixtures", {"date": str(yesterday)})
    if y_results:
        for f in y_results:
            if f['fixture']['status']['short']!='FT': continue
            if f['league']['id'] not in TOP_LEAGUES: continue
            home_id, away_id = f['teams']['home']['id'], f['teams']['away']['id']
            hg, ag = f['goals']['home'] or 0, f['goals']['away'] or 0
            supabase.table("fixtures").upsert({
                "fixture_id": f['fixture']['id'], "league_id": f['league']['id'], "league_name": f['league']['name'],
                "home_team_id": home_id, "away_team_id": away_id,
                "home_team_name": f['teams']['home']['name'], "away_team_name": f['teams']['away']['name'],
                "fixture_date": f['fixture']['date'], "status": "FT", "home_goals": hg, "away_goals": ag
            }, on_conflict="fixture_id").execute()
            update_team_form(supabase, home_id, f['teams']['home']['name'], f['league']['id'], f['league']['name'], hg, ag, True)
            update_team_form(supabase, away_id, f['teams']['away']['name'], f['league']['id'], f['league']['name'], ag, hg, False)

    # === FETCH WITH 3-DAY RETRY + FALLBACK ===
    print(f"Fetching fixtures for {today}...")
    todays = api_football_get("fixtures", {"date": str(today)})

    if not todays:
        tomorrow = today + timedelta(days=1)
        print(f"No fixtures {today}, trying {tomorrow}")
        todays = api_football_get("fixtures", {"date": str(tomorrow)})
        if todays: today = tomorrow

    if not todays:
        day_after = today + timedelta(days=2)
        print(f"Still empty, trying {day_after}")
        todays = api_football_get("fixtures", {"date": str(day_after)})
        if todays: today = day_after

    if not todays:
        print("❌ No fixtures at all in next 3 days - API may be down")
        return

    # FALLBACK LOGIC FOR MAJOR LEAGUES
    major_count = len([f for f in todays if f['league']['id'] in TOP_LEAGUES])
    print(f"Total {len(todays)} fixtures, {major_count} in major leagues")

    if major_count == 0 and len(todays) > 0:
        print(f"⚠️ NO MAJOR LEAGUES TODAY - FALLING BACK TO ALL {len(todays)} LEAGUES")
        ACTIVE_LEAGUES = None # None = accept all leagues
    else:
        print(f"✅ Using major leagues filter: {TOP_LEAGUES}")
        ACTIVE_LEAGUES = TOP_LEAGUES

    # Save fixtures
    for f in todays:
        if ACTIVE_LEAGUES is not None and f['league']['id'] not in ACTIVE_LEAGUES:
            continue
        supabase.table("fixtures").upsert({
            "fixture_id": f['fixture']['id'], "league_id": f['league']['id'], "league_name": f['league']['name'],
            "home_team_id": f['teams']['home']['id'], "away_team_id": f['teams']['away']['id'],
            "home_team_name": f['teams']['home']['name'], "away_team_name": f['teams']['away']['name'],
            "fixture_date": f['fixture']['date'], "status": f['fixture']['status']['short']
        }, on_conflict="fixture_id").execute()

    odds_map = fetch_odds_the_odds_api()
    print(f"Odds loaded {len(odds_map)}")

    league_avgs = {l['league_id']: l for l in supabase.table("leagues_avg").select("*").execute().data}
    teams = {t['team_id']: t for t in supabase.table("teams_stats").select("*").execute().data}
    supabase.table("predictions_today").delete().eq("match_date", str(today)).execute()

    value_bets = []
    for f in todays:
        if ACTIVE_LEAGUES is not None and f['league']['id'] not in ACTIVE_LEAGUES:
            continue
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
        odds_key = f"{home_team} vs {away_team}".lower()
        o = odds_map.get(odds_key, {"over25": 1.90, "btts_yes": 1.85, "home": 2.1, "away": 2.8})
        for market_name, prob, odds in [
            ("Over2.5", pred['over_2_5'], o['over25']),
            ("BTTS_Yes", pred['btts_yes'], o['btts_yes']),
            ("1_Over2.5", pred['home_win_over25'], o['home'] * o['over25'] * 0.88),
            ("2_Over2.5", pred['away_win_over25'], o['away'] * o['over25'] * 0.88),
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
        print("Saved predictions_today ✅")
        history_rows = [{
            "date": b["match_date"], "fixture_id": b["fixture_id"], "league": b["league_name"],
            "home_team": b["home_team"], "away_team": b["away_team"], "market": b["market"],
            "your_prob": b["your_prob"], "bookie_odds": b["bookie_odds"], "edge": b["edge_percent"],
            "stake": 100, "result": "PENDING", "profit": 0, "expected_score": b["expected_score"]
        } for b in value_bets]
        supabase.table("prediction_history").delete().eq("date", str(today)).eq("result", "PENDING").execute()
        supabase.table("prediction_history").insert(history_rows).execute()
        print(f"Archived {len(history_rows)} ✅")
    else:
        print("No value today")

if __name__ == "__main__":
    main()
