#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""sherpa-onnx streaming ASR (paraformer bilingual zh-en, int8) from the default mic.

Live streaming: prints `TEXT: <accumulated>` lines as you speak.
On release (host writes `f\n` to stdin): runs a high-accuracy OFFLINE paraformer
over the full recorded audio and prints `FINAL: <refined text>`, then exits.

Test mode: `python stream-recognize.py <stream-dir> <offline-dir> --file=<wav>`
feeds the wav instead of the mic and finalizes at EOF.

Boundary fixes: decode is drained before reading results; endpoint feeds tail
silence so the last word decodes; the offline refinement recovers the utterance
head/tail the streaming model drops.
"""
import sys
import threading
import time

# Force UTF-8 on stdout (Chinese Windows pipe default is GBK -> garbles).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

import numpy as np
import sounddevice as sd
import sherpa_onnx

STREAM_DIR = r"G:\dsh\_tools\asr\sherpa-onnx-streaming-paraformer-bilingual-zh-en"
OFFLINE_DIR = r"G:\dsh\_tools\asr\sherpa-onnx-whisper-base"
TAIL_SILENCE = 0.5  # seconds fed at endpoint so the last word is decoded


def drain(recognizer, stream):
    while recognizer.is_ready(stream):
        recognizer.decode_streams([stream])


def main():
    stream_dir = sys.argv[1] if len(sys.argv) > 1 else STREAM_DIR
    offline_dir = sys.argv[2] if len(sys.argv) > 2 else OFFLINE_DIR
    file_path = None
    if len(sys.argv) > 3 and sys.argv[3].startswith("--file="):
        file_path = sys.argv[3][7:]

    release = threading.Event()

    def listen_stdin():
        try:
            for line in sys.stdin:
                if line.strip() in ("f", "finalize"):
                    release.set()
                    break
        except Exception:
            pass

    threading.Thread(target=listen_stdin, daemon=True).start()

    stream_recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
        tokens=stream_dir + r"\tokens.txt",
        encoder=stream_dir + r"\encoder.int8.onnx",
        decoder=stream_dir + r"\decoder.int8.onnx",
        num_threads=2,
        sample_rate=16000,
        feature_dim=80,
        decoding_method="greedy_search",
        enable_endpoint_detection=True,
        rule1_min_trailing_silence=1.2,
        rule2_min_trailing_silence=0.8,
        rule3_min_utterance_length=2.0,
    )
    s = stream_recognizer.create_stream()
    committed = []
    recording = []  # full float32 audio for offline refinement
    print("READY", flush=True)

    def chunks():
        if file_path:
            import wave
            w = wave.open(file_path, "rb")
            sr = w.getframerate()
            all_samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
            for i in range(0, len(all_samples), 1600):
                yield all_samples[i:i + 1600]
            release.set()  # EOF -> finalize
            return
        with sd.InputStream(samplerate=16000, channels=1, dtype="int16", blocksize=1600) as inp:
            while True:
                chunk, _ = inp.read(1600)
                yield np.asarray(chunk, dtype=np.int16).reshape(-1).astype(np.float32) / 32768.0

    last_print = 0.0
    for samples in chunks():
        recording.append(samples)
        s.accept_waveform(16000, samples)
        drain(stream_recognizer, s)
        if stream_recognizer.is_endpoint(s):
            tail = np.zeros(int(TAIL_SILENCE * 16000), dtype=np.float32)
            s.accept_waveform(16000, tail)
            drain(stream_recognizer, s)
            txt = stream_recognizer.get_result(s).strip()
            if txt:
                committed.append(txt)
            stream_recognizer.reset(s)
        now = time.time()
        if now - last_print >= 0.25:
            last_print = now
            partial = stream_recognizer.get_result(s).strip()
            full = " ".join(committed + ([partial] if partial else []))
            sys.stdout.write("TEXT: " + full + "\n")
            sys.stdout.flush()
        if release.is_set():
            break

    # ---- offline refinement on the full recording (whisper-base: zh+en) ----
    try:
        offline = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=offline_dir + r"\base-encoder.int8.onnx",
            decoder=offline_dir + r"\base-decoder.int8.onnx",
            tokens=offline_dir + r"\base-tokens.txt",
            num_threads=2,
            decoding_method="greedy_search",
            language="",
            task="transcribe",
        )
        audio = np.concatenate(recording) if recording else np.zeros(0, dtype=np.float32)
        tail = np.zeros(int(0.66 * 16000), dtype=np.float32)
        audio = np.concatenate([audio, tail])
        o = offline.create_stream()
        o.accept_waveform(16000, audio)
        offline.decode_streams([o])
        refined = o.result.text.strip()
    except Exception as e:
        refined = ""
        sys.stderr.write("offline failed: %s\n" % e)
    if refined:
        sys.stdout.write("FINAL: " + refined + "\n")
    else:
        sys.stdout.write("FINAL: " + " ".join(committed) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
