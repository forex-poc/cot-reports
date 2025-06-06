import json
from pathlib import Path
from datetime import datetime
from operator import itemgetter


def parse_date(d):
    return datetime.strptime(d, "%Y-%m-%d")


def calc_bias(long, short):
    denom = long + short
    return (long - short) / denom if denom != 0 else 0


def calc_pct_change(new, old):
    if old == 0:
        return 0
    return (new - old) / abs(old)


def normalize(v, limit=1.0):
    return max(-limit, min(limit, v))


def analyze_instruments(cot_data, weeks=3):
    # Currency mapping: instrument name to currency code
    currency_map = {
        "CANADIAN DOLLAR": "CAD",
        "SWISS FRANC": "CHF",
        "BRITISH POUND": "GBP",
        "JAPANESE YEN": "JPY",
        "EURO FX": "EUR",
        "NZ DOLLAR": "NZD",
        "AUSTRALIAN DOLLAR": "AUD",
    }

    # Organize the data by instrument
    instrument_data = {}

    for date_str, instruments in cot_data.items():
        for name, entry in instruments.items():
            noncomm = entry.get("commitments", {}).get("non_commercial", {})
            oi = entry.get("open_interest", 0)
            bias = calc_bias(noncomm.get("long", 0), noncomm.get("short", 0))

            if name not in instrument_data:
                instrument_data[name] = []

            instrument_data[name].append(
                {"date": date_str, "bias": bias, "open_interest": oi}
            )

    # Process instruments with at least `weeks` entries
    result = {}

    for name, data in instrument_data.items():
        if len(data) < weeks:
            continue

        # Sort by date descending
        sorted_data = sorted(data, key=lambda x: parse_date(x["date"]), reverse=True)[
            :weeks
        ]
        biases = [d["bias"] for d in sorted_data]
        ois = [d["open_interest"] for d in sorted_data]

        bias_now = biases[0]
        bias_prev = biases[1:]

        # Bias trend (average of weekly differences)
        bias_changes = [
            calc_pct_change(biases[i], biases[i + 1]) for i in range(len(biases) - 1)
        ]
        bias_trend = sum(bias_changes) / len(bias_changes)

        # Open interest change
        oi_change = calc_pct_change(ois[0], ois[-1])

        # Weighted score
        score = normalize(bias_now) + normalize(bias_trend) + normalize(oi_change)
        direction = "BUY" if score > 0.1 else "SELL" if score < -0.1 else "neutral"

        # Get the corresponding currency from currency_map, or None if not found
        currency = currency_map.get(name)

        # Add the currency to the result
        result[name] = {
            "bias_now": round(bias_now, 4),
            "bias_prev": [round(b, 4) for b in bias_prev],
            "bias_trend": f"{bias_trend * 100:.1f}%",
            "open_interest_change": f"{oi_change * 100:.1f}%",
            "score": round(score, 4),
            "direction": direction,
            "currency": currency,
        }

    return result, instrument_data


def calculate_usd_score(cot_strength_data, instrument_data, weeks=3):
    # Currency mapping: instrument name to currency code
    currency_map = {
        "CANADIAN DOLLAR": "CAD",
        "SWISS FRANC": "CHF",
        "BRITISH POUND": "GBP",
        "JAPANESE YEN": "JPY",
        "EURO FX": "EUR",
        "NZ DOLLAR": "NZD",
        "AUSTRALIAN DOLLAR": "AUD",
    }

    # Extract biases for the last 3 weeks for each currency
    currency_biases = {i: [] for i in range(weeks)}
    for instrument, data in cot_strength_data.items():
        if instrument in currency_map:
            sorted_data = sorted(
                instrument_data[instrument],
                key=lambda x: parse_date(x["date"]),
                reverse=True,
            )[:weeks]
            biases = [d["bias"] for d in sorted_data]
            for i, bias in enumerate(biases):
                currency_biases[i].append(bias)

    if not currency_biases[0]:  # Check if current week data exists
        return {
            "bias_now": 0.0,
            "bias_prev": [],
            "bias_trend": "0.0%",
            "open_interest_change": "0.0%",
            "score": 0.0,
            "direction": "neutral",
            "currency": "USD",
            "note": "No currency data available to score USD",
        }

    # Calculate USD biases for each week by inverting the average
    usd_biases = []
    for i in range(weeks):
        if currency_biases[i]:
            usd_bias = sum([-bias for bias in currency_biases[i]]) / len(
                currency_biases[i]
            )
            usd_biases.append(usd_bias)
        else:
            usd_biases.append(0.0)

    # Assign biases
    bias_now = normalize(usd_biases[0])
    bias_prev = [round(normalize(b), 4) for b in usd_biases[1:]]  # Previous 2 weeks

    # Calculate bias trend (percentage change from the oldest to the current)
    bias_trend = calc_pct_change(usd_biases[0], usd_biases[-1]) * 100

    # Determine direction
    direction = "BUY" if bias_now > 0.1 else "SELL" if bias_now < -0.1 else "neutral"

    return {
        "bias_now": round(bias_now, 4),
        "bias_prev": bias_prev,  # Last 2 weeks
        "bias_trend": f"{bias_trend:.1f}%",
        "open_interest_change": "0.0%",  # No open interest data for USD
        "score": round(bias_now, 4),
        "direction": direction,
        "currency": "USD",
        "based_on_currencies": len(currency_biases[0]),
    }


def get_recommendations(cot_strength_data):
    # Currency mapping: instrument name to currency code
    currency_map = {
        "CANADIAN DOLLAR": "CAD",
        "SWISS FRANC": "CHF",
        "BRITISH POUND": "GBP",
        "JAPANESE YEN": "JPY",
        "EURO FX": "EUR",
        "NZ DOLLAR": "NZD",
        "AUSTRALIAN DOLLAR": "AUD",
    }

    # Valid currency pairs
    valid_pairs = [
        "EURUSD",
        "GBPUSD",
        "AUDUSD",
        "NZDUSD",
        "USDJPY",
        "USDCAD",
        "USDCHF",
        "EURJPY",
        "EURGBP",
        "EURCHF",
        "EURAUD",
        "GBPJPY",
        "GBPCHF",
        "GBPAUD",
        "AUDJPY",
        "AUDCHF",
        "NZDJPY",
        "NZDCHF",
        "CADJPY",
        "CADCHF",
        "CHFJPY",
    ]

    # Extract bias for each currency
    biases = {}
    for instrument, data in cot_strength_data.items():
        currency = currency_map.get(instrument)
        if currency:
            biases[currency] = data["bias_now"]
        elif instrument == "USD":  # Use USD bias if present
            biases["USD"] = data["bias_now"]

    # Generate recommendations
    recommendations = []
    for pair in valid_pairs:
        base = pair[:3]  # e.g., "EUR" in "EURUSD"
        quote = pair[3:]  # e.g., "USD" in "EURUSD"

        if base in biases and quote in biases:
            base_bias = biases[base]
            quote_bias = biases[quote]
            diff = base_bias - quote_bias

            # Determine recommendation
            if diff > 0:
                signal = "BUY"
            elif diff < 0:
                signal = "SELL"
            else:
                signal = "neutral"

            recommendations.append(
                f"{pair}: {signal} ({base_bias:.4f} vs {quote_bias:.4f})"
            )
        else:
            recommendations.append(f"{pair}: N/A")

    return recommendations


if __name__ == "__main__":
    input_path = Path("../oraculum/src/app/data/cot/cot.json")
    output_path = Path("../oraculum/src/app/data/cot/cot_strength.json")

    with open(input_path) as f:
        cot_data = json.load(f)

    # Find the most recent date in cot_data
    dates = list(cot_data.keys())
    most_recent_date = max(dates, key=parse_date) if dates else "Unknown"

    result, instrument_data = analyze_instruments(cot_data)

    # Calculate USD score
    usd_score_data = calculate_usd_score(result, instrument_data)

    # Add USD score to the result
    result["USD"] = usd_score_data

    # Add the most recent report date to the result
    result["report_date"] = most_recent_date

    # Get recommendations
    recommendations = get_recommendations(result)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"✅ Termômetro de força salvo em: {output_path}")
    print(
        f"\n💵 USD Score: {usd_score_data['score']} (Direction: {usd_score_data['direction']})"
    )
    print(f"Based on {usd_score_data['based_on_currencies']} currencies")
    print(f"Most recent COT report date: {most_recent_date}")

    # Print recommendations
    print("\n🏆 Recomendações por par:")
    for rec in recommendations:
        print(rec)
