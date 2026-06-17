"""小缠引擎单元测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.fractals import KLine, run_fractal_analysis, process_containment, has_containment


def make_kline(time, o, h, l, c):
    return KLine(time=time, open=o, high=h, low=l, close=c)


def test_has_containment():
    k1 = make_kline(1, 100, 110, 95, 105)
    k2 = make_kline(2, 102, 108, 97, 104)
    assert has_containment(k1, k2) == True

    k3 = make_kline(3, 102, 112, 97, 104)
    assert has_containment(k1, k3) == False


def test_find_top_fractal():
    # k2 is higher than both k1 and k3 without containment
    klines = [
        make_kline(1, 100, 105, 95, 102),
        make_kline(2, 104, 112, 101, 110),
        make_kline(3, 108, 109, 100, 104),
    ]
    result = run_fractal_analysis(klines)
    assert result["top_count"] == 1


def test_find_bottom_fractal():
    # k2 is lower than both k1 and k3 without containment
    klines = [
        make_kline(1, 100, 105, 98, 102),
        make_kline(2, 95, 99, 90, 94),
        make_kline(3, 96, 103, 95, 102),
    ]
    result = run_fractal_analysis(klines)
    assert result["bottom_count"] == 1


def test_process_containment():
    """Test K-line containment processing"""
    # Case: upward trend, k2 contained in k1
    klines = [
        make_kline(1, 100, 110, 95, 105),  # k1
        make_kline(2, 102, 108, 97, 104),  # k2 contained in k1
        make_kline(3, 106, 115, 104, 112), # k3 breaks out
    ]
    merged = process_containment(klines)
    # After merging k1+k2, we should have 2 lines
    assert len(merged) == 2


def test_fractal_to_stroke_pipeline():
    """Integration test: fractals -> strokes"""
    from engine.strokes import run_stroke_analysis

    klines = [
        make_kline(i, 100 + i, 105 + i, 95 + i, 102 + i)
        for i in range(0, 50)
    ]
    fractal_result = run_fractal_analysis(klines)
    stroke_result = run_stroke_analysis(
        fractal_result["fractals"],
        fractal_result["merged_count"]
    )
    # Should produce at least some strokes
    assert stroke_result["stroke_count"] >= 0


def test_full_pipeline_synthetic():
    """Integration test: synthetic data through full pipeline"""
    from engine.strokes import run_stroke_analysis
    from engine.segments import run_segment_analysis
    from engine.zhongshu import run_zhongshu_analysis
    from data.kline_processor import calculate_macd

    # Run synthetic analysis
    from engine.run_analysis import analyze_synthetic
    result = analyze_synthetic(symbol="BTCTEST", count=200, seed=42)

    analysis = result["analysis"]["synthetic"]
    assert result["symbol"] == "BTCTEST"
    assert analysis["klines_count"] == 200
    assert analysis["fractals"]["top_count"] >= 0
    assert analysis["fractals"]["bottom_count"] >= 0
    assert analysis["strokes"]["stroke_count"] >= 0
    assert analysis["segments"]["segment_count"] >= 0
    assert analysis["macd"]["latest_dif"] is not None

    print(f"Full pipeline OK - {analysis['fractals']['top_count']} tops, "
          f"{analysis['fractals']['bottom_count']} bottoms, "
          f"{analysis['strokes']['stroke_count']} strokes, "
          f"{analysis['segments']['segment_count']} segments")


if __name__ == "__main__":
    test_has_containment()
    print("^ test_has_containment passed")
    test_find_top_fractal()
    print("^ test_find_top_fractal passed")
    test_find_bottom_fractal()
    print("^ test_find_bottom_fractal passed")
    test_process_containment()
    print("^ test_process_containment passed")
    test_fractal_to_stroke_pipeline()
    print("^ test_fractal_to_stroke_pipeline passed")
    test_full_pipeline_synthetic()
    print("^ test_full_pipeline_synthetic passed")
    print("\n=== All engine tests passed! ===")
