"""
ROI calculations for CGC10 → PSA10 arbitrage via 진스카 grading service.

Formula:
  cost   = buy_price + grading_fee_usd
  profit = psa10_price - cost
  ROI    = profit / cost * 100
"""
from config import EXCHANGE_RATE_KRW, MIN_ROI, GRADING_TIERS


def krw_to_usd(krw: float) -> float:
    return round(krw / EXCHANGE_RATE_KRW, 2)


def calc_roi(buy_price: float, psa10_price: float, grading_krw: float) -> float:
    fee_usd = krw_to_usd(grading_krw)
    cost    = buy_price + fee_usd
    profit  = psa10_price - cost
    if cost <= 0:
        return 0.0
    return round((profit / cost) * 100, 1)


def max_buy_for_roi(psa10_price: float, grading_krw: float, target_roi: float = None) -> float:
    """
    Max CGC10 buy price that still hits target_roi after grading.
    Derived from: ROI = (sell - buy - fee) / (buy + fee) = r
      => buy = (sell - fee * (1 + r)) / (1 + r)
    """
    if target_roi is None:
        target_roi = MIN_ROI
    fee_usd = krw_to_usd(grading_krw)
    r = target_roi / 100
    max_buy = (psa10_price - fee_usd * (1 + r)) / (1 + r)
    return round(max(max_buy, 0), 2)


def analyze(buy_price: float, psa10_price: float) -> dict:
    """
    Analyze a card across all 3 grading tiers.
    Returns full tier breakdown + recommended tier + any_feasible flag.
    """
    tiers = []
    recommended = None

    for tier in GRADING_TIERS:
        roi      = calc_roi(buy_price, psa10_price, tier["krw"])
        max_buy  = max_buy_for_roi(psa10_price, tier["krw"])
        fee_usd  = krw_to_usd(tier["krw"])
        profit   = round(psa10_price - buy_price - fee_usd, 2)
        feasible = roi >= MIN_ROI

        result = {
            "name":         tier["name"],
            "krw":          tier["krw"],
            "turnaround":   tier["turnaround"],
            "grading_usd":  fee_usd,
            "roi":          roi,
            "profit_usd":   profit,
            "max_buy_usd":  max_buy,
            "feasible":     feasible,
        }
        tiers.append(result)

        if recommended is None and feasible:
            recommended = result

    return {
        "buy_price":   buy_price,
        "psa10_price": psa10_price,
        "tiers":       tiers,
        "recommended": recommended,
        "any_feasible": recommended is not None,
    }
