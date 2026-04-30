# main.py
from flask import Flask, render_template_string, Response, request
import time
from tts import tts_generate
from VPlay import audio_get_wav

app = Flask(__name__)

# 全局状态
latest_audio = None
last_phone_heart = 0
need_play_flag = False

# 电脑控制端页面
CTRL_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>局域网TTS控制端</title>
    <style>
        body{text-align:center;margin-top:60px;}
        textarea{width:80%;height:130px;padding:10px;font-size:16px;}
        button{padding:10px 25px;margin:15px;font-size:16px;}
        .status{margin:15px;font-size:18px;}
        .online{color:green;}
        .offline{color:red;}
    </style>
</head>
<body>
    <h2>🖥️ 电脑控制端</h2>
    <div class="status" id="phoneStatus">🔴 手机未连接</div>
    <textarea id="ttsText" placeholder="输入要合成的文字..."></textarea>
    <br>
    <button onclick="sendTTS()">📤 生成并在手机播放</button>

    <script>
        setInterval(async ()=>{
            let res = await fetch("/check_phone");
            let ok = await res.text();
            let dom = document.getElementById("phoneStatus");
            if(ok === "online"){
                dom.className="status online";
                dom.innerText="🟢 手机已连接(同局域网)";
            }else{
                dom.className="status offline";
                dom.innerText="🔴 手机未连接";
            }
        }, 1200);

        async function sendTTS(){
            let text = document.getElementById("ttsText").value.trim();
            if(!text){alert("请输入文字！");return;}
            await fetch("/make_tts",{
                method:"POST",
                headers:{"Content-Type":"application/x-www-form-urlencoded"},
                body:"text="+encodeURIComponent(text)
            });
        }
    </script>
</body>
</html>
'''

# 手机播放端页面【已修复防重复播放】
PLAYER_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>手机播放端</title>
    <style>
        body{background:#111;color:#fff;text-align:center;padding-top:80px;}
    </style>
</head>
<body>
    <h3>🔈 手机局域网播放器</h3>
    <audio id="aud">

    <script>
        const aud = document.getElementById("aud");
        let isPlaying = false;

        // 手机心跳
        setInterval(()=>fetch("/phone_heart"), 800);

        // 播放结束/出错 解锁
        aud.onended = () => { isPlaying = false; };
        aud.onerror = () => { isPlaying = false; };

        // 轮询播放指令
        setInterval(async ()=>{
            if (isPlaying) return;

            let res = await fetch("/need_play");
            let cmd = await res.text();

            if (cmd === "play") {
                isPlaying = true;
                aud.pause();
                aud.currentTime = 0;
                aud.src = "/stream_wav?t=" + Date.now();
                aud.load();
                aud.play().catch(e => { isPlaying = false; });
            }
        }, 1000);
    </script>
</body>
</html>
'''

# 路由
@app.route("/")
def ctrl_page():
    return render_template_string(CTRL_HTML)

@app.route("/player")
def player_page():
    return render_template_string(PLAYER_HTML)

# 手机心跳上报
@app.route("/phone_heart")
def phone_heart():
    global last_phone_heart
    last_phone_heart = time.time()
    return "ok"

# 检测手机在线
@app.route("/check_phone")
def check_phone():
    if time.time() - last_phone_heart < 2.5:
        return "online"
    return "offline"

# 生成TTS
@app.route("/make_tts", methods=["POST"])
def make_tts():
    global latest_audio, need_play_flag
    text = request.form.get("text", "")
    audio_obj = tts_generate(text)
    latest_audio = audio_get_wav(audio_obj)
    need_play_flag = True
    return "ok"

# 获取播放指令（只返回一次）
@app.route("/need_play")
def need_play():
    global need_play_flag
    if need_play_flag:
        need_play_flag = False
        return "play"
    return ""

# 音频流
@app.route("/stream_wav")
def stream_wav():
    global latest_audio
    if not latest_audio:
        return "empty", 404
    return Response(latest_audio, mimetype="audio/wav")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)