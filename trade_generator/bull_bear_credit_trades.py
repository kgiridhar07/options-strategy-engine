import yfinance as yf
import mibian
import numpy as np
import json
import os
import glob
from strategy_json_parser import parse_strategy_json, find_latest_analysis_json, get_tickers_by_signal
from datetime import datetime, timedelta

# --- Compute Greeks using mibian for each option ---
def compute_greeks(row, S, r, expiry_days, option_type):
    # S: underlying price, r: risk-free rate (annual, %), expiry_days: days to expiry
    # row: option row from yfinance DataFrame
    K = row['strike']
    IV = row.get('impliedVolatility', np.nan)
    if np.isnan(IV) or IV == 0:
        return {k: np.nan for k in ['delta', 'gamma', 'theta', 'vega', 'rho']}
    # mibian requires IV in percent, not decimal
    c = mibian.BS([S, K, r, expiry_days], volatility=IV*100)
    if option_type == 'call':
        return {
            'delta': c.callDelta,
            'gamma': c.gamma,
            'theta': c.callTheta,
            'vega': c.vega,
            'rho': c.callRho
        }
    else:
        return {
            'delta': c.putDelta,
            'gamma': c.gamma,
            'theta': c.putTheta,
            'vega': c.vega,
            'rho': c.putRho
        }

def get_option_chain_with_greeks(ticker_str, chosen_exp=None, r=5.0, week_offsets=None):
    ticker = yf.Ticker(ticker_str.upper())
    expirations = ticker.options
    if not expirations:
        print(f"No expirations for {ticker_str}")
        return []
    results = []
    # Calculate target expirations: 2, 4, 6 weeks from now
    now = datetime.now()
    week_offsets = week_offsets or [2, 4, 6]
    target_dates = [(now + timedelta(weeks=w)).date() for w in week_offsets]
    # Find the closest available expiration for each target week
    chosen_exps = []
    for td in target_dates:
        closest = min(expirations, key=lambda x: abs((datetime.strptime(x, "%Y-%m-%d").date() - td).days))
        if closest not in chosen_exps:
            chosen_exps.append(closest)
    for chosen_exp in chosen_exps:
        opt_chain = ticker.option_chain(chosen_exp)
        calls = opt_chain.calls
        puts = opt_chain.puts
        S = ticker.history(period="1d")['Close'].iloc[-1]
        expiry_date = datetime.strptime(chosen_exp, "%Y-%m-%d")
        now_dt = datetime.now()
        expiry_days = max((expiry_date - now_dt).days, 1)
        # Compute Greeks for calls
        call_greeks = calls.apply(lambda row: compute_greeks(row, S, r, expiry_days, 'call'), axis=1, result_type='expand')
        calls = calls.join(call_greeks)
        # Compute Greeks for puts
        put_greeks = puts.apply(lambda row: compute_greeks(row, S, r, expiry_days, 'put'), axis=1, result_type='expand')
        puts = puts.join(put_greeks)
        results.append((calls, puts, S, chosen_exp))
    return results

def find_bull_put_spreads(puts, current_price):
    # Find all possible bull put spreads (short put at higher strike, long put at lower strike)
    spreads = []
    puts_sorted = puts.sort_values("strike", ascending=False).reset_index(drop=True)
    for i in range(len(puts_sorted)-1):
        short = puts_sorted.iloc[i]
        long = puts_sorted.iloc[i+1]
        # Both must have bid/ask
        if np.isnan(short['bid']) or np.isnan(long['ask']):
            continue
        # Only consider spreads where both strikes are below current price
        if short['strike'] >= current_price or long['strike'] >= current_price:
            continue
        credit = short['bid'] - long['ask']
        if credit > 0:
            width = short['strike'] - long['strike']
            max_loss = round((width - credit) * 100, 2)  # in dollars
            max_profit = round(credit * 100, 2)  # in dollars
            percent_from_strike = round(100 * (current_price - short['strike']) / current_price, 2)
            avg_oi = round((float(short.get('openInterest', 0)) + float(long.get('openInterest', 0))) / 2, 2)
            percent_profit_of_width = round(100 * (credit / width), 2) if width != 0 else 0
            spreads.append({
                'ticker': '',  # to be filled in main
                'current_price': round(float(current_price), 2),
                'strategy': 'Bull Put',
                'percent_from_strike': percent_from_strike,
                'short_strike': round(float(short['strike']), 2),
                'long_strike': round(float(long['strike']), 2),
                'short_strike_price': round(float(short['bid']), 2),
                'long_strike_credit': round(float(long['ask']), 2),
                'max_loss': max_loss,
                'max_profit': max_profit,
                'width': round(float(width), 2),
                'percent_profit_of_width': percent_profit_of_width,
                'avg_oi': avg_oi,
                'expiration': ''  # to be filled in main
            })
    return spreads, 0, 0

def find_bear_call_spreads(calls, current_price):
    # Find all possible bear call spreads (short call at lower strike, long call at higher strike)
    spreads = []
    calls_sorted = calls.sort_values("strike", ascending=True).reset_index(drop=True)
    for i in range(len(calls_sorted)-1):
        short = calls_sorted.iloc[i]
        long = calls_sorted.iloc[i+1]
        if np.isnan(short['bid']) or np.isnan(long['ask']):
            continue
        # Only consider spreads where both strikes are above current price
        if short['strike'] <= current_price or long['strike'] <= current_price:
            continue
        credit = short['bid'] - long['ask']
        if credit > 0:
            width = long['strike'] - short['strike']
            max_loss = round((width - credit) * 100, 2)
            max_profit = round(credit * 100, 2)
            percent_from_strike = round(100 * (short['strike'] - current_price) / current_price, 2)
            avg_oi = round((float(short.get('openInterest', 0)) + float(long.get('openInterest', 0))) / 2, 2)
            percent_profit_of_width = round(100 * (credit / width), 2) if width != 0 else 0
            spreads.append({
                'ticker': '',
                'current_price': round(float(current_price), 2),
                'strategy': 'Bear Call',
                'percent_from_strike': percent_from_strike,
                'short_strike': round(float(short['strike']), 2),
                'long_strike': round(float(long['strike']), 2),
                'short_strike_price': round(float(short['bid']), 2),
                'long_strike_credit': round(float(long['ask']), 2),
                'max_loss': max_loss,
                'max_profit': max_profit,
                'width': round(float(width), 2),
                'percent_profit_of_width': percent_profit_of_width,
                'avg_oi': avg_oi,
                'expiration': ''
            })
    return spreads, 0, 0

def convert_np(obj):
    if isinstance(obj, dict):
        return {k: convert_np(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_np(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    else:
        return obj

def main():
    # Find latest analysis JSON and parse tickers
    analysis_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output/bull_bear_analysis')
    latest_json = find_latest_analysis_json(analysis_dir)
    bullish_tickers = get_tickers_by_signal(latest_json, 'Strongly Bullish')
    bearish_tickers = get_tickers_by_signal(latest_json, 'Strongly Bearish')
    print(f"Strongly Bullish: {bullish_tickers}")
    print(f"Strongly Bearish: {bearish_tickers}")
    week_offsets = [2, 4, 6]
    results = []
    csv_rows = []
    # Bull Put for bullish
    for stock in bullish_tickers:
        print(f"\n--- Bull Put for {stock.upper()} ---")
        option_data = get_option_chain_with_greeks(stock, week_offsets=week_offsets)
        for calls, puts, S, exp in option_data:
            spreads, _, _ = find_bull_put_spreads(puts, S)
            for s in spreads[:5]:
                s['ticker'] = stock.upper()
                s['expiration'] = exp
                csv_rows.append(s)
            result = {
                'ticker': stock.upper(),
                'expiration': exp,
                'current_price': float(S),
                'bull_put_spreads': spreads[:5]
            }
            results.append(result)
    # Bear Call for bearish
    for stock in bearish_tickers:
        print(f"\n--- Bear Call for {stock.upper()} ---")
        option_data = get_option_chain_with_greeks(stock, week_offsets=week_offsets)
        for calls, puts, S, exp in option_data:
            spreads, _, _ = find_bear_call_spreads(calls, S)
            for s in spreads[:5]:
                s['ticker'] = stock.upper()
                s['expiration'] = exp
                csv_rows.append(s)
            result = {
                'ticker': stock.upper(),
                'expiration': exp,
                'current_price': float(S),
                'bear_call_spreads': spreads[:5]
            }
            results.append(result)
    # Write results to JSON in the correct output folder
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output/bull_bear_trades_out')
    os.makedirs(out_dir, exist_ok=True)
    today_str = datetime.now().strftime('%Y-%m-%d')
    out_path = os.path.join(out_dir, f'bull_bear_trades_{today_str}.json')
    with open(out_path, 'w') as f:
        json.dump(convert_np(results), f, indent=2)
    print(f"Results written to {out_path}")
    # Write CSV summary to the same folder
    csv_path = os.path.join(out_dir, f'bull_bear_trades_summary_{today_str}.csv')
    csv_fields = [
        'ticker', 'current_price', 'strategy', 'percent_from_strike', 'short_strike', 'long_strike',
        'short_strike_price', 'long_strike_credit', 'max_loss', 'max_profit', 'width',
        'percent_profit_of_width', 'avg_oi', 'expiration'
    ]
    with open(csv_path, 'w', newline='') as f:
        import csv
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in csv_rows:
            row.pop('short_oi', None)
            row.pop('long_oi', None)
            if all(field in row and row[field] is not None for field in csv_fields):
                writer.writerow(convert_np(row))
            else:
                print(f"Skipping row due to missing fields: {row}")
    print(f"CSV summary written to {csv_path}")

if __name__ == "__main__":
    main()


