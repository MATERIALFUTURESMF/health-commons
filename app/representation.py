def get_avatar_state(user_value, community_avg):
    if community_avg == 0:
        return "STASIS"

    diff = (user_value / community_avg)
    
    if diff > 1.1:
        return "VIBRANT_GLOW"  # 10% above average
    elif diff < 0.9:
        return "DENSE_SHADOW"   # 10% below average
    else:
        return "HARMONIC_PULSE" # In sync
    