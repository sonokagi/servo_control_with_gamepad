# Bluetooth ゲームパッド → Raspberry Pi Pico W → 4ch サーボ制御 プランニング

## 0. 開発フェーズ計画

| フェーズ    | 内容                              | 完了条件                                   | 状態      |
| ----------- | --------------------------------- | ------------------------------------------ | --------- |
| **Phase 0** | 開発環境セットアップ・Pico W 準備 | Thonny で Hello World が動く               | ✅ 完了   |
| **Phase 1** | サンプルコード参照                | サンプルをダウンロードして内容を理解       | ✅ 完了   |
| **Phase 2** | BLE スキャン・デバイス確認        | COWBOX T-12 が Pico W から検出できる       | ✅ 完了   |
| **Phase 3** | HID レポート実機確認              | 各軸・ボタンのバイト位置が実機で確認できる | 🔲 未着手 |
| **Phase 4** | servo.py 作成                     | サーボが単体で動作確認できる               | 🔲 未着手 |
| **Phase 5** | main.py 作成（BLE + サーボ統合）  | ゲームパッドでサーボが動く                 | 🔲 未着手 |
| **Phase 6** | 調整・最終確認                    | 全機能が仕様通りに動作する                 | 🔲 未着手 |

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

| 項目                   | 値                    |
| ---------------------- | --------------------- |
| BLE アドバタイジング名 | `ZM T-12`             |
| MAC アドレス           | `03:12:08:20:34:12`   |
| アドレスタイプ         | `0`                   |
| RSSI                   | `-48 dBm`             |

> ※ デバイス名は "COWBOX T-12" ではなく **"ZM T-12"** として認識された。

**仕様疑問点 #4・#5 を解消。**

---

### Phase 3: HID レポート実機確認

`blegamepad.py` の `_IRQ_GATTC_NOTIFY` に生バイト表示を追加して実機確認する。

```python
# 確認用コードを _IRQ_GATTC_NOTIFY の先頭に追加
print([hex(b) for b in notify_data])
```

サンプルから推定した構造（Phase 1 参照）を実機で検証し、以下を確定する：

1. 各スティック（LX/LY/RY）のバイト位置と値範囲
2. L / R / B ボタンのビット位置
3. スティック中立時の値（128 か否か）

**確認後、仕様疑問点 #1〜#3 を解消し、本ドキュメントの「5. スティック → サーボ軸マッピング」を実測値で更新する。**

---

### Phase 4: servo.py 作成

`reference/multi_servo.py` から `Servo` / `ToggleLed` クラスをそのまま `servo.py` として切り出す。

**動作確認**:

- Thonny シェルから `servo.py` をインポートして、サーボが指定の角度に動くことを確認

---

### Phase 5: main.py 作成（BLE + サーボ統合）

Phase 2〜4 の結果を踏まえて `main.py` を実装する。  
詳細は「4. 実装方針」「5. スティック → サーボ軸マッピング」を参照。

**実装順序（推奨）**:

1. BLE 接続・切断のみ（サーボなし）で動作確認
2. HID レポートの受信・解析を追加
3. サーボ制御を追加
4. ボタン処理（L/R/B）を追加
5. LED 表示・再接続ロジックを追加

---

### Phase 6: 調整・最終確認

「8. 検証ステップ」に従って全機能を確認し、以下を調整する：

- 不感帯閾値 `CMD_THRESH`（仕様疑問点 #8）
- サーボ速度パラメータ `speed_us`（仕様疑問点 #9）
- BLE 切断時の挙動（仕様疑問点 #6）
- LED パターン（仕様疑問点 #7）

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

## 5. スティック → サーボ軸マッピング（旧実装から継承）

| 操作                   | HID バイト位置（推定・要実機確認） | サーボ          | 方向                |
| ---------------------- | ---------------------------------- | --------------- | ------------------- |
| 左スティック 左右 (LX) | Byte 0（中央=128）                 | Rotate (GP14)   | 反転（左 → 正方向） |
| 左スティック 上下 (LY) | Byte 1（中央=128）                 | Elbow (GP17)    | 正                  |
| 右スティック 上下 (RY) | Byte 3（中央=128）                 | Shoulder (GP15) | 正                  |
| L ボタン               | Byte 5 bit6                        | Hand (GP16)     | 閉じる方向          |
| R ボタン               | Byte 5 bit7                        | Hand (GP16)     | 開く方向            |
| B ボタン               | Byte 5 bit1                        | 全サーボ        | 初期位置にリセット  |

> バイト位置・ビット位置は `reference/sample/blegamepad.py` の解析値。Phase 3 で実機確認する。

---

## 6. HID レポート構造（サンプルコードより）

COWBOX T-12 は BLE 4.0 HID (HOGP: HID over GATT Profile) を使用。  
`reference/sample/blegamepad.py` の Notify ハンドラより以下の構造が推定される（Phase 3 で実機確認要）。

```text
Byte 0 : LX axis  (0〜255, 中央=128) → 正規化: byte - 128
Byte 1 : LY axis  (0〜255, 中央=128)
Byte 2 : RX axis  (0〜255, 中央=128)
Byte 3 : RY axis  (0〜255, 中央=128)
Byte 4 : D-pad
Byte 5 : ボタン下位 byte
            bit0(0x01) = A
            bit1(0x02) = B
            bit3(0x08) = X
            bit4(0x10) = Y
            bit6(0x40) = L
            bit7(0x80) = R
Byte 6 : ボタン上位 byte
            bit0(0x01) = LT
            bit1(0x02) = RT
            bit2(0x04) = START
            bit3(0x08) = SELECT
            bit5(0x20) = LB
            bit6(0x40) = RB
```

### スティック値の正規化

```python
# 0〜255 (unsigned), 中央=128
raw = state[0]              # 0〜255
normalized = (raw - 128) / 128.0   # -1.0 〜 +1.0 (近似)
```

---

## 7. 仕様疑問点リスト

### 【要実機確認】技術仕様

| #   | 疑問点                                                       | 状態                              | 確認方法                     |
| --- | ------------------------------------------------------------ | --------------------------------- | ---------------------------- |
| 1   | COWBOX T-12 の HID レポート構造（各バイトが何の軸/ボタンか） | サンプルより推定済み → 実機確認要 | Phase 3 でデバッグ print     |
| 2   | スティック値の範囲                                           | 0〜255 (中央=128) と推定          | Phase 3 で確認               |
| 3   | L / R / B ボタンのビット位置                                 | サンプルより推定済み → 実機確認要 | Phase 3 で確認               |
| 4   | BLE サービス UUID / Input Report Characteristic UUID         | ✅ 接続後に自動列挙（blegamepad.py が処理） | -                       |
| 5   | Pico W から見たデバイス名（BLE アドバタイジング名）          | ✅ **ZM T-12**（addr=03:12:08:20:34:12, type=0） | -                |

### 【設計判断が必要】機能仕様

| #   | 疑問点                       | 候補                                                                    |
| --- | ---------------------------- | ----------------------------------------------------------------------- |
| 6   | BLE 切断時のサーボ挙動       | A) 最終位置をホールド（安全） / B) 初期位置に戻す                       |
| 7   | 接続待機中の LED パターン    | A) 高速点滅（スキャン中） / B) 低速点滅（接続中） / C) 点灯（接続済み） |
| 8   | 不感帯閾値 CMD_THRESH の調整 | 旧実装の 0.375 を引き継ぐか、BLE レートに合わせて調整するか             |
| 9   | サーボ速度パラメータの調整   | 旧実装の speed_us 値を引き継ぐか（BLE 更新頻度が異なる場合は要調整）    |
| 10  | 自動再接続の要否             | 切断後に自動でスキャン再開するか、手動リセットが必要か                  |

### 【将来検討】

| #   | 項目                                                   |
| --- | ------------------------------------------------------ |
| 11  | 複数ゲームパッドへの対応（現時点では不要と想定）       |
| 12  | サーボ角度のセーブ / ロード（電源 OFF 後も姿勢を記憶） |

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
