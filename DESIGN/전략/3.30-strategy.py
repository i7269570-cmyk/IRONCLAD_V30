# =========================
# A: 기존  -메인전략
# =========================
class MeanReversionBBStrategy_A:
    TAKE_PROFIT = 0.015
    STOP_LOSS   = 0.010
    MAX_HOLD    = 5

    def on_bar(self, row, position):
        if position is not None:
            return None

        try:
            if row['close'] < row['ma20'] * 0.978:
                return None

            if row['rsi'] < 40 and row['close'] <= row['bb_lower'] * 1.006:
                if row['close'] > (row['low'] * 1.01):
                    return "BUY"
        except:
            return None

        return None

    def on_position(self, row, position):
        if position is None:
            return None

        pnl = (row["close"] - position["entry_price"]) / position["entry_price"]
        hold = position.get("hold_bars", 0)

        if row['close'] >= row['bb_middle']:
            return "EXIT"
        if pnl >= self.TAKE_PROFIT:
            return "EXIT"
        if hold >= self.MAX_HOLD:
            return "EXIT"
        if pnl <= -self.STOP_LOSS:
            return "EXIT"

        position["hold_bars"] = hold + 1
        return None


# =========================
# B: 중간 (추천 후보)-탈락
# =========================
class MeanReversionBBStrategy_B:
    TAKE_PROFIT = 0.015
    STOP_LOSS   = 0.010
    MAX_HOLD    = 5

    def on_bar(self, row, position):
        if position is not None:
            return None

        try:
            if row['close'] < row['ma20'] * 0.976:
                return None

            if row['rsi'] < 40 and row['close'] <= row['bb_lower'] * 1.008:
                if row['close'] > (row['low'] * 1.01):
                    return "BUY"
        except:
            return None

        return None

    def on_position(self, row, position):
        if position is None:
            return None

        pnl = (row["close"] - position["entry_price"]) / position["entry_price"]
        hold = position.get("hold_bars", 0)

        if row['close'] >= row['bb_middle']:
            return "EXIT"
        if pnl >= self.TAKE_PROFIT:
            return "EXIT"
        if hold >= self.MAX_HOLD:
            return "EXIT"
        if pnl <= -self.STOP_LOSS:
            return "EXIT"

        position["hold_bars"] = hold + 1
        return None


# =========================
# C: 강화 (현재 최고)-보조전략
# =========================
class MeanReversionBBStrategy_C:
    TAKE_PROFIT = 0.015
    STOP_LOSS   = 0.010
    MAX_HOLD    = 5

    def on_bar(self, row, position):
        if position is not None:
            return None

        try:
            if row['close'] < row['ma20'] * 0.97:
                return None

            if row['rsi'] < 35 and row['close'] <= row['bb_lower'] * 0.995:
                if row['close'] > (row['low'] * 1.005):
                    return "BUY"
        except:
            return None

        return None

    def on_position(self, row, position):
        if position is None:
            return None

        pnl = (row["close"] - position["entry_price"]) / position["entry_price"]
        hold = position.get("hold_bars", 0)

        if row['close'] >= row['bb_middle']:
            return "EXIT"
        if pnl >= self.TAKE_PROFIT:
            return "EXIT"
        if hold >= self.MAX_HOLD:
            return "EXIT"
        if pnl <= -self.STOP_LOSS:
            return "EXIT"

        position["hold_bars"] = hold + 1
        return None
        
        
        ===== A (기존) =====
거래수: 481
승률: 0.561
PF: 1.775
평균: 0.00261
MDD: 0.0971

===== B (중간) =====
거래수: 578
승률: 0.562
PF: 1.678
평균: 0.002473
MDD: 0.1418

===== C (강화) =====
거래수: 748
승률: 0.591
PF: 2.439
평균: 0.003991
MDD: 0.0795
        