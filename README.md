# BLE ゲームパッド による 4ch のサーボ制御

COWBOX Android Controller T-12（BLE HID ゲームパッド）を Raspberry Pi Pico W に BLE 接続し、4ch のサーボ（ロボットアーム）を制御する MicroPython プロジェクト。

```text
COWBOX T-12 (BLE Peripheral / HID)
    ↕ Bluetooth 4.0 BLE
Raspberry Pi Pico W (BLE Central)
    ↓ PWM
4ch サーボ
```

---

## ハードウェア要件

| 機器                           | 備考                     |
| ------------------------------ | ------------------------ |
| Raspberry Pi Pico W            | MicroPython v1.20.0 以降 |
| COWBOX Android Controller T-12 | BLE HID ゲームパッド     |
| サーボ × 4                     | PWM 制御（50Hz）         |
| LED × 1                        | 接続状態表示用           |

### ピンアサイン

| ピン | 種別   | 役割          |
| ---- | ------ | ------------- |
| GP14 | サーボ | 旋回 (Rotate) |
| GP15 | サーボ | 肩 (Shoulder) |
| GP17 | サーボ | 肘 (Elbow)    |
| GP16 | サーボ | 手首 (Hand)   |
| GP18 | LED    | 接続状態表示  |

---

## セットアップ

### 1. MicroPython の書き込み

1. [micropython.org](https://micropython.org/download/RPI_PICO_W/) から Pico W 用 `.uf2`（v1.20.0 以降）をダウンロード
2. BOOTSEL ボタンを押しながら USB 接続 → ドライブとして認識される
3. `.uf2` ファイルをドライブにコピー → 自動再起動

### 2. ファイルの転送

[Thonny IDE](https://thonny.org/) を使って以下の 2 ファイルを Pico W のルートに転送する。

```text
main.py     ← BLE 接続 + サーボ制御のメインループ
servo.py    ← Servo / ToggleLed クラス
```

### 3. ゲームパッドのペアリング

COWBOX T-12 の **X ボタン + HOME ボタンを長押し**してペアリングモードに移行する。

---

## 使い方

Pico W に電源を入れると自動で接続を開始する。

| LED 状態 | 意味     |
| -------- | -------- |
| 高速点滅 | 接続待ち |
| 点灯     | 接続済み |

### 操作方法

| 操作              | サーボ        | 動作               |
| ----------------- | ------------- | ------------------ |
| 左スティック 左右 | 旋回 (Rotate) | 左右に旋回         |
| 左スティック 上下 | 肘 (Elbow)    | 肘を曲げ伸ばし     |
| 右スティック 上下 | 肩 (Shoulder) | 肩を上げ下げ       |
| L ボタン          | 手首 (Hand)   | 左回転             |
| R ボタン          | 手首 (Hand)   | 右回転             |
| B ボタン          | 全サーボ      | 初期位置にリセット |

---

## ファイル構成

```text
servo_control_with_gamepad/
├── main.py              # BLE 接続 + サーボ制御のメインループ
├── servo.py             # Servo / ToggleLed クラス
├── tools/               # 開発・デバッグ用スクリプト（本番動作には不要）
│   ├── scan.py              # BLE スキャン確認
│   ├── hid_debug.py         # HID レポート確認・Notify レート計測
│   └── servo_test.py        # サーボ単体動作確認
├── docs/
│   ├── plan.md              # 開発フェーズ計画・仕様記録
│   └── zm_t12.md            # ZM T-12 コントローラ解析メモ
├── reference/
│   ├── multi_servo.py       # 旧 Pico 用サーボ制御コード（流用元）
│   └── serial_servo_control_from_gamepad.pde  # 旧 PC 用制御コード（流用元）
└── prompts/
    └── 作成依頼.md          # 依頼仕様書
```

---

## カスタマイズ

設定値は `main.py` の冒頭にまとまっている。

### BLE 設定

#### ゲームパッドの MAC アドレス

```python
TARGET_ADDR = bytes([0x03, 0x12, 0x08, 0x20, 0x34, 0x12])  # ZM T-12
```

別のゲームパッドを使う場合は `tools/scan.py` でアドレスを確認して書き換える。

### サーボ設定

PWM 信号の High 時間（マイクロ秒）で角度を指定する。

| サーボ        | 初期値 [us] | min [us] | max [us] | 速度 [us/20ms] |
| ------------- | ----------- | -------- | -------- | -------------- |
| 旋回 (Rotate) | 1520        | 620      | 2400     | 12             |
| 肩 (Shoulder) | 1540        | 920      | 2020     | 9              |
| 肘 (Elbow)    | 1490        | 820      | 2020     | 9              |
| 手首 (Hand)   | 1600        | 750      | 2450     | 36             |

- **初期値**: 起動時およびリセット（B ボタン）時の角度
- **min / max**: ソフトウェアリミット
- **速度**: 20ms ごとの最大移動量（大きいほど速く動く）

### 制御パラメータ

#### HID Notify 1回ごとの最大 Duty 変化量

ゲームパッドの入力 1 回あたりの目標角度変化量。大きいほど操作に対して素早く動く。

```python
DUTY_STEP = [10, 6, 7, 30]  # [Rotate, Shoulder, Elbow, Hand]（単位: us）
```

> **サーボ設定の速度との違い**: `速度 [us/20ms]` はサーボが目標角度に追従する物理的な速さ、`DUTY_STEP` は操作入力に対して目標角度がどれだけ変化するかを表す。  
> `DUTY_STEP` をサーボ設定の `速度` に対して大きくし過ぎると追従遅れが発生し、スティックを離しても目標角度に到達するまでサーボが動き続けるので注意。

#### 不感帯

```python
CMD_THRESH = 0.375  # スティックの遊び（0.0〜1.0）
```

スティック中立付近のノイズで誤動作する場合は値を大きくする。

---

## 参考

ゲームパッドでRaspberry Pi PicoWを操作する部分は、以下の動画を参考にさせていただきました。

[#22 ゲームパッドでRaspberry Pi PicoWを操作しよう～DHAの電子工作教室～【Raspberry Pi PicoW】](https://www.youtube.com/watch?v=WHLCnej2iQo)

---

## ライセンス

[MIT License](LICENSE)
