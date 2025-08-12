# scoring.py
import numpy as np

def ang_diff(a, b):
    return abs((a - b + 180) % 360 - 180)

class ScoreCalculator:
    """
    Calcula o score ponderando: altura, período, vento e offshore/alinhamento.
    Os 'pesos' e limites vêm dos sliders (por spot) e podem variar por praia.
    """
    def __init__(self, orientacao_spot: float,
                 altura_min: float, altura_max: float,
                 periodo_min: float, vento_max_ok: float, offshore_tol: float,
                 pesos: dict[str, float]):
        self.orient = orientacao_spot
        self.alt_min = altura_min
        self.alt_max = altura_max
        self.per_min = periodo_min
        self.wind_ok = vento_max_ok
        self.off_tol = offshore_tol
        self.pesos = pesos

    def _clamp01(self, x): return max(0.0, min(1.0, x))

    def calc_row(self, row) -> float:
        h = float(row.get("swell_wave_height", 0.0))
        p = float(row.get("swell_wave_period", 0.0))
        d_s = float(row.get("swell_wave_direction", 0.0))
        w = float(row.get("wind_speed_10m", 0.0))
        d_w = float(row.get("wind_direction_10m", 0.0))

        # Altura (janela ideal)
        if self.alt_max > self.alt_min:
            s_alt = self._clamp01((h - self.alt_min) / (self.alt_max - self.alt_min))
        else:
            s_alt = 0.0

        # Período (bom >= per_min)
        s_per = 1.0 if p >= self.per_min else self._clamp01(p / self.per_min)

        # Vento (quanto menor melhor, até o limite ok)
        s_wind = self._clamp01(1 - (w / max(self.wind_ok, 0.001)))

        # Offshore: vento oposto à orientação do pico
        offshore_target = (self.orient + 180) % 360
        s_off = self._clamp01(1 - ang_diff(offshore_target, d_w) / max(self.off_tol, 1))

        # Alinhamento do swell com a orientação
        s_align = self._clamp01(1 - ang_diff(d_s, self.orient) / 180.0)

        # Combina (offshore * vento) como um termo e soma alinhamento no bloco de direção
        wind_block = s_off * s_wind
        dir_block = 0.5 * s_off + 0.5 * s_align  # simples, pode ajustar

        score = (
            self.pesos.get("altura", 0.35)  * s_alt   +
            self.pesos.get("periodo", 0.35) * s_per   +
            self.pesos.get("vento", 0.10)   * wind_block +
            self.pesos.get("direcao", 0.20) * dir_block
        ) / max(sum(self.pesos.values()), 1e-6)

        return round(10 * self._clamp01(score), 2)

    def apply(self, df):
        df = df.copy()
        df["score"] = df.apply(self.calc_row, axis=1)
        return df