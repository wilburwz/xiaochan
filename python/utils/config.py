"""小缠全局配置"""

DEFAULT_CONFIG = {
    "kline_periods": ["1h", "4h", "1d"],
    "kline_limit": 500,
    "stroke_min_bars": 5,
    "macd_params": {"fast": 12, "slow": 26, "signal": 9},
    "divergence_threshold": 0.7,
    "watchlist": ["BTCUSDT", "ETHUSDT"],
    "stop_loss_buffer_pct": 0.02,
    "take_profit_ratio": 2.0,
}
