import os
import pandas as pd
from datetime import datetime
from utils.ticker_loader import load_tickers
from data.snapshot_collector import (
    get_all_snapshots,
    get_last_trade_price_from_snapshot,
    get_previous_close_from_snapshot,
    get_percent_change_from_snapshot,
    get_latest_volume_from_snapshot,
    get_latest_quote_from_snapshot,
    get_latest_trade_price
)
from data.history_collector import get_historical_closes, get_historical_ohlc
from indicators.rsi import calculate_rsi
from indicators.sma import sma_20, sma_50, sma_200
from indicators.ema import ema_12, ema_20, ema_50, ema_200
from indicators.macd import calculate_macd
from indicators.bollinger import calculate_bollinger_bands
from indicators.atr import calculate_atr
from indicators.adx import calculate_adx
from data.corporate_events import get_next_earnings_and_dividend_dates
from indicators.support_resistance import find_strong_swing_levels_from_arrays
from indicators.ytd_52w import get_ytd_52w_indicators_for_ticker


def process_indicators(output_dir=None, tickers=None, today_str=None, corporate_events=None):
    """
    Generate indicator CSV for today and save to output/indicator_out/indicators_<today>.csv
    """
    if output_dir is None:
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(PROJECT_ROOT, 'output/indicator_out')
    os.makedirs(output_dir, exist_ok=True)
    if today_str is None:
        today_str = datetime.now().strftime('%Y-%m-%d')
    output_path = os.path.join(output_dir, f'indicators_{today_str}.csv')
    if tickers is None:
        tickers = load_tickers()
    if corporate_events is None:
        corporate_events = {ticker: get_next_earnings_and_dividend_dates(ticker) for ticker in tickers}
    snapshots = get_all_snapshots(tickers)
    header = [
        "ticker", "current_price", "basic_snapshot", "previous_close", "percent_change", "latest_volume",
        "rsi_14", "sma_20", "sma_50", "sma_200", "ema_12", "ema_20", "ema_50", "ema_200",
        "macd", "macd_signal", "bb_upper", "bb_middle", "bb_lower", "atr_14", "adx_14",
        "support_20", "resistance_20",
        "support_75", "resistance_75",
        "support_200", "resistance_200",
        "pct_ytd_return", "low_52w", "high_52w", "range_pos_pct", "pct_from_52w_high", "pct_from_52w_low",
        "earnings_date", "dividend_date", "ex_dividend_date"
    ]
    rows = []
    for ticker in tickers:
        snap = snapshots[ticker]
        current_price = round(get_last_trade_price_from_snapshot(snap), 2) if get_last_trade_price_from_snapshot(snap) is not None else None
        basic_snapshot = get_latest_trade_price(ticker)
        previous_close = round(get_previous_close_from_snapshot(snap), 2) if get_previous_close_from_snapshot(snap) is not None else None
        percent_change = round(get_percent_change_from_snapshot(snap), 2) if get_percent_change_from_snapshot(snap) is not None else None
        latest_volume = round(get_latest_volume_from_snapshot(snap), 2) if get_latest_volume_from_snapshot(snap) is not None else None
        closes, highs, lows = get_historical_ohlc(ticker, lookback_days=365)
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
        def get_swing_sr(highs, lows, window):
            h = highs[-window:]
            l = lows[-window:]
            supports, resistances = find_strong_swing_levels_from_arrays(h, l, swing_window=3, rejection_window=window, tolerance=0.5, min_rejections=2)
            support = supports[-1][1] if supports else (min(l) if len(l) else None)
            resistance = resistances[-1][1] if resistances else (max(h) if len(h) else None)
            return support, resistance
        support_20, resistance_20 = get_swing_sr(highs, lows, 20)
        support_75, resistance_75 = get_swing_sr(highs, lows, 75)
        support_200, resistance_200 = get_swing_sr(highs, lows, 200)
        ytd_52w = get_ytd_52w_indicators_for_ticker(ticker, today_str)
        ce = corporate_events[ticker] if corporate_events and ticker in corporate_events else {}
        row = [
            ticker,
            current_price,
            basic_snapshot,
            previous_close,
            percent_change,
            latest_volume,
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
            ytd_52w['ytd_return'],
            ytd_52w['low_52w'],
            ytd_52w['high_52w'],
            ytd_52w['range_pos_pct'],
            ytd_52w['pct_from_52w_high'],
            ytd_52w['pct_from_52w_low'],
            ce.get('earnings_date'),
            ce.get('dividend_date'),
            ce.get('ex_dividend_date')
        ]
        rows.append(row)
    # Write to CSV
    import csv
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return output_path
