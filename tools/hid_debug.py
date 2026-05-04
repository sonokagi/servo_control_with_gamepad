"""
Phase 3: HID レポートデバッグスクリプト
ZM T-12 に直接接続し、生の HID レポートを表示して軸・ボタンの配置を確認する

--- 使い方 ---
1. COWBOX T-12 を X + HOME 長押しでペアリングモードにする
2. Thonny を使い、このスクリプトを Pico W 上で実行
3. 接続後に「=== Ready ===」が表示されたら操作開始
4. 各操作を行い、変化するバイト位置・ビットを確認する

--- 確認手順 ---
  a. 左スティックを左右にゆっくり動かす  → Byte 0 (LX) が変化するか確認
  b. 左スティックを上下にゆっくり動かす  → Byte 1 (LY) が変化するか確認
  c. 右スティックを上下にゆっくり動かす  → Byte 3 (RY) が変化するか確認
  d. L ボタンを押す                      → Byte 5 bit6(0x40) が 1 になるか確認
  e. R ボタンを押す                      → Byte 5 bit7(0x80) が 1 になるか確認
  f. B ボタンを押す                      → Byte 5 bit1(0x02) が 1 になるか確認
  g. 各スティックの中立時の値が 128 か確認する

--- 出力形式 ---
  Raw: [LX=xxx LY=xxx RX=xxx RY=xxx PAD=xxx BTN=xxx BTN2=xxx]
  Axes(signed): LX=xxx LY=xxx RX=xxx RY=xxx  Buttons: L=x R=x B=x

--- 本プロジェクトの推定構造（Phase 1 より）---
  Byte 0 : LX   (0~255, 中立=128)
  Byte 1 : LY   (0~255, 中立=128)
  Byte 2 : RX   (0~255, 中立=128)
  Byte 3 : RY   (0~255, 中立=128)
  Byte 4 : D-pad
  Byte 5 : ボタン下位  L=bit6(0x40)  R=bit7(0x80)  B=bit1(0x02)
  Byte 6 : ボタン上位
"""

import bluetooth
import utime
from machine import Pin
from micropython import const

# BLE IRQ イベント番号
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_NOTIFY = const(18)

# Phase 2 で確認済みの接続先
TARGET_ADDR = bytes([0x03, 0x12, 0x08, 0x20, 0x34, 0x12])
TARGET_ADDR_TYPE = const(0)

_FLAG_NOTIFY = const(0x10)

led = Pin("LED", Pin.OUT)

_conn_handle = None
_services = []  # [(start, end, uuid), ...]
_service_idx = 0
_prev_state = None  # 前回のレポート（変化検出用）
_notify_count = 0  # 計測用カウンタ
_measuring = False  # 計測中フラグ（True 中は debug 出力を抑制）
_ready = False  # サービス探索完了フラグ


def _irq(event, data):
    global _conn_handle, _services, _service_idx, _prev_state, _notify_count, _ready

    if event == _IRQ_PERIPHERAL_CONNECT:
        conn_handle, addr_type, addr = data
        _conn_handle = conn_handle
        print("Connected! Discovering services...")
        led.value(1)
        ble.gattc_discover_services(_conn_handle)

    elif event == _IRQ_PERIPHERAL_DISCONNECT:
        _conn_handle = None
        print("Disconnected.")
        led.value(0)

    elif event == _IRQ_GATTC_SERVICE_RESULT:
        conn_handle, start, end, uuid = data
        _services.append((start, end, uuid))
        print("  Service: uuid={} handles=[{}-{}]".format(uuid, start, end))

    elif event == _IRQ_GATTC_SERVICE_DONE:
        print("({} services found)".format(len(_services)))
        _service_idx = 0
        _discover_next_service()

    elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
        conn_handle, def_handle, value_handle, properties, uuid = data
        has_notify = bool(properties & _FLAG_NOTIFY)
        print(
            "  Char: uuid={} value_handle={} notify={}".format(
                uuid, value_handle, has_notify
            )
        )

    elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
        _service_idx += 1
        _discover_next_service()

    elif event == _IRQ_GATTC_NOTIFY:
        _notify_count += 1
        conn_handle, value_handle, notify_data = data
        state = list(notify_data)
        if not _measuring and state != _prev_state:
            _prev_state = state
            _print_report(value_handle, state)


def _discover_next_service():
    global _ready
    if _service_idx < len(_services):
        start, end, uuid = _services[_service_idx]
        ble.gattc_discover_characteristics(_conn_handle, start, end)
    else:
        _ready = True


def _print_report(handle, state):
    if len(state) < 7:
        print("h={} raw={}".format(handle, [hex(b) for b in state]))
        return

    # 生バイト（10進）
    raw = " ".join("{:3d}".format(b) for b in state[:7])

    # 解釈値
    lx = state[0] - 128
    ly = state[1] - 128
    rx = state[2] - 128
    ry = state[3] - 128
    btn = state[5]
    btn2 = state[6]
    l = bool(btn & 0x40)
    r = bool(btn & 0x80)
    b = bool(btn & 0x02)

    print(
        "Raw:[{}]  LX={:4d} LY={:4d} RX={:4d} RY={:4d}  L={} R={} B={}".format(
            raw, lx, ly, rx, ry, int(l), int(r), int(b)
        )
    )


# ----- メイン -----

addr_str = ":".join("{:02X}".format(b) for b in TARGET_ADDR)
print("Connecting to ZM T-12 ({}) ...".format(addr_str))
print("Put COWBOX T-12 into pairing mode: hold X + HOME")
print()

ble = bluetooth.BLE()
ble.active(True)
ble.irq(_irq)
ble.gap_connect(TARGET_ADDR_TYPE, TARGET_ADDR)

# 接続・操作確認が終わるまで待機
MEASURE_SEC = 5

while True:
    if _ready:
        _ready = False
        _measuring = True
        _notify_count = 0
        print()
        print(
            "=== Notify レート計測中（{}秒）... スティックを動かしてください ===".format(
                MEASURE_SEC
            )
        )
        utime.sleep_ms(MEASURE_SEC * 1000)
        count = _notify_count
        _measuring = False
        if count > 0:
            avg_ms = MEASURE_SEC * 1000 / count
            print(
                "受信数: {}  平均間隔: {:.1f}ms  レート: {:.1f}Hz".format(
                    count, avg_ms, 1000 / avg_ms
                )
            )
        else:
            print("notify なし（ゲームパッドを操作してください）")
        print()
        print("=== デバッグモード ===")
        print("Byte:  [ 0   1   2   3   4   5   6 ]")
        print("       [ LX  LY  RX  RY  PAD BTN BTN2]")
        print()
    utime.sleep_ms(100)
