"""
BLE ゲームパッド (ZM T-12) + 4ch サーボ制御

操作:
  左スティック LX  → 旋回 (Rotate,   GP14)  ※反転
  左スティック LY  → 肘   (Elbow,    GP17)
  右スティック RY  → 肩   (Shoulder, GP15)
  L ボタン         → 手首 (Hand,     GP16) 閉じる
  R ボタン         → 手首 (Hand,     GP16) 開く
  B ボタン         → 全サーボ 初期位置リセット

LED (GP18):
  高速点滅 → 接続待ち
  点灯     → 接続済み
"""

import bluetooth
import utime
from machine import Pin, Timer
from micropython import const
import servo

# ===== BLE 設定 =====

_IRQ_PERIPHERAL_CONNECT          = const(7)
_IRQ_PERIPHERAL_DISCONNECT       = const(8)
_IRQ_GATTC_SERVICE_RESULT        = const(9)
_IRQ_GATTC_SERVICE_DONE          = const(10)
_IRQ_GATTC_CHARACTERISTIC_DONE   = const(12)
_IRQ_GATTC_NOTIFY                = const(18)

TARGET_ADDR      = bytes([0x03, 0x12, 0x08, 0x20, 0x34, 0x12])  # ZM T-12
TARGET_ADDR_TYPE = const(0)

# ===== サーボ設定 =====
#               pin       ini   min   max  speed
_SERVO_PARAMS = [
    (Pin(14), 1520,  620, 2400, 12),  # Rotate   (旋回)
    (Pin(15), 1540,  920, 2020,  9),  # Shoulder (肩)
    (Pin(17), 1490,  820, 2020,  9),  # Elbow    (肘)
    (Pin(16), 1600,  750, 2450, 36),  # Hand     (手首)
]

# ===== 制御パラメータ =====

CMD_THRESH = 0.375  # 不感帯（1/4 + 1/8、旧実装から継承）

# HID Notify 1回ごとの最大 Duty 変化量 [us]
# 旧実装 (Processing 60fps) の DUTY_CHANGE_PAR_FRAME を継承。Phase 6 で要調整。
DUTY_STEP = [10, 6, 7, 30]  # [Rotate, Shoulder, Elbow, Hand]

_BTN_B = const(0x02)  # Byte5 bit1
_BTN_L = const(0x40)  # Byte5 bit6
_BTN_R = const(0x80)  # Byte5 bit7

# ===== 初期化 =====

servos = [servo.Servo(*p) for p in _SERVO_PARAMS]
led    = servo.ToggleLed(18, 5)  # 5周期=100ms トグル（高速点滅）

_cmd = [float(s.initial_us) for s in servos]  # 指令 Duty（float で保持）

_conn_handle     = None
_connected       = False
_needs_reconnect = False
_services        = []
_service_idx     = 0


# ===== Timer コールバック（20ms 周期・割り込み）=====

def _timer_cb(t):
    for s in servos:
        s.update()
    if not _connected:
        led.update()  # 接続待ち中のみ点滅


# ===== BLE 接続 =====

def _connect():
    global _services, _service_idx
    _services    = []
    _service_idx = 0
    print('Connecting to ZM T-12...')
    ble.gap_connect(TARGET_ADDR_TYPE, TARGET_ADDR)


def _discover_chars():
    if _service_idx < len(_services):
        start, end = _services[_service_idx]
        ble.gattc_discover_characteristics(_conn_handle, start, end)


def _irq(event, data):
    global _conn_handle, _connected, _needs_reconnect, _service_idx

    if event == _IRQ_PERIPHERAL_CONNECT:
        conn_handle, _, _ = data
        _conn_handle = conn_handle
        _connected   = True
        led.on()
        print('Connected.')
        ble.gattc_discover_services(_conn_handle)

    elif event == _IRQ_PERIPHERAL_DISCONNECT:
        _conn_handle     = None
        _connected       = False
        _needs_reconnect = True
        print('Disconnected.')

    elif event == _IRQ_GATTC_SERVICE_RESULT:
        _, start, end, _ = data
        _services.append((start, end))

    elif event == _IRQ_GATTC_SERVICE_DONE:
        _service_idx = 0
        _discover_chars()

    elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
        _service_idx += 1
        _discover_chars()

    elif event == _IRQ_GATTC_NOTIFY:
        _, _, notify_data = data
        _on_notify(list(notify_data))


# ===== サーボ制御ロジック =====

def _on_notify(state):
    if len(state) < 6:
        return

    btn = state[5]

    # B ボタン: 全サーボを初期位置にリセット
    if btn & _BTN_B:
        for i, s in enumerate(servos):
            s.reset()
            _cmd[i] = float(s.initial_us)
        return

    # スティック → サーボ軸マッピング
    _update_axis(0, -(state[0] - 128) / 128.0)  # Rotate:   LX 反転
    _update_axis(1,  (state[3] - 128) / 128.0)  # Shoulder: RY 正
    _update_axis(2,  (state[1] - 128) / 128.0)  # Elbow:    LY 正

    # Hand: L/R ボタン
    if btn & _BTN_L:
        _update_axis(3, -1.0)
    elif btn & _BTN_R:
        _update_axis(3, +1.0)


def _update_axis(idx, normalized):
    """正規化入力値 (-1.0〜+1.0) から Duty を増減して set_duty に渡す。

    不感帯 CMD_THRESH 以内は無視。超えた分に比例して Duty を変化させる。
    旧実装 (Processing manualOperation) と同アルゴリズム。
    """
    if normalized < -CMD_THRESH:
        delta = DUTY_STEP[idx] * (normalized + CMD_THRESH) / (1.0 - CMD_THRESH)
    elif normalized > CMD_THRESH:
        delta = DUTY_STEP[idx] * (normalized - CMD_THRESH) / (1.0 - CMD_THRESH)
    else:
        return

    _cmd[idx] = max(servos[idx].min_us,
                    min(servos[idx].max_us, _cmd[idx] + delta))
    servos[idx].set_duty(int(_cmd[idx]))


# ===== メインループ =====

ble = bluetooth.BLE()
ble.active(True)
ble.irq(_irq)

timer = Timer()
timer.init(period=20, mode=Timer.PERIODIC, callback=_timer_cb)

_connect()

while True:
    if _needs_reconnect:
        _needs_reconnect = False
        utime.sleep_ms(1000)
        _connect()
    utime.sleep_ms(100)
