import ollama
import re

# 只让AI说人话，不需要任何标签
SYSTEM_PROMPT = """
你是温柔的陪伴机器狗。
名字叫小伴
只用简短日常大白话，15字以内，纯中文。
不要任何符号、括号、标签、多余内容。
"""

# 关键词自动判断情绪
def auto_get_emotion(text: str):
    happy_words = ["开心", "快乐", "喜欢", "不错", "挺好", "幸福"]
    excited_words = ["厉害", "太棒", "好想", "期待", "超爱","棒"]
    angry_words = ["讨厌", "很烦", "气死", "不要", "不行"]
    doubt_words = ["为什么", "啥", "怎么", "？", "吗"]

    txt = text.lower()
    if any(w in txt for w in happy_words):
        return "开心"
    elif any(w in txt for w in doubt_words):
        return "疑惑"
    elif any(w in txt for w in excited_words):
        return "兴奋"
    elif any(w in txt for w in angry_words):
        return "生气"
    return "其它"

def chat_with_dog(text: str):
    user_input = text.strip()
    if not user_input:
        return {"success": True, "response": "我会一直陪着你", "emotion": "其它"}

    try:
        res = ollama.chat(
            model="qwen2:1.5b-instruct-q4_K_M",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}
            ],
            options={
                "temperature": 0.2,
                "max_tokens": 25
            }
        )

        reply = res["message"]["content"].strip()
        # 限制长度
        if len(reply) > 20:
            reply = reply[:20]
        # 代码自动判情绪
        emotion = auto_get_emotion(reply)

        return {
            "success": True,
            "response": reply,
            "emotion": emotion
        }

    except Exception as e:
        return {"success": True, "response": "我一直都在哦", "emotion": "其它"}

if __name__ == "__main__":
    while True:
        t = input("\n你说：")
        if t == "exit":
            break
        print(chat_with_dog(t))