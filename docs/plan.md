# Bluetooth ゲームパッド → Raspberry Pi Pico W → 4ch サーボ制御 プランニング

## 0. 開発フェーズ計画

| フェーズ    | 内容                              | 完了条件                                   | 状態      |
| ----------- | --------------------------------- | ------------------------------------------ | --------- |
| **Phase 0** | 開発環境セットアップ・Pico W 準備 | Thonny で Hello World が動く               | ✅ 完了   |
| **Phase 1** | サンプルコード参照                | サンプルをダウンロードして内容を理解       | ✅ 完了   |
| **Phase 2** | BLE スキャン・デバイス確認        | COWBOX T-12 が Pico W から検出できる       | ✅ 完了   |
| **Phase 3** | HID レポート実機確認              | 各軸・ボタンのバイト位置が実機で確認できる | ✅ 完了   |
| **Phase 4** | servo.py 作成                     | サーボが単体で動作確認できる               | ✅ 完了   |
| **Phase 5** | main.py 作成（BLE + サーボ統合）  | ゲームパッドでサーボが動く                 | ✅ 完了   |
| **Phase 6** | 調整・最終確認                    | 全機能が仕様通りに動作する                 | ✅ 完了   |
| **Phase 7** | GitHub 公開準備                   | リポジトリが公開できる状態になる           | 🔲 未着手 |

---

### Phase 0: 開発環境セットアップ・Pico W 準備 ✅

#### 0-1. Thonny IDE のインストール（PC 側）

1. [https://thonny.org/](https://thonny.org/) から最新版をダウンロード・インストール
2. 起動して「ツール → オプション → インタープリタ」で **MicroPython (Raspberry Pi Pico)** を選択

#### 0-2. Pico W に MicroPython ファームウェアを書き込む

1. [https://micropython.org/download/RPI_PICO_W/](https://micropython.org/download/RPI_PICO_W/) から **最新の .uf2 ファイル**をダウンロード
   - Bluetooth 対応には **v1.20.0 以降**が必要（v1.23.x 推奨）
2. Pico W の BOOTSEL ボタンを押しながら USB 接続 → ドライブとして認識される
3. ダウンロードした `.uf2` ファイルをドライブにコピー → 自動的に再起動
4. Thonny でシリアル接続を確認（右下に "MicroPython (Raspberry Pi Pico W)" と表示）

#### 0-3. aioble ライブラリのインストール（Pico W 側）

Wi-Fi 経由でインストール済み（実機確認済み）:

```python
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("SSID", "PASSWORD")  # 自宅 Wi-Fi に接続

import mip
mip.install("aioble")
```

> **注意**: 実装では raw `bluetooth` モジュールを使うため aioble は不使用。  
> ただし Phase 2 以降で必要になった場合のために、インストール済みのまま残す。

#### 0-4. 動作確認

Thonny のシェルで確認済み:

```python
import aioble       # OK
from machine import Pin, PWM  # OK
```

---

### Phase 1: サンプルコード参照 ✅

**出典**: DHA の電子工作教室  
**参照動画**: [Pico W で Bluetooth ゲームパッドを接続する](https://www.youtube.com/watch?v=WHLCnej2iQo)  
**Google Drive フォルダ**: [#22\_ゲームコントローラ](https://drive.google.com/drive/folders/1h_aNwIv26q8gpyyus-07lHX0YHY2T57M)

サンプルを `/reference/sample/` 以下にコピー済み。

| ファイル名      | 内容                                               |
| --------------- | -------------------------------------------------- |
| `blegamepad.py` | BLE ゲームパッド接続・HID レポート解析のメイン実装 |
| `bletest.py`    | BLE スキャン・接続・軸値表示の簡易スクリプト       |
| `pico_pong.py`  | サンプルアプリ（参考）                             |
| `ssd1306.py`    | OLED ドライバ（今回は不要）                        |

#### サンプル解析結果

**BLE ライブラリ**: `aioble` ではなく MicroPython 標準の **`bluetooth` モジュール（IRQ コールバック方式）** を使用。  
→ 実装方針を `aioble + asyncio` から **raw `bluetooth` + Timer 割り込み**に変更する。

**HID レポート構造**: `blegamepad.py` の `_IRQ_GATTC_NOTIFY` ハンドラから判明（→ Phase 3 で実機確認）:

```text
Byte 0 : LX axis  (0〜255, 中央=128)
Byte 1 : LY axis  (0〜255, 中央=128)
Byte 2 : RX axis  (0〜255, 中央=128)
Byte 3 : RY axis  (0〜255, 中央=128)
Byte 4 : D-pad
Byte 5 : ボタン下位 byte
           bit0 = A, bit1 = B, bit3 = X, bit4 = Y
           bit6 = L,  bit7 = R
Byte 6 : ボタン上位 byte
           bit0 = LT, bit1 = RT, bit2 = START, bit3 = SELECT
           bit5 = LB, bit6 = RB
```

スティック値の正規化: `state[x] - 128` → -128〜+127 の signed 値として扱う。

**`bletest.py` の注意点**: コードの先頭に LED の無限ループ (`while True:`) があり、そのままでは BLE 処理に到達しない。  
→ LED 無限ループを削除または `for` ループに修正してから使う。

---

### Phase 2: BLE スキャン・デバイス確認 ✅

COWBOX T-12 のペアリングモードへの移行: **X ボタン + HOME ボタンを長押し**

`scan.py` を Pico W で実行（使い方・出力例・トラブルシュートは `scan.py` 冒頭コメント参照）。

確認済みデバイス情報：

| 項目                   | 値                  |
| ---------------------- | ------------------- |
| BLE アドバタイジング名 | `ZM T-12`           |
| MAC アドレス           | `03:12:08:20:34:12` |
| アドレスタイプ         | `0`                 |
| RSSI                   | `-48 dBm`           |

> ※ デバイス名は "COWBOX T-12" ではなく **"ZM T-12"** として認識された。

**仕様疑問点 #4・#5 を解消。**

---

### Phase 3: HID レポート実機確認 ✅

`hid_debug.py` を実行して実機確認済み（使い方・確認手順は `hid_debug.py` 冒頭コメント参照）。

**確認結果（実測値）:**

| 操作             | Byte | 実測値                   | 解釈        |
| ---------------- | ---- | ------------------------ | ----------- |
| 左スティック 左  | 0    | 0 (LX = -128)            | ✅ 想定通り |
| 左スティック 右  | 0    | 255 (LX = +127)          | ✅ 想定通り |
| 左スティック 上  | 1    | 0 (LY = -128)            | ✅ 想定通り |
| 左スティック 下  | 1    | 255 (LY = +127)          | ✅ 想定通り |
| 右スティック 上  | 3    | 0 (RY = -128)            | ✅ 想定通り |
| 右スティック 下  | 3    | 255 (RY = +127)          | ✅ 想定通り |
| 各スティック中立 | 0〜3 | 128 (signed = 0)         | ✅ 想定通り |
| L ボタン         | 5    | 64 = 0x40 = bit6 → L=1   | ✅ 想定通り |
| R ボタン         | 5    | 128 = 0x80 = bit7 → R=1  | ✅ 想定通り |
| B ボタン         | 5    | 2 = 0x02 = bit1 → B=1    | ✅ 想定通り |
| D-pad 未操作     | 4    | 255 = 0xFF（全ビット 1） | 📝 新規発見 |

> Byte 4（D-pad）は未操作時に `0xFF`。方向キー押下で対応ビットが 0 になる反転論理。今回の実装では D-pad は使用しないため影響なし。

**仕様疑問点 #1〜#3 を解消。**

---

### Phase 4: servo.py 作成 ✅

`reference/multi_servo.py` の `Servo` / `ToggleLed` クラスを `servo.py` として切り出す。

`reference/multi_servo.py` からの主な変更点:

- `set_duty()` のリミット処理を `max()/min()` で 1 行に簡略化
- `reset()` メソッドを追加（B ボタンで初期位置に即時戻す用）
- `initial_us` 属性を追加（`reset()` の参照用）
- `ToggleLed` に `on()` / `off()` を追加（接続状態表示用）
- メインループ・`is_int()` など、`main.py` に属するコードは含めない

`servo_test.py` で全サーボの動作確認済み（使い方は `servo_test.py` 冒頭コメント参照）：

| サーボ        | ピン | 動作 | IO 割り当て |
| ------------- | ---- | ---- | ----------- |
| 旋回 (Rotate) | GP14 | ✅   | ✅ 確認済み |
| 肩 (Shoulder) | GP15 | ✅   | ✅ 確認済み |
| 肘 (Elbow)    | GP17 | ✅   | ✅ 確認済み |
| 手首 (Hand)   | GP16 | ✅   | ✅ 確認済み |

---

### Phase 5: main.py 作成（BLE + サーボ統合） ✅

`blegamepad.py` は別ファイル化せず `main.py` 1ファイルに集約（MAC アドレス・HID 構造が確定しているため）。

**確認済み動作**:

| 項目                     | 結果        |
| ------------------------ | ----------- |
| 左スティック LX → 旋回   | ✅ 確認済み |
| 左スティック LY → 肘     | ✅ 確認済み |
| 右スティック RY → 肩     | ✅ 確認済み |
| L ボタン → 手首 左回転   | ✅ 確認済み |
| R ボタン → 手首 右回転   | ✅ 確認済み |
| B ボタン → 全軸リセット  | ✅ 確認済み |
| LED 高速点滅（接続待ち） | ✅ 確認済み |
| LED 点灯（接続済み）     | ✅ 確認済み |

**実装内容**:

- BLE: `gap_connect` で直接接続（Phase 2 で確認済みアドレス使用）
- 切断時: 自動再接続（1秒待機後に `gap_connect` 再試行）
- 制御アルゴリズム: 旧実装 `manualOperation()` と同ロジック
  - 不感帯 `CMD_THRESH = 0.375`、`SCALE` は削除（詳細は「6節 スティック値の正規化」参照）
  - `DUTY_STEP = [10, 6, 7, 30]` は旧実装の `DUTY_CHANGE_PAR_FRAME` から継承（Phase 6 で調整）
- 切断時のサーボ: 最終位置をホールド
- LED: 接続待ち=高速点滅、接続済み=点灯

---

### Phase 6: 調整・最終確認 ✅

仕様疑問点 #6〜#10 をすべて解消。各パラメータは現行実装で確定（詳細は「7. 仕様疑問点リスト」参照）。

---

### Phase 7: GitHub 公開準備

#### 7-1. 開発用スクリプトの整理 ✅

`scan.py` / `hid_debug.py` / `servo_test.py` は本番動作には不要な開発・デバッグ用スクリプト。  
`tools/` フォルダを作成して移動し、本番ファイル（`main.py` / `servo.py`）との区別を明確にする。

```text
servo_control_with_gamepad/
├── main.py        # 本番: BLE + サーボ制御
├── servo.py       # 本番: Servo / ToggleLed クラス
└── tools/
    ├── scan.py        # 開発用: BLE スキャン確認
    ├── hid_debug.py   # 開発用: HID レポート確認・Notify レート計測
    └── servo_test.py  # 開発用: サーボ単体動作確認
```

#### 7-2. README.md の作成

GitHub のトップページに表示される公開向けドキュメント。  
CLAUDE.md / plan.md との役割分担:

| ファイル     | 対象読者         | 内容                                         |
| ------------ | ---------------- | -------------------------------------------- |
| `README.md`  | GitHub 閲覧者    | 概要・ハードウェア構成・セットアップ・使い方・ライセンス |
| `CLAUDE.md`  | Claude Code (AI) | 技術詳細・HID 構造・サーボパラメータ・開発ルール |
| `docs/plan.md` | 開発者（自身） | 開発ログ・フェーズ記録・疑問点解消履歴       |

README.md に記載する内容:

1. プロジェクト概要（構成図）
2. ハードウェア要件（機器リスト・サーボ配線）
3. セットアップ手順（MicroPython 書き込み・ファイル転送）
4. 操作方法（スティック・ボタン割り当て）
5. ライセンス

#### 7-3. 重複情報の整理

README.md 作成にあわせて、CLAUDE.md / plan.md の重複を以下の方針で整理する:

- **サーボパラメータ表**: README.md をメインに。CLAUDE.md はクイックリファレンスとして残す
- **スティック → サーボ マッピング**: README.md（操作説明）と CLAUDE.md（技術参照）の両方に置く
- **HID レポート構造**: CLAUDE.md と plan.md に残す。README.md には記載しない（実装詳細のため）
- **フェーズ履歴**: plan.md のみ。README.md / CLAUDE.md には不要

---

## 1. 背景・目的

### 旧構成（参照実装）

```text
COWBOX T-12 以外のゲームパッド
    → PC (Processing3 + GameControlPlus)
        → USB シリアル (115200bps)
            → Raspberry Pi Pico (MicroPython)
                → 4ch サーボ (PWM)
```

### 新構成（今回の目標）

```text
COWBOX T-12 (BLE Peripheral / HID)
    ↕ Bluetooth 4.0 BLE
Raspberry Pi Pico W (BLE Central)
    → 4ch サーボ (PWM)
```

PC を排除し、COWBOX Android Controller T-12 と Raspberry Pi Pico W を直接 BLE で接続する。  
Pico W 側の制御プログラムは MicroPython のみで実装する。

---

## 2. システム構成

### ハードウェア

| 機器                | 役割                             |
| ------------------- | -------------------------------- |
| COWBOX T-12         | BLE ゲームパッド (Bluetooth 4.0) |
| Raspberry Pi Pico W | BLE Central + サーボ制御         |
| サーボ × 4          | ロボットアームの各関節           |

### サーボ接続ピン（旧実装から継承）

| サーボ        | ピン | 初期値 [us] | min [us] | max [us] | speed [us/20ms] |
| ------------- | ---- | ----------- | -------- | -------- | --------------- |
| 旋回 (Rotate) | GP14 | 1520        | 620      | 2400     | 12              |
| 肩 (Shoulder) | GP15 | 1540        | 920      | 2020     | 9               |
| 肘 (Elbow)    | GP17 | 1490        | 820      | 2020     | 9               |
| 手首 (Hand)   | GP16 | 1600        | 750      | 2450     | 36              |

### LED ピン

| 用途         | ピン |
| ------------ | ---- |
| 状態表示 LED | GP18 |

---

## 3. 使用技術・ライブラリ

| ライブラリ      | 用途                                                      |
| --------------- | --------------------------------------------------------- |
| `bluetooth`     | BLE Central として GATT 接続・HID Notify 受信（IRQ 方式） |
| `machine.PWM`   | サーボの PWM 出力 (50Hz)                                  |
| `machine.Timer` | 20ms 周期のサーボ更新割り込み                             |
| `machine.Pin`   | GPIO / LED 制御                                           |

> **方針変更**: 当初 `aioble + asyncio` を予定していたが、サンプルコード (`blegamepad.py`) が  
> raw `bluetooth` モジュールの IRQ コールバック方式を採用しており、`machine.Timer` による  
> サーボ更新とも相性が良いため、サンプルの方式を踏襲する。

---

## 4. 実装方針

### ファイル構成（新規作成）

```text
servo_control_with_gamepad/
├── main.py        # BLE 接続 + サーボ制御のメインループ
├── servo.py       # Servo / ToggleLed クラス
├── blegamepad.py  # BLE ゲームパッドクラス（サンプルを改変）
├── docs/
│   └── plan.md
└── reference/
    ├── multi_servo.py
    ├── serial_servo_control_from_gamepad.pde
    └── sample/    # 参照用サンプル（変更しない）
```

### 処理フロー

```text
起動
 └─ Timer 初期化 (20ms 周期でサーボ update)
 └─ BLE 初期化・IRQ 登録
 └─ スキャン開始（LED 高速点滅）
      └─ COWBOX T-12 を発見
           └─ BLE 接続（LED 低速点滅）
                └─ GATT サービス探索・HID Input Characteristic 取得
                     └─ Notify 有効化（LED 点灯）
                          └─ IRQ ループ:
                               - HID Notify 受信 → スティック/ボタン値を解析
                               - 不感帯処理 (CMD_THRESH)
                               - Servo.set_duty() 呼び出し
                          └─ 切断検知 → 再スキャンへ戻る（LED 高速点滅）
```

### 既存コードの再利用

| 旧コード                                   | 再利用箇所                                    | 新ファイル      |
| ------------------------------------------ | --------------------------------------------- | --------------- |
| `multi_servo.py` の `Servo` クラス         | そのまま流用                                  | `servo.py`      |
| `multi_servo.py` の `ToggleLed` クラス     | そのまま流用                                  | `servo.py`      |
| `multi_servo.py` のサーボパラメータ        | ピン/初期値/min/max/speed をそのまま継承      | `main.py`       |
| `sample/blegamepad.py` の `gamepad` クラス | 接続・Notify 受信部分を流用・改変             | `blegamepad.py` |
| Processing の `manualOperation()` ロジック | スティック → Duty 変換を MicroPython で再実装 | `main.py`       |
| Processing の `CMD_THRESH = 0.375`         | 不感帯閾値をそのまま適用                      | `main.py`       |
| Processing の `initServo()`                | B ボタンで初期位置に戻す処理                  | `main.py`       |

---

## 5. スティック → サーボ軸マッピング（実機確認済み）

| 操作                   | HID バイト位置（実機確認済み） | サーボ          | 方向                |
| ---------------------- | ------------------------------ | --------------- | ------------------- |
| 左スティック 左右 (LX) | Byte 0（中立=128）             | Rotate (GP14)   | 反転（左 → 正方向） |
| 左スティック 上下 (LY) | Byte 1（中立=128）             | Elbow (GP17)    | 正                  |
| 右スティック 上下 (RY) | Byte 3（中立=128）             | Shoulder (GP15) | 正                  |
| L ボタン               | Byte 5 bit6 (0x40)             | Hand (GP16)     | 閉じる方向          |
| R ボタン               | Byte 5 bit7 (0x80)             | Hand (GP16)     | 開く方向            |
| B ボタン               | Byte 5 bit1 (0x02)             | 全サーボ        | 初期位置にリセット  |

---

## 6. HID レポート構造（実機確認済み）

COWBOX T-12 は BLE 4.0 HID (HOGP: HID over GATT Profile) を使用。  
Phase 3（`hid_debug.py`）にて実機確認済み。

```text
Byte 0 : LX axis  (0〜255, 中立=128) → 正規化: byte - 128
Byte 1 : LY axis  (0〜255, 中立=128)
Byte 2 : RX axis  (0〜255, 中立=128)  ※ 今回未使用
Byte 3 : RY axis  (0〜255, 中立=128)
Byte 4 : D-pad    (未操作=0xFF, 各方向で対応ビットが 0 になる反転論理)  ※ 今回未使用
Byte 5 : ボタン下位 byte
            bit1(0x02) = B  ← リセット
            bit6(0x40) = L  ← Hand 閉じる
            bit7(0x80) = R  ← Hand 開く
            (他ボタンは今回未使用)
Byte 6 : ボタン上位 byte  ※ 今回未使用
```

### スティック値の正規化

```python
# 0〜255 (unsigned), 中立=128
raw = state[0]                     # 0〜255
signed = raw - 128                 # -128〜+127
normalized = signed / 128.0        # -1.0〜+1.0 (近似)
```

Phase 3 実測で ZM T-12 のスティックは生値 0〜255 のフルレンジに到達することを確認（左端=0, 右端=255）。  
`normalized` の実測最大値は -1.0〜+0.992 であり、旧実装の `SCALE = 1.25`（スティック最大値 0.8 前提）のような補正は不要。

### HID Notify レート

Phase 6 実測（`hid_debug.py` 計測モード）による ZM T-12 の Notify 特性:

| 操作状態                     | Notify  | 平均間隔  | レート   |
| ---------------------------- | ------- | --------- | -------- |
| 何も触れない（アイドル）     | なし    | -         | 0 Hz     |
| スティック倒し続け / ボタン押し続け | あり | 約 32ms | 約 31 Hz |
| スティックを動かし続け       | あり    | 約 31ms   | 約 32 Hz |

**特性まとめ**: ZM T-12 は**イベント駆動型**。入力がある間だけ約 30Hz で Notify を送信し、入力がなくなると停止する。

旧実装（Processing 60fps）の半分のレートだが、`DUTY_STEP` は現行値のまま実機で違和感なし。  
参考: 旧 60fps 相当にするには `DUTY_STEP` を 2 倍にする必要があるが、今回は調整不要と判断。

---

## 7. 仕様疑問点リスト

### 【要実機確認】技術仕様

| #   | 疑問点                                                       | 状態                                             | 確認方法 |
| --- | ------------------------------------------------------------ | ------------------------------------------------ | -------- |
| 1   | COWBOX T-12 の HID レポート構造（各バイトが何の軸/ボタンか） | ✅ 実機確認済み（6節参照）                       | -        |
| 2   | スティック値の範囲                                           | ✅ 0〜255（中立=128）確認済み                    | -        |
| 3   | L / R / B ボタンのビット位置                                 | ✅ 実機確認済み（6節参照）                       | -        |
| 4   | BLE サービス UUID / Input Report Characteristic UUID         | ✅ 接続後に自動列挙（blegamepad.py が処理）      | -        |
| 5   | Pico W から見たデバイス名（BLE アドバタイジング名）          | ✅ **ZM T-12**（addr=03:12:08:20:34:12, type=0） | -        |

### 【設計判断が必要】機能仕様

| #   | 疑問点                       | 候補                                                                    |
| --- | ---------------------------- | ----------------------------------------------------------------------- |
| 6   | BLE 切断時のサーボ挙動       | ✅ 最終位置をホールド（安全側）                                          |
| 7   | 接続待機中の LED パターン    | ✅ 高速点滅（接続待ち）/ 点灯（接続済み）                               |
| 8   | 不感帯閾値 CMD_THRESH の調整 | ✅ 旧実装値 0.375 を継続使用（実機で違和感なし）                        |
| 9   | サーボ速度パラメータの調整   | ✅ 旧実装値を継続使用（約 30Hz で違和感なし。詳細は「6節 HID Notify レート」参照） |
| 10  | 自動再接続の要否             | ✅ 切断後 1 秒待機して自動再接続                                        |

---

## 8. 検証ステップ

1. **BLE スキャン確認**
   - Pico W でスキャンを実行し、COWBOX T-12 がリストに表示されることを確認
   - デバイス名と MAC アドレスをメモしておく
   - COWBOX T-12 ペアリングモード: **X + HOME ボタン長押し**

2. **HID レポートのデバッグ確認**
   - 接続後、HID Notify を受信して生バイト列を print
   - 各スティック / ボタン操作を行い、変化するバイト位置を特定
   - 疑問点 #1〜#3 を解消する

3. **軸マッピングの確認**
   - 各スティック操作で意図したサーボが動くことを確認

4. **ボタン動作の確認**
   - L/R ボタンで Hand サーボが開閉
   - B ボタンで全サーボが初期位置に戻る

5. **速度・リミット動作の確認**
   - 急激な指令に対してサーボが滑らかに追従すること
   - min/max 範囲でサーボが停止すること

6. **切断・再接続の確認**
   - BLE 切断後のサーボ挙動
   - 再接続後に正常動作すること

---

## 9. 参照ファイル

| ファイル                                          | 内容                                               |
| ------------------------------------------------- | -------------------------------------------------- |
| `reference/multi_servo.py`                        | 旧 Pico 側コード（Servo クラス・サーボパラメータ） |
| `reference/serial_servo_control_from_gamepad.pde` | 旧 PC 側コード（制御ロジック・軸マッピング）       |
| `reference/sample/blegamepad.py`                  | BLE ゲームパッドクラス（サンプル）                 |
| `reference/sample/bletest.py`                     | BLE スキャン・接続テスト（サンプル）               |
