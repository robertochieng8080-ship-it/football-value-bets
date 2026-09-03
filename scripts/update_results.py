import os, sys
from datetime import datetime, timedelta, timezone
from supabase import create_client
import requests

API_FOOTBALL_URL = "https://v3.football.api-sports.io"

def get_supabase():
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def check_market_won(market, hg, ag):
    total = hg + ag
    if market == "Over2.5": return total > 2.5
    if market == "Under2.5": return total < 2.5
    if market == "BTTS_Yes": return hg > 0 and ag > 0
    if market == "BTTS_No": return not (hg > 0 and ag > 0)
    if market == "1_Over2.5": return hg > ag and total > 2.5
    if market == "2_Over2.5": return ag > hg and total > 2.5
    if market == "1": return hg > ag
    if market == "2": return ag > hg
    if market == "X": return hg == ag
    return False

def main():
    print("Running nightly P/L updater - 11 PM EAT")
    supabase = get_supabase()
    
    # Get all PENDING history from last 7 days
    pending = supabase.table("prediction_history").select("*").eq("result","PENDING").execute().data
    if not pending:
        print("No pending bets")
        return

    # Fetch fixtures table which already has yesterday results from morning bot
    fixtures = {f['fixture_id']: f for f in supabase.table("fixtures").select("*").execute().data if f.get('home_goals') is not None}

    updated = 0
    for bet in pending:
        fid = bet.get('fixture_id')
        f = fixtures.get(fid)
        if not f or f.get('home_goals') is None:
            continue # match not finished yet
        
        hg = f['home_goals']; ag = f['away_goals']
        won = check_market_won(bet['market'], hg, ag)
        result = "WON" if won else "LOST"
        profit = (bet['stake'] * bet['bookie_odds'] - bet['stake']) if won else -bet['stake']
        
        supabase.table("prediction_history").update({
            "result": result,
            "profit": round(profit,2),
            "actual_score": f"{hg}-{ag}",
            "actual_home_goals": hg,
            "actual_away_goals": ag
        }).eq("id", bet['id']).execute()
        updated += 1
    
    print(f"Updated {updated} bets")

    # Update ACCA history
    accas = supabase.table("acca_history").select("*").eq("result","PENDING").execute().data
    for acca in accas:
        legs = acca.get('legs', [])
        all_won = True
        any_pending = False
        for leg in legs:
            fid = leg.get('fixture_id')
            f = fixtures.get(fid)
            if not f or f.get('home_goals') is None:
                any_pending = True
                break
            if not check_market_won(leg['market'], f['home_goals'], f['away_goals']):
                all_won = False
                break
        if any_pending: continue
        result = "WON" if all_won else "LOST"
        profit = (acca['stake'] * acca['total_odds'] - acca['stake']) if all_won else -acca['stake']
        supabase.table("acca_history").update({"result": result, "profit": round(profit,2)}).eq("id", acca['id']).execute()

if __name__ == "__main__":
    main()
