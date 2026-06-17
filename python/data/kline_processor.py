"""K线数据预处理模块"""

from typing import List


def parse_klines(raw_data: List[list]) -> "List":
    """
    Convert Binance kline raw data to KLine list.
    Binance kline format: [open_time, open, high, low, close, volume, ...]

    Raises ValueError if any row has fewer than 6 elements.
    """
    from engine.fractals import KLine

    klines = []
    for i, row in enumerate(raw_data):
        if len(row) < 6:
            raise ValueError(f"Row {i}: expected at least 6 elements, got {len(row)}")
        try:
            klines.append(KLine(
                time=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5])
            ))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Row {i}: invalid data — {e}") from e

    return klines


def calculate_macd(klines: "List", fast: int = 12, slow: int = 26, signal: int = 9) -> "dict":
    """
    Calculate MACD indicator.

    Returns dict with keys: dif, dea, macd (the histogram bar = (DIF-DEA)*2).
    All values rounded to 6 decimal places.
    Returns empty lists when fewer than slow+signal klines.
    """
    if len(klines) < slow + signal:
        return {"dif": [], "dea": [], "macd": []}

    closes = [k.close for k in klines]

    def ema(data, period):
        result = []
        multiplier = 2 / (period + 1)
        result.append(data[0])
        for i in range(1, len(data)):
            result.append(data[i] * multiplier + result[-1] * (1 - multiplier))
        return result

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)

    dif = [ema_fast[i] - ema_slow[i] for i in range(len(closes))]
    dea = ema(dif, signal)
    macd_bar = [(dif[i] - dea[i]) * 2 for i in range(len(dif))]

    return {
        "dif": [round(x, 6) for x in dif],
        "dea": [round(x, 6) for x in dea],
        "macd": [round(x, 6) for x in macd_bar],
    }


if __name__ == "__main__":
    import sys, os, math
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from engine.fractals import KLine

    # Create synthetic klines (100 candles with sine wave)
    raw_data = []
    for i in range(100):
        base = 50000.0 + 1000.0 * math.sin(i * 0.1)
        open_val = base
        close_val = base + 100.0 * math.sin((i + 1) * 0.1)
        high_val = max(open_val, close_val) + 50.0
        low_val = min(open_val, close_val) - 50.0
        raw_data.append([1700000000000 + i * 60000, open_val, high_val, low_val, close_val, 100.0 + i])

    klines = parse_klines(raw_data)
    assert len(klines) == 100, f"Expected 100 klines, got {len(klines)}"
    assert klines[0].time == 1700000000000
    assert abs(klines[0].open - 50000.0) < 1.0

    macd = calculate_macd(klines)
    assert len(macd["dif"]) == 100
    assert len(macd["dea"]) == 100
    assert len(macd["macd"]) == 100
    assert "histogram" not in macd  # removed

    # Test input validation
    try:
        parse_klines([[1, 2, 3]])
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    # Test insufficient data
    short_data = [[1700000000000 + i * 60000, 50000.0, 50100.0, 49900.0, 50050.0, 100.0] for i in range(10)]
    short_klines = parse_klines(short_data)
    short_macd = calculate_macd(short_klines)
    assert short_macd == {"dif": [], "dea": [], "macd": []}

    print("All self-tests passed!")
    print(f"  - Parsed {len(klines)} K-lines")
    print(f"  - MACD DIF last: {macd['dif'][-1]:.6f}")
    print(f"  - MACD DEA last: {macd['dea'][-1]:.6f}")
    print(f"  - MACD bar last: {macd['macd'][-1]:.6f}")
