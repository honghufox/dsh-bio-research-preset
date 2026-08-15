#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SenseVoice offline refinement (standalone) — test mode for switching the
voice-input offline pass from whisper-small to sherpa-onnx SenseVoice.

Usage: python sense_refine.py <model_dir> <wav>

Prints the cleaned transcription. SenseVoice emits control tokens like
<|zh|><|NEUTRAL|><|Speech|><|woitn|> which are stripped here.
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import re
import numpy as np
import sherpa_onnx
import wave

MODEL_DIR = r"G:\dsh\_tools\asr\sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"


def clean(text):
    if not text:
        return ""
    # strip SenseVoice control tokens and collapse whitespace
    text = re.sub(r"<\|[^|]*\|>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def main():
    model_dir = sys.argv[1] if len(sys.argv) > 1 else MODEL_DIR
    wav_path = sys.argv[2] if len(sys.argv) > 2 else None

    rec = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=model_dir + r"\model.onnx",
        tokens=model_dir + r"\tokens.txt",
        num_threads=2,
        language="zh",
        use_itn=True,
    )

    if wav_path is None:
        print("READY", flush=True)
        return

    with wave.open(wav_path, "rb") as w:
        sr = w.getframerate()
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    stream = rec.create_stream()
    stream.accept_waveform(sr, samples)
    rec.decode_streams([stream])
    print("SENSE: " + clean(stream.result.text), flush=True)


if __name__ == "__main__":
    main()
