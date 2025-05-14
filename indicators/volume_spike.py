# indicators/volume_spike.py

def detect_volume_spike(volumes, window=20, threshold=2.0):
    """
    Detects if the latest volume is a spike compared to the rolling average.
    Args:
        volumes (list[float]): List of volume values.
        window (int): Number of periods for rolling average.
        threshold (float): Multiplier for spike detection.
    Returns:
        bool: True if latest volume is a spike, False otherwise.
    """
    if len(volumes) < window + 1:
        return False
    avg = sum(volumes[-window-1:-1]) / window
    return volumes[-1] > avg * threshold
