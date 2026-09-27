# アークウォーカー（ARKWALKER）

「歩く方舟」の背中で暮らす少年が、失われた文明の遺跡に潜る 3D アクションアドベンチャー。
現在は **MVP（遊びの骨格を確かめる試遊版）** の段階。見た目は仮。

- 試遊版：https://hassy0511.github.io/project-relic/ （GitHub Pages）
- 企画・設計：[`docs/`](docs/README.md)

## 遊び方（MVP）

| 操作 | キーボード＋マウス | ゲームパッド |
|------|-------------------|-------------|
| 移動 | WASD | 左スティック |
| カメラ | マウス（画面をクリックで固定） | 右スティック |
| ジャンプ・調べる | Space | A |
| ダッシュ | Shift | B |
| 主武器 | 左クリック | RT |
| 光刃 | E（連打でコンボ、長押しで溜め斬り） | X |
| 特殊武器（ドリル） | Q（押しっぱなし） | Y |
| ロックオン | 右クリック（押している間） | LT |
| 対象の切り替え | ロックオン中にマウスを横に振る | 右スティックを弾く |
| 回復 | R | 十字キー上 |
| ポーズ | Esc | Menu |
| 調整パネル | F1 | — |

調整パネルで手触りの数値を変え、「YAML としてコピー」で値をそのまま共有できる。

## 開発

```bash
npm install
npm run dev          # 開発サーバー
npm test             # 単体テスト・手触りの数値テスト
npm run e2e          # ブラウザでの通し確認（撮影は test-results/shots/）
npm run build        # 本番ビルド（dist/）

npm run setup:blender  # Blender（bpy）と音の生成用の Python 環境を作る（初回のみ、Python 3.11）
npm run assets         # Blender スクリプトから 3D モデルと地形を書き出す
npm run audio          # 効果音と BGM を書き出す
```

## 構成

| 場所 | 内容 |
|------|------|
| `src/sim/` | ゲームの中身（描画に依存しない。Node.js でも動く） |
| `src/view/` | 3D の描画 |
| `src/ui/` | HUD、会話、メニュー |
| `content/` | ゲームデータ（手触りの数値、配置、会話、イベント） |
| `tools/blender/` | 3D モデル・アニメーション・地形を作る Python スクリプト（正本） |
| `tools/audio/` | 効果音と BGM を作る自作シンセ |
| `public/assets/` | 書き出した GLB と音 |
| `tests/` | `sim/`（手触りと仕組み）、`e2e/`（ブラウザ） |
