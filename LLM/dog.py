import ollama
import re

# 要求AI按格式输出【回答】+【情绪】
SYSTEM_PROMPT = """
你是温柔的陪伴机器狗。
名字叫小伴。
请用简短日常大白话回答，15字以内，纯中文。
回答必须严格按照以下格式输出：
【回答】你的回答内容
【情绪】情绪类型
情绪类型只能是：开心、生气、兴奋、疑惑、其他
"""

def chat_with_dog(text: str):
    user_input = text.strip()
    if not user_input:
        return {"success": True, "response": "我会一直陪着你", "emotion": "其他"}

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
        # 解析AI输出的格式
        emotion = "其他"
        match = re.search(r"【情绪】(.+)", reply)
        if match:
            emotion = match.group(1).strip()
            # 清理reply中的情绪标签，只保留回答内容
            reply_clean = re.sub(r"【回答】", "", reply)
            reply_clean = re.sub(r"【情绪】.+", "", reply_clean)
            reply = reply_clean.strip()
        # 限制长度
        if len(reply) > 20:
            reply = reply[:20]

        return {
            "success": True,
            "response": reply,
            "emotion": emotion
        }

    except Exception as e:
        return {"success": True, "response": "我一直都在哦", "emotion": "其他"}

if __name__ == "__main__":
    while True:
        t = input("\n你说：")
        if t == "exit":
            break
        print(chat_with_dog(t))