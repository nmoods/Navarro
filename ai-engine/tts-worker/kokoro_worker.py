# SPDX-License-Identifier: GPL-3.0-or-later
"""NaRRAVO Kokoro TTS worker.

Runs as a separate process so the GPL-3.0 phonemizer/espeak-ng dependency chain stays isolated from the
(permissively licensed) NaRRAVO backend. Protocol: one JSON object per line on stdin, one JSON response
per line on stdout.

  {"op": "ping"}
  {"op": "voices"}
  {"op": "synthesize", "text": "...", "voice": "am_michael" | "af_bella:0.6,am_adam:0.4",
   "speed": 1.0, "lang": "en-us", "out": "C:/path/file.wav"}
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro


def _voice(engine: Kokoro, spec: str):
    if "," not in spec and ":" not in spec:
        return spec
    total, style = 0.0, None
    for part in spec.split(","):
        name, _, weight = part.partition(":")
        w = float(weight or 1.0)
        vec = engine.get_voice_style(name.strip()) * w
        style = vec if style is None else style + vec
        total += w
    return style / max(total, 1e-6)


def main() -> int:
    model, voices = Path(sys.argv[1]), Path(sys.argv[2])
    engine = Kokoro(str(model), str(voices))
    out = sys.stdout
    out.write(json.dumps({"ok": True, "ready": True}) + "\n")
    out.flush()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            op = req.get("op")
            if op == "ping":
                resp = {"ok": True}
            elif op == "voices":
                resp = {"ok": True, "voices": sorted(engine.get_voices())}
            elif op == "synthesize":
                text = str(req["text"])[:5000]
                samples, rate = engine.create(text, voice=_voice(engine, req["voice"]), speed=float(req.get("speed", 1.0)),
                                              lang=req.get("lang", "en-us"))  # fmt: skip
                target = Path(req["out"])
                target.parent.mkdir(parents=True, exist_ok=True)
                sf.write(str(target), np.asarray(samples, dtype=np.float32), rate, subtype="PCM_16")
                resp = {"ok": True, "duration": len(samples) / rate, "sample_rate": rate}
            else:
                resp = {"ok": False, "error": f"unknown op {op}"}
        except Exception as exc:  # report every failure to the caller instead of dying
            resp = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()[-600:]}
        out.write(json.dumps(resp) + "\n")
        out.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
