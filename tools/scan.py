"""
Phase 2: BLE スキャンスクリプト
COWBOX T-12 のデバイス名と MAC アドレスを確認する

--- 使い方 ---
1. COWBOX T-12 を X + HOME 長押しでペアリングモードにする
   （LED が点滅し始めたら準備 OK）
2. Thonny を使い、このスクリプトを Pico W 上で実行
3. Pico W の LED が 3 回点滅してスキャン開始
4. SCAN_DURATION_MS（デフォルト 10 秒）の間、検出デバイスを表示
5. 最後に全デバイスの一覧を表示
   → デバイス名付きのものに "<<<" が付く
6. COWBOX T-12 の Addr と type を main.py の接続設定に記録する

--- 出力例 ---
--- BLE scan start (10 sec) ---
Put COWBOX T-12 into pairing mode: hold X + HOME

  03:12:08:20:34:12 | type=0 | rssi= -48 | ZM T-12
scan done.

=== Result: 35 device(s) found ===
  Addr=03:12:08:20:34:12 | type=0 | rssi= -48 | ZM T-12 <<<
  ...

Record "Addr" and "type" for Phase 3 connection.

--- 本プロジェクトの確認結果 ---
  BLE アドバタイジング名 : ZM T-12  (製品名 COWBOX T-12 とは異なる)
  MAC アドレス           : 03:12:08:20:34:12
  アドレスタイプ         : 0

--- COWBOX T-12 が表示されない場合 ---
- ペアリングモードが解除された可能性あり → 再度 X + HOME 長押し
- Pico W との距離を近づける
- SCAN_DURATION_MS を 20000 に増やして再実行
"""

import bluetooth
import utime
from machine import Pin
from micropython import const

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)

_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_SHORT_NAME = const(0x08)

SCAN_DURATION_MS = 10000  # スキャン時間（ms）


def _decode_field(payload, adv_type):
    i = 0
    while i + 1 < len(payload):
        if payload[i + 1] == adv_type:
            return payload[i + 2 : i + payload[i] + 1]
        i += 1 + payload[i]
    return None


def _decode_name(adv_data):
    raw = _decode_field(adv_data, _ADV_TYPE_NAME) or _decode_field(
        adv_data, _ADV_TYPE_SHORT_NAME
    )
    return str(raw, "utf-8") if raw else ""


def _addr_str(addr):
    return ":".join("{:02X}".format(b) for b in addr)


# アドレス文字列 → (addr_type, name, rssi) の辞書（重複除去用）
_found = {}


def _irq(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data
        key = _addr_str(bytes(addr))
        if key not in _found:
            name = _decode_name(bytes(adv_data))
            _found[key] = (addr_type, name, rssi)
            print(
                "  {} | type={} | rssi={:4d} | {}".format(
                    key, addr_type, rssi, name if name else "(no name)"
                )
            )

    elif event == _IRQ_SCAN_DONE:
        print("scan done.")


# ----- メイン -----

led = Pin("LED", Pin.OUT)

# 3回点滅してスキャン開始を通知
for _ in range(6):
    led.toggle()
    utime.sleep_ms(200)
led.value(1)

print("--- BLE scan start ({} sec) ---".format(SCAN_DURATION_MS // 1000))
print("Put COWBOX T-12 into pairing mode: hold X + HOME")
print()

ble = bluetooth.BLE()
ble.active(True)
ble.irq(_irq)
ble.gap_scan(SCAN_DURATION_MS, 30000, 30000)

utime.sleep_ms(SCAN_DURATION_MS + 500)

led.value(0)

print()
print("=== Result: {} device(s) found ===".format(len(_found)))
for addr, (addr_type, name, rssi) in _found.items():
    marker = " <<<" if name else ""
    print(
        "  Addr={} | type={} | rssi={:4d} | {}{}".format(
            addr, addr_type, rssi, name if name else "(no name)", marker
        )
    )

print()
print('Record "Addr" and "type" for Phase 3 connection.')
