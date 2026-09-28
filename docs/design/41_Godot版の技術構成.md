# Godot 版の技術構成

> 2026-09-28、ユーザーの判断でエンジンを three.js から **Godot 4.5** に移した。
> `40_技術設計.md` のうち、エンジン・描画・物理・UI・配布の部分はこの文書が正本。
> データの考え方（数値や台本をコードの外に置く、ゲームの中身と見た目を分ける、同じ入力なら同じ結果）は引き継ぐ。

## 1. 移した理由
- 動作のつなぎ、骨を後から動かす仕組み（SkeletonModifier3D）、影・環境光の遮り・光のにじみ・霧などの画面の質が、エンジンに最初から揃っている。
- Windows・Linux の実行ファイルを自動で書き出せる（Steam などでの販売に向く）。ブラウザ版も書き出せる。
- Godot のファイルはすべて文字で書かれているので、Claude が読み書きして作り込める。この作業環境でもテストと撮影ができることを確かめた。
- 費用がかからない（オープンソース、売上の取り分なし）。

## 2. 構成

| 分類 | 採用 |
|------|------|
| エンジン | Godot 4.5.1（GDScript） |
| 描画 | Forward+（Windows・Linux 版）／Compatibility（ブラウザ版） |
| 物理 | Jolt Physics。キャラクターは CharacterBody3D を move_and_collide で動かし、three.js 版と同じ規則を再現（`scripts/sim/phys.gd`） |
| 補間 | 物理の補間（1/60 秒刻みで動かし、描画ではなめらかに見せる） |
| UI | Godot の Control。フォントは Noto Sans JP（SIL OFL。`assets/fonts/OFL.txt`） |
| 音 | AudioStreamPlayer／AudioStreamPlayer3D。素材は three.js 版と同じ自作シンセの OGG |
| 3D 制作 | Blender 4.5（`bpy`）のスクリプトで作った GLB をそのまま取り込む |

## 3. フォルダ

```
godot/
  project.godot, export_presets.cfg
  content/           数値（tuning.json）、配置（areas/）、会話（dialogue/）、イベント（events/）。JSON が正本
  assets/            models/（ハル）、levels/（地形）、audio/、fonts/、shaders/、textures/
  scenes/main.tscn
  scripts/
    core/            数学の小道具（u.gd）、種つきの乱数（rng.gd）、入力の 1 刻み分（input_frame.gd）
    sim/             ゲームの中身（描画を知らない）：game_sim, player, phys, camera_orbit, lock_on,
                     shot, props, story, enemies/（enemy, sentry, charger）
    view/            見た目：地形の読み込み、光と空気感、カメラ、ハル（player_view、haru_pose）、
                     番機、仕掛け、効果
    ui/              HUD・会話ウィンドウ・照準、タイトルとポーズのメニュー
    audio/, platform/（入力の割り当て）, debug/（自動の見本 demo.gd）
    main.gd          タイトル → プレイ ⇔ ポーズ、セーブ
  tests/             自動テスト（run_tests.gd、test_feel.gd、test_combat.gd）
tools/setup_godot.sh, tools/godot.sh   Godot の用意と実行
```

## 4. ゲームの中身と見た目の分け方
- `GameSim` が 1/60 秒ごとに `step(入力)` で進む。入力は `InputFrame`（ただのデータ）だけを見る。
- 見た目・音・UI へは出来事（events）で伝える。見た目は毎刻み、ゲームの中身の状態を読んで合わせる。
- テストでは、ゲームごとに別の物理の世界（`own_world_3d` の SubViewport）を持たせ、画面なしで高速に回す。

## 5. 動きを良くする仕組み（今回入れたもの）
- 動作の切り替えは、動作ごとの時間でなめらかに混ぜる（斬撃は 0.05 秒、通常は 0.15 秒）。走りの再生の速さは移動の速さに合わせる。
- `HaruPose`（SkeletonModifier3D）で、動作の上から次を重ねる：
  - 撃つとき：右腕を照準へ向け、胸を少しひねる（上半身だけの重ね合わせ）
  - 走るとき：曲がる速さで体を内側へ傾け、加速・減速で前後に傾ける
  - ロックオン中：頭を対象へ向ける
- まだ入れていないもの：足の接地（坂や段で足を地面に合わせる）、髪や服の揺れ。髪と服の揺れは揺れ用の骨が必要なので、本番のモデル（B案の AI 変換）の取り込みと一緒に入れる。

## 6. テストと確認
| 何を | どうやって | 時間 |
|------|-----------|------|
| 手触りの数値、戦闘、仕掛け、会話、セーブ、決定性（19 本） | `tools/godot.sh test` | 約 2 秒 |
| 起動から一通り遊べるか（会話 → ドリル受け取り → ロックオン → 壁の破壊） | `tools/godot.sh run --fixed-fps 60 -- --demo=<フォルダ>`（画面なし） | 約 1 秒 |
| 画面の見た目 | `tools/godot.sh shot --resolution 1600x900 -- --demo=<フォルダ>`（ソフトウェア描画で撮影） | 約 4 分 |

CI（GitHub Actions）で、テストと画面なしの通しの確認を毎回行う。

## 7. 試遊版の届け方
| 版 | 場所 | 画質 |
|----|------|------|
| Windows・Linux | GitHub のリリース「playtest」（`.github/workflows/playtest.yml` が自動で最新版に差し替える） | 本来の画質（Forward+） |
| ブラウザ | GitHub Pages の URL の直下 | 軽い描画方式（影・光のにじみなどが一部効かない） |
| 以前の three.js 版 | GitHub Pages の `/threejs/`（見た目の確認ページ `lookdev.html` を含む） | — |

ハルは絵から起こしたモデル（`haru_r`、`docs/art_orders/W1_ハル再構築の結果.md`）が既定。遊んでいる間に F2 で以前の試作（`haru_a`）と切り替えられる。

スマホ・タブレットのブラウザでは、画面の操作（左半分でスティック、右半分でカメラ、右下にボタン）が自動で出る（開発中の確認用。本番はキーボード＋マウスとゲームパッドが前提）。`scripts/platform/touch_controls.gd`。スマホで確かめるときは横向きにする。

起動時の引数：`-- --touch`（画面の操作を出す）、`-- --haru=a`（以前の試作のハル）、`-- --haru=proxy`（MVP の仮のハル）、`-- --shade=toon`（3 段の塗り分け）、`-- --demo=<フォルダ>`（自動の見本）。F1 で性能の表示。

## 8. この作業環境で動かすための準備
- `bash tools/setup_godot.sh`：Godot 本体（`.tools/godot/`）と、画面を撮るための部品（Vulkan のソフトウェア実装、仮想ディスプレイ）。`--templates` で書き出し用の部品（約 1.3GB）も入れる。
- 作業環境は毎回作り直されるので、次のセッションでも最初にこのスクリプトを実行する。
