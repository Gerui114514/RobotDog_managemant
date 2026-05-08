from .gsv_tts import TTS

tts_engine = TTS()

def tts_generate(text: str, emotion: str, speed: float = 1.0):
    if emotion == "生气":
        audio = tts_engine.infer(
            spk_audio_path="VoiceSystem/m/angry.MP3",
            prompt_audio_path="VoiceSystem/m/angry.MP3",
            prompt_audio_text="谁罕见啊？骂谁罕见呢？骂谁罕见？",
            text=text,
            gpt_model="VoiceSystem/model/lwj8-e15.ckpt",
            sovits_model="VoiceSystem/model/lwj8_e4_s136.pth",
            speed=speed,
        )
    elif emotion == "开心":
        audio = tts_engine.infer(
            spk_audio_path="VoiceSystem/m/happy.MP3",
            prompt_audio_path="VoiceSystem/m/happy.MP3",
            prompt_audio_text="春风正好，满心欢喜，岁岁无忧",
            text=text,
            gpt_model="VoiceSystem/model/lwj8-e15.ckpt",
            sovits_model="VoiceSystem/model/lwj8_e4_s136.pth",
            speed=speed,
        )
    elif emotion == "疑惑":
        audio = tts_engine.infer(
            spk_audio_path="VoiceSystem/m/confused.MP3",
            prompt_audio_path="VoiceSystem/m/confused.MP3",
            prompt_audio_text="世事难解，心底满是茫然困惑",
            text=text,
            gpt_model="VoiceSystem/model/lwj8-e15.ckpt",
            sovits_model="VoiceSystem/model/lwj8_e4_s136.pth",
            speed=speed,
        )
    elif emotion == "兴奋":
        audio = tts_engine.infer(
            spk_audio_path="VoiceSystem/m/excited.MP3",
            prompt_audio_path="VoiceSystem/m/excited.MP3",
            prompt_audio_text="满心雀跃，奔赴所有热烈与美好",
            text=text,
            gpt_model="VoiceSystem/model/lwj8-e15.ckpt",
            sovits_model="VoiceSystem/model/lwj8_e4_s136.pth",
            speed=speed,
        )
    else:
        audio = tts_engine.infer(
            spk_audio_path="VoiceSystem/m/neutral.MP3",
            prompt_audio_path="VoiceSystem/m/neutral.MP3",
            prompt_audio_text="风掠过山野，云漫过晴空，世间万物都在按自己的节奏缓缓生长。",
            text=text,
            gpt_model="VoiceSystem/model/lwj8-e15.ckpt",
            sovits_model="VoiceSystem/model/lwj8_e4_s136.pth",
            speed=speed,
        )
    return audio