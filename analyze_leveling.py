import math

def get_xp_requirement_cumulative(level):
    if level <= 1: return 0
    # Single expression: Power Law + Aggressive Exponential
    # Hits: 40=100k, 70=2.6M, 100=69B (Approx 6 years at 1h/day)
    return int(10 * (level ** 2.5) + 0.00023 * math.exp(level / 3.0))

def calculate_reward(mob_level, hp, difficulty):
    hp_scaling = (hp / 500) ** 0.5
    difficulty_multiplier = difficulty ** 1.8
    base_xp_pool = int((mob_level * 5) * hp_scaling * difficulty_multiplier)
    if base_xp_pool < 10: base_xp_pool = 10
    return base_xp_pool

def get_cooldown(speed):
    return 60 / (1 + speed * 0.05)

# Simulation
level = 1
current_xp = 0
total_time_s = 0
total_mobs = 0

print(f"{'Level':<6} | {'Next LV EXP':<12} | {'Mob XP':<10} | {'Mobs/LV':<8} | {'Total Mobs':<10} | {'Time (h)':<10}")
print("-" * 70)

levels_to_report = [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

print("\n--- LEECHER PROTECTION SIMULATION ---")
print(f"{'User Level':<12} | {'Mob Level':<12} | {'Total Pool':<12} | {'Damage %':<10} | {'Raw XP':<10} | {'Final XP':<10} | {'Status'}")
print("-" * 100)

def simulate_participation(u_level, m_level, pool, share):
    raw_xp = int(pool * share)
    
    # 1. Challenge Mult
    challenge_mult = min(1.0, (u_level + 10) / (m_level + 10))
    
    # 2. Overlevel Penalty (not applicable here as we are lower level)
    
    # Apply
    xp = int(raw_xp * challenge_mult)
    
    # 3. Cap
    req_curr = get_xp_requirement_cumulative(u_level)
    req_next = get_xp_requirement_cumulative(u_level + 1)
    level_pool = max(100, req_next - req_curr)
    max_gain = int(level_pool * 1.5)
    
    capped_xp = min(xp, max_gain)
    
    status = "Capped!" if xp > max_gain else "Under Cap"
    print(f"{u_level:<12} | {m_level:<12} | {pool:<12} | {share*100:<10}% | {raw_xp:<10} | {capped_xp:<10} | {status}")

# Case 1: Level 1 in Level 70 Boss
simulate_participation(1, 70, 90000, 0.05) # 5% dmg

# Case 2: Level 1 in Level 100 Mega Boss
simulate_participation(1, 100, 500000, 0.01) # 1% dmg

# Case 3: Level 40 in Level 70 Boss
simulate_participation(40, 70, 90000, 0.10) # 10% dmg
