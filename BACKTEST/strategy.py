# =========================
# A: 기존 - 메인전략
# =========================
class MeanReversionBBStrategy_A:
    TAKE_PROFIT = 0.015
    STOP_LOSS   = 0.010
    MAX_HOLD    = 5

    def on_bar(self, row, position):
        if position is not None: return None
        try:
            if row['close'] < row['ma20'] * 0.978: return None
            if row['rsi'] < 40 and row['close'] <= row['bb_lower'] * 1.006:
                if row['close'] > (row['low'] * 1.01): return "BUY"
        except: return None
        return None

    def on_position(self, row, position):
        if position is None: return None
        pnl = (row["close"] - position["entry_price"]) / position["entry_price"]
        hold = position.get("hold_bars", 0)
        if row['close'] >= row['bb_middle'] or pnl >= self.TAKE_PROFIT or hold >= self.MAX_HOLD or pnl <= -self.STOP_LOSS:
            return "EXIT"
        position["hold_bars"] = hold + 1
        return None

# =========================
# B: 기존 - 전략 B
# =========================
class MeanReversionBBStrategy_B:
    TAKE_PROFIT = 0.015
    STOP_LOSS   = 0.010
    MAX_HOLD    = 5

    def on_bar(self, row, position):
        if position is not None: return None
        try:
            if row['close'] < row['ma20'] * 0.97: return None
            if row['rsi'] < 37 and row['close'] <= row['bb_lower'] * 1.0:
                if row['close'] > (row['low'] * 1.006): return "BUY"
        except: return None
        return None

    def on_position(self, row, position):
        if position is None: return None
        pnl = (row["close"] - position["entry_price"]) / position["entry_price"]
        hold = position.get("hold_bars", 0)
        if row['close'] >= row['bb_middle'] or pnl >= self.TAKE_PROFIT or hold >= self.MAX_HOLD or pnl <= -self.STOP_LOSS:
            return "EXIT"
        position["hold_bars"] = hold + 1
        return None

# =========================
# C: 기존 - 보조전략 C
# =========================
class MeanReversionBBStrategy_C:
    TAKE_PROFIT = 0.015
    STOP_LOSS   = 0.010
    MAX_HOLD    = 5

    def on_bar(self, row, position):
        if position is not None: return None
        try:
            if row['close'] < row['ma20'] * 0.97: return None
            if row['rsi'] < 35 and row['close'] <= row['bb_lower'] * 0.995:
                if row['close'] > (row['low'] * 1.005): return "BUY"
        except: return None
        return None

    def on_position(self, row, position):
        if position is None: return None
        pnl = (row["close"] - position["entry_price"]) / position["entry_price"]
        hold = position.get("hold_bars", 0)
        if row['close'] >= row['bb_middle'] or pnl >= self.TAKE_PROFIT or hold >= self.MAX_HOLD or pnl <= -self.STOP_LOSS:
            return "EXIT"
        position["hold_bars"] = hold + 1
        return None

# =========================
# D: 신규 - MeanReversion_Disparity
# =========================
class MeanReversion_Disparity:
    TAKE_PROFIT = 0.015
    STOP_LOSS   = 0.010
    MAX_HOLD    = 5

    def on_bar(self, row, position):
        if position is not None: return None
        try:
            # ENTRY: ma20 대비 -4% ~ -10% 구간 & 거래량 1.2배 & 저가반등 0.5%
            if (row['close'] < row['ma20'] * 0.96) and (row['close'] > row['ma20'] * 0.90):
                if row['volume_ratio'] >= 1.2 and row['close'] > (row['low'] * 1.005):
                    return "BUY"
        except: return None
        return None

    def on_position(self, row, position):
        if position is None: return None
        pnl = (row["close"] - position["entry_price"]) / position["entry_price"]
        hold = position.get("hold_bars", 0)
        # EXIT: 이평선 터치 또는 익절/손절/보유일수
        if row['close'] >= row['ma20'] or pnl >= self.TAKE_PROFIT or pnl <= -self.STOP_LOSS or hold >= self.MAX_HOLD:
            return "EXIT"
        position["hold_bars"] = hold + 1
        return None