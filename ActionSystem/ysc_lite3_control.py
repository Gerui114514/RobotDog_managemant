import socket, struct, time, threading, math, random
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from collections import deque


class TwistSpeedLevel(Enum):
    VERY_SLOW = 1
    SLOW = 2
    MODERATE = 3
    FAST = 4
    VERY_FAST = 5


class TwistAmplitudeLevel(Enum):
    MINIMAL = 1
    SMALL = 2
    MEDIUM = 3
    LARGE = 4
    EXTREME = 5


class EmotionClassification(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    CONFUSED = "confused"
    ANGRY = "angry"
    ANXIOUS = "anxious"
    SARCASTIC = "sarcastic"


@dataclass
class TwistMotionData:
    speed_hz: float
    amplitude_deg: float
    duration_s: float
    rhythm_regularity: float
    direction_changes: int

    def __post_init__(self):
        self.speed_hz = max(0.0, self.speed_hz)
        self.amplitude_deg = max(0.0, min(self.amplitude_deg, 180.0))
        self.rhythm_regularity = max(0.0, min(self.rhythm_regularity, 1.0))


class YscLite3Controller:
    def __init__(self, ip='192.168.1.120', port=43893, debug=False):
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._send_addr = (ip, int(port))
        self.debug = debug

        self._current_emotion = 'normal_happy'
        self._emotion_intensity = {
            'excited': 1.0,
            'normal_happy': 0.6,
            'confused': 0.4,
            'angry': 0.8
        }

        self._twist_lock = threading.Lock()
        self._twist_active = False
        self._action_interrupted = False
        self._current_sequence_index = 0
        self._twist_config = {
            'excited': {
                'frequency': 0.08,
                'duration': 2.55,
                'amplitude': 1.0,
                'pattern': 'fast_vibrate'
            },
            'normal_happy': {
                'frequency': 0.25,
                'duration': 2.125,
                'amplitude': 0.7,
                'pattern': 'smooth_sway'
            },
            'confused': {
                'frequency': 0.5,
                'duration': 2.975,
                'amplitude': 0.5,
                'pattern': 'hesitant_search'
            },
            'angry': {
                'frequency': 0.1,
                'duration': 1.7,
                'amplitude': 0.9,
                'pattern': 'aggressive_shake'
            }
        }

        self._last_performed_sequence: Dict[str, str] = {}

        self._init_heartbeat()

        self._init_emotion_analyzer()

        self._init_variation_manager()

        self._init_variation_injector()

    def _init_heartbeat(self):
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._send_heartbeat)
        self._heartbeat_thread.daemon = True
        self._heartbeat_thread.start()

    def _send_heartbeat(self):
        while self._heartbeat_running:
            try:
                data = struct.pack("<3i", 0x21040001, 0, 0)
                self._udp_socket.sendto(data, self._send_addr)
            except Exception:
                pass
            time.sleep(0.5)

    def _init_emotion_analyzer(self):
        self._speed_thresholds = {
            (0.0, 0.3): TwistSpeedLevel.VERY_SLOW,
            (0.3, 0.8): TwistSpeedLevel.SLOW,
            (0.8, 2.0): TwistSpeedLevel.MODERATE,
            (2.0, 4.0): TwistSpeedLevel.FAST,
            (4.0, float('inf')): TwistSpeedLevel.VERY_FAST
        }

        self._amplitude_thresholds = {
            (0.0, 10.0): TwistAmplitudeLevel.MINIMAL,
            (10.0, 30.0): TwistAmplitudeLevel.SMALL,
            (30.0, 60.0): TwistAmplitudeLevel.MEDIUM,
            (60.0, 120.0): TwistAmplitudeLevel.LARGE,
            (120.0, float('inf')): TwistAmplitudeLevel.EXTREME
        }

        self._emotion_rules = {
            (TwistSpeedLevel.FAST, TwistAmplitudeLevel.EXTREME): EmotionClassification.EXCITED,
            (TwistSpeedLevel.VERY_FAST, TwistAmplitudeLevel.LARGE): EmotionClassification.EXCITED,
            (TwistSpeedLevel.VERY_FAST, TwistAmplitudeLevel.EXTREME): EmotionClassification.EXCITED,
            (TwistSpeedLevel.MODERATE, TwistAmplitudeLevel.MEDIUM): EmotionClassification.HAPPY,
            (TwistSpeedLevel.SLOW, TwistAmplitudeLevel.SMALL): EmotionClassification.HAPPY,
            (TwistSpeedLevel.SLOW, TwistAmplitudeLevel.MEDIUM): EmotionClassification.CONFUSED,
            (TwistSpeedLevel.VERY_SLOW, TwistAmplitudeLevel.MEDIUM): EmotionClassification.CONFUSED,
            (TwistSpeedLevel.VERY_SLOW, TwistAmplitudeLevel.LARGE): EmotionClassification.CONFUSED,
            (TwistSpeedLevel.FAST, TwistAmplitudeLevel.LARGE): EmotionClassification.ANGRY,
            (TwistSpeedLevel.VERY_FAST, TwistAmplitudeLevel.MEDIUM): EmotionClassification.ANGRY,
            (TwistSpeedLevel.FAST, TwistAmplitudeLevel.MEDIUM): EmotionClassification.ANXIOUS,
            (TwistSpeedLevel.MODERATE, TwistAmplitudeLevel.LARGE): EmotionClassification.ANXIOUS,
        }

        self._validation_samples = []
        self._validation_threshold = 0.7

    def _init_variation_manager(self):
        self._variation_history: deque = deque(maxlen=5)
        self._variation_sets: Dict[str, List[dict]] = {}
        self._emotion_variation_history: Dict[str, deque] = {}

    def _init_variation_injector(self):
        self._variations = {
            'excited': [
                {'vibration_intensity': (0.08, 0.12), 'pause_duration': (0.08, 0.12), 'sequence_order': [0, 1, 2]},
                {'vibration_intensity': (0.06, 0.10), 'pause_duration': (0.10, 0.15), 'sequence_order': [1, 0, 2]},
                {'vibration_intensity': (0.10, 0.15), 'pause_duration': (0.06, 0.10), 'sequence_order': [2, 1, 0]},
            ],
            'normal_happy': [
                {'vibration_intensity': (0.25, 0.30), 'pause_duration': (0.35, 0.45), 'sequence_order': [0, 1, 2]},
                {'vibration_intensity': (0.20, 0.25), 'pause_duration': (0.40, 0.50), 'sequence_order': [1, 2, 0]},
                {'vibration_intensity': (0.30, 0.35), 'pause_duration': (0.30, 0.40), 'sequence_order': [2, 0, 1]},
            ],
            'confused': [
                {'vibration_intensity': (0.50, 0.60), 'pause_duration': (0.60, 0.80), 'sequence_order': [0, 1, 2]},
                {'vibration_intensity': (0.45, 0.55), 'pause_duration': (0.70, 0.90), 'sequence_order': [1, 0, 2]},
                {'vibration_intensity': (0.55, 0.65), 'pause_duration': (0.50, 0.70), 'sequence_order': [2, 0, 1]},
            ],
            'angry': [
                {'vibration_intensity': (0.06, 0.08), 'pause_duration': (0.05, 0.07), 'sequence_order': [0, 1, 2]},
                {'vibration_intensity': (0.07, 0.09), 'pause_duration': (0.06, 0.08), 'sequence_order': [1, 2, 0]},
                {'vibration_intensity': (0.05, 0.07), 'pause_duration': (0.07, 0.09), 'sequence_order': [2, 0, 1]},
            ]
        }
        self._injector_history: deque = deque(maxlen=10)

    def set_emotion(self, emotion):
        valid_emotions = ['excited', 'normal_happy', 'confused', 'angry']
        if emotion in valid_emotions:
            self._current_emotion = emotion
            if self.debug:
                print(f"Emotion set to: {emotion}")
        else:
            if self.debug:
                print(f"Invalid emotion: {emotion}. Valid options: {valid_emotions}")

    def get_emotion(self):
        return self._current_emotion

    def get_intensity(self):
        return self._emotion_intensity.get(self._current_emotion, 0.5)

    def set_twist_config(self, emotion, frequency=None, duration=None, amplitude=None, pattern=None):
        if emotion in self._twist_config:
            if frequency is not None:
                self._twist_config[emotion]['frequency'] = frequency
            if duration is not None:
                self._twist_config[emotion]['duration'] = duration
            if amplitude is not None:
                self._twist_config[emotion]['amplitude'] = amplitude
            if pattern is not None:
                self._twist_config[emotion]['pattern'] = pattern
            if self.debug:
                print(f"更新 {emotion} 扭动配置: {self._twist_config[emotion]}")

    def get_twist_config(self, emotion=None):
        if emotion:
            return self._twist_config.get(emotion, None)
        return self._twist_config

    def calculate_scaled_parameters(self, emotion=None):
        target_emotion = emotion if emotion else self._current_emotion
        config = self._twist_config.get(target_emotion, self._twist_config['normal_happy'])
        intensity = self.get_intensity()

        scaled = {
            'frequency': config['frequency'] * (1.5 - intensity * 0.5),
            'duration': config['duration'] * intensity,
            'amplitude': config['amplitude'] * intensity,
            'pattern': config['pattern']
        }
        return scaled

    def emotion_twist(self, emotion=None, custom_config=None):
        with self._twist_lock:
            if self._twist_active:
                if self.debug:
                    print("扭动动画正在执行，跳过")
                return
            self._twist_active = True

        try:
            target_emotion = emotion if emotion else self._current_emotion
            self.set_emotion(target_emotion)
            self.stay()

            config = custom_config if custom_config else self.calculate_scaled_parameters(target_emotion)

            if self.debug:
                print(f"执行 {target_emotion} 情感扭动: {config}")

            pattern = config['pattern']

            if pattern == 'fast_vibrate':
                self._twist_fast_vibrate(config)
            elif pattern == 'smooth_sway':
                self._twist_smooth_sway(config)
            elif pattern == 'hesitant_search':
                self._twist_hesitant_search(config)
            elif pattern == 'aggressive_shake':
                self._twist_aggressive_shake(config)
            else:
                self._twist_smooth_sway(config)

        finally:
            with self._twist_lock:
                self._twist_active = False

    def _twist_fast_vibrate(self, config):
        duration = config['duration']
        freq = config['frequency']
        amp = config['amplitude']

        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            if amp > 0.7:
                self.send_data(0x21010204, 0, 0)
                time.sleep(freq * 0.6)
            self.DZ_1(0.1 * amp)
            time.sleep(freq * 0.4)
            self.send_data(0x21010204, 0, 0)
            time.sleep(freq * 0.6)
            self.DZ_2(0.1 * amp)
            time.sleep(freq * 0.4)

    def _twist_smooth_sway(self, config):
        duration = config['duration']
        freq = config['frequency']
        amp = config['amplitude']

        cycles = int(duration / (freq * 4))
        for _ in range(cycles):
            if self._check_interruption():
                return
            self.send_data(0x21010204, 0, 0)
            time.sleep(freq)
            self.DZ_dzh(freq * 0.5)
            time.sleep(freq * 0.5)
            if amp > 0.5:
                self.DZ_1(0.2 * amp)
                time.sleep(freq * 0.5)
                self.DZ_2(0.2 * amp)
                time.sleep(freq * 0.5)

    def _twist_hesitant_search(self, config):
        duration = config['duration']
        freq = config['frequency']
        amp = config['amplitude']

        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010204, 0, 0)
            time.sleep(freq * 1.2)
            self.DZ_1(0.3 * amp)
            time.sleep(freq * 0.8)
            self.send_data(0x21010204, 0, 0)
            time.sleep(freq * 1.2)
            self.DZ_2(0.3 * amp)
            time.sleep(freq * 0.8)
            time.sleep(freq * 0.5)

    def _twist_aggressive_shake(self, config):
        duration = config['duration']
        freq = config['frequency']
        amp = config['amplitude']

        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.DZ_1(0.08 * amp)
            time.sleep(freq * 0.3)
            self.DZ_2(0.08 * amp)
            time.sleep(freq * 0.3)
            self.send_data(0x21010204, 0, 0)
            time.sleep(freq * 0.3)
            self.DZ_4(0.1 * amp)
            time.sleep(freq * 0.3)

    def send_data(self, code, value, type):
        data = struct.pack("<3i", code, value, type)
        try:
            if self.debug:
                print(f"send_data -> addr={self._send_addr}, code={hex(code)}, value={value}, type={type}, bytes={data}")
            self._udp_socket.sendto(data, self._send_addr)
        except Exception:
            if self.debug:
                import traceback
                traceback.print_exc()

    def stand_up(self):
        self.send_data(0x21010202, 0, 0)
        self.send_data(0x21010D06, 0, 0)
        time.sleep(1.7)

    def sit(self):
        self.send_data(0x21010202, 0, 0)
        time.sleep(1.7)

    def move_x(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010130, 1000, 0)
            time.sleep(0.05)

    def forward(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010130, 13000, 0)
            time.sleep(0.05)

    def move_y(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010131, 1000, 0)
            time.sleep(0.05)

    def move_left(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010131, -26000, 0)
            time.sleep(0.05)

    def move_right(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010131, 26000, 0)
            time.sleep(0.05)

    def turn_l(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010135, -10000, 0)
            time.sleep(0.05)

    def turn_r(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010135, 10000, 0)
            time.sleep(0.05)

    def forward_left(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010130, 11000, 0)
            self.send_data(0x21010135, -15000, 0)
            self.send_data(0x21010131, -16000, 0)
            time.sleep(0.05)

    def forward_move_right(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010130, 9100, 0)
            self.send_data(0x21010131, 46000, 0)
            time.sleep(0.05)

    def stay(self):
        self.send_data(0x21010D05, 0, 0)

    def move(self):
        self.send_data(0x21010D06, 0, 0)

    def low_speed(self):
        self.send_data(0x21010300, 0, 0)

    def medium_speed(self):
        self.send_data(0x21010307, 0, 0)

    def high_speed(self):
        self.send_data(0x21010303, 0, 0)

    def normal_creep(self):
        self.send_data(0x21010406, 0, 0)

    def climb_1(self):
        self.send_data(0x21010402, 0, 0)

    def climb_2(self):
        self.send_data(0x21010401, 0, 0)

    def obstacle_high_step(self):
        self.send_data(0x21010301, 0, 0)

    def going_on(self):
        self.send_data(0x21010C06, -1, 0)

    def going_off(self):
        self.send_data(0x21010C06, 2, 0)

    def automatic_mode(self):
        self.send_data(0x21010C03, 0, 0)

    def manual_mode(self, duration):
        self.send_data(0x21010C02, 0, 0)

    def DZ_dzh(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010507, 0, 0)
            time.sleep(0.5)

    def DZ_nst(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010204, 0, 0)
            time.sleep(0.5)

    def DZ_tkb(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x2101030C, 0, 0)
            time.sleep(0.5)
        while time.time() - start_time > 6:
            if self._check_interruption():
                return
            self.send_data(0x21010D05, 0, 0)
            time.sleep(0.5)

    def DZ_1(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010D05, 0, 0)
            self.send_data(0x21010131, 30000, 0)
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010D05, 0, 0)
            time.sleep(0.1)

    def DZ_2(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010D05, 0, 0)
            self.send_data(0x21010131, -30000, 0)
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010D05, 0, 0)
            time.sleep(0.1)

    def DZ_3(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010D05, 0, 0)
            self.send_data(0x21010130, -30000, 0)
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010D05, 0, 0)
            time.sleep(0.1)

    def DZ_4(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010D05, 0, 0)
            self.send_data(0x21010130, 30000, 0)
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.send_data(0x21010D05, 0, 0)
            time.sleep(0.1)

    def act_cute(self, duration):
        self.stay()
        intensity = self.get_intensity()

        if self._current_emotion == 'excited':
            start_time = time.time()
            while time.time() - start_time < duration:
                if self._check_interruption():
                    return
                self.DZ_nst(0.255)
                self.DZ_dzh(0.17)
                time.sleep(0.085)
        elif self._current_emotion == 'normal_happy':
            start_time = time.time()
            while time.time() - start_time < duration:
                if self._check_interruption():
                    return
                self.DZ_nst(0.425)
                time.sleep(0.17)
        elif self._current_emotion == 'confused':
            start_time = time.time()
            while time.time() - start_time < duration:
                if self._check_interruption():
                    return
                self.DZ_3(0.17)
                self.DZ_4(0.17)
                time.sleep(0.255)
        elif self._current_emotion == 'angry':
            start_time = time.time()
            while time.time() - start_time < duration:
                if self._check_interruption():
                    return
                self.DZ_1(0.1275)
                self.DZ_2(0.1275)
                time.sleep(0.085)

    def twist_body(self, duration):
        self.stay()
        intensity = self.get_intensity()
        base_duration = duration * intensity

        if self._current_emotion == 'excited':
            start_time = time.time()
            while time.time() - start_time < base_duration:
                if self._check_interruption():
                    return
                self.send_data(0x21010204, 0, 0)
                time.sleep(0.1275)
        elif self._current_emotion == 'normal_happy':
            self.DZ_nst(base_duration)
        elif self._current_emotion == 'confused':
            start_time = time.time()
            while time.time() - start_time < base_duration:
                if self._check_interruption():
                    return
                self.send_data(0x21010204, 0, 0)
                time.sleep(0.34)
        elif self._current_emotion == 'angry':
            start_time = time.time()
            while time.time() - start_time < base_duration:
                if self._check_interruption():
                    return
                self.DZ_1(0.085)
                self.DZ_2(0.085)
                time.sleep(0.0425)

    def wave_hand(self, duration):
        self.stay()
        intensity = self.get_intensity()
        self.DZ_dzh(duration * intensity)

    def stamp_foot(self, duration):
        self.stay()
        intensity = self.get_intensity()
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_interruption():
                return
            self.DZ_4(0.17 * intensity)
            time.sleep(0.085)

    def perform_emotion_action(self, action_type, duration):
        if action_type == 'act_cute':
            self.act_cute(duration)
        elif action_type == 'twist_body':
            self.twist_body(duration)
        elif action_type == 'wave_hand':
            self.wave_hand(duration)
        elif action_type == 'stamp_foot':
            self.stamp_foot(duration)
        else:
            if self.debug:
                print(f"Unknown action type: {action_type}")

    def get_emotion_actions(self):
        emotion_actions = {
            'excited': ['act_cute', 'twist_body', 'wave_hand'],
            'normal_happy': ['act_cute', 'twist_body', 'wave_hand'],
            'confused': ['act_cute', 'twist_body'],
            'angry': ['twist_body', 'stamp_foot']
        }
        return emotion_actions.get(self._current_emotion, [])

    def excited_explosive_jump(self, variation=None):
        self.stay()
        if self.debug: print("执行: 爆发性跳跃")

        vib_range = variation.get('vibration_intensity', (0.08, 0.12)) if variation else (0.08, 0.12)
        pause_range = variation.get('pause_duration', (0.08, 0.12)) if variation else (0.08, 0.12)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.085, pause_range)

        start_time = time.time()
        while time.time() - start_time < 0.68:
            if self._check_interruption():
                self.stay()
                return
            self.send_data(0x21010204, 0, 0)
            time.sleep(pause_time)

        for _ in range(4):
            if self._check_interruption():
                self.stay()
                return
            self.DZ_4(0.17 * vib_intensity)
            time.sleep(0.1275 * vib_intensity)
            self.DZ_3(0.17 * vib_intensity)
            time.sleep(0.1275 * vib_intensity)

        self.DZ_dzh(0.68)
        self.emotion_twist('excited')
        self.stay()

    def excited_joyful_spin(self, variation=None):
        self.stay()
        if self.debug: print("执行: 欢乐旋转")

        vib_range = variation.get('vibration_intensity', (0.06, 0.10)) if variation else (0.06, 0.10)
        pause_range = variation.get('pause_duration', (0.10, 0.15)) if variation else (0.10, 0.15)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.17, pause_range)

        for _ in range(3):
            if self._check_interruption():
                self.stay()
                return
            self.DZ_1(0.255 * vib_intensity)
            time.sleep(pause_time)
            self.DZ_2(0.255 * vib_intensity)
            time.sleep(pause_time)

        self.move()
        self.forward(0.34)
        time.sleep(0.085)
        self.move_x(0.255)
        time.sleep(0.255)
        self.stay()

        custom_config = {
            'frequency': 0.06,
            'duration': 2.125,
            'amplitude': 1.0,
            'pattern': 'fast_vibrate'
        }
        self.emotion_twist('excited', custom_config)
        self.DZ_dzh(0.51)
        self.stay()

    def excited_bouncing_celebration(self, variation=None):
        self.stay()
        if self.debug: print("执行: 弹跳庆祝")

        vib_range = variation.get('vibration_intensity', (0.10, 0.15)) if variation else (0.10, 0.15)
        pause_range = variation.get('pause_duration', (0.06, 0.10)) if variation else (0.06, 0.10)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.102, pause_range)

        for _ in range(5):
            if self._check_interruption():
                self.stay()
                return
            self.DZ_4(0.1275 * vib_intensity)
            time.sleep(pause_time)
            self.DZ_3(0.1275 * vib_intensity)
            time.sleep(pause_time)

        self.DZ_tkb(1.02)

        start_time = time.time()
        while time.time() - start_time < 1.275:
            if self._check_interruption():
                self.stay()
                return
            self.send_data(0x21010204, 0, 0)
            time.sleep(pause_time)
            self.DZ_dzh(0.17)
            time.sleep(pause_time)
        self.stay()

    def happy_smooth_sway(self, variation=None):
        self.stay()
        if self.debug: print("执行: 流畅摇摆")

        vib_range = variation.get('vibration_intensity', (0.25, 0.30)) if variation else (0.25, 0.30)
        pause_range = variation.get('pause_duration', (0.35, 0.45)) if variation else (0.35, 0.45)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.34, pause_range)

        custom_config = {
            'frequency': 0.3 * vib_intensity,
            'duration': 1.7,
            'amplitude': 0.51 * vib_intensity,
            'pattern': 'smooth_sway'
        }
        self.emotion_twist('normal_happy', custom_config)

        self.DZ_dzh(0.85)
        time.sleep(pause_time)

        self.DZ_1(0.34 * vib_intensity)
        time.sleep(0.425)
        self.DZ_2(0.34 * vib_intensity)
        time.sleep(0.425)
        self.stay()

    def happy_gentle_nod(self, variation=None):
        self.stay()
        if self.debug: print("执行: 温柔点头")

        vib_range = variation.get('vibration_intensity', (0.20, 0.25)) if variation else (0.20, 0.25)
        pause_range = variation.get('pause_duration', (0.40, 0.50)) if variation else (0.40, 0.50)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.2975, pause_range)

        for _ in range(4):
            if self._check_interruption():
                self.stay()
                return
            self.DZ_4(0.2975 * vib_intensity)
            time.sleep(pause_time)
            self.DZ_3(0.2125 * vib_intensity)
            time.sleep(pause_time * 0.68)

        self.emotion_twist('normal_happy')

        self.DZ_dzh(1.02)
        self.stay()

    def happy_cheerful_step(self, variation=None):
        self.stay()
        if self.debug: print("执行: 轻快步伐")

        vib_range = variation.get('vibration_intensity', (0.30, 0.35)) if variation else (0.30, 0.35)
        pause_range = variation.get('pause_duration', (0.30, 0.40)) if variation else (0.30, 0.40)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.2975, pause_range)

        for _ in range(3):
            if self._check_interruption():
                self.stay()
                return
            self.DZ_1(0.255 * vib_intensity)
            time.sleep(pause_time)
            self.DZ_2(0.255 * vib_intensity)
            time.sleep(pause_time)

        self.move()
        self.forward(0.255)
        time.sleep(0.17)
        self.stay()

        self.emotion_twist('normal_happy')
        self.DZ_dzh(0.68)
        self.stay()

    def confused_curious_tilt(self, variation=None):
        self.stay()
        if self.debug: print("执行: 好奇倾斜")

        vib_range = variation.get('vibration_intensity', (0.50, 0.60)) if variation else (0.50, 0.60)
        pause_range = variation.get('pause_duration', (0.60, 0.80)) if variation else (0.60, 0.80)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.595, pause_range)

        self.DZ_1(0.595 * vib_intensity)
        time.sleep(pause_time)
        self.DZ_2(0.595 * vib_intensity)
        time.sleep(pause_time)

        self.DZ_4(0.425 * vib_intensity)
        time.sleep(pause_time * 0.68)
        self.DZ_3(0.425 * vib_intensity)
        time.sleep(pause_time * 0.68)

        custom_config = {
            'frequency': 0.6,
            'duration': 2.125,
            'amplitude': 0.34 * vib_intensity,
            'pattern': 'hesitant_search'
        }
        self.emotion_twist('confused', custom_config)
        self.stay()

    def confused_hesitant_backtrack(self, variation=None):
        self.stay()
        if self.debug: print("执行: 迟疑后退")

        vib_range = variation.get('vibration_intensity', (0.45, 0.55)) if variation else (0.45, 0.55)
        pause_range = variation.get('pause_duration', (0.70, 0.90)) if variation else (0.70, 0.90)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.68, pause_range)

        self.DZ_4(0.34 * vib_intensity)
        time.sleep(pause_time * 0.6375)
        self.DZ_3(0.425 * vib_intensity)
        time.sleep(pause_time * 0.425)

        self.DZ_1(0.425 * vib_intensity)
        time.sleep(pause_time * 0.74375)
        self.DZ_2(0.425 * vib_intensity)
        time.sleep(pause_time * 0.74375)
        self.DZ_1(0.255 * vib_intensity)
        time.sleep(pause_time * 0.53125)

        self.emotion_twist('confused')
        self.stay()

    def confused_puzzled_search(self, variation=None):
        self.stay()
        if self.debug: print("执行: 困惑搜索")

        vib_range = variation.get('vibration_intensity', (0.55, 0.65)) if variation else (0.55, 0.65)
        pause_range = variation.get('pause_duration', (0.50, 0.70)) if variation else (0.50, 0.70)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.51, pause_range)

        for _ in range(3):
            if self._check_interruption():
                self.stay()
                return
            self.DZ_4(0.34 * vib_intensity)
            time.sleep(pause_time * 0.7055)
            time.sleep(pause_time * 0.425)
            self.DZ_3(0.34 * vib_intensity)
            time.sleep(pause_time * 0.7055)
            time.sleep(pause_time * 0.425)

        self.DZ_1(0.3825 * vib_intensity)
        time.sleep(pause_time)
        self.DZ_2(0.3825 * vib_intensity)
        time.sleep(pause_time)

        self.emotion_twist('confused')
        self.stay()

    def angry_intense_stomp(self, variation=None):
        self.stay()
        if self.debug: print("执行: 剧烈跺脚")

        vib_range = variation.get('vibration_intensity', (0.06, 0.08)) if variation else (0.06, 0.08)
        pause_range = variation.get('pause_duration', (0.05, 0.07)) if variation else (0.05, 0.07)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.051, pause_range)

        for _ in range(6):
            if self._check_interruption():
                self.stay()
                return
            self.DZ_4(0.085 * vib_intensity)
            time.sleep(pause_time * 1.7)

        start_time = time.time()
        while time.time() - start_time < 1.02:
            if self._check_interruption():
                self.stay()
                return
            self.DZ_1(0.068 * vib_intensity)
            time.sleep(pause_time)
            self.DZ_2(0.068 * vib_intensity)
            time.sleep(pause_time)

        custom_config = {
            'frequency': 0.07,
            'duration': 1.7,
            'amplitude': 1.0,
            'pattern': 'aggressive_shake'
        }
        self.emotion_twist('angry', custom_config)
        self.stay()

    def angry_fierce_shake(self, variation=None):
        self.stay()
        if self.debug: print("执行: 凶猛摇晃")

        vib_range = variation.get('vibration_intensity', (0.07, 0.09)) if variation else (0.07, 0.09)
        pause_range = variation.get('pause_duration', (0.06, 0.08)) if variation else (0.06, 0.08)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.0425, pause_range)

        start_time = time.time()
        while time.time() - start_time < 1.275:
            if self._check_interruption():
                self.stay()
                return
            self.DZ_1(0.051 * vib_intensity)
            time.sleep(pause_time)
            self.DZ_2(0.051 * vib_intensity)
            time.sleep(pause_time)

        self.DZ_4(0.255 * vib_intensity)
        time.sleep(pause_time * 6.8)
        self.DZ_3(0.17 * vib_intensity)
        time.sleep(pause_time * 5.1)

        self.emotion_twist('angry')
        for _ in range(4):
            if self._check_interruption():
                self.stay()
                return
            self.DZ_4(0.102 * vib_intensity)
            time.sleep(pause_time * 1.7)
        self.stay()

    def angry_defensive_threat(self, variation=None):
        self.stay()
        if self.debug: print("执行: 防御威胁")

        vib_range = variation.get('vibration_intensity', (0.05, 0.07)) if variation else (0.05, 0.07)
        pause_range = variation.get('pause_duration', (0.07, 0.09)) if variation else (0.07, 0.09)

        vib_intensity = self._randomize_parameter(1.0, vib_range)
        pause_time = self._randomize_parameter(0.068, pause_range)

        start_time = time.time()
        while time.time() - start_time < 0.85:
            if self._check_interruption():
                self.stay()
                return
            self.DZ_1(0.085 * vib_intensity)
            self.DZ_2(0.085 * vib_intensity)
            time.sleep(pause_time)

        self.DZ_4(0.2975 * vib_intensity)
        time.sleep(pause_time * 5.3125)
        self.DZ_3(0.255 * vib_intensity)
        time.sleep(pause_time * 4.25)

        self.emotion_twist('angry')
        self.stay()

    def transition_happy_to_excited(self):
        self.stay()
        if self.debug: print("情绪过渡: 开心 → 兴奋")

        self.DZ_dzh(0.425)
        self.DZ_nst(0.85)

        start_time = time.time()
        while time.time() - start_time < 1.275:
            if self._check_interruption():
                self.stay()
                return
            self.send_data(0x21010204, 0, 0)
            time.sleep(0.1275)

        self.emotion_twist('excited')
        self.stay()

    def transition_confused_to_happy(self):
        self.stay()
        if self.debug: print("情绪过渡: 疑惑 → 开心")

        self.DZ_1(0.425)
        time.sleep(0.51)
        self.DZ_2(0.425)
        time.sleep(0.51)

        self.DZ_4(0.17)
        time.sleep(0.255)
        self.DZ_dzh(0.68)

        self.emotion_twist('normal_happy')
        self.stay()

    def transition_angry_to_calm(self):
        self.stay()
        if self.debug: print("情绪过渡: 生气 → 平静")

        for _ in range(3):
            if self._check_interruption():
                self.stay()
                return
            self.DZ_4(0.102)
            time.sleep(0.1275)

        start_time = time.time()
        while time.time() - start_time < 1.7:
            if self._check_interruption():
                self.stay()
                return
            self.send_data(0x21010204, 0, 0)
            time.sleep(0.255)

        self.DZ_1(0.255)
        time.sleep(0.34)
        self.DZ_2(0.255)
        time.sleep(0.34)
        self.DZ_nst(0.85)
        self.stay()

    def combo_excited_celebration(self):
        self.stay()
        if self.debug: print("组合动作: 兴奋庆祝")

        self.excited_explosive_jump()
        time.sleep(0.5)
        self.excited_bouncing_celebration()
        self.stay()

    def combo_thoughtful_confused(self):
        self.stay()
        if self.debug: print("组合动作: 深思疑惑")

        self.confused_curious_tilt()
        time.sleep(0.5)
        self.confused_puzzled_search()
        self.stay()

    def get_emotion_sequences(self):
        return {
            'excited': [
                {'name': '爆发性跳跃', 'func': self.excited_explosive_jump},
                {'name': '欢乐旋转', 'func': self.excited_joyful_spin},
                {'name': '弹跳庆祝', 'func': self.excited_bouncing_celebration}
            ],
            'normal_happy': [
                {'name': '流畅摇摆', 'func': self.happy_smooth_sway},
                {'name': '温柔点头', 'func': self.happy_gentle_nod},
                {'name': '轻快步伐', 'func': self.happy_cheerful_step}
            ],
            'confused': [
                {'name': '好奇倾斜', 'func': self.confused_curious_tilt},
                {'name': '迟疑后退', 'func': self.confused_hesitant_backtrack},
                {'name': '困惑搜索', 'func': self.confused_puzzled_search}
            ],
            'angry': [
                {'name': '剧烈跺脚', 'func': self.angry_intense_stomp},
                {'name': '凶猛摇晃', 'func': self.angry_fierce_shake},
                {'name': '防御威胁', 'func': self.angry_defensive_threat}
            ]
        }

    def perform_emotion_sequence(self, emotion, sequence_index=0, use_variation=True):
        sequences = self.get_emotion_sequences()
        if emotion not in sequences:
            if self.debug: print(f"未知情感: {emotion}")
            return

        emotion_seqs = sequences[emotion]
        if sequence_index >= len(emotion_seqs):
            if self.debug: print(f"序列索引超出范围")
            return

        self.set_emotion(emotion)
        seq = emotion_seqs[sequence_index]

        if use_variation:
            variation = self._get_variation(emotion)
            if self.debug: print(f"执行 {emotion} 情感: {seq['name']} (变化参数已应用)")
            seq['func'](variation)
        else:
            if self.debug: print(f"执行 {emotion} 情感: {seq['name']}")
            seq['func']()

    def perform_emotion_sequence_random(self, emotion, use_variation=True):
        sequences = self.get_emotion_sequences()
        if emotion not in sequences:
            if self.debug: print(f"未知情感: {emotion}")
            return

        emotion_seqs = sequences[emotion]

        last_seq = self._last_performed_sequence.get(emotion)
        available = [s for s in emotion_seqs if s['name'] != last_seq]
        if not available:
            available = emotion_seqs

        selected = random.choice(available)
        self._last_performed_sequence[emotion] = selected['name']

        self.set_emotion(emotion)

        if use_variation:
            variation = self._get_variation(emotion)
            if self.debug: print(f"随机执行 {emotion} 情感: {selected['name']} (变化参数已应用)")
            selected['func'](variation)
        else:
            if self.debug: print(f"随机执行 {emotion} 情感: {selected['name']}")
            selected['func']()

    def perform_all_emotions_demo(self, use_variation=True):
        sequences = self.get_emotion_sequences()

        for emotion, seq_list in sequences.items():
            print(f"\n{'='*50}")
            print(f"情感: {emotion.upper()}")
            print(f"{'='*50}")

            for i, seq in enumerate(seq_list):
                print(f"\n--- 序列 {i+1}: {seq['name']} ---")
                self.set_emotion(emotion)
                if use_variation:
                    variation = self._get_variation(emotion)
                    seq['func'](variation)
                else:
                    seq['func']()
                time.sleep(1)

            time.sleep(1.5)

    def perform_varied_sequence_loop(self, emotion, count=5, use_variation=True):
        print(f"\n开始执行 {count} 次 {emotion} 情感序列 (变化模式: {'启用' if use_variation else '禁用'})")
        print("="*50)

        for i in range(count):
            print(f"\n--- 第 {i+1}/{count} 次执行 ---")
            self.perform_emotion_sequence_random(emotion, use_variation)
            time.sleep(0.5)

        print(f"\n{emotion} 情感序列执行完成!")

    def voice_stand_up(self):
        self.send_data(0x21010C0A, 1, 0)
        time.sleep(1.7)

    def voice_sit(self):
        self.send_data(0x21010C0A, 2, 0)
        time.sleep(1.7)

    def voice_forward(self):
        self.send_data(0x21010C0A, 3, 0)
        time.sleep(1.7)

    def voice_backward(self):
        self.send_data(0x21010C0A, 4, 0)
        time.sleep(1.7)

    def voice_lmove(self):
        self.send_data(0x21010C0A, 5, 0)
        time.sleep(1.7)

    def voice_rmove(self):
        self.send_data(0x21010C0A, 6, 0)
        time.sleep(1.7)

    def voice_stop(self):
        self.send_data(0x21010C0A, 7, 0)
        time.sleep(1.7)

    def voice_l_head(self):
        self.send_data(0x21010C0A, 8, 0)
        time.sleep(1.7)

    def voice_u_head(self):
        self.send_data(0x21010C0A, 9, 0)
        time.sleep(1.7)

    def voice_llook(self):
        self.send_data(0x21010C0A, 11, 0)
        time.sleep(1.7)

    def voice_rlook(self):
        self.send_data(0x21010C0A, 12, 0)
        time.sleep(1.7)

    def voice_tl_90(self):
        self.send_data(0x21010C0A, 13, 0)
        time.sleep(1.7)

    def voice_tr_90(self):
        self.send_data(0x21010C0A, 14, 0)
        time.sleep(1.7)

    def voice_tb_90(self, duration):
        start_time = time.time()
        while time.time() - start_time < duration:
            self.send_data(0x21010C0A, 15, 0)
            time.sleep(1.7)

    def voice_tb_180(self):
        self.send_data(0x21010C0A, 15, 0)
        time.sleep(1.7)

    def voice_dzh(self):
        self.send_data(0x21010C0A, 22, 0)
        time.sleep(1.7)

    def voice_tr_120(self, duration):
        self.send_data(0x21010C0A, 19, 0)
        time.sleep(2.55)
        self.send_data(0x21010C0A, 7, 0)

    def qian(self, num):
        start_time = time.time()
        while time.time() - start_time < num:
            self.send_data(0x21010130, 13000, 0)
            time.sleep(0.05)

    def go_left(self, num):
        a = 0
        while a < num:
            self.send_data(0x21010135, 10000, 0)
            time.sleep(0.05)
            a = a + 0.1
            print(a)

    def _classify_speed(self, speed_hz: float) -> TwistSpeedLevel:
        for (min_s, max_s), level in self._speed_thresholds.items():
            if min_s <= speed_hz < max_s:
                return level
        return TwistSpeedLevel.MODERATE

    def _classify_amplitude(self, amplitude_deg: float) -> TwistAmplitudeLevel:
        for (min_a, max_a), level in self._amplitude_thresholds.items():
            if min_a <= amplitude_deg < max_a:
                return level
        return TwistAmplitudeLevel.MEDIUM

    def analyze_emotion(self, motion_data: TwistMotionData) -> Dict:
        speed_level = self._classify_speed(motion_data.speed_hz)
        amplitude_level = self._classify_amplitude(motion_data.amplitude_deg)

        key = (speed_level, amplitude_level)
        emotion = self._emotion_rules.get(key)

        if emotion is None:
            emotion = self._infer_emotion_fallback(speed_level, amplitude_level, motion_data)

        confidence = self._calculate_confidence(motion_data)

        result = {
            'emotion': emotion,
            'speed_level': speed_level,
            'amplitude_level': amplitude_level,
            'confidence': confidence,
            'parameters': {
                'speed_hz': motion_data.speed_hz,
                'amplitude_deg': motion_data.amplitude_deg,
                'duration_s': motion_data.duration_s,
                'rhythm_regularity': motion_data.rhythm_regularity,
                'direction_changes': motion_data.direction_changes
            }
        }

        self._add_validation_sample(result)

        if self.debug:
            print(f"[情感分析] 速度:{speed_level.name} | 幅度:{amplitude_level.name} => {emotion.value} (置信度:{confidence:.2f})")

        return result

    def _infer_emotion_fallback(self, speed: TwistSpeedLevel, amp: TwistAmplitudeLevel, data: TwistMotionData) -> EmotionClassification:
        if data.rhythm_regularity > 0.8:
            return EmotionClassification.HAPPY
        elif data.direction_changes > 5 and data.duration_s < 2.0:
            return EmotionClassification.ANXIOUS
        elif speed.value >= 4:
            return EmotionClassification.EXCITED
        elif amp.value >= 4:
            return EmotionClassification.ANGRY
        else:
            return EmotionClassification.CONFUSED

    def _calculate_confidence(self, data: TwistMotionData) -> float:
        confidence = 0.5
        confidence += data.rhythm_regularity * 0.3
        if data.duration_s > 1.0:
            confidence += 0.2
        elif data.duration_s > 0.5:
            confidence += 0.1
        return min(confidence, 1.0)

    def _add_validation_sample(self, result: Dict):
        self._validation_samples.append({
            'emotion': result['emotion'],
            'confidence': result['confidence'],
            'timestamp': time.time()
        })
        if len(self._validation_samples) > 100:
            self._validation_samples = self._validation_samples[-50:]

    def get_validation_report(self) -> Dict:
        if not self._validation_samples:
            return {'status': 'no_samples'}

        emotion_counts = {}
        total_confidence = 0

        for sample in self._validation_samples:
            emo = sample['emotion'].value
            emotion_counts[emo] = emotion_counts.get(emo, 0) + 1
            total_confidence += sample['confidence']

        avg_confidence = total_confidence / len(self._validation_samples)
        consistent = avg_confidence >= self._validation_threshold

        return {
            'total_samples': len(self._validation_samples),
            'emotion_distribution': emotion_counts,
            'average_confidence': avg_confidence,
            'validation_threshold': self._validation_threshold,
            'is_consistent': consistent,
            'consistency_status': 'PASS' if consistent else 'REVIEW_NEEDED'
        }

    def validate_observer_agreement(self, observer_results: List[Dict]) -> float:
        if len(observer_results) < 2:
            return 0.0

        emotions = [r['emotion'] for r in observer_results]
        unique_emotions = set(emotions)

        if len(unique_emotions) == 1:
            return 1.0

        most_common = max(set(emotions), key=emotions.count)
        agreement = emotions.count(most_common) / len(emotions)
        return agreement

    @staticmethod
    def speed_to_robot_params(speed_level: TwistSpeedLevel) -> Dict:
        speed_map = {
            TwistSpeedLevel.VERY_SLOW: {'frequency': 0.6, 'interval': 0.8},
            TwistSpeedLevel.SLOW: {'frequency': 0.4, 'interval': 0.5},
            TwistSpeedLevel.MODERATE: {'frequency': 0.25, 'interval': 0.35},
            TwistSpeedLevel.FAST: {'frequency': 0.1, 'interval': 0.2},
            TwistSpeedLevel.VERY_FAST: {'frequency': 0.06, 'interval': 0.12}
        }
        return speed_map.get(speed_level, speed_map[TwistSpeedLevel.MODERATE])

    @staticmethod
    def amplitude_to_robot_params(amplitude_level: TwistAmplitudeLevel) -> Dict:
        amp_map = {
            TwistAmplitudeLevel.MINIMAL: {'twist_value': 0.2, 'tilt_value': 0.15},
            TwistAmplitudeLevel.SMALL: {'twist_value': 0.4, 'tilt_value': 0.3},
            TwistAmplitudeLevel.MEDIUM: {'twist_value': 0.6, 'tilt_value': 0.45},
            TwistAmplitudeLevel.LARGE: {'twist_value': 0.8, 'tilt_value': 0.6},
            TwistAmplitudeLevel.EXTREME: {'twist_value': 1.0, 'tilt_value': 0.8}
        }
        return amp_map.get(amplitude_level, amp_map[TwistAmplitudeLevel.MEDIUM])

    def generate_emotion_display(self, motion_data: TwistMotionData) -> str:
        result = self.analyze_emotion(motion_data)
        emotion = result['emotion']

        display = {
            EmotionClassification.EXCITED: "🎉 兴奋",
            EmotionClassification.HAPPY: "😊 开心",
            EmotionClassification.CONFUSED: "🤔 疑惑",
            EmotionClassification.ANGRY: "😠 生气",
            EmotionClassification.ANXIOUS: "😰 焦虑",
            EmotionClassification.SARCASTIC: "🙃 讽刺",
            EmotionClassification.NEUTRAL: "😐 中性"
        }

        lines = [
            "=" * 40,
            "情感扭动分析报告",
            "=" * 40,
            f"识别情感: {display.get(emotion, emotion.value)}",
            f"置信度: {result['confidence']:.1%}",
            "-" * 40,
            f"速度等级: {result['speed_level'].name} ({motion_data.speed_hz:.2f} Hz)",
            f"幅度等级: {result['amplitude_level'].name} ({motion_data.amplitude_deg:.1f}°)",
            f"持续时间: {motion_data.duration_s:.1f}s",
            f"节奏规律性: {motion_data.rhythm_regularity:.1%}",
            f"方向变化: {motion_data.direction_changes} 次",
            "-" * 40,
            f"验证状态: {self.get_validation_report().get('consistency_status', 'N/A')}",
            "=" * 40
        ]
        return "\n".join(lines)

    def _register_variations(self, emotion: str, variations: List[dict]):
        self._variation_sets[emotion] = variations
        self._emotion_variation_history[emotion] = deque(maxlen=3)

    def _select_variation(self, emotion: str) -> Optional[dict]:
        if emotion not in self._variation_sets:
            return None

        variations = self._variation_sets[emotion]
        if not variations:
            return None

        if len(variations) == 1:
            return variations[0]

        history = self._emotion_variation_history.get(emotion, deque(maxlen=3))
        recent_names = set(history)

        available = [v for v in variations if v.get('name') not in recent_names]
        if not available:
            available = variations

        weights = []
        for v in available:
            weight = 1.0
            if v.get('name') in recent_names:
                weight *= 0.3
            weights.append(weight)

        total = sum(weights)
        weights = [w / total for w in weights]

        selected = random.choices(available, weights=weights, k=1)[0]

        history.append(selected.get('name'))
        self._variation_history.append(f"{emotion}:{selected.get('name')}")

        return selected

    def _add_variation(self, emotion: str, variation: dict):
        if emotion not in self._variation_sets:
            self._variation_sets[emotion] = []
        self._variation_sets[emotion].append(variation)

    def _get_variation_history(self) -> List[str]:
        return list(self._variation_history)

    def _clear_variation_history(self, emotion: str = None):
        if emotion:
            if emotion in self._emotion_variation_history:
                self._emotion_variation_history[emotion].clear()
        else:
            self._variation_history.clear()
            for h in self._emotion_variation_history.values():
                h.clear()

    def _get_variation(self, emotion: str) -> dict:
        if emotion not in self._variations:
            return self._variations['normal_happy'][0]

        variations = self._variations[emotion]
        if len(variations) == 1:
            return variations[0]

        recent = list(self._injector_history)[-3:]
        available = [v for v in variations if v not in recent]
        if not available:
            available = variations

        selected = random.choice(available)
        self._injector_history.append(selected)

        return selected

    def _randomize_parameter(self, base_value: float, variation_range: Tuple[float, float]) -> float:
        low, high = variation_range
        variation = random.uniform(low, high)
        return base_value * variation

    def trigger_emotion_transformation(self, trigger_value):
        if trigger_value == "1234":
            if self.debug:
                print("[情绪转化触发] 接收到触发值 '1234'，终止当前动作并启动下一个动作")
            
            self._action_interrupted = True
            
            with self._twist_lock:
                self._twist_active = False
            
            self._current_sequence_index = (self._current_sequence_index + 1) % len(self.get_emotion_sequences()[self._current_emotion])
            
            if self.debug:
                print(f"[情绪转化触发] 启动下一个动作，序列索引: {self._current_sequence_index}")
            
            self.perform_emotion_sequence(self._current_emotion, self._current_sequence_index)
            
            return True
        return False

    def _check_interruption(self):
        if self._action_interrupted:
            if self.debug:
                print("[动作中断] 检测到中断信号，终止当前动作")
            self._action_interrupted = False
            return True
        return False

    def interrupt_action(self):
        """中断当前正在执行的动作"""
        if self.debug:
            print("[动作中断] 收到中断信号，终止当前动作")
        self._action_interrupted = True
        with self._twist_lock:
            self._twist_active = False

    def trigger_next_action(self, emotion=None):
        """触发下一个动作的执行"""
        target_emotion = emotion if emotion else self._current_emotion
        self.set_emotion(target_emotion)
        
        sequences = self.get_emotion_sequences()
        if target_emotion not in sequences:
            if self.debug:
                print(f"[动作触发] 未知情感: {target_emotion}")
            return
        
        emotion_seqs = sequences[target_emotion]
        self._current_sequence_index = (self._current_sequence_index + 1) % len(emotion_seqs)
        
        if self.debug:
            print(f"[动作触发] 启动下一个动作，序列索引: {self._current_sequence_index}")
        
        self.perform_emotion_sequence(target_emotion, self._current_sequence_index)

    def close(self):
        self._heartbeat_running = False
        try:
            self._udp_socket.close()
        except Exception:
            pass

    def test_adjusted_sequences(self, test_count=10):
        """测试调整后的动作序列，验证执行时间缩短效果"""
        print(f"\n开始执行 {test_count} 次连续动作测试...")
        print("="*60)
        
        total_time = 0
        test_results = []
        
        for i in range(test_count):
            print(f"\n--- 第 {i+1}/{test_count} 次测试 ---")
            
            start_time = time.time()
            
            # 执行基础动作
            print("执行基础动作...")
            self.stand_up()
            self.sit()
            
            # 执行情感动作
            print("执行情感动作...")
            emotions = ['excited', 'normal_happy', 'confused', 'angry']
            for emotion in emotions:
                print(f"  - {emotion}")
                self.perform_emotion_sequence_random(emotion, use_variation=True)
                time.sleep(0.5)
            
            # 执行过渡动作
            print("执行过渡动作...")
            self.transition_happy_to_excited()
            time.sleep(0.5)
            self.transition_confused_to_happy()
            time.sleep(0.5)
            self.transition_angry_to_calm()
            
            end_time = time.time()
            execution_time = end_time - start_time
            total_time += execution_time
            
            test_results.append(execution_time)
            print(f"执行时间: {execution_time:.2f} 秒")
        
        avg_time = total_time / test_count
        print(f"\n" + "="*60)
        print(f"测试完成!")
        print(f"总执行时间: {total_time:.2f} 秒")
        print(f"平均执行时间: {avg_time:.2f} 秒")
        print(f"单次执行时间范围: {min(test_results):.2f} - {max(test_results):.2f} 秒")
        print("="*60)
        
        return {
            'total_time': total_time,
            'average_time': avg_time,
            'min_time': min(test_results),
            'max_time': max(test_results),
            'test_count': test_count
        }


if __name__ == '__main__':
    time.sleep(1)

    robot = YscLite3Controller(debug=True)

    print("="*60)
    print("      机器狗情感场景演示系统 (升级版)")
    print("="*60)
    print("\n新功能说明:")
    print("- 可配置扭动参数: 频率、持续时间、幅度、模式")
    print("- 情感强度驱动: 幅度随强度自动调整")
    print("- 线程安全机制: 防止动作冲突")
    print("- 四种扭动模式: 快速振动、流畅摇摆、迟疑探索、凶猛摇晃")
    print("\n情感说明:")
    print("- 兴奋 (Excited): 快速、高频率、大幅度")
    print("- 开心 (Normal Happy): 中等速度、温和")
    print("- 疑惑 (Confused): 慢速、迟疑、探索")
    print("- 生气 (Angry): 快速、剧烈、有攻击性")
    print("="*60)
    
    robot.sit()
    time.sleep(1)
    robot.stay()
    print("\n系统初始化完成...")
    time.sleep(1)

    emotion_menu = {
        '1': {'name': '兴奋', 'key': 'excited'},
        '2': {'name': '开心', 'key': 'normal_happy'},
        '3': {'name': '疑惑', 'key': 'confused'},
        '4': {'name': '生气', 'key': 'angry'},
        '5': {'name': '演示所有情感', 'key': 'all'},
        '6': {'name': '情绪过渡演示', 'key': 'transitions'},
        '7': {'name': '组合动作演示', 'key': 'combos'},
        '8': {'name': '直接扭动测试', 'key': 'twist_test'},
        '9': {'name': '查看扭动配置', 'key': 'view_config'},
        '10': {'name': '修改扭动配置', 'key': 'edit_config'},
        '11': {'name': '变化序列循环测试', 'key': 'variation_loop'},
        '12': {'name': '调整后动作测试', 'key': 'adjusted_test'},
        '0': {'name': '退出', 'key': 'exit'}
    }

    while True:
        print("\n" + "="*60)
        print("情感选择菜单:")
        print("="*60)
        print("  1. 兴奋 (Excited)")
        print("  2. 开心 (Normal Happy)")
        print("  3. 疑惑 (Confused)")
        print("  4. 生气 (Angry)")
        print("  5. 演示所有情感")
        print("  6. 情绪过渡演示")
        print("  7. 组合动作演示")
        print("  8. 直接扭动测试")
        print("  9. 查看扭动配置")
        print(" 10. 修改扭动配置")
        print(" 11. 变化序列循环测试")
        print(" 12. 调整后动作测试")
        print("  0. 退出程序")
        print("="*60)
        
        choice = input("\n请输入数字选择 (0-12): ").strip()
        
        if choice == '0':
            print("\n感谢使用，再见!")
            robot.sit()
            break
        
        if choice not in emotion_menu:
            print("输入无效，请重新输入!")
            time.sleep(0.5)
            continue
        
        # 中断当前动作
        robot.interrupt_action()
        time.sleep(0.1)  # 短暂延迟确保中断生效
        
        emotion_info = emotion_menu[choice]
        
        if emotion_info['key'] == 'all':
            print(f"\n开始演示所有情感...")
            robot.perform_all_emotions_demo()
        elif emotion_info['key'] == 'transitions':
            print("\n--- 情绪过渡演示 ---")
            print("  1. 开心 → 兴奋")
            print("  2. 疑惑 → 开心")
            print("  3. 生气 → 平静")
            print("  4. 所有过渡演示")
            trans_choice = input("请选择 (1-4): ").strip()
            
            if trans_choice == '1':
                robot.transition_happy_to_excited()
            elif trans_choice == '2':
                robot.transition_confused_to_happy()
            elif trans_choice == '3':
                robot.transition_angry_to_calm()
            elif trans_choice == '4':
                print("\n演示所有情绪过渡...")
                robot.transition_happy_to_excited()
                time.sleep(1)
                robot.transition_confused_to_happy()
                time.sleep(1)
                robot.transition_angry_to_calm()
        elif emotion_info['key'] == 'combos':
            print("\n--- 组合动作演示 ---")
            print("  1. 兴奋庆祝组合")
            print("  2. 深思疑惑组合")
            print("  3. 所有组合演示")
            combo_choice = input("请选择 (1-3): ").strip()
            
            if combo_choice == '1':
                robot.combo_excited_celebration()
            elif combo_choice == '2':
                robot.combo_thoughtful_confused()
            elif combo_choice == '3':
                print("\n演示所有组合动作...")
                robot.combo_excited_celebration()
                time.sleep(1)
                robot.combo_thoughtful_confused()
        elif emotion_info['key'] == 'twist_test':
            print("\n--- 直接扭动测试 ---")
            print("  1. 兴奋扭动")
            print("  2. 开心扭动")
            print("  3. 疑惑扭动")
            print("  4. 生气扭动")
            twist_choice = input("请选择 (1-4): ").strip()
            twist_map = {
                '1': 'excited',
                '2': 'normal_happy',
                '3': 'confused',
                '4': 'angry'
            }
            if twist_choice in twist_map:
                robot.emotion_twist(twist_map[twist_choice])
        elif emotion_info['key'] == 'view_config':
            print("\n--- 当前扭动配置 ---")
            configs = robot.get_twist_config()
            for emo, cfg in configs.items():
                print(f"\n{emo}:")
                print(f"  频率: {cfg['frequency']}")
                print(f"  持续时间: {cfg['duration']}")
                print(f"  幅度: {cfg['amplitude']}")
                print(f"  模式: {cfg['pattern']}")
        elif emotion_info['key'] == 'edit_config':
            print("\n--- 修改扭动配置 ---")
            print("选择情感:")
            print("  1. 兴奋")
            print("  2. 开心")
            print("  3. 疑惑")
            print("  4. 生气")
            edit_choice = input("请选择 (1-4): ").strip()
            edit_map = {
                '1': 'excited',
                '2': 'normal_happy',
                '3': 'confused',
                '4': 'angry'
            }
            if edit_choice in edit_map:
                target_emo = edit_map[edit_choice]
                print(f"\n编辑 {target_emo} 配置 (留空跳过):")
                freq = input("频率 (当前值: {}): ".format(robot.get_twist_config(target_emo)['frequency']))
                dur = input("持续时间 (当前值: {}): ".format(robot.get_twist_config(target_emo)['duration']))
                amp = input("幅度 (当前值: {}): ".format(robot.get_twist_config(target_emo)['amplitude']))
                
                robot.set_twist_config(
                    target_emo,
                    frequency=float(freq) if freq else None,
                    duration=float(dur) if dur else None,
                    amplitude=float(amp) if amp else None
                )
        elif emotion_info['key'] == 'variation_loop':
            print("\n--- 变化序列循环测试 ---")
            print("选择情感:")
            print("  1. 兴奋")
            print("  2. 开心")
            print("  3. 疑惑")
            print("  4. 生气")
            var_choice = input("请选择 (1-4): ").strip()
            var_map = {
                '1': 'excited',
                '2': 'normal_happy',
                '3': 'confused',
                '4': 'angry'
            }
            if var_choice in var_map:
                target_emo = var_map[var_choice]
                count = input("请输入循环次数 (默认5): ").strip()
                count = int(count) if count else 5
                use_var = input("是否启用变化参数? (y/n, 默认y): ").strip().lower()
                use_var = use_var != 'n'
                robot.perform_varied_sequence_loop(target_emo, count, use_var)
        elif emotion_info['key'] == 'adjusted_test':
            print("\n--- 调整后动作测试 ---")
            test_count = input("请输入测试次数 (默认10): ").strip()
            test_count = int(test_count) if test_count else 10
            robot.test_adjusted_sequences(test_count)
        else:
            emotion_key = emotion_info['key']
            emotion_name = emotion_info['name']
            sequences = robot.get_emotion_sequences()[emotion_key]
            
            print(f"\n" + "="*60)
            print(f"开始演示: {emotion_name}")
            print(f"="*60)
            print(f"该情感共有 {len(sequences)} 个动作序列")
            
            for i, seq in enumerate(sequences):
                print(f"\n--- 序列 {i+1}: {seq['name']} ---")
                robot.set_emotion(emotion_key)
                variation = robot._get_variation(emotion_key)
                seq['func'](variation)
                time.sleep(1)
            
            print(f"\n{emotion_name} 情感演示完成!")
        
        # 短暂延迟后自动重新显示菜单
        time.sleep(0.5)
