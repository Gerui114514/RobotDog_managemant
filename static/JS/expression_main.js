const face = document.getElementById('face');
const faceContainer = document.getElementById('faceContainer');
const audioPlayer = document.getElementById('audioPlayer');
const unlockBtn = document.getElementById('unlockBtn');
const pupils = document.querySelectorAll('.pupil');
const hidden_1 = document.querySelectorAll('.hidden_1');
const hidden_2 = document.querySelectorAll('.hidden_2');
const eye = document.querySelectorAll('.eye')

let currentMood = 'neutral';
let resetTimer = null, idleTimer = null, blinkTimer = null;
const IDLE_TIME = 1200000;
let socket = null, audioUnlocked = false;

// 点击按钮：触发全屏 + 解锁声音
unlockBtn.addEventListener('click', async () => {
    // 浏览器原生全屏
    if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen().catch(e => { });
    } else if (document.documentElement.webkitRequestFullscreen) {
        document.documentElement.webkitRequestFullscreen();
    }
    audioUnlocked = true;
    unlockBtn.style.display = 'none';
    audioPlayer.play().catch(e => { });
});

function changeEyeColor(){
    let R = Math.floor(Math.random()*256);
    let G = Math.floor(Math.random()*256);
    let B = Math.floor(Math.random()*256);
    let EyeColor = `rgb(${R}, ${G}, ${B})`;
    eye.forEach(e => e.style.setProperty('--eye-color', EyeColor));
    eye[0].style.backgroundColor = EyeColor;
    eye[1].style.backgroundColor = EyeColor;
}

function getUrlParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

function getMoodFromId(idStr) {
    switch (idStr) {
        case '1': return 'angry';
        case '2': return 'happy';
        case '3': return 'excited';
        case '4': return 'confused';
        default: return 'neutral';
    }
}

// 只做整体等比缩小，绝不改变眼睛间距/尺寸
function applyFixedRotationAndScale() {
    const w = window.innerWidth, h = window.innerHeight;
    const ow = 640, oh = 360;
    // 整体容器等比缩放，内部元素尺寸、间距完全固定
    const scale = Math.min(h / ow, w / oh) * 0.92;
    faceContainer.style.transform = `translate(-50%, -50%) rotate(-90deg) scale(${scale})`;
}
// --- 表情控制 ---
function setMood(mood) {
    let ischangeColor = null;
    face.className = 'face';

    if (resetTimer) clearTimeout(resetTimer);
    currentMood = mood;
    
    if (mood !== 'neutral' && mood !== 'sleep') {
        face.classList.add(`mood-${mood}`);
        switch (mood) {
            case 'angry':
                hidden_1.forEach(h => h.style.opacity = '0');
                hidden_2.forEach(h => h.style.opacity = '0');
                break;
            case 'happy':
                hidden_1.forEach(h => h.style.opacity = '0');
                hidden_2.forEach(h => h.style.opacity = '0');
                pupils.forEach(p => p.style.opacity = '0');
                eye.forEach(e => e.style.backgroundColor = '#222');
                break;
            case 'excited':
                hidden_1.forEach(h => h.style.opacity = '0');
                hidden_2.forEach(h => h.style.opacity = '0');
                pupils.forEach(p => {
                    p.style.width = '120px';
                    p.style.height = '100px';
                    p.style.borderRadius = '50% 50% 0 0';
                });
                ischangeColor = setInterval(() => changeEyeColor(), 100);
                break;
            case 'confused':
                hidden_1.forEach(h => h.style.opacity = '0');
                hidden_2.forEach(h => h.style.opacity = '0');
                break;
        }
        resetTimer = setTimeout(() => {
            face.className = 'face';
            currentMood = 'neutral';
            startIdleTimer();
            scheduleBlink();
            eye.forEach(e => e.style.backgroundColor = '#00f0ff');
            pupils.forEach(p => {
                p.style.opacity = '0.9'
                p.style.width = 'var(--original-pupil-size)';
                p.style.height = 'var(--original-pupil-size)';
                p.style.borderRadius = '50%';
            });
            hidden_1.forEach(h => h.style.opacity = '1');
            hidden_2.forEach(h => h.style.opacity = '1');
            clearInterval(ischangeColor);
            ischangeColor = null;
        }, 1500);
    } else {
        if (mood !== 'neutral') face.classList.add(`mood-${mood}`);
        if (blinkTimer) clearTimeout(blinkTimer);
        if (mood === 'neutral' || mood === 'excited') scheduleBlink();
    }
}
// --- 待机管理 ---
function startIdleTimer() {
    if (idleTimer) clearTimeout(idleTimer);
    if (currentMood === 'neutral') {
        idleTimer = setTimeout(() => setMood('sleep'), IDLE_TIME);
    }
}
function resetIdle() {
    if (idleTimer) clearTimeout(idleTimer);
    if (currentMood === 'sleep') setMood('neutral');
    else startIdleTimer();
}
function scheduleBlink() {
    if (blinkTimer) clearTimeout(blinkTimer);
    const delay = Math.random() * 3000 + 2000;
    blinkTimer = setTimeout(() => {
        if (currentMood === 'neutral' || currentMood === 'excited') {
            document.querySelectorAll('.eye').forEach(eye => {
                eye.classList.add('blinking');
                eye.addEventListener('animationend', () => {
                    eye.classList.remove('blinking');
                    scheduleBlink();
                }, { once: true });
            });
        }
    }, delay);
}

function playAudio(base64Data) {
    if (!audioUnlocked) return;
    try {
        const binary = atob(base64Data);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const blob = new Blob([bytes], { type: 'audio/wav' });
        const url = URL.createObjectURL(blob);
        audioPlayer.src = url;
        audioPlayer.onended = () => URL.revokeObjectURL(url);
        audioPlayer.play();
    } catch (e) { }
}

function connectSocket() {
    socket = io(window.location.origin, { transports: ['websocket', 'polling'] });
    socket.on('connect', () => console.log("WS连接成功"));
    socket.on('message', (data) => {
        try {
            const d = JSON.parse(data);
            if (d.type === 'command') setMood(d.value);
        } catch (e) { }
    });
    socket.on('audio_data', (data) => {
        try {
            const d = JSON.parse(data);
            playAudio(d.data);
        } catch (e) { }
    });
}

window.addEventListener('load', () => {
    applyFixedRotationAndScale();
    setMood(getMoodFromId(getUrlParameter('id')));
    startIdleTimer();
    scheduleBlink();
    connectSocket();
});
window.addEventListener('resize', applyFixedRotationAndScale);