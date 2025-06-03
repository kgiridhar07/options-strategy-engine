import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from data.history_collector import get_historical_ohlc
from utils.ticker_loader import load_tickers
import csv
import glob

# --- CONFIGURABLE PARAMETERS ---
BULLISH_THRESHOLD = 1.0  # combined_signal.value >= this is 'strongly bullish'
PROTECTION_LEVELS = [0.10, 0.07, 0.05]  # 10%, 7%, 5% below entry price
HOLDING_PERIODS = [5, 10, 25]  # trading days (1, 2, 5 weeks)

# --- UTILITY FUNCTIONS ---
def load_analysis(filepath: str) -> List[Dict]:
    with open(filepath, 'r') as f:
        return json.load(f)

def get_strongly_bullish(analysis: List[Dict]) -> List[Dict]:
    return [x for x in analysis if x.get('combined_signal', {}).get('value', 0) >= BULLISH_THRESHOLD]

def load_all_indicators():
    """
    Loads all indicators_YYYY-MM-DD.csv files into a dict:
    {date: {ticker: current_price}}
    """
    indicators = {}
    backtest_dir = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(backtest_dir, 'indicators_2023-*.csv')
    for csv_path in sorted(glob.glob(pattern)):
        date_part = os.path.basename(csv_path).replace('indicators_', '').replace('.csv', '')
        indicators[date_part] = {}
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row['ticker']
                try:
                    price = float(row['current_price'])
                except Exception:
                    price = None
                indicators[date_part][ticker] = price
    return indicators

def get_exit_date(start_date: str, n: int, indicator_dates: list) -> str:
    """
    Given a start_date and n, return the date n trading days after start_date from indicator_dates (sorted).
    """
    if start_date not in indicator_dates:
        return None
    idx = indicator_dates.index(start_date)
    exit_idx = idx + n
    if exit_idx >= len(indicator_dates):
        return None
    return indicator_dates[exit_idx]

def simulate_spread(entry_price: float, ticker: str, entry_date: str, protection: float, holding_days: int) -> Dict:
    short_strike = entry_price * (1 - protection)
    exit_date = (datetime.strptime(entry_date, '%Y-%m-%d') + timedelta(days=holding_days)).strftime('%Y-%m-%d')
    price_at_exit = get_price_on_date(ticker, exit_date)
    breached = price_at_exit is not None and price_at_exit < short_strike
    return {
        'ticker': ticker,
        'entry_date': entry_date,
        'exit_date': exit_date,
        'protection': protection,
        'short_strike': short_strike,
        'price_at_exit': price_at_exit,
        'breached': breached
    }

def aggregate_results(results: List[Dict]) -> Dict:
    total = len(results)
    wins = sum(1 for r in results if not r['breached'])
    losses = total - wins
    win_rate = wins / total if total else 0
    return {'total': total, 'wins': wins, 'losses': losses, 'win_rate': win_rate}

def get_all_mondays(start_date, end_date):
    """Return a list of all Mondays between start_date and end_date (inclusive)."""
    mondays = []
    current = start_date
    while current <= end_date:
        if current.weekday() == 0:
            mondays.append(current)
        current += timedelta(days=1)
    return mondays

def batch_generate_bull_put_analysis():
    """
    For each indicators_2023-*.csv in the backtest directory, generate a bull_put_analysis_YYYY-MM-DD.json
    using the production logic from strategy/bull_put.py, and add entry/exit prices for 5, 10, 25 trading days.
    """
    import glob
    import importlib.util
    backtest_dir = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(backtest_dir, 'indicators_2023-*.csv')
    csv_files = sorted(glob.glob(pattern))
    bull_put_path = os.path.join(os.path.dirname(__file__), '../strategy/bull_put.py')
    spec = importlib.util.spec_from_file_location('bull_put', bull_put_path)
    bull_put = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bull_put)
    config_path = os.path.join(os.path.dirname(__file__), '../config/credit_spread_indicator.json')
    # Load all indicators into a dict for fast lookup
    indicators_dict = {}
    for csv_path in csv_files:
        date_part = os.path.basename(csv_path).replace('indicators_', '').replace('.csv', '')
        indicators_dict[date_part] = {}
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row['ticker']
                try:
                    price = float(row['current_price'])
                except Exception:
                    price = None
                indicators_dict[date_part][ticker] = price
    indicator_dates = sorted(indicators_dict.keys())
    for i, csv_path in enumerate(csv_files):
        date_part = os.path.basename(csv_path).replace('indicators_', '').replace('.csv', '')
        results = bull_put.analyze_all_stocks(config_path=config_path, csv_path=csv_path)
        # Add entry/exit prices to each ticker in results
        for entry in results:
            ticker = entry['ticker']
            entry['entry_price'] = indicators_dict[date_part].get(ticker)
            for n, key in zip([5, 10, 25], ['price_5d', 'price_10d', 'price_25d']):
                exit_idx = indicator_dates.index(date_part) + n
                if exit_idx < len(indicator_dates):
                    exit_date = indicator_dates[exit_idx]
                    entry[key] = indicators_dict[exit_date].get(ticker)
                else:
                    entry[key] = None
        output_json = os.path.join(backtest_dir, f'bull_put_analysis_{date_part}.json')
        with open(output_json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Wrote {output_json} ({len(results)} tickers)")

def generate_all_indicators_csvs():
    """
    For each Monday in 2023, compute indicators for all tickers and write to indicators_YYYY-MM-DD.csv in the backtest directory.
    """
    tickers = load_tickers()
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    mondays = get_all_mondays(start_date, end_date)
    for monday in mondays:
        date_str = monday.strftime('%Y-%m-%d')
        rows = []
        for ticker in tickers:
            # Import indicator calculation functions only here to avoid top-level clutter
            from indicators.rsi import calculate_rsi
            from indicators.sma import sma_20, sma_50, sma_200
            from indicators.ema import ema_12, ema_20, ema_50, ema_200
            from indicators.macd import calculate_macd
            from indicators.bollinger import calculate_bollinger_bands
            from indicators.atr import calculate_atr
            from indicators.adx import calculate_adx
            from indicators.support_resistance import calculate_support_resistance
            lookback_days = 400
            end_dt = monday.replace(tzinfo=timezone.utc)
            closes, highs, lows = get_historical_ohlc(ticker, lookback_days=lookback_days, end_date=end_dt)
            if not closes or len(closes) < 50:
                continue
            rsi = calculate_rsi(closes[-150:], period=14)
            sma20 = sma_20(closes)
            sma50 = sma_50(closes)
            sma200 = sma_200(closes)
            ema12 = ema_12(closes)
            ema20 = ema_20(closes)
            ema50 = ema_50(closes)
            ema200 = ema_200(closes)
            macd_line, signal_line = calculate_macd(closes)
            macd_val = macd_line[-1] if macd_line else None
            signal_val = signal_line[-1] if signal_line else None
            upper, middle, lower = calculate_bollinger_bands(closes)
            atr14 = calculate_atr(highs, lows, closes, period=14)
            adx14 = calculate_adx(highs, lows, closes, period=14)
            support_20, resistance_20 = calculate_support_resistance(closes, window=20)
            support_75, resistance_75 = calculate_support_resistance(closes, window=75)
            support_200, resistance_200 = calculate_support_resistance(closes, window=200)
            row = [
                ticker,
                closes[-1],
                closes[-2] if len(closes) > 1 else None,
                ((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) > 1 and closes[-2] else None,
                None,
                round(rsi, 2) if rsi is not None else None,
                round(sma20, 2) if sma20 is not None else None,
                round(sma50, 2) if sma50 is not None else None,
                round(sma200, 2) if sma200 is not None else None,
                round(ema12, 2) if ema12 is not None else None,
                round(ema20, 2) if ema20 is not None else None,
                round(ema50, 2) if ema50 is not None else None,
                round(ema200, 2) if ema200 is not None else None,
                round(macd_val, 2) if macd_val is not None else None,
                round(signal_val, 2) if signal_val is not None else None,
                round(upper, 2) if upper is not None else None,
                round(middle, 2) if middle is not None else None,
                round(lower, 2) if lower is not None else None,
                round(atr14, 2) if atr14 is not None else None,
                round(adx14, 2) if adx14 is not None else None,
                round(support_20, 2) if support_20 is not None else None,
                round(resistance_20, 2) if resistance_20 is not None else None,
                round(support_75, 2) if support_75 is not None else None,
                round(resistance_75, 2) if resistance_75 is not None else None,
                round(support_200, 2) if support_200 is not None else None,
                round(resistance_200, 2) if resistance_200 is not None else None,
                None, None, None
            ]
            rows.append(row)
        if rows:
            backtest_dir = os.path.dirname(os.path.abspath(__file__))
            out_path = os.path.join(backtest_dir, f'indicators_{date_str}.csv')
            with open(out_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'ticker','current_price','previous_close','percent_change','latest_volume','rsi_14','sma_20','sma_50','sma_200','ema_12','ema_20','ema_50','ema_200','macd','macd_signal','bb_upper','bb_middle','bb_lower','atr_14','adx_14','support_20','resistance_20','support_75','resistance_75','support_200','resistance_200','earnings_date','dividend_date','ex_dividend_date'])
                writer.writerows(rows)
            print(f"Wrote indicators for {date_str} ({len(rows)} tickers) at {out_path}")

# --- MAIN BACKTESTER LOGIC ---
def main():
    # Only run the backtest simulation using pre-generated JSONs
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    mondays = get_all_mondays(start_date, end_date)
    all_results = []
    total_hits = 0
    csv_rows = []
    # Load all indicator prices for breach counting
    indicators = {}
    backtest_dir = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(backtest_dir, 'indicators_2023-*.csv')
    indicator_files = sorted(glob.glob(pattern))
    indicator_dates = [os.path.basename(f).replace('indicators_', '').replace('.csv', '') for f in indicator_files]
    for f, d in zip(indicator_files, indicator_dates):
        indicators[d] = {}
        with open(f, 'r') as fin:
            reader = csv.DictReader(fin)
            for row in reader:
                try:
                    indicators[d][row['ticker']] = float(row['current_price'])
                except Exception:
                    indicators[d][row['ticker']] = None
    # Only keep the final signal value and text in the output
    csv_header = [
        'date', 'ticker', 'entry_price', 'exit_price', 'protection', 'holding_days', 'breached',
        'protection_price', 'actual_move', 'pct_move',
        'combined_signal_value', 'combined_signal_text',
        'breaches_5d', 'breaches_10d', 'breaches_25d'
    ]
    for monday in mondays:
        date_str = monday.strftime('%Y-%m-%d')
        analysis_path = os.path.join(os.path.dirname(__file__), f'bull_put_analysis_{date_str}.json')
        if not os.path.exists(analysis_path):
            continue
        analysis = load_analysis(analysis_path)
        tickers_in_file = [x['ticker'] for x in analysis]
        strongly_bullish = [x for x in analysis if x.get('combined_signal', {}).get('text', '').lower() == 'strongly bullish']
        print(f"{date_str}: {len(strongly_bullish)} strongly bullish hits | tickers checked: {', '.join(tickers_in_file)}")
        total_hits += len(strongly_bullish)
        for stock in strongly_bullish:
            ticker = stock['ticker']
            entry_price = stock.get('entry_price')
            price_5d = stock.get('price_5d')
            price_10d = stock.get('price_10d')
            price_25d = stock.get('price_25d')
            print(f"Processing ticker: {ticker} for {date_str}")
            if entry_price is None:
                print(f"Skipping {ticker}: no entry price in JSON for {date_str} [{ticker}]")
                continue
            # Precompute breach counts for each holding period
            breach_counts = {}
            start_idx = indicator_dates.index(date_str) if date_str in indicator_dates else None
            for holding in [5, 10, 25]:
                breaches = 0
                if start_idx is not None:
                    protection_prices = [entry_price * (1 - p) for p in PROTECTION_LEVELS]
                    for offset in range(1, holding+1):
                        idx = start_idx + offset
                        if idx >= len(indicator_dates):
                            break
                        d = indicator_dates[idx]
                        price = indicators[d].get(ticker)
                        if price is None:
                            continue
                        # For each protection level, count breach if price < protection
                        for p_idx, protection in enumerate(PROTECTION_LEVELS):
                            if price < protection_prices[p_idx]:
                                breach_counts.setdefault((protection, holding), 0)
                                breach_counts[(protection, holding)] += 1
                # For summary columns (total breaches for each holding period, lowest protection)
                if PROTECTION_LEVELS:
                    # Use the lowest protection (highest strike) for summary
                    summary_protection = PROTECTION_LEVELS[0]
                    summary_price = entry_price * (1 - summary_protection)
                    breaches = 0
                    if start_idx is not None:
                        for offset in range(1, holding+1):
                            idx = start_idx + offset
                            if idx >= len(indicator_dates):
                                break
                            d = indicator_dates[idx]
                            price = indicators[d].get(ticker)
                            if price is not None and price < summary_price:
                                breaches += 1
                    breach_counts[f'breaches_{holding}d'] = breaches
            for protection in PROTECTION_LEVELS:
                for holding in HOLDING_PERIODS:
                    if holding == 5:
                        exit_price = price_5d
                    elif holding == 10:
                        exit_price = price_10d
                    elif holding == 25:
                        exit_price = price_25d
                    else:
                        exit_price = None
                    breached = exit_price is not None and exit_price < entry_price * (1 - protection)
                    protection_price = entry_price * (1 - protection) if entry_price is not None else None
                    actual_move = (exit_price - entry_price) if (exit_price is not None and entry_price is not None) else None
                    pct_move = ((exit_price - entry_price) / entry_price * 100) if (exit_price is not None and entry_price) else None
                    row = [
                        date_str, ticker, entry_price, exit_price, protection, holding, breached,
                        protection_price, actual_move, pct_move,
                        stock['combined_signal']['value'],
                        stock['combined_signal']['text'],
                        breach_counts.get('breaches_5d', 0),
                        breach_counts.get('breaches_10d', 0),
                        breach_counts.get('breaches_25d', 0)
                    ]
                    csv_rows.append(row)
    # Round all numeric values in csv_rows to two decimal places
    def round_value(val):
        if isinstance(val, bool):
            return val
        if isinstance(val, (float, int)) and val is not None:
            return round(val, 2)
        return val
    rounded_csv_rows = [[round_value(v) for v in row] for row in csv_rows]
    out_csv = os.path.join(os.path.dirname(__file__), 'backtest_results.csv')
    with open(out_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(csv_header)
        writer.writerows(rounded_csv_rows)
    # Print win rate summary for each protection/holding period
    for protection in PROTECTION_LEVELS:
        for holding in HOLDING_PERIODS:
            subset = [r for r in csv_rows if r[4] == protection and r[5] == holding]
            if subset:
                wins = sum(1 for r in subset if not r[6])
                total = len(subset)
                win_rate = wins / total if total else 0
                print(f"Protection: {int(protection*100)}%, Holding: {holding}d => Win rate: {win_rate:.2%} ({wins}/{total})")

if __name__ == '__main__':
    generate_all_indicators_csvs()
    batch_generate_bull_put_analysis()
    main()