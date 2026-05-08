const statusElement = document.getElementById('status');
const textInput = document.getElementById('textInput');
const ttsInput = document.getElementById('ttsInput');
let socket = null;

function connect() {
    socket = io('http://localhost:5000', {
        transports: ['websocket'],
        autoConnect: true,
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000
    });

    socket.on('connect', () => {
        console.log("✅ Socket.IO Connected");
        statusElement.textContent = "状态: 已连接";
    });

    socket.on('connect_error', (error) => {
        console.error("❌ Socket.IO 连接错误:", error);
        statusElement.textContent = "状态: 连接错误";
    });

    socket.on('disconnect', () => {
        console.log("❌ Socket.IO Disconnected");
        statusElement.textContent = "状态: 连接断开，正在重连...";
    });

    socket.on('message', (data) => {
        try {
            const message_data = JSON.parse(data);
            console.log("📨 收到消息:", message_data);
            if (message_data.type === 'pong') {
                statusElement.textContent = "状态: 表情页面在线";
            }
        } catch (e) {
            console.log("收到非JSON消息:", data);
        }
    });

    socket.on('command', (data) => {
        try {
            const message_data = JSON.parse(data);
            console.log("⚙️ 收到 command:", message_data);
        } catch (e) {
            console.log("收到非JSON command:", data);
        }
    });
}

function send(mood) {
    if (socket && socket.connected) {
        const message = { type: 'command', command: 'SET_MOOD', value: mood };
        socket.emit('message', JSON.stringify(message));
        console.log("📤 发送指令:", mood);
        statusElement.textContent = `发送: ${mood}`;
    } else {
        statusElement.textContent = "状态: 未连接";
    }
}

// 新增函数：发送数字ID对应的指令
function sendById(id) {
    if (socket && socket.connected) {
        let mood;
        switch(id) {
            case '1': mood = 'angry'; break;
            case '2': mood = 'happy'; break;
            case '3': mood = 'excited'; break;
            case '4': mood = 'confused'; break;
            default: mood = 'neutral'; break;
        }

        const message = {
            type: 'command',
            command: 'SET_MOOD',
            value: mood,
            id: id // 添加ID标识
        };

        socket.emit('message', JSON.stringify(message));
        console.log("📤 发送ID指令:", id, "->", mood);
        statusElement.textContent = `发送ID: ${id} (${mood})`;
    } else {
        statusElement.textContent = "状态: 未连接";
    }
}

// 发送文本消息
function sendText() {
    const text = textInput.value.trim();
    if (text && socket && socket.connected) {
        const message = { type: 'text', content: text, timestamp: Date.now() };
        socket.emit('message', JSON.stringify(message));
        console.log("📤 发送文本:", text);
        statusElement.textContent = `发送文本: ${text}`;
        textInput.value = ''; // 清空输入框
    } else {
        statusElement.textContent = "状态: 未连接或文本为空";
    }
}

// 回车发送文本
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendText();
    }
}

// 回车发送TTS
function handleTtsKeyPress(event) {
    if (event.key === 'Enter') {
        sendTtsOnly();
    }
}

// 发送TTS Only消息
function sendTtsOnly() {
    const text = ttsInput.value.trim();
    const mood = document.getElementById('ttsMood').value;
    if (text && socket && socket.connected) {
        const message = { type: 'tts_only', content: text, mood: mood, timestamp: Date.now() };
        socket.emit('message', JSON.stringify(message));
        console.log("📤 发送TTS:", text, "情绪:", mood);
        statusElement.textContent = `发送TTS: ${text} (${mood})`;
        ttsInput.value = '';
    } else {
        statusElement.textContent = "状态: 未连接或文本为空";
    }
}

window.onload = connect;