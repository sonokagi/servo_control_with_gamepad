# CLAUDE.md

## 絶対ルール

### git コミットは明示的な指示があるまで行わない

**ユーザーが「コミットしてください」と明示的に指示するまで、いかなる状況でも `git commit` を実行してはならない。**

- ファイルの編集・作成は自由に行ってよい
- `git add` も確認なしで実行してよい
- **`git commit` だけは必ず明示的な指示を待つこと**
- 「変更を保存した」「完了した」などの文脈でも、コミットを勝手に行ってはならない

---

## 技術方針

### BLE ライブラリ

`aioble` ではなく MicroPython 標準の **`bluetooth` モジュール（IRQ コールバック方式）** を使用する。  
理由: サンプルコード (`reference/sample/blegamepad.py`) が同方式を採用しており、`machine.Timer` によるサーボ更新とも相性が良い。

### サーボ制御

`machine.Timer`（20ms 周期）の割り込みでサーボの `update()` を呼ぶ方式。  
`reference/multi_servo.py` の `Servo` / `ToggleLed` クラスをそのまま流用する。

---

## サンプルコードについて

`reference/sample/` は DHA の電子工作教室が公開しているコードのコピー。  
第三者の著作物のため **git 管理対象外**（`.gitignore` で除外済み）。

- 出典: [DHA の電子工作教室 #22 ゲームコントローラ](https://drive.google.com/drive/folders/1h_aNwIv26q8gpyyus-07lHX0YHY2T57M)
- 参照動画: <https://www.youtube.com/watch?v=WHLCnej2iQo>
