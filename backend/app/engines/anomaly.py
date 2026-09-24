"""Live anomaly signals on the replay stream (SPEC.md §9.6).

  * rolling robust z-score (median / MAD) on torque, SPP, hookload and delta pit volume
  * two-sided CUSUM on delta pit volume: sustained drop -> possible_losses, sustained gain -> possible_influx
Output wording is always "Abnormal behaviour" + the channels that triggered it; never a diagnosis.
"""
from __future__ import annotations

from collections import deque

import numpy as np

from app.config import cfg

CHANNELS = ("torque", "spp", "hookload", "dpit")


class AnomalyDetector:
    def __init__(self, sample_period_s: float):
        c = cfg()["anomaly"]
        self.n = max(c["min_samples"], int(c["window_s"] / max(sample_period_s, 1)))
        self.z = c["z_thresh"]
        self.k, self.h = c["cusum_k"], c["cusum_h"]
        self.min_samples = c["min_samples"]
        self.buf = {ch: deque(maxlen=self.n) for ch in CHANNELS}
        self.last_pit = None
        self.cpos = self.cneg = 0.0
        self.persist = c["persist"]
        self.min_flow = c["min_flow_gpm"]
        self.streak: dict[str, int] = {ch: 0 for ch in CHANNELS}

    def update(self, s: dict) -> dict | None:
        """Only evaluated while circulating (flow above min_flow_gpm); a channel must stay abnormal for
        `persist` consecutive samples, so single spikes at pipe connections do not fire."""
        pit = s.get("pit_vol")
        if (s.get("flow_in") or 0) < self.min_flow:
            self.last_pit = pit if pit is not None else self.last_pit
            self.streak = {ch: 0 for ch in CHANNELS}
            return None
        dpit = None if pit is None or self.last_pit is None else pit - self.last_pit
        self.last_pit = pit if pit is not None else self.last_pit
        vals = {"torque": s.get("torque"), "spp": s.get("spp"), "hookload": s.get("hookload"), "dpit": dpit}
        triggered = []
        zs = {}
        for ch, v in vals.items():
            b = self.buf[ch]
            if v is None:
                continue
            if len(b) >= self.min_samples:
                arr = np.fromiter(b, float)
                med = float(np.median(arr))
                mad = float(np.median(np.abs(arr - med))) * 1.4826
                if mad > 1e-9:
                    z = (v - med) / mad
                    zs[ch] = round(z, 2)
                    if abs(z) >= self.z and ch != "dpit":
                        self.streak[ch] += 1
                        if self.streak[ch] >= self.persist:
                            triggered.append(ch)
                    else:
                        self.streak[ch] = 0
            b.append(v)
        signal = None
        if dpit is not None and len(self.buf["dpit"]) >= self.min_samples:
            arr = np.fromiter(self.buf["dpit"], float)
            med = float(np.median(arr))
            mad = float(np.median(np.abs(arr - med))) * 1.4826 or 1e-6
            x = (dpit - med) / mad
            self.cpos = max(0.0, self.cpos + x - self.k)
            self.cneg = max(0.0, self.cneg - x - self.k)
            if self.cneg > self.h:
                signal, self.cneg = "possible_losses", 0.0
                triggered.append("pit volume (sustained drop)")
            elif self.cpos > self.h:
                signal, self.cpos = "possible_influx", 0.0
                triggered.append("pit volume (sustained gain)")
        if not triggered:
            return None
        return {"title": "Abnormal behaviour", "channels": triggered, "signal": signal, "z": zs}
