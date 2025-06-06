import requests
import os
import json
import re
import argparse
from datetime import datetime
from bs4 import BeautifulSoup

URL_CURRENT = "https://www.cftc.gov/dea/futures/deacmesf.htm"
OUTPUT_FILE = "../oraculum/src/app/data/cot/cot.json"
HISTORY_FILE = "../oraculum/src/app/data/cot/cot_history.json"
LAST_UPDATED_FILE = "last_updated/cot.txt"


def ensure_dirs():
    os.makedirs("data", exist_ok=True)
    os.makedirs("last_updated", exist_ok=True)


def load_last_updated():
    if os.path.exists(LAST_UPDATED_FILE):
        with open(LAST_UPDATED_FILE, "r") as f:
            return f.read().strip()
    return None


def save_last_updated(date_str):
    with open(LAST_UPDATED_FILE, "w") as f:
        f.write(date_str)


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def load_latest():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            return json.load(f)
    return {}


def save_latest(data):
    latest = load_latest()
    for instrument, entry in data.items():
        date = entry["date"]
        if date not in latest:
            latest[date] = {}
        latest[date][instrument] = entry

    with open(OUTPUT_FILE, "w") as f:
        json.dump(latest, f, indent=2)


def extract_pre_text(html):
    soup = BeautifulSoup(html, "html.parser")
    pre = soup.find("pre")
    return pre.get_text() if pre else ""


def parse_cot_data(text):
    entries = re.split(r"\n(?=[A-Z\s-]+- CHICAGO MERCANTILE EXCHANGE\s+Code-\d+)", text)
    result = {}

    for entry in entries:
        lines = entry.strip().splitlines()
        if not lines:
            continue

        header = lines[0]
        code_match = re.search(r"Code-(\d+)", header)
        code = code_match.group(1) if code_match else "UNKNOWN"
        instrument = header.split(" - ")[0].strip().upper()
        exchange = "CHICAGO MERCANTILE EXCHANGE"

        date_match = re.search(r"AS OF (\d{2}/\d{2}/\d{2})", entry)
        if not date_match:
            continue
        date_str = datetime.strptime(date_match.group(1), "%m/%d/%y").strftime(
            "%Y-%m-%d"
        )

        data_block = {
            "instrument": instrument,
            "exchange": exchange,
            "code": code,
            "date": date_str,
        }

        for i, line in enumerate(lines):
            if "OPEN INTEREST:" in line:
                oi_match = re.search(r"OPEN INTEREST:\s+(\d[\d,]*)", line)
                if oi_match:
                    data_block["open_interest"] = int(
                        oi_match.group(1).replace(",", "")
                    )
            if "CHANGE IN OPEN INTEREST:" in line:
                chg_match = re.search(r"CHANGE IN OPEN INTEREST:\s+(-?\d[\d,]*)", line)
                if chg_match:
                    data_block["change_in_oi"] = int(
                        chg_match.group(1).replace(",", "")
                    )
            if line.strip().startswith("COMMITMENTS"):
                try:
                    data_line = lines[i + 1].strip().split()
                    data_block["commitments"] = {
                        "non_commercial": {
                            "long": int(data_line[0].replace(",", "")),
                            "short": int(data_line[1].replace(",", "")),
                            "spreads": int(data_line[2].replace(",", "")),
                        },
                        "commercial": {
                            "long": int(data_line[3].replace(",", "")),
                            "short": int(data_line[4].replace(",", "")),
                        },
                        "total": {
                            "long": int(data_line[5].replace(",", "")),
                            "short": int(data_line[6].replace(",", "")),
                        },
                        "non_reportable": {
                            "long": int(data_line[7].replace(",", "")),
                            "short": int(data_line[8].replace(",", "")),
                        },
                    }
                except Exception as e:
                    print(f"Erro ao parsear COMMITMENTS de {instrument}: {e}")
            if line.strip().startswith("PERCENT OF OPEN INTEREST"):
                try:
                    perc_line = lines[i + 1].strip().split()
                    data_block["percentages"] = {
                        "non_commercial": {
                            "long": float(perc_line[0]),
                            "short": float(perc_line[1]),
                            "spreads": float(perc_line[2]),
                        },
                        "commercial": {
                            "long": float(perc_line[3]),
                            "short": float(perc_line[4]),
                        },
                        "total": {
                            "long": float(perc_line[5]),
                            "short": float(perc_line[6]),
                        },
                        "non_reportable": {
                            "long": float(perc_line[7]),
                            "short": float(perc_line[8]),
                        },
                    }
                except Exception as e:
                    print(f"Erro ao parsear PERCENTAGENS de {instrument}: {e}")
            if line.strip().startswith("NUMBER OF TRADERS"):
                try:
                    trader_line = lines[i + 1].strip().split()
                    data_block["trader_count"] = {
                        "non_commercial": {
                            "long": int(trader_line[0]),
                            "short": int(trader_line[1]),
                        },
                        "spreads": int(trader_line[2]),
                        "commercial": {
                            "long": int(trader_line[3]),
                            "short": int(trader_line[4]),
                        },
                        "total": int(trader_line[-1]),
                    }
                except Exception as e:
                    print(f"Erro ao parsear TRADERS de {instrument}: {e}")

        result[instrument] = data_block

    return result


def merge_with_history(new_data, history):
    for inst, new_entry in new_data.items():
        if inst not in history:
            history[inst] = []

        if not any(e["date"] == new_entry["date"] for e in history[inst]):
            history[inst].append(new_entry)
            print(f"Adicionado histórico para {inst} ({new_entry['date']})")
        else:
            print(f"Já existe histórico para {inst} ({new_entry['date']})")

    return history


def run(from_url=None):
    ensure_dirs()
    if from_url:
        print(f"📥 Baixando dados do COT da URL fornecida: {from_url}")
        response = requests.get(from_url)
        if response.status_code != 200:
            raise Exception(f"Erro HTTP {response.status_code}")
    else:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if load_last_updated() == today:
            print("COT já atualizado hoje.")
            return
        print("📥 Baixando dados COT da semana atual...")
        response = requests.get(URL_CURRENT)
        if response.status_code != 200:
            raise Exception(f"Erro HTTP {response.status_code}")

    raw_text = extract_pre_text(response.text)
    new_data = parse_cot_data(raw_text)

    if not new_data:
        print("Nenhum dado extraído.")
        return

    save_latest(new_data)
    history = load_history()
    updated_history = merge_with_history(new_data, history)
    save_history(updated_history)

    if not from_url:
        save_last_updated(datetime.utcnow().strftime("%Y-%m-%d"))

    print("✅ Coleta do COT finalizada.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coletor de COT da CFTC")
    parser.add_argument(
        "--from-url",
        help="URL alternativa para coletar relatório histórico",
        default=None,
    )
    args = parser.parse_args()
    run(from_url=args.from_url)
