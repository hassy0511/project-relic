# ハル：外部の Blender スキル集で別に作る試作（haru_bs）

## 目的

主人公ハルを、外部のスキル集 [arjun988/blender-skills](https://github.com/arjun988/blender-skills)（MIT、コミット 8f778d2）の手順を主な作り方にして、**別のモデル `haru_bs`** として作り直してみる。
これまでのハル（`haru_r`）はそのまま残し、上書きしない。ゲームでは `--haru=bs` で切り替えて遊べるところまで持っていく（4 段に分ける）。

- 段 1：モデル（骨なし）。絵との比べ、検証、比べの画像。←この文書の今の範囲
- 段 2：骨と重み。段 3：14 の動作。段 4：Godot への書き出しと、ゲームでの確認。

確かめたいのは「スキル集の手順に沿うと、どういう作り方になり、何が良くなって何が足りないか」。
きれいに比べるため、プロジェクトの人物の作り方（`.claude/skills/model-from-art/SKILL.md`、`tools/blender/recon/`、以前のハルの記録）と、
haru_r などの形・重み・テクスチャ・UV・キーは使わない。haru_r.glb からは、ゲームとの約束（名前・動作の長さ・身長・向き・原点）だけを読む。

## 使ったスキル集

スキル集は Markdown だけ（手順と表）。各スキルの SKILL.md と references を、作業の段ごとに読んで従う。
本来は Blender MCP（Blender を動かしたまま外から命令する仕組み）で操作する前提だが、ここでは使えないので、
bpy のスクリプトを頭なし（画面なし）の Blender で走らせて代わりにする（置き換えの一覧は「スキル集との食い違い」）。

| 段 | 読んだスキル・参照 |
|----|------------------|
| 計画 | blender-director（「Game Character」の流れ、Reference Image Workflow）、references/asset-pipeline、reference-image-match、reference-analysis-template、naming-conventions、polycount-budgets |
| 形 | character-artist（body-proportions、facial-topology）、anime-style（anime-proportion、cel-shader-setup）、chibi-style、stylized-style、hair-groom（groom-flow-regions、hair-card-atlas、cinematic-vs-game）、blender-modeler、retopology、sculpting、cloth-sim（流れの確認だけ） |
| UV・色 | uv-workflow（texel-density、trim-sheets）、materials、texture-workflow |
| 検証 | validation-checklist、visual-match-checklist |

スキルごとに「何をしろと書いてあったか・実際にしたこと・役に立ったか」は 「試してわかったこと」 にまとめる。

## 制作の概要（Production Brief）

blender-director の Production Brief の型に沿って、作り始める前に書いたもの。

```
## Production Brief: haru_bs（ハル、主人公）

Type:        character（人型、15 歳・155 cm・約 4.4 頭身）
Target:      game engine — Godot 4.5、PC とスマホ（スマホは gl_compatibility の描画）
Style:       anime（平らな色、2〜4 段の明るさ）。stylized の形の簡略を少し借りる
Poly Budget: 30,000 三角形以下（polycount-budgets の「Mobile hero 15k–30k」。PC と同じモデルを使うのでスマホに合わせる）
             目安の内訳：頭と髪 9k、体と服 13k、フレーム 4k、銃・籠手・光刃 3k
Texture Budget: 体と服の地図 2048²（Hero 2048–4096 の下限）、顔の 2×2 表情 2048²（1 区画 1024²）、
             フレーム 1024²、銃 512²
Export:      GLB（godot-export / export-pipeline。段 4）。+Y 上、正面は glTF の +Z（Blender の -Y）
Pivot:       足元の床（原点 = 両足の間の床）。身長 1.556 m（haru_r と同じ）
Animation:   rigged + animated（29 の骨、14 の動作。段 2・3）

### Active Skills
1. blender-director — 流れの指揮、Brief、検証の門
2. reference-image-match — 絵への合わせ（カメラ → 3 段の形 → 色 → 比べの輪）
3. character-artist — 体の比率・面の流れ・服と硬い物は別のメッシュ
4. anime-style（+ stylized-style）— 平らな色、髪は塊、細かい凹凸を避ける
5. hair-groom — 髪を地域（前・頭頂・横・後ろ・えり足）ごとの塊で作る
6. uv-workflow — 継ぎ目は見えない側、texel 密度をそろえる、詰め込み
7. materials / texture-workflow — 材質を少なく（人物 3〜8）、色の地図を作る
8. rigging / animation（段 2・3）、godot-export / export-pipeline（段 4）
9. validation-checklist / visual-match-checklist / qa-review — 出す前の確認

### Pipeline Phases
- [ ] Reference & Planning（この文書）
- [ ] Blockout & Silhouette（絵の正面・横の影と重ねる）
- [ ] Modeling（体・頭・髪・服・硬い部品）
- [ ] Cleanup & Topology
- [ ] UVs
- [ ] Materials/Textures
- [ ] Optimization
- [ ] Rig/Animate（段 2・3）
- [ ] Export & Validation（段 4）

### 実行の計画（MCP の代わり）
1. bpy のスクリプト tools/blender/trial_bs/ を書き、Blender を頭なしで走らせて build/trial_bs/haru_bs.blend を作り直す
2. 絵と同じカメラ（正投影、絵の画素と寸法を合わせる）で静止画を描き、絵と横に並べる
3. 違いを最大 5 つ挙げて直す（最大 3 回）
4. 検証の 2 つの表を通す
```

### 名前（naming-conventions）

| 種類 | スキル集の名前 | この試作 |
|------|---------------|---------|
| 集まり | `COL_` | `COL_HaruBS`、`COL_Reference`、`COL_Blockout`、`COL_Geo`（体・頭・髪・服）、`COL_Frame`、`COL_Props`、`COL_Cameras`、`COL_Lights` |
| メッシュ | `SM_[分類]_[説明]` | `SM_Char_HaruBS_Body` など。**ゲームが名前で探す物は約束の名前**：`Frame_core`・`Frame_arm`・`Frame_legs`（部品をまとめる空の物体）、`LightBlade`、`muzzle` |
| 材質 | `MAT_[面の種類]_[説明]` | `MAT_Cloth_HaruBS` など。**顔は名前に小文字の `face`**（Godot の `contains("face")` は大文字小文字を区別）→ `MAT_face_HaruBS`。**銃は `spark_gun` で始める** → `spark_gun_HaruBS` |
| テクスチャ | `T_[物]_[種類]` | ファイル名はゲームの決まり `haru_bs_*` で始める → `haru_bs_T_Body_BC.png` など |
| カメラ・光 | `CAM_`・`LGT_` | `CAM_Ref_Front` など（絵ごと）、`LGT_Key_Sun` |

## 絵の分析（Reference Analysis）

reference-analysis-template の型に沿って、作り始める前に書いたもの。絵は Codex の W1-00（`origin/art/w1-haru3d` の `art/concepts/W1_haru_3d/`）。

### 1. 何か
- 種類：人物（主人公、ゲームの操作キャラクター）。平らな色のアニメ調、面の少し角ばった「ローポリ寄り」の塊（ズボン・靴・板の面が平らに折れている）。
- 正面：Blender の -Y（glTF の +Z）。左右は本人の基準（本人の左 = +X）。
- 大きさ：高さ 1.556 m（髪の先まで。haru_r と同じ）、A ポーズの幅 約 1.0 m（指先から指先）、前後 約 0.32 m（靴の爪先〜髪の後ろ）。

### 2. 形と比率
- 大きい塊：①頭と髪（全体の約 1/4。とがった葉の形の房が頭頂の後ろ寄りから放射状）②短い上着と肩の板 ③太いズボン（膝まで）④膝当て・すねの板・靴 ⑤腕（A ポーズで約 35 度開く）。
- 比率：4.4 頭身。正面の絵（2048 角、全身 1802 px = 1.556 m、1 px ≒ 0.864 mm）で、あご 約 1.23 m、肩 約 1.17 m、ベルト 約 0.90 m、股 約 0.80 m、ズボンの裾 約 0.62 m、膝当ての中心 約 0.47 m、足首のカフ 約 0.21 m。（寸法は作りながら絵の影と重ねて直す）
- 形の言葉：丸い頭と頬（親しみ）＋四角い板と靴（安定）＋とがった髪の房（勢い）。上着とズボンは面を平らに折った塊、細い布のしわは描かない。

### 3. カメラ（先に合わせる）
- 全身 7 枚：正投影、胸の高さ、余白をそろえてある（髪先 123 px〜靴底 1925 px）。正面・背面・本人右の真横・本人左の真横・右前 45 度（三分の四）・左前 45 度・右前 45 度。
- 頭 4 枚：正投影、首から上（本人右の真横・背面・右前 45 度・真上）。顔：正面と 2×2 の表情。
- 計画：絵ごとに `CAM_Ref_*`（正投影、ortho_scale = 2048 px × 0.864 mm ≒ 1.769 m、中心の高さ 0.778 m）。頭の絵は髪の外形の箱で大きさと位置を合わせる。

### 4. 光
- 鍵の光：正面からの柔らかい一様な光、影はほとんどない（絵の発注が「平らな色、ごく弱い形の陰だけ」）。縁の光なし。背景は透明。
- 計画：比べの絵は「正面からの一様な光＋陰の 2 段」のトゥーン（cel-shader-setup：拡散 → 段の ColorRamp）。`LGT_Key_Sun` は左上前。

### 5. 色（hex）
絵の画素を拾った値（12 色に減色した面積順と、点の拾い）と、発注書の基準色を比べ、基準色を採った（画素は弱い陰とにじみを含む）。

| 役割 | 基準 hex | 絵から拾った値 | 使う所 |
|------|---------|--------------|-------|
| 上着・ズボン（れんが） | #B75B43 | #BB5E3B・#C2613C | 上着、ズボン、足首のカフ |
| 白磁（明るい外殻） | #F3E9D2 | #F7E4C8・#F9E7CB | シャツ、肩・太ももの板、膝、すねの側板、爪先、背中の板、籠手 |
| 黒鉛（暗い） | #444641 | #4E433D・#4D4542 | 帯、手袋、支持部、ゴーグル枠、銃、靴底 |
| 真鍮 | #A98749 | #C99E5F | バックル、レール、継ぎ目 |
| 焦げ茶 | #594333 | #603F34・#63493D | 髪、襟、靴、すねの中央 |
| 琥珀（発光） | #FFBC52 | #FAB632 | レンズ、膝の継ぎ目、銃の窓、光刃 |
| 肌 | #E7B58D | #EFC79D・#FCB986 | 肌 |
| 虹彩・白目・口 | #795334・#FFF8EA・#98684F | — | 顔のテクスチャ |

### 6. 材質
- 布（上着・ズボン・シャツ）：つや無し。白磁の板：つや無しの非透過の殻（発注書：金属の反射やグローを焼かない）。真鍮：つやを抑える。琥珀：ゲームで別に光らせる。
- 汚れ・傷：なし（anime-style：PBR の粗さのむらを主にしない）。

### 7. 必ず入れる物
- [ ] 額の上の大きいゴーグル（黒鉛の枠・琥珀の角ばったレンズ 2 枚）と、後頭部を水平に回る 1 本の帯
- [ ] 葉の形の短い房の髪（長い襟足・細い毛束なし）
- [ ] 短い上着（開いた前、焦げ茶の返った襟、短い袖に暗いカフ）、白いシャツ
- [ ] 2 本の暗い肩ひも（背中でも平行、X にしない）、帯の間の白い背中の板
- [ ] 本人右の肩だけの白磁の板（上腕の暗い帯で支える）、本人右の太ももの外の大きい板
- [ ] ベルト（真鍮の四角いバックル）、両腰の暗いポーチ
- [ ] 太いズボン（膝まで）、膝当て（前だけ白、後ろは暗い帯、横に琥珀の丸い継ぎ目）、すね（中央は焦げ茶、外に細い白い板）、足首のれんがのカフ
- [ ] 靴（焦げ茶、爪先だけ白いブロック、厚い黒鉛の底、踵と爪先の間に浅い切り欠き）
- [ ] 指の出る手袋（指は肌）、本人左の前腕の籠手（白磁、暗い端の帯、小指側の真鍮のレール）
- [ ] 光刃（籠手の手首側から拳の先へ前腕と平行に約 45 cm、琥珀）、スパーク（約 30 cm、右手。灰色の角形、真鍮のレール、琥珀の窓、後ろの白いブロック）
- [ ] 顔：大きい茶の目（白い光の点 2 つ）、太い眉、小さい鼻、閉じた口。2×2 の表情（通常・笑顔・驚き・痛み）

### 8. 今の場面との違い
新しく作るので無し（haru_r は使わない）。

### 9. 使うスキル
blender-director → reference-image-match → character-artist → anime-style（+ stylized-style）→ hair-groom → uv-workflow → materials → texture-workflow → visual-match-checklist → validation-checklist

### 10. 段の計画（MCP の代わりに bpy）
1. 絵ごとの正投影カメラを置き、絵の影（アルファ）と重ねられるようにする
2. 1 段目：比率の塊（体・頭・服の外形）を絵の影に合わせる
3. 2 段目：服の境目・板・帯・ベルト・膝・靴の形
4. 3 段目：ゴーグル・バックル・レール・継ぎ目・ポーチ・顔
5. 色（基準 hex から地図を塗る）、トゥーンの光
6. 絵と同じカメラで描いて比べ、違いを直す（最大 3 回）
7. 保存と検証

## 段 1 の結果（モデル）

（作業後に書く）

## 絵との比べ（比べの輪）

（作業後に書く）

## 検証（validation-checklist・visual-match-checklist）

（作業後に書く）

## 段 2・3（骨・動作）

（あとの段で書く）

## 段 4（書き出し・ゲームでの確認）

（あとの段で書く）

## スキル集との食い違い

### ここで置き換えたこと（MCP が無い・画面が無い）

| スキル集の言うこと | ここでしたこと |
|------------------|--------------|
| Blender MCP で操作する（execute_blender_code・get_scene_info） | bpy のスクリプト（`tools/blender/trial_bs/`）を頭なしの Blender で走らせる。毎回 .blend を作り直す（「既存の .blend を上書きで直す」の代わりに、スクリプトを直して作り直す＝同じ結果を何度でも作れる） |
| get_viewport_screenshot で絵と比べる | 絵と同じ正投影のカメラで Cycles の静止画を描く（`render_compare.py`）。EEVEE と Workbench は EGL が無くて動かない |
| トゥーンの確認（Shader to RGB → ColorRamp） | Shader to RGB は EEVEE だけなので、法線と光の向きの内積 → 段の ColorRamp → 発光、で同じ 3 段を作った |
| 絵と見比べる | 横に並べるほか、影（アルファ）の重なりを色で出し、IoU（重なりの割合）を数にした |
| get_scene_info・査察 | `validate.py`（大きさ・三角形・n 角形・開いた辺・UV の範囲・材質・名前） |

### ゲームの約束を優先した名前

| スキル集の名前の決まり | 約束 | 使った名前 |
|---------------------|------|-----------|
| 材質は `MAT_[種類]_[説明]`、PascalCase | 顔の材質は名前に小文字の `face` を含む（`contains` は大文字小文字を区別） | `MAT_face_HaruBS` |
| 同上 | 銃の材質は `spark_gun` で始まる | `spark_gun_HaruBS` |
| メッシュは `SM_` | ゲームが探す物体 | `Frame_core`・`Frame_arm`・`Frame_legs`（空の物体で部品をまとめる）、`LightBlade`、`muzzle` |
| テクスチャは `T_[物]_[種類]` | 横に置くファイルは `haru_bs_*` | `haru_bs_T_HaruBS_Body_BC.png` など |

### スキル集の手順を変えたところ（理由つき）

- **sculpting → retopology を飛ばした**（Game Character の流れ）：平らな色のアニメ調で、細かい凹凸を作らない（anime-style：細かい形は避ける）。形は最初から四角の面の輪で作るので、作り直す元（高い面数の像）が無い。
- **cloth-sim を使わない**：絵の服は折れた平らな面の塊で、しわを描かない。揺れはゲームの骨（髪・ポーチ）で付ける。
- **髪のカード（アルファ）を使わない**（hair-groom の Game の道）：スマホの描画では透明がうまく描けない（gl_compatibility）。絵の髪も不透明の葉の形の房なので、厚みのある房の塊にした。地域の分け方・流れ・房の数・地肌の殻はスキル集のとおり。
- **顔の目・口の輪を作らない**（facial-topology）：表情は 2×2 のテクスチャの切り替え（ゲームの約束）なので、まぶたや口を曲げない。retopology の game-cinematic-topo の「台詞が無ければ少なくてよい」に当たる。
- **焼き（bake）・ORM を使わない**（texture-workflow）：高い面数の元が無く、色は平ら。陰の 2 段目は「描いた陰」（stylized-style：AO は描く、焼かない）。
- **光・色の調整（AgX、露出、リム）**（reference-image-match の 4・5 段）：宇宙船などの写実の場面向け。絵は一様な正面の光なので、Standard の色で 3 段のトゥーンにした。
- **chibi-style**：2〜4 頭身の決まり。ハルは 4.4 頭身なので当てはまらない。

## 試してわかったこと

（作業後に書く）
