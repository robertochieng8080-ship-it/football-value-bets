import os, requests
from datetime import datetime, timezone
from supabase import create_client

FOOTBALL_TOKEN = os.getenv("FOOTBALL_DATA_TOKEN")
BASE = "https://api.football-data.org/v4"

def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def get_team_form(team_name):
    """Fetch real form from football-data.org, fallback to estimated"""
    if not FOOTBALL_TOKEN:
        return None
    try:
        headers = {"X-Auth-Token": FOOTBALL_TOKEN}
        for comp in ["PL","PD","BL1","SA","FL1","PPL","DED","BSA"]:
            url = f"{BASE}/competitions/{comp}/matches?status=FINISHED&limit=20"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200: continue
            matches = r.json().get('matches',[])
            team_matches = [m for m in matches if team_name.lower() in m['homeTeam']['name'].lower() or team_name.lower() in m['awayTeam']['name'].lower() or m['homeTeam']['shortName'] and team_name.lower() in m['homeTeam']['shortName'].lower()]
            if team_matches:
                scored=[]; conceded=[]
                for m in team_matches[:10]:
                    is_home = team_name.lower() in m['homeTeam']['name'].lower() or (m['homeTeam']['shortName'] and team_name.lower() in m['homeTeam']['shortName'].lower())
                    hs = m['score']['fullTime']['home'] or 0
                    as_ = m['score']['fullTime']['away'] or 0
                    if is_home:
                        scored.append(hs); conceded.append(as_)
                    else:
                        scored.append(as_); conceded.append(hs)
                if scored:
                    avg_s = sum(scored)/len(scored)
                    avg_c = sum(conceded)/len(conceded)
                    return float(avg_s), float(avg_c)
    except Exception as e:
        print(f"Form fetch error {team_name}: {e}")
    return None

def main():
    print(f"Updating 20 teams - {datetime.now(timezone.utc)}")
    supabase = get_supabase()
    
    try:
        fixtures = supabase.table("fixtures").select("home_team_name,away_team_name").limit(100).execute().data
        teams = set()
        for f in fixtures:
            if f.get('home_team_name'): teams.add(f['home_team_name'])
            if f.get('away_team_name'): teams.add(f['away_team_name'])
        teams = list(teams)[:20]
    except:
        teams = ["AJ Auxerre","AS Monaco","VfB Stuttgart","FC Porto","Sparta Rotterdam","Como","Pachuca","Genoa","Ipswich Town","Liverpool","Real Betis","PEC Zwolle","New York City FC","Paris Saint-Germain","FC Juarez","Nashville SC","Moreirense","Lyon","Real Madrid","FC Cologne"]
    
    print(f"Updating {len(teams)} teams")
    
    for team in teams:
        real_form = get_team_form(team)
        if real_form:
            avg_scored, avg_conceded = real_form
            print(f"REAL {team}: {avg_scored} scored, {avg_conceded} conceded")
        else:
            h = abs(hash(team)) % 100
            avg_scored = float(1.0 + h % 15 / 20)
            avg_conceded = float(1.1 + h % 10 / 20)
            print(f"EST {team}: {avg_scored}/{avg_conceded}")
        
        # FIXED: upsert on team_name not team_id to avoid duplicate key error
        try:
            supabase.table("teams_stats").upsert({
                "team_name": str(team),
                "avg_goals_scored": float(avg_scored),
                "avg_goals_conceded": float(avg_conceded),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, on_conflict="team_name").execute()
            print(f"Saved {team} ✅")
        except Exception as e:
            print(f"Upsert error {team}: {e}")
            try:
                existing = supabase.table("teams_stats").select("team_name").eq("team_name", team).execute()
                if existing.data:
                    supabase.table("teams_stats").update({
                        "avg_goals_scored": float(avg_scored),
                        "avg_goals_conceded": float(avg_conceded),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }).eq("team_name", team).execute()
                    print(f"Updated {team} via update ✅")
                else:
                    supabase.table("teams_stats").insert({
                        "team_name": str(team),
                        "avg_goals_scored": float(avg_scored),
                        "avg_goals_conceded": float(avg_conceded)
                    }).execute()
                    print(f"Inserted {team} ✅")
            except Exception as e2:
                print(f"Second attempt failed {team}: {e2}")
    
    print("Stats updated")

if __name__ == "__main__":
    main()
