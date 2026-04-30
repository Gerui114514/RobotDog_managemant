import random, base64, logging, json, time, threading, os
import ActionSystem.ysc_lite3_control
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from datetime import datetime
from VoiceSystem import tts, VPlay
from LLM import dog

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
sio = SocketIO(app, cors_allowed_origin='*',
               engineio_logger=True,
               logger=True)

connected_clients = {}
last_heartbeat_time = {}

@sio.on('connect')
def handle_connect():
    sid = request.sid
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR')
    print(f'✅ 客户端连接: {sid}. IP: {client_ip}. 当前连接数: {len(connected_clients) + 1}')

    connected_clients[sid] = {
        'ip': client_ip,
        'connect_time': datetime.now(),
        'last_maessage_time': datetime.now()
    }
    last_heartbeat_time[sid] = time.time()

@sio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in connected_clients:
        connected_clients.pop(sid)
        print(f'❌ 客户端断开: {sid}. 当前连接数: {len(connected_clients)}')

ylc = ActionSystem.ysc_lite3_control.YscLite3Controller()

ylc.sit()
time.sleep(5)
ylc.stay()
time.sleep(5)

@sio.on('message')
def handle_message(data):
    sid = request.sid
    try:
        if isinstance(data, str):
            message_data = json.loads(data)
        else:
            message_data = data

        print(f'📨 收到消息 from {sid}: {message_data}')

        if sid in connected_clients:
            connected_clients[sid]['last_message_time'] = datetime.now()

        sio.emit('message', data)
        print(f'📤 转发消息给所有客户端: {message_data}')

        # ========================
        # 文字转语音部分
        # ========================

        if message_data['type'] == 'text':
            get_str = message_data['content']
            print(f"🗣️ 用户输入：{get_str}")

            # 调用LLM生成回应
            dog_response = dog.chat_with_dog(get_str)
            print(f"🐶 狗狗回应：{dog_response['response']},情绪为{dog_response['emotion']}")

            # 生成语音
            audio = tts.tts_generate(dog_response['response'], dog_response['emotion'])
            # 转WAV字节流
            wav_bytes = VPlay.audio_get_wav(audio)
            # 编码发送
            wav_base64 = base64.b64encode(wav_bytes).decode('utf-8')

            audio_message = {
                'type': 'audio',
                'data': wav_base64,
                'format': 'wav',
                'timestamp': time.time()
            }
            sio.emit('audio_data', json.dumps(audio_message))
            emotion = dog_response['emotion']  # 拿到AI情绪

            # 发给前端：切换表情标签

           # 中文情绪 → 前端mood值映射
            # ========================
            # 👇 👇 这是最终正确代码 👇 👇
            # ========================
            emotion = dog_response['emotion']

            # 中文情绪 → 前端需要的 ID 和 mood
            if emotion == "生气":
                face_id = "1"
                mood_val = "angry"
            elif emotion == "开心":
                face_id = "2"
                mood_val = "happy"
            elif emotion == "兴奋":
                face_id = "3"
                mood_val = "excited"
            elif emotion == "疑惑":
                face_id = "4"
                mood_val = "confused"
            else:
                face_id = "5"
                mood_val = "neutral"

            # 完全模拟前端 sendById 发送的格式
            emotion_msg = {
                "type": "command",
                "command": "SET_MOOD",
                "value": mood_val,
                "id": face_id
            }

            # 发送（和前端按钮发送的一模一样）
            sio.emit('message', json.dumps(emotion_msg))
            print(f'🔊 音频已发送')




        # 机器狗动作
        if 'id' in message_data:
            case = message_data['id']
            if case == '1':
                print('我愤怒了')
                random_num = random.randint(1, 3)
                if random_num == 1:
                    ylc.angry_fierce_shake()
                elif random_num == 2:
                    ylc.angry_intense_stomp()
                elif random_num == 3:
                    ylc.angry_defensive_threat()
            elif case == '2':
                print('我好开心')
                random_num = random.randint(1, 3)
                if random_num == 1:
                    ylc.happy_gentle_nod()
                elif random_num == 2:
                    ylc.happy_smooth_sway()
                elif random_num == 3:
                    ylc.happy_cheerful_step()
            elif case == '3':
                print('我好兴奋')
                random_num = random.randint(1, 2)
                if random_num == 1:
                    ylc.excited_joyful_spin()
                elif random_num == 2:
                    ylc.excited_bouncing_celebration()
            elif case == '4':
                print('我有点疑惑')
                random_num = random.randint(1, 3)
                if random_num == 1:
                    ylc.confused_curious_tilt()
                elif random_num == 2:
                    ylc.confused_puzzled_search()
                elif random_num == 3:
                    ylc.confused_hesitant_backtrack()
            ylc.stay()

    except Exception as e:
        print(f'❌ 消息处理错误: {e}')


@sio.on('command')
def handle_command(data):
    sid = request.sid
    try:
        if isinstance(data, str):
            message_data = json.loads(data)
        else:
            message_data = data
        print(f'⚙️ 收到命令 from {sid}: {message_data}')
        sio.emit('command', data)
    except Exception as e:
        print(f'❌ 命令错误: {e}')


@app.route('/')
def index():
    return """
    <h1>✅ Flask WebSocket 服务器运行中！</h1>
    <ul>
        <li><a href="/remote_controller_ws.html">遥控器页面</a></li>
        <li><a href="/expression_main_ws.html">表情页面</a></li>
    </ul>
    """

@app.route('/remote_controller_ws.html')
def serve_remote_controller():
    return send_from_directory('ExpressionSystem', 'remote_controller_ws.html')

@app.route('/expression_main_ws.html')
def serve_expression_main():
    return send_from_directory('ExpressionSystem', 'expression_main_ws.html')


def check_client_heartbeat():
    while True:
        current_time = time.time()
        disconnected_sids = []
        for sid, last_time in list(last_heartbeat_time.items()):
            if current_time - last_time > 30:
                print(f'⏰ 客户端 {sid} 心跳超时')
                disconnected_sids.append(sid)
        for sid in disconnected_sids:
            last_heartbeat_time.pop(sid, None)
        time.sleep(10)


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🔧 Flask WebSocket 中转服务器 启动中...")
    print("🌐 服务器地址: http://localhost:5000")
    print("🌐 http://localhost:5000/remote_controller_ws.html")
    print("🌐 http://localhost:5000/expression_main_ws.html")
    print("=" * 50 + "\n")

    heartbeat_thread = threading.Thread(target=check_client_heartbeat, daemon=True)
    heartbeat_thread.start()

    try:
        sio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    except OSError as e:
        if e.errno == 10048:
            print("❌ 端口 5000 已被占用")
        else:
            print(f"❌ 启动错误: {e}")