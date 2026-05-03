# CLAUDE.md

## 絶対ルール

### git コミットは明示的な指示があるまで行わない

**ユーザーが「コミットしてください」と明示的に指示するまで、いかなる状況でも `git commit` を実行してはならない。**

- ファイルの編集・作成は自由に行ってよい
- `git add` も確認なしで実行してよい
- **`git commit` だけは必ず明示的な指示を待つこと**
- 「変更を保存した」「完了した」などの文脈でも、コミットを勝手に行ってはならない

---

## プロジェクト概要

COWBOX Android Controller T-12（BLE HID ゲームパッド）を Raspberry Pi Pico W に直接 BLE 接続し、4ch サーボ（ロボットアーム）を MicroPython で制御する。

```
COWBOX T-12 (BLE Peripheral / HID)
    ↕ Bluetooth 4.0 BLE
Raspberry Pi Pico W (BLE Central)
    → 4ch サーボ (PWM)
```

**旧構成との違い**: PC（Processing3）を介さず、Pico W と BLE ゲームパッドを直接接続する。

---

## ファイル構成

```
servo_control_with_gamepad/
├── CLAUDE.md                              # 本ファイル
├── .gitignore
├── .markdownlint.json
├── docs/
│   └── plan.md                            # 開発フェーズ計画・仕様・疑問点リスト
├── prompts/
│   └── 作成依頼.md                        # 依頼仕様書
└── reference/
    ├── multi_servo.py                     # 旧 Pico 用サーボ制御コード（流用元）
    ├── serial_servo_control_from_gamepad.pde  # 旧 PC 用制御コード（流用元）
    └── sample/                            # DHA の電子工作教室 公開サンプル（git 除外）
        ├── blegamepad.py                  # BLE ゲームパッドクラス
        ├── bletest.py                     # BLE スキャン・接続テスト
        ├── pico_pong.py                   # サンプルアプリ
        └── ssd1306.py                     # OLED ドライバ
```

### 今後作成するファイル（Phase 4〜5）

```
servo_control_with_gamepad/
├── main.py        # BLE 接続 + サーボ制御のメインループ
├── servo.py       # Servo / ToggleLed クラス（reference/multi_servo.py から切り出し）
└── blegamepad.py  # BLE ゲームパッドクラス（reference/sample/blegamepad.py を改変）
```

---

## 開発フェーズ

| フェーズ    | 内容                             | 状態    |
| ----------- | -------------------------------- | ------- |
| **Phase 0** | 開発環境・Thonny・MicroPython 準備 | ✅ 完了 |
| **Phase 1** | サンプルコード参照・解析         | ✅ 完了 |
| **Phase 2** | BLE スキャン・デバイス確認       | 未着手  |
| **Phase 3** | HID レポート実機確認             | 未着手  |
| **Phase 4** | servo.py 作成                    | 未着手  |
| **Phase 5** | main.py 作成（BLE + サーボ統合） | 未着手  |
| **Phase 6** | 調整・最終確認                   | 未着手  |

詳細は [docs/plan.md](docs/plan.md) を参照。

---

## 技術方針

### BLE ライブラリ

`aioble` ではなく MicroPython 標準の **`bluetooth` モジュール（IRQ コールバック方式）** を使用する。  
理由: サンプルコード (`reference/sample/blegamepad.py`) が同方式を採用しており、`machine.Timer` によるサーボ更新とも相性が良い。

### サーボ制御

`machine.Timer`（20ms 周期）の割り込みでサーボの `update()` を呼ぶ方式。  
`reference/multi_servo.py` の `Servo` / `ToggleLed` クラスをそのまま流用する。

### HID レポート構造（サンプルコードより推定・Phase 3 で実機確認要）

```
Byte 0 : LX axis  (0〜255, 中央=128)
Byte 1 : LY axis  (0〜255, 中央=128)
Byte 2 : RX axis  (0〜255, 中央=128)
Byte 3 : RY axis  (0〜255, 中央=128)
Byte 4 : D-pad
Byte 5 : ボタン下位 (L=bit6, R=bit7, B=bit1)
Byte 6 : ボタン上位
```

### スティック → サーボ マッピング

| 操作           | サーボ          | 備考          |
| -------------- | --------------- | ------------- |
| 左スティック LX | Rotate (GP14)   | 反転          |
| 左スティック LY | Elbow (GP17)    | 正            |
| 右スティック RY | Shoulder (GP15) | 正            |
| L ボタン       | Hand (GP16)     | 閉じる        |
| R ボタン       | Hand (GP16)     | 開く          |
| B ボタン       | 全サーボ        | 初期位置リセット |

### サーボパラメータ

| サーボ        | ピン | 初期値 [us] | min [us] | max [us] | speed [us/20ms] |
| ------------- | ---- | ----------- | -------- | -------- | --------------- |
| 旋回 (Rotate) | GP14 | 1520        | 620      | 2400     | 12              |
| 肩 (Shoulder) | GP15 | 1540        | 920      | 2020     | 9               |
| 肘 (Elbow)    | GP17 | 1490        | 820      | 2020     | 9               |
| 手首 (Hand)   | GP16 | 1600        | 750      | 2450     | 36              |

LED: GP18

---

## COWBOX T-12 操作メモ

- **ペアリングモード**: X ボタン + HOME ボタン 長押し
- **BLE アドバタイジング名**: `ZM T-12`
- **MAC アドレス**: `03:12:08:20:34:12`
- **アドレスタイプ**: `0`

---

## サンプルコードについて

`reference/sample/` は DHA の電子工作教室が公開しているコードのコピー。  
第三者の著作物のため **git 管理対象外**（`.gitignore` で除外済み）。

- 出典: [DHA の電子工作教室 #22 ゲームコントローラ](https://drive.google.com/drive/folders/1h_aNwIv26q8gpyyus-07lHX0YHY2T57M)
- 参照動画: <https://www.youtube.com/watch?v=WHLCnej2iQo>
