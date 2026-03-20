"""
Scenario calculation engine.

All monetary values are GBP. Energy in kWh.

Assumptions are rule-of-thumb for the UK; stored here as constants so the
team can tune them without touching business logic.
"""
from typing import Optional, List, Dict, Any


# ── Solar yield: kWh generated per kWp installed per year, by UK city ─────────

SOLAR_YIELD: Dict[str, float] = {
    "london": 950,
    "birmingham": 900,
    "manchester": 850,
    "leeds": 870,
    "sheffield": 860,
    "bristol": 960,
    "cardiff": 910,
    "edinburgh": 800,
    "glasgow": 790,
    "belfast": 800,
    "exeter": 990,
    "cambridge": 930,
    "norwich": 940,
    "brighton": 970,
    "southampton": 960,
    "liverpool": 860,
    "nottingham": 880,
    "default": 900,
}

# ── Rule-of-thumb installed costs ─────────────────────────────────────────────

SOLAR_COST_PER_KWP = 1_100      # GBP, fully installed
BATTERY_COST_PER_KWH = 600      # GBP, fully installed
EFFICIENCY_COST_PER_M2 = 30     # GBP, LED + controls bundle

# ── Efficiency savings by building type (fraction of annual kWh) ──────────────

EFFICIENCY_SAVINGS: Dict[str, float] = {
    "office": 0.15,
    "hospital": 0.10,
    "data_centre": 0.08,
    "factory": 0.12,
}

# ── Typical energy intensity (kWh/m²/year) – used to estimate floor area ─────

ENERGY_INTENSITY: Dict[str, float] = {
    "office": 175,
    "hospital": 500,
    "data_centre": 650,
    "factory": 300,
}

DEFAULT_DISCOUNT_RATE = 0.06  # 6 %


# ── Helpers ───────────────────────────────────────────────────────────────────

def _yield_for(location: str) -> float:
    """Return kWh/kWp/yr for the closest matching city."""
    key = location.strip().lower().split(",")[0].split(" ")[0]
    return SOLAR_YIELD.get(key, SOLAR_YIELD["default"])


def _npv(annual_savings: float, capex: float, years: int, rate: float = DEFAULT_DISCOUNT_RATE) -> float:
    pv = sum(annual_savings / (1 + rate) ** t for t in range(1, years + 1))
    return round(pv - capex, 0)


def _payback(capex: float, annual_savings: float) -> Optional[float]:
    if annual_savings <= 0:
        return None
    return round(capex / annual_savings, 1)


# ── Scenarios ─────────────────────────────────────────────────────────────────

def run_scenario_solar(
    annual_kwh: float, annual_cost: float, solar_kw: float, location: str
) -> Dict[str, Any]:
    """Scenario A – Solar PV only."""
    yield_kwh = _yield_for(location)
    generation = solar_kw * yield_kwh
    self_consumption = 0.35          # 35 % used on-site without a battery
    savings_kwh = generation * self_consumption
    avg_tariff = annual_cost / annual_kwh
    savings_gbp = round(savings_kwh * avg_tariff, 0)
    capex = round(solar_kw * SOLAR_COST_PER_KWP, 0)

    return {
        "scenario": "solar_only",
        "name": f"Solar PV ({solar_kw} kWp)",
        "capex_gbp": capex,
        "annual_savings_kwh": round(savings_kwh, 0),
        "annual_savings_gbp": savings_gbp,
        "payback_years": _payback(capex, savings_gbp),
        "npv_gbp": _npv(savings_gbp, capex, years=20),
        "assumptions": {
            "solar_kw": solar_kw,
            "location": location,
            "yield_kwh_per_kwp_yr": yield_kwh,
            "annual_generation_kwh": round(generation, 0),
            "self_consumption_rate": self_consumption,
            "avg_tariff_p_per_kwh": round(avg_tariff * 100, 2),
        },
    }


def run_scenario_solar_battery(
    annual_kwh: float,
    annual_cost: float,
    solar_kw: float,
    battery_kwh: float,
    location: str,
) -> Dict[str, Any]:
    """Scenario B – Solar + battery (raises self-consumption ~35 % → ~55 %)."""
    yield_kwh = _yield_for(location)
    generation = solar_kw * yield_kwh
    self_consumption = 0.55
    savings_kwh = generation * self_consumption
    avg_tariff = annual_cost / annual_kwh
    savings_gbp = round(savings_kwh * avg_tariff, 0)
    capex = round(solar_kw * SOLAR_COST_PER_KWP + battery_kwh * BATTERY_COST_PER_KWH, 0)

    return {
        "scenario": "solar_battery",
        "name": f"Solar ({solar_kw} kWp) + Battery ({battery_kwh} kWh)",
        "capex_gbp": capex,
        "annual_savings_kwh": round(savings_kwh, 0),
        "annual_savings_gbp": savings_gbp,
        "payback_years": _payback(capex, savings_gbp),
        "npv_gbp": _npv(savings_gbp, capex, years=20),
        "assumptions": {
            "solar_kw": solar_kw,
            "battery_kwh": battery_kwh,
            "location": location,
            "yield_kwh_per_kwp_yr": yield_kwh,
            "annual_generation_kwh": round(generation, 0),
            "self_consumption_rate": self_consumption,
            "avg_tariff_p_per_kwh": round(avg_tariff * 100, 2),
        },
    }


def run_scenario_efficiency(
    annual_kwh: float,
    annual_cost: float,
    building_type: str,
    floor_area: Optional[float] = None,
) -> Dict[str, Any]:
    """Scenario C – LED + controls retrofit."""
    savings_rate = EFFICIENCY_SAVINGS.get(building_type, 0.12)
    savings_kwh = annual_kwh * savings_rate
    avg_tariff = annual_cost / annual_kwh
    savings_gbp = round(savings_kwh * avg_tariff, 0)

    # Use actual floor area if supplied, else back-calculate from energy intensity
    if floor_area:
        area = floor_area
    else:
        intensity = ENERGY_INTENSITY.get(building_type, 200)
        area = annual_kwh / intensity

    capex = round(area * EFFICIENCY_COST_PER_M2, 0)

    return {
        "scenario": "efficiency_bundle",
        "name": "LED + Controls Retrofit",
        "capex_gbp": capex,
        "annual_savings_kwh": round(savings_kwh, 0),
        "annual_savings_gbp": savings_gbp,
        "payback_years": _payback(capex, savings_gbp),
        "npv_gbp": _npv(savings_gbp, capex, years=15),
        "assumptions": {
            "building_type": building_type,
            "savings_rate_pct": f"{savings_rate * 100:.0f}%",
            "floor_area_m2": round(area, 0),
            "avg_tariff_p_per_kwh": round(avg_tariff * 100, 2),
        },
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def run_all_scenarios(
    annual_kwh: float,
    annual_cost: float,
    building_type: str,
    location: str,
    floor_area: Optional[float] = None,
    solar_kw: float = 50.0,
    battery_kwh: float = 75.0,
) -> List[Dict[str, Any]]:
    return [
        run_scenario_solar(annual_kwh, annual_cost, solar_kw, location),
        run_scenario_solar_battery(annual_kwh, annual_cost, solar_kw, battery_kwh, location),
        run_scenario_efficiency(annual_kwh, annual_cost, building_type, floor_area),
    ]
