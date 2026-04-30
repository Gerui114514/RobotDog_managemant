# import soundfile as sf
# import numpy as np
# from gsv_tts import TTS

# tts = TTS(use_bert=True)
# # tts = TTS(use_flash_attn=True) 如果安装了Flash Attention，建议这样设置

# # 将 GPT 模型权重从指定路径加载到内存中，这里加载默认模型。
# tts.load_gpt_model()

# # 将 SoVITS 模型权重从指定路径加载到内存中，这里加载默认模型。
# tts.load_sovits_model()

# # 预加载与缓存资源，可显著减少首次推理的延迟
# # tts.init_language_module("ja")
# # tts.cache_spk_audio("examples\laffey.mp3")
# # tts.cache_prompt_audio(
# #     prompt_audio_paths="examples\AnAn.ogg",
# #     prompt_audio_texts="ちが……ちがう。レイア、貴様は間違っている。",
# # )

# # infer 是最简单、最原始的推理方式，只适用于短文本推理，一般建议用 infer_batched 替代 infer 推理。
# audio = tts.infer(
#     spk_audio_path="m/m2.MP3", # 音色参考音频
#     prompt_audio_path="m/m2.MP3", # 风格参考音频
#     prompt_audio_text="谁罕见啊？骂谁罕见呢？骂谁罕见？", # 风格参考音频对应的文本
#     text="谁罕见啊？骂谁罕见呢？骂谁罕见？", # 目标生成文本
#     gpt_model = "model/qihai-e15.ckpt", # 用于推理的GPT模型路径，默认用第一个加载的GPT模型推理
#     sovits_model = "model/qihai_e100_s16300.pth", # 用于推理的SoVITS模型路径，默认用第一个加载的SoVITS模型推理
# )
# # 保存文件（想改路径直接改这里）
# audio.play()
# tts.audio_queue.wait()
# # tts.audio_queue.stop() 停止播放
# tts.py
# tts.py
# tts.py
from .gsv_tts import TTS

tts_engine = TTS()

def tts_generate(text: str, emotion: str):
    #生气
    if emotion == "生气":
        audio = tts_engine.infer(
            spk_audio_path="VoiceSystem/m/angry.MP3",
            prompt_audio_path="VoiceSystem/m/angry.MP3",
            prompt_audio_text="谁罕见啊？骂谁罕见呢？骂谁罕见？",
            text=text,
            gpt_model="VoiceSystem/model/lwj8-e15.ckpt",
            sovits_model="VoiceSystem/model/lwj8_e4_s136.pth",
        )
    # 开心
    elif emotion == "开心":
        audio = tts_engine.infer(
            spk_audio_path="VoiceSystem/m/happy.MP3",
            prompt_audio_path="VoiceSystem/m/happy.MP3",
            prompt_audio_text="春风正好，满心欢喜，岁岁无忧",
            text=text,
            gpt_model="VoiceSystem/model/lwj8-e15.ckpt",
            sovits_model="VoiceSystem/model/lwj8_e4_s136.pth",
        )
        # 疑惑
    elif emotion == "疑惑":
        audio = tts_engine.infer(
            spk_audio_path="VoiceSystem/m/confused.MP3",
            prompt_audio_path="VoiceSystem/m/confused.MP3",
            prompt_audio_text="世事难解，心底满是茫然困惑",
            text=text,
            gpt_model="VoiceSystem/model/lwj8-e15.ckpt",
            sovits_model="VoiceSystem/model/lwj8_e4_s136.pth",
        )
        # 兴奋
    elif emotion == "兴奋":
        audio = tts_engine.infer(
            spk_audio_path="VoiceSystem/m/excited.MP3",
            prompt_audio_path="VoiceSystem/m/excited.MP3",
            prompt_audio_text="满心雀跃，奔赴所有热烈与美好",
            text=text,
            gpt_model="VoiceSystem/model/lwj8-e15.ckpt",
            sovits_model="VoiceSystem/model/lwj8_e4_s136.pth",
        )
        # 其他
    else:
        audio = tts_engine.infer(
            spk_audio_path="VoiceSystem/m/neutral.MP3",
            prompt_audio_path="VoiceSystem/m/neutral.MP3",
            prompt_audio_text="风掠过山野，云漫过晴空，世间万物都在按自己的节奏缓缓生长。",
            text=text,
            gpt_model="VoiceSystem/model/lwj8-e15.ckpt",
            sovits_model="VoiceSystem/model/lwj8_e4_s136.pth",
        )
    return audio