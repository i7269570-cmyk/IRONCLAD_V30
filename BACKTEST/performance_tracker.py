# ============================================================
# IRONCLAD_BACKTEST - Performance Tracker
# ============================================================
import json
import os
from typing import List, Dict


def calculate_performance(results: List[Dict]) -> Dict:
    """
    백테스트 결과 전체 성과 집계
    - 승률, 총수익률, MDD, 샤프비율
    """
    all_trades = []
    for r in results:
        all_trades.extend(r.get("trades", []))

    if not all_trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_pnl": 0,
            "total_return_pct": 0,
            "max_drawdown_pct": 0,
            "sharpe_ratio": 0,
            "avg_hold_bars": 0,
            "profit_factor": 0
        }

    total_trades = len(all_trades)
    wins = [t for t in all_trades if t["pnl"] > 0]
    losses = [t for t in all_trades if t["pnl"] <= 0]

    win_rate = round(len(wins) / total_trades * 100, 2)
    total_pnl = round(sum(t["pnl"] for t in all_trades), 2)
    avg_hold_bars = round(sum(t["hold_bars"] for t in all_trades) / total_trades, 1)

    # 수익 합계 / 손실 합계
    gross_profit = sum(t["pnl"] for t in wins) if wins else 0
    gross_loss = abs(sum(t["pnl"] for t in losses)) if losses else 0
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0

    # MDD 계산
    equity = []
    cumulative = 0
    for t in all_trades:
        cumulative += t["pnl"]
        equity.append(cumulative)

    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / abs(peak) * 100 if peak != 0 else 0
        if dd > max_dd:
            max_dd = dd

    # 샤프비율 (간이)
    import statistics
    pnl_list = [t["pnl_pct"] for t in all_trades]
    if len(pnl_list) > 1:
        avg_pnl = statistics.mean(pnl_list)
        std_pnl = statistics.stdev(pnl_list)
        sharpe = round(avg_pnl / std_pnl * (252 ** 0.5), 2) if std_pnl > 0 else 0
    else:
        sharpe = 0

    # 종목별 요약
    symbol_summary = {}
    for r in results:
        symbol_summary[r["symbol"]] = {
            "trades": r["total_trades"],
            "return_pct": r["total_return_pct"],
            "final_capital": r["final_capital"]
        }

    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": profit_factor,
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": sharpe,
        "avg_hold_bars": avg_hold_bars,
        "symbol_summary": symbol_summary
    }


def save_results(performance: Dict, results: List[Dict], output_path: str) -> None:
    os.makedirs(output_path, exist_ok=True)

    # 성과 요약
    summary_path = os.path.join(output_path, "performance_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(performance, f, ensure_ascii=False, indent=2)

    # 전체 거래 내역
    trades_path = os.path.join(output_path, "all_trades.json")
    all_trades = []
    for r in results:
        all_trades.extend(r.get("trades", []))
    with open(trades_path, "w", encoding="utf-8") as f:
        json.dump(all_trades, f, ensure_ascii=False, indent=2)

    print(f"[BACKTEST] 결과 저장 완료: {output_path}")
    print(f"  총 거래: {performance['total_trades']}회")
    print(f"  승률: {performance['win_rate']}%")
    print(f"  수익 합계: {performance['total_pnl']:,.0f}원")
    print(f"  Profit Factor: {performance['profit_factor']}")
    print(f"  MDD: {performance['max_drawdown_pct']}%")
    print(f"  샤프비율: {performance['sharpe_ratio']}")
