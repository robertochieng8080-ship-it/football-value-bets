# scripts/math_engine.py - ADVANCED POISSON + DIXON-COLES + TIME DECAY
# Free-tier, no API calls needed for math
import math
import numpy as np
from scipy.stats import poisson

# CRITICAL CONSTANT - Dixon-Coles draw adjustment
# 0.10 - 0.15 is industry standard. 0.13 = best for quality > quantity
DIXON_COLES_RHO = 0.13
MAX_GOALS = 7 # 0-7 matrix covers 99.9% of games

def time_decay_weights(n=10, decay=0.88):
    """
    Most recent game = weight 1.0
    10th game = decay^9 = much less
    decay 0.88 = aggressive recency, perfect for form teams
    """
    weights = [decay ** i for i in range(n)]
    total = sum(weights)
    return [w / total for w in weights] # normalized to sum to 1

def calculate_weighted_stats(form_list, is_home_filter=None):
    """
    form_list: list of dicts from teams_stats.form_last_10
    e.g. [{"gf":2, "ga":1, "is_home":True, "date":"2026-09-01"},...]
    Most recent first (index 0 = most recent)
    Returns: weighted_avg_scored, weighted_avg_conceded
    """
    if not form_list:
        return 0, 0

    # Filter for home/away if needed
    if is_home_filter is not None:
        filtered = [g for g in form_list if g.get('is_home') == is_home_filter]
        # If not enough home games, fallback to all games
        if len(filtered) < 3:
            filtered = form_list
    else:
        filtered = form_list

    filtered = filtered[:10] # only last 10
    weights = time_decay_weights(len(filtered), decay=0.88)

    scored = sum(g.get('gf', 0) * w for g, w in zip(filtered, weights))
    conceded = sum(g.get('ga', 0) * w for g, w in zip(filtered, weights))

    return scored, conceded

def get_poisson_matrix(lambda_home, lambda_away, max_goals=MAX_GOALS):
    """Builds 8x8 scoreline probability matrix"""
    home_probs = [poisson.pmf(i, lambda_home) for i in range(max_goals + 1)]
    away_probs = [poisson.pmf(j, lambda_away) for j in range(max_goals + 1)]

    matrix = np.outer(home_probs, away_probs)
    return matrix

def dixon_coles_correction(matrix, lambda_home, lambda_away, rho=DIXON_COLES_RHO):
    """
    THE SECRET SAUCE - Fixes bookies underestimating 0-0,1-0,0-1,1-1
    """
    corrected = matrix.copy()

    # Apply tau correction only to low scores
    for i in range(2):
        for j in range(2):
            if i == 0 and j == 0:
                tau = 1 - (lambda_home * lambda_away * rho)
            elif i == 0 and j == 1:
                tau = 1 + (lambda_away * rho)
            elif i == 1 and j == 0:
                tau = 1 + (lambda_home * rho)
            elif i == 1 and j == 1:
                tau = 1 - rho

            # Prevent negative probs
            tau = max(tau, 0.1)
            corrected[i, j] = matrix[i, j] * tau

    # Renormalize to 1.0
    corrected = corrected / corrected.sum()
    return corrected

def calculate_markets_from_matrix(matrix):
    """From 0-7 matrix, extract your 3 markets"""
    over25 = 0
    btts_yes = 0
    home_win = 0
    away_win = 0
    draw = 0
    home_win_over25 = 0
    away_win_over25 = 0

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            p = matrix[i, j]
            total = i + j

            if total > 2.5:
                over25 += p
            if i > 0 and j > 0:
                btts_yes += p
            if i > j:
                home_win += p
                if total > 2.5:
                    home_win_over25 += p
            elif i < j:
                away_win += p
                if total > 2.5:
                    away_win_over25 += p
            else:
                draw += p

    return {
        "over_2_5": over25,
        "btts_yes": btts_yes,
        "home_win": home_win,
        "away_win": away_win,
        "draw": draw,
        "home_win_over25": home_win_over25,
        "away_win_over25": away_win_over25,
    }

def predict_match(home_attack_home, away_defense_away, away_attack_away, home_defense_home, league_avg_home, league_avg_away):
    """
    Core xG Formula: xG = Attack * Defense * LeagueAvg
    """
    # Expected Goals
    lambda_home = home_attack_home * away_defense_away * league_avg_home
    lambda_away = away_attack_away * home_defense_home * league_avg_away

    # Cap xG to avoid crazy values (0.2 - 4.0)
    lambda_home = max(0.2, min(lambda_home, 4.0))
    lambda_away = max(0.2, min(lambda_away, 4.0))

    # 1. Raw Poisson matrix
    matrix = get_poisson_matrix(lambda_home, lambda_away)

    # 2. Dixon-Coles correction
    matrix_dc = dixon_coles_correction(matrix, lambda_home, lambda_away)

    # 3. Extract markets
    probs = calculate_markets_from_matrix(matrix_dc)

    # 4. Most likely scoreline
    idx = np.unravel_index(np.argmax(matrix_dc), matrix_dc.shape)
    expected_score = f"{idx[0]}-{idx[1]}"

    return {
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "expected_score": expected_score,
        "matrix": matrix_dc,
        **probs
    }

def calculate_value_edge(your_prob, bookie_odds):
    """Edge = (Prob * Odds) - 1. Must be > 0.05 (5%) to be quality"""
    if not bookie_odds or bookie_odds <= 1:
        return -1
    edge = (your_prob * bookie_odds) - 1
    return edge

# --- HOW TO USE WITH YOUR SUPABASE DATA ---
def team_strengths_from_supabase_row(team_row, league_avg_row):
    """
    team_row: from teams_stats
    league_avg_row: from leagues_avg
    Returns attack/defense strengths
    """
    # Weighted stats are already calculated in fetch script, here we just compute strength
    # Strength = WeightedAvg / LeagueAvg
    avg_scored = team_row.get('avg_goals_scored', 0) or 1.2
    avg_conceded = team_row.get('avg_goals_conceded', 0) or 1.2

    league_home = league_avg_row.get('avg_home_goals', 1.45)
    league_away = league_avg_row.get('avg_away_goals', 1.15)
    league_total = (league_home + league_away) / 2

    attack = avg_scored / league_total if league_total > 0 else 1.0
    defense = avg_conceded / league_total if league_total > 0 else 1.0

    # Clamp strengths (0.5 = very weak, 1.8 = elite like Man City attack)
    attack = max(0.5, min(attack, 1.8))
    defense = max(0.5, min(defense, 1.8))

    return attack, defense

# --- TEST IT LOCALLY ---
if __name__ == "__main__":
    print("Testing Advanced Poisson Engine...")

    # Example: Arsenal (strong home) vs Bournemouth (weak away)
    # These would normally come from your DB
    league_avg_home = 1.55
    league_avg_away = 1.20

    home_attack_home = 1.45 # Arsenal strong at home
    home_defense_home = 0.85 # Arsenal solid defense (0.85 < 1 = good)
    away_attack_away = 0.95
    away_defense_away = 1.25 # Bournemouth leaky away

    result = predict_match(
        home_attack_home, away_defense_away,
        away_attack_away, home_defense_home,
        league_avg_home, league_avg_away
    )

    print(f"xG: Home {result['lambda_home']:.2f} - Away {result['lambda_away']:.2f}")
    print(f"Expected Score: {result['expected_score']}")
    print(f"Over 2.5 Prob: {result['over_2_5']*100:.1f}%")
    print(f"BTTS Yes Prob: {result['btts_yes']*100:.1f}%")
    print(f"1 & Over2.5 Prob: {result['home_win_over25']*100:.1f}%")

    # Test Edge
    mock_odds_over25 = 1.85
    edge = calculate_value_edge(result['over_2_5'], mock_odds_over25)
    print(f"\nBookie Odds Over2.5: {mock_odds_over25} -> Edge: {edge*100:.1f}%")
    if edge > 0.05:
        print("✅ VALUE BET - Keep it")
    else:
        print("❌ Trash - Discard (Quality > Quantity)")
