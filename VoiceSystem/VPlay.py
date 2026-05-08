# VPlay.py
import os

TEMP_FILE = "_tmp_tts_audio.wav"

def audio_get_wav(audio):
    audio.save(TEMP_FILE)
    with open(TEMP_FILE, "rb") as f:
        wav_bytes = f.read()
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)
    return wav_bytes