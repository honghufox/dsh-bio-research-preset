#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""sherpa-onnx streaming ASR (paraformer bilingual zh-en, int8) from the default mic.
Streams partial results as `TEXT: <accumulated text>` lines; runs until killed.

IMPORTANT: the recognizer must be driven by the is_ready()/decode_streams()
loop — accept_waveform alone never runs the model (this was the "no text"
bug). Tail silence + input_finished flush the final result.
"""
import sys
import time

import numpy as np
import sounddevice as sd
import sherpa_onnx


def main():
    model_dir = sys.argv[1] if len(sys.argv) > 1 else r"G:\dsh\_tools\asr\sherpa-onnx-streaming-paraformer-bilingual-zh-en"
    recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
        tokens=model_dir + r"\tokens.txt",
        encoder=model_dir + r"\encoder.int8.onnx",
        decoder=model_dir + r"\decoder.int8.onnx",
        num_threads=2,
        sample_rate=16000,
        feature_dim=80,
        decoding_method="greedy_search",
        enable_endpoint_detection=True,
        rule1_min_trailing_silence=1.5,
        rule2_min_trailing_silence=0.8,
        rule3_min_utterance_length=2.0,
    )
    s = recognizer.create_stream()
    committed = []
    print("READY", flush=True)
    with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=1600) as inp:
        last_print = 0.0
        while True:
            chunk, _ = inp.read(1600)
            samples = np.asarray(chunk, dtype=np.int16).reshape(-1)
            s.accept_waveform(16000, samples)
            # drive the model: decode as much as the recognizer is ready for
            while recognizer.is_ready(s):
                recognizer.decode_streams([s])
            if recognizer.is_endpoint(s):
                txt = recognizer.get_result(s).strip()
                if txt:
                    committed.append(txt)
                recognizer.reset(s)
            now = time.time()
            if now - last_print >= 0.25:
                last_print = now
                partial = recognizer.get_result(s).strip()
                full = " ".join(committed + ([partial] if partial else []))
                sys.stdout.write("TEXT: " + full + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
