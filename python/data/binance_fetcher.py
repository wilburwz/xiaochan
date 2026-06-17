"""Binance 数据拉取 — 通过公开 REST API 获取K线"""

import urllib.request
import json
import time


BINANCE_KLINE_URL = "https://api.binance.com/api/v3/klines"


def fetch_klines(symbol: str, period: str, limit: int = 500) -> list:
    """
    从 Binance 公开 API 获取 K 线数据

    参数：
    - symbol: 交易对如 BTCUSDT
    - period: K线周期 1m/5m/15m/1h/4h/1d/1w
    - limit: 获取数量（最大1000）

    返回原始 K 线列表，每根为 [time, open, high, low, close, volume, ...]
    """
    url = f"{BINANCE_KLINE_URL}?symbol={symbol.upper()}&interval={period}&limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data
        except Exception as e:
            if attempt == 2:
                raise ConnectionError(f"无法获取 {symbol} {period} K线: {e}")
            time.sleep(1)

    return []
