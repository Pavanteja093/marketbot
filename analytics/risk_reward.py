def risk_reward(target, stop):

    risk = abs(stop)

    reward = abs(target)

    if risk == 0:
        return 0

    return round(reward / risk, 2)