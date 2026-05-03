# Bluetooth ゲームパッド → Raspberry Pi Pico W → 4ch サーボ制御 プランニング

## 0. 開発フェーズ計画

現時点では開発環境・Pico W の準備がゼロの状態からスタートする。以下の順番で進める。

| フェーズ    | 内容                              | 完了条件                                            |
| ----------- | --------------------------------- | --------------------------------------------------- |
| **Phase 0** | 開発環境セットアップ・Pico W 準備 | Thonny で Hello World が動く                        |
| **Phase 1** | サンプルコード参照                | Google Drive のサンプルをダウンロードして内容を理解 |
| **Phase 2** | BLE スキャン・デバイス確認        | COWBOX T-12 が Pico W から検出できる                |
| **Phase 3** | HID レポート解析                  | 各軸・ボタンのバイト位置が特定できる                |
| **Phase 4** | servo.py 作成                     | サーボが単体で動作確認できる                        |
| **Phase 5** | main.py 作成（BLE + サーボ統合）  | ゲームパッドでサーボが動く                          |
| **Phase 6** | 調整・最終確認                    | 全機能が仕様通りに動作する                          |

---

### Phase 0: 開発環境セットアップ・Pico W 準備

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

Thonny のシェルで以下を実行（Pico W が Wi-Fi に接続できる環境が必要）:

```python
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("SSID", "PASSWORD")  # 自宅 Wi-Fi に接続

import mip
mip.install("aioble")
```

Wi-Fi が使えない場合は PC 経由でインストール：

```bash
# PC の Python 環境で mpremote を使用
pip install mpremote
mpremote mip install aioble
```

#### 0-4. 動作確認

Thonny のシェルで確認:

```python
import aioble
print("aioble OK")
from machine import Pin, PWM
print("machine OK")
```

---

### Phase 1: サンプルコード参照

参照動画の作者（DHA の電子工作教室）が Google Drive でサンプルコードを公開している。

**Google Drive フォルダ**: [#22\_ゲームコントローラ](https://drive.google.com/drive/folders/1h_aNwIv26q8gpyyus-07lHX0YHY2T57M)

| ファイル名      | サイズ    | 内容                                               |
| --------------- | --------- | -------------------------------------------------- |
| `blegamepad.py` | 11 KB     | BLE ゲームパッド接続・HID レポート解析のメイン実装 |
| `bletest.py`    | 523 bytes | BLE スキャン・デバイス確認用の簡易スクリプト       |
| `pico_pong.py`  | 8 KB      | サンプルアプリ（参考）                             |
| `ssd1306.py`    | 5 KB      | OLED ドライバ（今回は不要）                        |

**作業**:

1. 上記フォルダから `blegamepad.py` と `bletest.py` をダウンロード
2. コードを読んで BLE 接続方法・HID レポートの解析方法を把握する
3. `bletest.py` を Pico W に書き込んで COWBOX T-12 が検出できるか確認 → Phase 2 へ

---

### Phase 2: BLE スキャン・デバイス確認

`bletest.py`（またはサンプルを参考に作成するスキャンスクリプト）を Pico W で実行し、以下を確認・記録する：

- COWBOX T-12 の BLE アドバタイジング名（デバイス名）
- BLE アドレス
- HID サービスの UUID

**確認後、仕様疑問点 4・5 を解消する。**

---

### Phase 3: HID レポート解析

接続後に生の HID Input Report を print するデバッグスクリプトを実行する。

```python
# 動作確認用 疑似コード
# HID Notify 受信時に生バイトを表示
def on_notify(data):
    print([hex(b) for b in data])
```

各操作を行い、変化するバイト位置を特定する：

1. 左スティック 左右 → LX 軸のバイト位置と範囲
2. 左スティック 上下 → LY 軸
3. 右スティック 上下 → RY 軸
4. L ボタン / R ボタン / B ボタン → ボタンバイトのビット位置

**確認後、仕様疑問点 1〜3 を解消する。** → `docs/plan.md` の「HID レポート解析方針」を実測値で更新する。

---

### Phase 4: servo.py 作成

`reference/multi_servo.py` から `Servo` / `ToggleLed` クラスを `servo.py` として独立させる。

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

- 不感帯閾値 `CMD_THRESH`（仕様疑問点 8）
- サーボ速度パラメータ `speed_us`（仕様疑問点 9）
- BLE 切断時の挙動（仕様疑問点 6）
- LED パターン（仕様疑問点 7）

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

| ライブラリ      | 用途                                          |
| --------------- | --------------------------------------------- |
| `aioble`        | BLE Central として GATT 接続・HID Notify 受信 |
| `asyncio`       | 非同期メインループ（aioble が前提）           |
| `machine.PWM`   | サーボの PWM 出力 (50Hz)                      |
| `machine.Timer` | 20ms 周期のサーボ更新割り込み                 |
| `machine.Pin`   | GPIO / LED 制御                               |

### aioble のインストール

Thonny の「パッケージを管理」または `upip` でインストール：

```python
import mip
mip.install("aioble")
```

---

## 4. 実装方針

### ファイル構成（新規作成）

```text
c:\User\claude\firststep\
├── main.py       # BLE 接続 + サーボ制御のメインループ
├── servo.py      # Servo / ToggleLed クラス
└── docs\
    └── plan.md   # 本ドキュメント
```

### 処理フロー

```text
起動
 └─ Timer 初期化 (20ms 周期でサーボ update)
 └─ asyncio.run(main())
      └─ BLE スキャン開始
           └─ COWBOX T-12 を発見 (名前 or UUID でフィルタ)
                └─ BLE 接続
                     └─ HID サービスの Input Report Characteristic を取得
                          └─ Notify を有効化
                               └─ ループ:
                                    - HID レポートを受信
                                    - スティック値 / ボタン値を解析
                                    - 不感帯処理 (CMD_THRESH)
                                    - Servo.set_duty() を呼び出し
                               └─ 切断検知 → 再スキャンへ戻る
```

### 既存コードの再利用

| 旧コード                                   | 再利用箇所                                    | 新ファイル |
| ------------------------------------------ | --------------------------------------------- | ---------- |
| `multi_servo.py` の `Servo` クラス         | そのまま流用                                  | `servo.py` |
| `multi_servo.py` の `ToggleLed` クラス     | そのまま流用                                  | `servo.py` |
| `multi_servo.py` のサーボパラメータ        | ピン/初期値/min/max/speed をそのまま継承      | `main.py`  |
| Processing の `manualOperation()` ロジック | スティック → Duty 変換を MicroPython で再実装 | `main.py`  |
| Processing の `CMD_THRESH = 0.375`         | 不感帯閾値をそのまま適用                      | `main.py`  |
| Processing の `initServo()`                | B ボタンで初期位置に戻す処理                  | `main.py`  |

---

## 5. スティック → サーボ軸マッピング（旧実装から継承）

| 操作                   | 軸 / ボタン    | サーボ          | 方向                |
| ---------------------- | -------------- | --------------- | ------------------- |
| 左スティック 左右 (LX) | BLE HID axis   | Rotate (GP14)   | 反転（左 → 正方向） |
| 右スティック 上下 (RY) | BLE HID axis   | Shoulder (GP15) | 正                  |
| 左スティック 上下 (LY) | BLE HID axis   | Elbow (GP17)    | 正                  |
| L ボタン               | BLE HID button | Hand (GP16)     | 閉じる方向          |
| R ボタン               | BLE HID button | Hand (GP16)     | 開く方向            |
| B ボタン               | BLE HID button | 全サーボ        | 初期位置にリセット  |

> **注意**: BLE HID レポートの実際のバイト位置は「仕様疑問点 1〜3」で確認が必要。  
> 最初にレポートを生のまま print するデバッグスクリプトを実行して確認する。

---

## 6. HID レポート解析方針

COWBOX T-12 は BLE 4.0 HID (HOGP: HID over GATT Profile) を使用。  
HID Input Report の構造はメーカー仕様 / 実測で確認が必要。

### 一般的な BLE ゲームパッドのレポート形式（要実測確認）

```text
Byte 0    : LX axis  (0x00〜0xFF, 中央 0x7F)
Byte 1    : LY axis
Byte 2    : RX axis
Byte 3    : RY axis
Byte 4    : ボタン下位 8bit
Byte 5    : ボタン上位 8bit
...
```

### スティック値の正規化

```python
# HID レポートが 0〜255 (unsigned) の場合
raw = byte_value          # 0〜255
normalized = (raw - 128) / 128.0  # -1.0 〜 +1.0 (近似)

# HID レポートが signed (-128〜127) の場合
raw = ctypes.c_int8(byte_value).value
normalized = raw / 128.0
```

---

## 7. 仕様疑問点リスト

### 【要実測確認】技術仕様

| #   | 疑問点                                                       | 確認方法                                                |
| --- | ------------------------------------------------------------ | ------------------------------------------------------- |
| 1   | COWBOX T-12 の HID レポート構造（各バイトが何の軸/ボタンか） | デバッグスクリプトで生レポートを print して各操作を試す |
| 2   | スティック値の範囲（0〜255 か、-128〜127 か）                | 同上                                                    |
| 3   | L / R / B ボタンのビット位置（何バイト目の何ビットか）       | 同上                                                    |
| 4   | BLE サービス UUID / Input Report Characteristic UUID         | `aioble` でスキャン時に GATT を列挙して確認             |
| 5   | Pico W から見たデバイス名（BLE アドバタイジング名）          | スキャン時に `device.name` を print して確認            |

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
   - デバイス名と UUID をメモしておく

2. **HID レポートのデバッグ確認**
   - 接続後、HID Notify を受信して生バイト列を print
   - 各スティック / ボタン操作を行い、変化するバイト位置を特定
   - 疑問点 1〜3 を解消する

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
