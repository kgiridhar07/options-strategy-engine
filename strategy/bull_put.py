import json
import pandas as pd
import os

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
    print(f"Calculated indicators for {ticker}: {calculated_indicators}")
    
    # 2. Evaluate Strategies:
    strategy_signals = []
    total_weight = 0
    for strategy in strategies:
        strategy_name = strategy['name']
        combo = strategy['combo']
        strategy_type = strategy['type']
        strategy_weight = strategy['weight']

        indicator_values = [calculated_indicators.get(c) for c in combo]

        if all(v is not None for v in indicator_values):
            # Evaluate the signal logic
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
                if indicator_values[0] > stock_data['atr_14'] and (stock_data['bb_upper'] - stock_data['bb_lower']) > 0:
                    signal = "high volatility"
                else:
                    signal = "normal volatility"
            else:
                signal = "neutral"

            analysis["signals"][strategy_name] = {
                "signal": signal,
                "type": strategy_type,
                "weight": strategy_weight,
            }

            # Convert signals to numerical values for combining
            signal_value = 0
            if "strongly bullish" in signal:
                signal_value = 3
            elif "medium bullish" in signal:
                signal_value = 2
            elif "weakly bullish" in signal:
                signal_value = 1
            elif "strongly bearish" in signal:
                signal_value = -3
            elif "medium bearish" in signal:
                signal_value = -2
            elif "weakly bearish" in signal:
                signal_value = -1
            elif "neutral" in signal:
                signal_value = 0  # Default to neutral
            elif "overbought" in signal or "oversold" in signal:
                signal_value = 1 if "overbought" in signal else -1  # Slight adjustment for overbought/oversold

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
    if combined_signal > 2:
        combined_signal_text = "Strongly Bullish"
    elif combined_signal > 0.5:
        combined_signal_text = "Medium Bullish"
    elif combined_signal > -0.5:
        combined_signal_text = "Weakly Bullish"
    elif combined_signal < -2:
        combined_signal_text = "Strongly Bearish"
    elif combined_signal < -0.5:
        combined_signal_text = "Medium Bearish"
    else:
        combined_signal_text = "Weakly Bearish"

    analysis["combined_signal"] = {
        "value": combined_signal,
        "text": combined_signal_text,
    }

    return analysis

def load_config(config_path=None):
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), '../config/credit_spread_indicator.json')
    with open(config_path, 'r') as f:
        return json.load(f)

def load_stock_data(csv_path=None):
    if csv_path is None:
        # Default to latest indicators file in output dir
        output_dir = os.path.join(os.path.dirname(__file__), '../output')
        files = [f for f in os.listdir(output_dir) if f.startswith('indicators_') and f.endswith('.csv')]
        if not files:
            raise FileNotFoundError('No indicators CSV file found in output directory.')
        latest = sorted(files)[-1]
        csv_path = os.path.join(output_dir, latest)
    return pd.read_csv(csv_path)

# Example batch analysis function

def analyze_all_stocks(config_path=None, csv_path=None):
    config = load_config(config_path)
    df = load_stock_data(csv_path)
    results = []
    for _, row in df.iterrows():
        analysis = analyze_stock(row, config)
        results.append(analysis)
    return results

if __name__ == "__main__":
    import json
    output_dir = os.path.join(os.path.dirname(__file__), '../output')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'bull_put_analysis.json')
    with open(output_path, "w") as f:
        json.dump(analyze_all_stocks(), f, indent=2, default=str)
    print(f"Analysis written to {output_path}")