"""
Phase 4: servo.py 動作確認スクリプト
実行するだけで全サーボの動作確認ができる（シェルへの入力不要）

--- 使い方 ---
1. servo.py と servo_test.py を両方 Pico W に保存
2. servo_test.py を実行（F5）
3. 全サーボが順番に min → initial → max → initial と動く
4. 実行後もシェルから追加操作が可能（下記参照）

--- 実行後のシェル操作例 ---
servos[0].set_duty(2400)   # 旋回を最大へ（滑らか移動）
servos[0].reset()          # 旋回を初期位置へ（即時移動）
"""

import utime
from machine import Pin, Timer
import servo

# サーボ初期化（接続ピン・パラメータは plan.md 2節参照）
servos = [
    servo.Servo(Pin(14), 1520, 620, 2400, 12),  # 旋回
    servo.Servo(Pin(15), 1540, 920, 2020, 9),  # 肩
    servo.Servo(Pin(17), 1490, 820, 2020, 9),  # 肘
    servo.Servo(Pin(16), 1600, 750, 2450, 36),  # 手首
]
NAMES = ["Rotate  (GP14)", "Shoulder(GP15)", "Elbow   (GP17)", "Hand    (GP16)"]


# タイマー割り込みでサーボ更新（20ms 周期）
def _timer_cb(t):
    for s in servos:
        s.update()


timer = Timer()
timer.init(period=20, mode=Timer.PERIODIC, callback=_timer_cb)


def _wait(ms):
    utime.sleep_ms(ms)


def reset_all():
    """全サーボを初期位置に戻す。"""
    for s in servos:
        s.reset()


# ----- 自動テストシーケンス -----
print("=== servo_test: 動作確認開始 ===")
print()

for i, (s, name) in enumerate(zip(servos, NAMES)):
    print(
        "[{}] {} initial={} min={} max={}".format(
            i, name, s.initial_us, s.min_us, s.max_us
        )
    )

    print("      → max  ({})".format(s.max_us))
    s.set_duty(s.max_us)
    _wait(1500)

    print("      → initial ({})".format(s.initial_us))
    s.reset()
    _wait(800)

    print("      → min  ({})".format(s.min_us))
    s.set_duty(s.min_us)
    _wait(1500)

    print("      → initial ({})".format(s.initial_us))
    s.reset()
    _wait(800)

    print()

print("=== 完了 ===")
print("追加操作: servos[0].set_duty(2400) / servos[0].reset() / reset_all()")
