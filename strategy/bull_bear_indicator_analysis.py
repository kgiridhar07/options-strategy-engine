import json
import pandas as pd
import os
from datetime import datetime

def analyze_stock(stock_data, config):
    """
    Analyzes a stock based on the provided data and configuration,
    combining signals from all strategies.

    Args:
        stock_data (pd.Series): Pandas Series containing stock data.
        config (dict): Configuration loaded from the JSON file.

    Returns:
        dict: A dictionary containing the analysis and a combined signal.
    """
    ticker = stock_data['ticker']
    analysis = {"ticker": ticker, "signals": {}, "combined_signal": {}}
    indicators = config['indicators']
    strategies = config['strategies']

    # 1. Calculate Indicators:
    calculated_indicators = {}
    for indicator_name, indicator_data in indicators.items():
        if indicator_name in stock_data:
            calculated_indicators[indicator_name] = stock_data[indicator_name]
        else:
            calculated_indicators[indicator_name] = None  # Handle missing
    
    # 2. Evaluate Strategies:
    strategy_signals = []
    total_weight = 0
    for strategy in strategies:
        strategy_name = strategy['name']
        combo = strategy['combo']
        strategy_type = strategy['type']
        strategy_weight = strategy['weight']

        indicator_values = [calculated_indicators.get(c) for c in combo]

        if all(v is not None for v in indicator_values) and stock_data['current_price'] is not None: # Ensure current_price is available too
            signal = "neutral" # Default signal for specific strategy if conditions aren't met

            # --- Specific Strategy Logic ---
            if strategy_name == "Trend Crossover: SMA":
                if indicator_values[0] > indicator_values[1]:
                    signal = "strongly bullish"
                elif indicator_values[0] < indicator_values[1]:
                    signal = "strongly bearish"
                else:
                    signal = "neutral"
            elif strategy_name == "Trend Crossover: EMA":
                if indicator_values[0] > indicator_values[1]:
                    signal = "medium bullish"
                elif indicator_values[0] < indicator_values[1]:
                    signal = "medium bearish"
                else:
                    signal = "neutral"
            elif strategy_name == "Trend Strength with ADX":
                if indicator_values[0] > 20 and indicator_values[1] > indicator_values[2]:
                    signal = "strongly bullish"
                elif indicator_values[0] > 20 and indicator_values[1] < indicator_values[2]:
                    signal = "strongly bearish"
                else:
                    signal = "weakly neutral"
            elif strategy_name == "MACD Crossover":
                if indicator_values[0] > indicator_values[1]:
                    signal = "bullish crossover"
                elif indicator_values[0] < indicator_values[1]:
                    signal = "bearish crossover"
                else:
                    signal = "neutral"
            elif strategy_name == "Overbought/Oversold with RSI & Bollinger Bands":
                if indicator_values[0] > 70 and stock_data['current_price'] > stock_data['bb_upper']:
                    signal = "strongly overbought"
                elif indicator_values[0] < 30 and stock_data['current_price'] < stock_data['bb_lower']:
                    signal = "strongly oversold"
                else:
                    signal = "neutral"
            elif strategy_name == "Support Confirmation for Bull Put":
                if stock_data['current_price'] > indicator_values[0] and stock_data['current_price'] > indicator_values[1] and stock_data['current_price'] > indicator_values[2]:
                    signal = "strongly bullish"
                else:
                    signal = "weakly bullish"
            elif strategy_name == "Resistance Confirmation for Bear Call":
                if stock_data['current_price'] < indicator_values[0] and stock_data['current_price'] < indicator_values[1] and stock_data['current_price'] < indicator_values[2]:
                    signal = "strongly bearish"
                else:
                    signal = "weakly bearish"
            elif strategy_name == "High Volatility Opportunity":
                # Assuming atr_14 is the first indicator_value
                # The signal in config is "high premium potential if atr_14 is elevated and bb range is wide; ensure trend direction is favorable"
                # This logic is simplified for now; you might want to compare atr_14 to its own historical average or a fixed threshold.
                # Also, the combo for this strategy in config is ["atr_14", "bb_upper", "bb_lower"]
                current_atr = calculated_indicators.get('atr_14')
                bb_upper = calculated_indicators.get('bb_upper')
                bb_lower = calculated_indicators.get('bb_lower')

                if current_atr is not None and bb_upper is not None and bb_lower is not None:
                    # Define what "elevated" ATR means (e.g., > 1.5, or > average ATR)
                    # For simplicity, let's say if ATR is above a certain value AND BB range is wide enough
                    # You'll need to define `YOUR_ATR_THRESHOLD` and `YOUR_BB_RANGE_THRESHOLD`
                    # For now, a placeholder logic.
                    if current_atr > 1.0 and (bb_upper - bb_lower) / stock_data['current_price'] > 0.05: # Example thresholds
                        signal = "high volatility"
                    else:
                        signal = "normal volatility"
                else:
                    signal = "normal volatility" # Default if ATR/BB data is missing
            
            # --- NEW STRATEGY LOGIC: Relative Strength & Position for Bull Put ---
            elif strategy_name == "Relative Strength & Position for Bull Put":
                pct_ytd_return = calculated_indicators.get('pct_ytd_return')
                pct_from_52w_low = calculated_indicators.get('pct_from_52w_low')
                pct_from_52w_high = calculated_indicators.get('pct_from_52w_high')
                current_price = stock_data.get('current_price') # Ensure current_price is directly accessible

                # Define thresholds (adjust these based on your strategy and backtesting)
                YTD_POSITIVE_STRONG = 10.0  # > +10% YTD
                YTD_POSITIVE_MODERATE = 0.5  # > +0.5% YTD (small positive)
                YTD_NEGATIVE_MODERATE = -10.0 # < -10% YTD
                YTD_NEGATIVE_STRONG = -20.0 # < -20% YTD

                FROM_LOW_STRONG_REBOUND = 50.0 # > 50% above 52-week low
                FROM_LOW_MODERATE_REBOUND = 20.0 # > 20% above 52-week low
                FROM_LOW_NEAR = 5.0 # Within 5% of 52-week low (i.e., pct_from_52w_low <= 5.0)

                # pct_from_52w_high is already a negative value if below the high (e.g., -35.47)
                FROM_HIGH_CLOSE = -20.0 # Within 20% below 52-week high (e.g., pct_from_52w_high > -20.0)
                FROM_HIGH_MODERATE_BELOW = -40.0 # Between 20% and 40% below 52-week high (e.g., pct_from_52w_high > -40.0 and <= -20.0)
                FROM_HIGH_FAR_BELOW = -50.0 # More than 50% below 52-week high (e.g., pct_from_52w_high <= -50.0)


                if all(x is not None for x in [pct_ytd_return, pct_from_52w_low, pct_from_52w_high, current_price]):
                    # Scenario 1: Strongly Bullish for Bull Put (strong performance and well off lows)
                    if pct_ytd_return > YTD_POSITIVE_STRONG and \
                       pct_from_52w_low > FROM_LOW_STRONG_REBOUND and \
                       pct_from_52w_high > FROM_HIGH_MODERATE_BELOW: # e.g., -30%
                        signal = "strongly bullish"
                        signal_value_numeric = 1.0 # Using a scale for this specific indicator

                    # Scenario 2: Moderately Bullish for Bull Put (decent performance, good distance from lows)
                    elif (YTD_POSITIVE_MODERATE <= pct_ytd_return <= YTD_POSITIVE_STRONG or (pct_ytd_return > YTD_NEGATIVE_MODERATE and pct_ytd_return < YTD_POSITIVE_MODERATE)) and \
                         pct_from_52w_low > FROM_LOW_MODERATE_REBOUND and \
                         pct_from_52w_high > FROM_HIGH_FAR_BELOW: # e.g., -45%
                        signal = "medium bullish" # Changed from "moderately bullish" for consistency with existing signals
                        signal_value_numeric = 0.6

                    # Scenario 3: Neutral for Bull Put (mixed signals, stock in a range)
                    elif (YTD_NEGATIVE_MODERATE <= pct_ytd_return <= YTD_POSITIVE_MODERATE) and \
                         (FROM_LOW_NEAR <= pct_from_52w_low <= FROM_LOW_STRONG_REBOUND) and \
                         (FROM_HIGH_FAR_BELOW <= pct_from_52w_high <= FROM_HIGH_CLOSE):
                        signal = "neutral"
                        signal_value_numeric = 0.2 # Slightly positive bias for neutral, as we are looking for bull put

                    # Scenario 4: Weakly Bearish (Cautious for Bull Put) - underperformance, closer to lows
                    elif pct_ytd_return < YTD_NEGATIVE_MODERATE and \
                         pct_from_52w_low < FROM_LOW_MODERATE_REBOUND and \
                         pct_from_52w_high < FROM_HIGH_MODERATE_BELOW: # Meaning it's further below the high
                        signal = "weakly bearish"
                        signal_value_numeric = -0.4

                    # Scenario 5: Strongly Bearish (Avoid Bull Put) - significant weakness, near lows
                    elif pct_ytd_return < YTD_NEGATIVE_STRONG and \
                         pct_from_52w_low <= FROM_LOW_NEAR: # Very close to 52-week low
                        signal = "strongly bearish"
                        signal_value_numeric = -1.0
                    else: # Default if none of the above scenarios match, still within valid data
                        signal = "neutral"
                        signal_value_numeric = 0.0 # Truly neutral if no specific condition met
                else:
                    signal = "Insufficient data"
                    signal_value_numeric = 0 # Cannot determine, treat as neutral for combined signal if data is missing

            # --- END NEW STRATEGY LOGIC ---
            else:
                signal = "neutral" # Default for strategies not explicitly handled, though all should be.
                signal_value_numeric = 0 # Default for strategies not explicitly handled.


            analysis["signals"][strategy_name] = {
                "signal": signal,
                "type": strategy_type,
                "weight": strategy_weight,
            }

            # Convert signals to numerical values for combining
            # This block needs to be updated to match the new `signal_value_numeric` for the new strategy
            # For other strategies, ensure your mapping is consistent.
            signal_value = 0
            if "strongly bullish" in signal:
                signal_value = 3
            elif "medium bullish" in signal or "bullish crossover" in signal: # "medium bullish" now covers the new strategy's 0.6
                signal_value = 2
            elif "weakly bullish" in signal:
                signal_value = 1
            elif "strongly bearish" in signal:
                signal_value = -3
            elif "medium bearish" in signal or "bearish crossover" in signal:
                signal_value = -2
            elif "weakly bearish" in signal:
                signal_value = -1
            elif "neutral" in signal or "normal volatility" in signal:
                signal_value = 0  # Default to neutral
            elif "overbought" in signal:
                signal_value = 1 # Overbought is often seen as negative for bullish, positive for bearish. Adjust if you need a specific value.
            elif "oversold" in signal:
                signal_value = -1 # Oversold is often seen as positive for bullish, negative for bearish. Adjust.
            elif "high volatility" in signal:
                signal_value = 0 # Volatility itself isn't bullish/bearish, but a condition. Adjust if you want to bias it.
            
            # For the new strategy, directly use the calculated numeric value if it was calculated
            if strategy_name == "Relative Strength & Position for Bull Put" and signal != "Insufficient data":
                # Scale the 1.0 to -1.0 scale to your existing 3 to -3 scale
                # Mapping: 1.0 -> 3, 0.6 -> 2, 0.2 -> 0, -0.4 -> -1, -1.0 -> -3
                if signal_value_numeric == 1.0:
                    signal_value = 3
                elif signal_value_numeric == 0.6:
                    signal_value = 2
                elif signal_value_numeric == 0.2:
                    signal_value = 0 # Neutral is 0
                elif signal_value_numeric == -0.4:
                    signal_value = -1
                elif signal_value_numeric == -1.0:
                    signal_value = -3
                elif signal_value_numeric == 0.0: # Explicitly neutral for the new strategy
                    signal_value = 0


            strategy_signals.append((signal_value, strategy_weight))
            total_weight += strategy_weight

        else:
            analysis["signals"][strategy_name] = {
                "signal": "Insufficient data",
                "type": strategy_type,
                "weight": strategy_weight,
            }

    # 3. Combine Signals:
    combined_signal = 0
    if total_weight > 0:
        for signal_value, strategy_weight in strategy_signals:
            combined_signal += signal_value * (strategy_weight / total_weight)

    # Interpret the combined signal
    if combined_signal > 1.25:
        combined_signal_text = "Strongly Bullish"
    elif combined_signal > 0.75:
        combined_signal_text = "Medium Bullish"
    elif combined_signal > 0.25:
        combined_signal_text = "Weakly Bullish"
    elif combined_signal < -1.25:
        combined_signal_text = "Strongly Bearish"
    elif combined_signal < -0.75:
        combined_signal_text = "Medium Bearish"
    elif combined_signal < -0.25: # Added this to catch between -0.75 and -0.25 as weakly bearish
        combined_signal_text = "Weakly Bearish"
    else: # This will catch values between -0.25 and 0.25
        combined_signal_text = "Neutral" # Explicitly neutral for values close to zero

    analysis["combined_signal"] = {
        "value": combined_signal,
        "text": combined_signal_text,
    }

    # Add earnings information at the top level
    days_to_earnings, earnings_nearby = process_earnings_days(stock_data)
    analysis['earnings_nearby'] = earnings_nearby
    analysis['earnings_date'] = stock_data.get('earnings_date')
    analysis['days_to_earnings'] = days_to_earnings

    return analysis

def load_config(config_path=None):
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), '../config/credit_spread_indicator.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def load_stock_data(csv_path=None):
    if csv_path is None:
        # Always use today's indicator file from output/indicator_out
        today_str = datetime.today().strftime('%Y-%m-%d')
        output_dir = os.path.join(os.path.dirname(__file__), '../output/indicator_out')
        csv_path = os.path.join(output_dir, f'indicators_{today_str}.csv')
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Indicator CSV for today not found: {csv_path}")
    df = pd.read_csv(csv_path)
    # Ensure numerical columns are truly numerical, coercing errors
    numerical_cols = [
        'current_price', 'previous_close', 'percent_change', 'latest_volume',
        'rsi_14', 'sma_20', 'sma_50', 'sma_200', 'ema_12', 'ema_20', 'ema_50', 'ema_200',
        'macd', 'macd_signal', 'bb_upper', 'bb_middle', 'bb_lower', 'atr_14', 'adx_14',
        'support_20', 'resistance_20', 'support_75', 'resistance_75', 'support_200',
        'resistance_200', 'pct_ytd_return', 'low_52w', 'high_52w', 'range_pos_pct',
        'pct_from_52w_high', 'pct_from_52w_low'
    ]
    for col in numerical_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def process_earnings_days(row):
    """
    Returns:
      - days_to_earnings (int or None)
      - earnings_nearby: True if earnings within 10 days (including today), else False
    """
    earnings_date = row.get('earnings_date')

    if earnings_date and str(earnings_date).strip():
        try:
            today = datetime.today().date()
            # Handle potential timestamp in earnings_date if it's from a DataFrame
            if isinstance(earnings_date, pd.Timestamp):
                earnings_dt = earnings_date.date()
            else:
                earnings_dt = datetime.strptime(str(earnings_date), '%Y-%m-%d').date()
            
            days_to_earnings = (earnings_dt - today).days

            if days_to_earnings < 0:
                return None, False  # Earnings already passed
            earnings_nearby = days_to_earnings <= 10
            return days_to_earnings, earnings_nearby
        except Exception as e:
            print(f"Error parsing earnings date: {earnings_date} - {e}")
            return None, False

    return None, False

# Example batch analysis function
def analyze_all_stocks(config_path=None, csv_path=None):
    config = load_config(config_path)
    df = load_stock_data(csv_path)
    results = []
    for _, row in df.iterrows():
        analysis = analyze_stock(row, config) # analyze_stock now handles earnings itself
        # Add current_price, high_52w, and low_52w from indicator CSV to the analysis output
        analysis['current_price'] = row.get('current_price')
        analysis['high_52w'] = row.get('high_52w')
        analysis['low_52w'] = row.get('low_52w')
        results.append(analysis)
    return results

if __name__ == "__main__":
    import json
    from datetime import datetime
    # Create the output directory 'output/bull_bear_analysis' if it doesn't exist
    bull_bear_dir = os.path.join(os.path.dirname(__file__), '../output/bull_bear_analysis')
    os.makedirs(bull_bear_dir, exist_ok=True)
    today_str = datetime.today().strftime('%Y-%m-%d')
    output_path = os.path.join(bull_bear_dir, f'bull_bear_analysis_{today_str}.json')
    with open(output_path, "w") as f:
        json.dump(analyze_all_stocks(), f, indent=2, default=str)
    print(f"Analysis written to {output_path}")