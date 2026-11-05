---
name: stage-from-parts
description: Codex が描いた部品の絵（2 m の升目の部品組・表面・遠景）から、ステージの部屋の見た目を「部品を組む方式」で作る手順。Blender で部品（キット）を作り、部屋の JSON に飾り（dress）・面（skin）・汚れの層・小物・動き・灯を書き、当たり判定と詰み探し・決まった向きの撮影・重さで確かめる。遺構・町の部屋の見た目を作る・広げる・直すとき、部品の絵を発注するとき、BlenderKit の素材を使うか決めるときに使う。部品の絵から作る部屋の小物もここ。人物・番機・オルドのような機械・キャラクターの 3D 化は model-from-art を使う。
---

# 部品の絵からステージを組む

遺構 B1〜B4 の 19 部屋と町の 10 部屋（第 1 章の 29 部屋）で行き着いたやり方。部屋の形と当たり判定は灰色の箱（geometry）のままで、その上に**見た目だけ**をかぶせる。
書き方の正本：`docs/design/42_コンテンツの書き方.md` 14 章（キット・飾り・当たり判定・汚れ・動き・停電）、2.2（詰みを作らない）、`docs/design/43_遺構の見た目.md`（B2〜B4・汚れの置き場所・部屋ごと）。
経過と画像：`docs/art_orders/BlenderKit検討.md`、`docs/progress_shots/`（`stage`・`rollout`・`grime`・`props`・`props2`・`props_motion`・`night_power`・`back_town`）。

---

## 0. 結論：4 つの決まり

1. **当たり判定は geometry だけから作る。** 見た目（`kit`・`dress`・`skin`・`hide`）は当たり判定・目印・出口・トリガー・置く物を何も変えない。
   手で触れる大きさの飾りは `"solid"` で、道具が描かない箱を geometry に足す（9 章）。見えている面は当たり判定の面と同じ所に置く。
2. **部品は寸法表から単純な形で組み、部品ごとに平らな 1 色。** 絵の色・陰を写さない（model-from-art の 2.2 と同じ）。汚れは写真を貼らず、CC0 の写真から取った「型」をパレットの色で塗る層にする（5 章）。
3. **描画の数は「部屋に置いた部品の種類 × 材質の数」。** 同じ部品は部屋で 1 つの MultiMesh なので、数を増やしても描画は増えない。絞るのは種類と材質。
4. **報告の前に、決まった向きを PC とスマホの描き方の両方で全部撮り、詰み探しとテストと章の通しを通す**（10〜13 章）。直した所だけの数枚で「直った」としない。

| やり方 | 結果 |
|-------|------|
| 広場の壁の面に家の正面の板だけを貼る | ユーザーの試遊で「ハリボテ」。側面・屋根・奥行きのある箱の建物に作り直した（42 の 14.6） |
| 飾りに当たり判定を付けない | 箱・樽の中にハルが入り込み、頭だけ出して立てた → `solid` |
| 写真の材質をそのまま面に貼る | 写実の背景になり、絵に描いた板の割り付け・鋲も消えた → 型＋パレットの色 |
| 汚れのしみを掛け算の半透明（`blend_mul`）で描く | スマホ・ブラウザ版（`gl_compatibility`）で真っ黒 → 普通の半透明 |
| BlenderKit の小物をそのまま置く | 形・色が合わず、三角形は今の部品の 17〜590 倍 → CC0 の 2 点だけ、今の画風に直して使う |

---

## 1. 最初にすること：1 枚の計画

形を作る前に、その段の結果を書く所（遺構は `docs/design/43_遺構の見た目.md`、町は 42 の 14 章に、段の節を作る。発注ごとの結果の文書を作るなら `docs/art_orders/<発注>_結果.md`）の初めに次の 1 枚を書く（外部のスキル集の試しで効いた「作る前の Brief」。13 章）。

| 書くこと | 中身 |
|---------|------|
| 部品の表 | 部品の名前・大きさ（m、2 m の升目）・原点・三角形の目当て・材質（いくつか）・当たり判定（`solid`／体だけ／乗れない柱／なし）・動きの重み・灯の出所（電気／油） |
| 予算 | 部品 1 つの三角形（11 章）、部屋ごとの描画の上限（前の何倍まで）、スマホの描き方での数 |
| 撮る向き | `tools/audit_views_*.json` のどれを使うか、足す向き（入口・いちばん重い向き・新しい物の近く・スマホ） |
| 変えないもの | geometry の位置と大きさ、目印・出口・トリガー・住人・置く物・敵・動く足場 |
| 必ず入れる物 | 絵・雰囲気画にある物の一覧。これがそのまま 13 章の受け入れの表になる |

同時に確かめること：
1. 環境：`bash tools/setup_blender.sh`、`bash tools/setup_godot.sh`（作業環境は作り直されるので、セッションごとに必要）。新しい作業場所では先に `tools/godot.sh import`。Blender で部品を作り直したあとも、撮影・テストの前に毎回取り込む（3 章）。
2. 絵の取り出し（`tar -C` の先のフォルダは先に作る）：
   - 町：`mkdir -p build/intake/w2town && git archive origin/art/w2-town art/concepts/W2_town | tar -x -C build/intake/w2town --strip-components=3`（`town.py` の冒頭）。
   - 遺構：手元に無ければ先に `git fetch origin art/w2-ruins`。`mkdir -p build/intake/w2ruins && git archive origin/art/w2-ruins art/concepts/W2_back_ruins | tar -x -C build/intake/w2ruins --strip-components=3`（`textures.py` の冒頭）。
3. 汚れの型を作り直すなら、型の元の CC0 の写真 4 枚を先に `build/blenderkit/` へ落とし直す（新しい作業環境では空）：`godot/assets/kit/grime/SOURCES.json` の `id` ごとに `python3 tools/blenderkit_fetch.py get <id> --file <file_type>`、できたフォルダ（`made_from` の名前）に `texture <フォルダ>`（5 章）。
4. 雰囲気画と今の画面を同じ向きで並べる。差の大きいのは汚れよりも**光・物の密度・砂の吹きだまりの形**だった（`BlenderKit検討.md` 0 章）。足りない物は部品組として発注する（2 章）。
5. 担当に任せるときの指示は model-from-art の 6.1 のとおり（開始時に `date` で時間の区切り、こまめなコミット、自分のファイルだけを add、一時ファイルは `build/`、予約や通知を作らない）。Godot は `flock -o /tmp/godot.lock` で、Blender の流しが 1 分を超えそうなら（Cycles で描く `town.py --review`、`--only` なしの全部の作り直しなど）`flock -o /tmp/blender_heavy.lock` で囲む（同じ機械でほかの担当も Blender・Godot を回す）。

---

## 2. 部品の絵の発注（Codex。`docs/art_orders/`）

- 条件は `01_3D変換用の絵の条件.md` の 5b 章（部品・表面・遠景）。発注書は `W2_05_オルド背町.md`・`W2_06_背中の遺構.md`（キットの土台）、`W2_05b_市場のにぎわい.md`・`W2_06b_遺構の散らかりと砂.md`（物の密度）。Codex に貼る文は `codex_prompts.md`。
  - 部品組ごとに正面・真横・真上の 3 枚（同じ並び・同じ縮尺）と組み立て例 1 枚、spec に部品ごとの寸法（m）とつなぐ面。幅・奥行き・高さは 2 m の倍数（小物は 0.5 m）。
  - 表面 `tex_<名前>.png` は 2048 px・端がつながる絵。遠景 `bg_<名前>.png` は 4096×1024・左右がつながる。
- 納品の絵はそのままでは合わないことがある。わかったこと：
  - 表面の絵の端は数学的には一致しない（RGB の平均の差 4〜19/255）。`tools/blender/kit/textures.py` が半分ずらした絵を端ほど強く重ねて消す。
  - 遠景 `bg_desert_*` は左右を鏡に映してつないであり、つなぎ目の列が暗かった。`town_backdrop._fix_seam` が両側 6 列の明るさを合わせる。
  - 真鍮の角の金具は絵では使いすぎ。**硬い売り物だけ**に付け、かご・麻袋・布・玩具には付けない（ユーザーの見直し）。
  - 上面図の吊り布・看板・旗は正面図と同じ描き方なので、奥行きは寸法表の値で作る（布 2 cm・札 5 cm・旗 2 cm）。

---

## 3. Blender の部品（`tools/blender/kit/`、`.venv-blender/bin/python`）

| 何を | 入口 | 中身 |
|------|------|------|
| 遺構 B1 | `build.py [--only b1_wall,…]` | `ruins_b1.py`（寸法・原点）、形は `geo.py` |
| 遺構 B2〜B4・しみ・散らかり | `ruins_build.py [--kits=ruins_b2] [--only …]` | `ruins_b2.py`・`ruins_b3.py`・`ruins_b4.py`・`ruins_common.py`・`ruins_clutter.py` |
| 町 | `town.py [--only …] [--list] [--review] [--gallery] [--tex] [--sky]` | `town_parts.py`・`town_sets.py`・`town_terrace.py`・`town_goods.py`・`town_rooms.py`・`town_landing.py`、形は `town_geo.py` |
| 背の町の遠景 | `town_far.py`（Blender なし、numpy で GLB） | 絵の帳 `town_far_atlas.py` → `godot/assets/kit/tex/town_far.png` |
| CC0 の小物 | `cc0_props.py [--only cask] [--gallery]` | 6 章 |

出力は `godot/assets/kit/<ruins|town|cc0>/<部品>.glb`。**何度流しても同じ GLB**（重みの無い部品は作り直してもバイトまで同じ）。
確認ページの一覧 `tools/model_viewer/kit_*.glb` は、`build.py`・`ruins_build.py` では `--only` なしで流したときだけ、`town.py`・`cc0_props.py` では `--gallery` を付けたときだけ作り直される（`--only` で部品だけ直すと、確認ページは前のまま）。

- **作り直したら Godot に取り込む**：撮影・テストの前に `tools/godot.sh import`。取り込むまで、新しい部品は Godot に無く（撮影の「飾りの部品がそろっている」が落ちる）、変えた部品は前の形のまま映る。
- **原点と向き**：底の中心、正面（通路の側）が +Z。壁に付く物は背面（壁の面）。部屋の座標のまま作る大きな組（`*_set`・`terrace_*`・`stair_gate`）は `pos [0,0,0]`・yaw 0 で置く。
- **面は外向き**（model-viewer と Godot は裏の面を描かない）。`geo.py` の `lathe`・`cyl` の始めのふたが内向きで、筒の端が抜けて中が透けたことがある。手で頂点を書いた薄く広い板は `geo.Part.add` の向きそろえ（閉じた形の体積の符号）に任せない：全部の面が裏返り、上の面が消えた（布をかけた木箱）。
- **同じ平面の重なり**（ちらつき）：書き出し（`geo.to_blender`・`town_geo.to_object`）が 5 mm 以内の重なりをほどき、小さい方を 1.5 cm 外へ出す。部品と地形の箱の重なりは置く部品の側で 2 cm 外へ。芯の箱と冠・金具の上の面を同じ高さにしない。壁の列が角で交わる所は `b1_corner` でふさぐ。
  探すのは `.venv-blender/bin/python tools/blender/kit/check_coplanar.py`（`--only`・`--raw`・`--room ch1_town.json:mid,ch1_ruins.json:r02`。材質の違う重なりが 1 つでもあれば終わりの値 1）。
  **この道具が知っているのは町の部品（`town.catalog()`）と遺構 B1 の部品（`ruins_b1.PARTS`）だけ**。引数なしでも `--kit town,ruins_b1` しか見ない。`--room` でも、知らない部品（B2〜B4・しみの `ruins_common`・散らかりの `ruins_clutter`・`cc0/*`）は**何も言わずに飛ばす**ので、それらの重なりがあっても 0 になる。
  2026-11-05 に数えた、飾りの部品の種類のうち調べられないもの：r07・r08・r10・r19・r20 は全部、r06 は 25 のうち 21、r09 は 18 のうち 16、r13 は 20 のうち 18、r04 は 35 のうち 18、r02 は 39 のうち 9、r01 は 19 のうち 3、町のほかの部屋は `cc0` の 0〜2。
  飛ばされる部品は、近くから撮った向き（10 章）で重なりを目で確かめる。道具に B2〜B4 などを足すまでは、0 を「重なりが無い」の証にしない。
- **壁の部品の出っ張り**は壁の面から 0.35 m まで（`ruins_b1.RELIEF`。当たり判定の壁の帯の内）。前は柱が 0.42〜0.65 m 出て、壁ぎわを歩く体が柱に半分入った。
- **材質**：町は平らな色を頂点の色にして `flat` 1 つ、黒鉛と真鍮は `metal`、電気の灯の芯は `amber`、油の灯は `flame`、大きな面は `shell`（`town_geo.MATERIALS` に色を足しても `flat` なら描画は増えない）。
  遺構は材質の名前でキットの材質に置き換わる（`RoomKit.part_mesh`）ので、同じ GLB が B3 と B4 で違う色になる。部品の材質は 1〜3 個に（暗い板は黒鉛にまとめる）。
- **三角形を増やさない**：柄（布の山形・かごの編み目・看板の絵記号）は形にせず、面から 1.5 cm 浮かせた平らな色の板か色の帯。
- 確認ページ（`tools/model_viewer/index.html` の `MODELS`）の `kit_*` の行に、部品の数と作り方・置き方を書く。

---

## 4. 部屋に置く（部屋の JSON：`godot/content/areas/ch1_*.json`）

- 部屋に `"kit": "<id>"`（`godot/content/kits/<id>.json`：面 `surfaces`・部品の材質 `materials`・自動の貼り分け `auto`・縁取り `trim`・雰囲気ごとの光 `light`・空 `sky`）と `"dress": [{"part", "pos", "yaw"|"rot", "scale", "count", "step", "shadow", "light", "solid"}]`。
  形には `"skin"`（面の名前）・`"hide": true`（描かない、当たり判定は残る）・`"trim": false`。キットの受け継ぎは `"base": "town"` と `"detail_scale"`（`town_tidy`・`town_worn`）。
- **手で書かない。道具で書く**（何度流しても同じ。形の位置・当たり判定・目印は変えず、飾りの箱だけ作り直す）：
  - 町：`.venv-blender/bin/python tools/dress_town.py [部屋]`（部屋は `mid`・`lower`・`upper`・`training`・`home`・`workshop`・`guild`・`mayor`・`r01`・`opening`）。`--check` で、流し直してもファイルが変わらないかだけを見る。
    numpy が要る（`town_landing.py`）。この機械の `python3` には numpy が無く、`ModuleNotFoundError` で止まった。
    `r01` は遺構 B1 のキット（`ruins_b1`）の部屋だが `ch1_town.json` にあり、書くのは `dress_town.py`（`dress_ruins.py r01` は KeyError で止まる）。
  - 遺構：`python3 tools/dress_ruins.py [部屋]`（r02・r03 はこのファイル、r04〜r20 は `tools/dress_ruins_deep.py`）。`--check` は無い。流し直したあと `git diff --exit-code godot/content/areas/ch1_ruins.json` が何も出さなければ同じ。
- **組で置く**：1 つずつ散らさず、話のある組（回収の山・野営・作業の跡・市場の露店）にする。壁ぎわ・柱・山に寄せ、通り道・出口・扉・住人・トリガー・看板と、それを見るカメラの前は空ける。壁ぎわの組は正面（+Z）を部屋へ向ける。
  箱どうし・壁の帯とは 2 cm 離して並べる（`Dress.snug`・`dress_solid.snap`）。別の組とは 0.75 m 以上離す。
- **ハリボテを作らない**（42 の 14.6）：建物は箱で作る（正面・側面・屋根・奥行き）。飾りの列は当たり判定の箱の端で止める。当たり判定の無い見た目だけの塊は、届く縁より 2.5 m 以上低くする（跳ぶ高さは 2.2 m）。出口の先の壁には門・扉を描く。
- **カメラ**（42 の 14.6、`camera_rig.gd`）：
  - カメラの高さ（約 1.9 m）に届く物を、カメラが下がってくる部屋の角に置かない（`near_fade` の網目の箱が画面の真ん中に透けた）。決まった撮影の向きで、カメラの真ん前に物を置かない。撃つ・見る仕掛けの前に板を置かない（r10 の弁の輪が見えなくなった）。
  - カメラは当たり判定の箱の 0.3 m 手前で止まり、体だけの箱には当たらない。見た目だけの塊（`shell` など）にはカメラが入りうるので、カメラが届く所（立てる所から 5.5 m、跳んで 2.2 m 上）では、当たり判定の上の面より下げるか、当たり判定の面から十分に引っ込める。
  - 縁から見下ろす穴は底が見えない深さにする（遺構の `b1_pit` は 20 m）。
  - `near_fade`（カメラの近くを網目で消す）はスマホ・ブラウザ版（`gl_compatibility`）では外れる（12 章）。網目で消えるのを当てにして、カメラの前に見た目だけの物を置かない（スマホでは消えずに画面をふさぐ）。
- **影**：今のキットはどれも `"dress_shadows": false` を書いて、飾りを影なしにしている。**コードの既定は影あり**（`RoomKit` の `get("dress_shadows", true)`）なので、新しいキットの JSON にも必ず書く（書かないと飾りの部品が全部影を落とし、描画が増える）。
  町は近くで形を読ませる物だけ（`dress_town.py` の `SHADOW`）。生活感の小物には影を付けない（CC0 の 2 つに付けたら市場の向きで +16 回、見た目はほとんど変わらなかった）。

---

## 5. 汚れと細部の層（`detail`。型は CC0 だけ）

- 面・部品の材質に `"detail": [ … ]` を 4 つまで（42 の 14.2.1。シェーダーは `godot/assets/shaders/kit_detail.gdshaderinc`、値を入れるのは `RoomKit._set_detail`）。
  `mask`（`grime`・`chips`・`mottle`・`streaks`）・`color`（パレットの色）・`amount`・`mode`（`paint`／`multiply`。シェーダーの中の混ぜ方で、半透明の掛け算ではない）・`cover`（面積の割合）・`edge`・`uv_m`、置き場所 `on`・`feet`・`top`・`seam`・`gate`。
- 型の絵は `.venv-blender/bin/python tools/grime_masks.py`（numpy と PIL が要る。`build/blenderkit` の CC0 の写真 4 枚（先に落とし直す。1 章）から形だけ → `godot/assets/kit/grime/masks.png`・`masks2.png`、出所は `SOURCES.json`。CC0 でなければ止まる）。
  1 枚に型を 2 つだけ（白黒の RGB と A）。RGB に 3 つ入れたら、VRAM 圧縮で縁が 4×4 画素の段々に崩れた。
- **汚れは 3 段で決める**（43 の 3 章。ユーザー「汚れているべきところではこうだし、その辺の調整する前提だね」）：
  1. キットごとの強さと色（B2 は濡れたさび、B3 は油とさび、B4 はきれいめ。町は `town_tidy` できれいに・`town_worn` で汚く）。
  2. 同じ部品の中で汚れるべき所だけ別の材質（遺構の `ivory_stain`：灯の下と足元、扉の枠の足元）。
  3. 置き場所の部品：遺構は `dress_ruins_deep.py` の `grime()`・`drips()`（`stain_floor`：扉の前、`stain_path`：通り道、`stain_corner`：部屋の隅、`stain_floor_b`：機械の下、`stain_drip`：壁を垂れるさびの筋。B2 の太い管は垂れつきの部品 `b2_pipe_drip`）、町は `dress_town.dirt()`（`grime_patch`・`oil_patch`：戸口・階段の足元・路地・作業台）。部屋の真ん中・戦いの広間には置かない。
- わかったこと：欠けを一面に貼ると御影石の模様に見えた（`gate` で大きな斑の中だけに）。しみを不透明な板で塗ると床の絵が消えて茶色のペンキに見えた。遠くで型が画面の画素より細かいと汚れが消えるので、そこは平均の濃さで塗る（シェーダーがする）。
- 重さ：描画・三角形は変わらない（シェーダーの中だけ）。ブラウザ版の大きさは型の絵 2 枚で +0.83 MB（PC 用とスマホ用の 2 形式）。

---

## 6. 小物と BlenderKit（CC0 だけ。Royalty Free は使わない）

- リポジトリは公開で、確認ページは GLB をそのまま公開する。Royalty Free は「簡単に取り出せない」ことが条件なので**置けない**（ブラウザ版の `index.pck` も取り出せる）。**コミットしてよいのは CC0 だけ。**
- 取る道具 `python3 tools/blenderkit_fetch.py`：`search "<語>" --type material --cc0`、`get <id>`（`build/blenderkit/` へ。`asset.json` に出所とライセンス）、`texture <フォルダ>`、`glb <フォルダ>`、`install <フォルダ> <置き先>`（CC0 でなければ断り、`SOURCES.json` に出所を足す）。
- 小物は `tools/blender/kit/cc0_props.py` で今の画風に直す：材質をキットの名前へ、三角形を目当てへ（樽は縮約で崩れたので、高さごとの半径を読んで回転体で組み直した）、大きさを 2 m の升目に、原点を底の中心に。Royalty Free の物は表 `NEVER` で読まない。
  6 点を試して残したのは `cc0/cask`（304 三角形）と `cc0/plank_box`（498）だけ。**ほとんどの小物は、今の部品のスクリプトで寸法表から作るほうが早く、形と色がそろう。**
- 絵から作る小物（W2-05b・W2-06b）：町 `town.py --only <部品>`（`town_goods.py` の `PARTS`）、遺構 `ruins_build.py --kits=ruins_clutter`。露店の台の上の品は**露店ごとに 1 つの部品**にまとめた（`market_general`・`market_junk`。品が何十個あっても描画は増えない）。
- 当たり判定の無い小物は、床の上の薄い物（0.3 m 以下）・壁に平らな物（壁から 0.08 m）・頭の上の物（跳んだ頭が届かない高さ）・壁の帯の内の物だけ。それ以外は `solid`。新しく `solid` の部品を作ったら `tests/test_kit.gd` の `SOLID_CLASS` に足す。

---

## 7. 動き：揺れ（`sway`）・流れ（`flow`）・粒（`emitters`）

- **見た目だけ**。時刻は描画の時計 `TIME` と Fx の刻みだけで、ゲームの中身（`GameSim`）は読まない・変えない（決まった刻みのテストと章の通しは前と同じになる）。
- **動かす所は頂点の色のアルファ**（1 − 重み。0 = 留まった端、1 = 自由な端）。材質を分けると部品ごとに描画が増えるので、材質は前のまま頂点で選ぶ。
  町は `town_geo.py` の `sway(形, fn)`・`hang`・`sagging`・`Part.mark()`／`sway_since()`、遺構は `geo.Part.motion`（`ruins_clutter.py` の `cable_hang`・`sand_fall` など）。
  **重みは位置だけで決める**（布の表と裏・柄の板が一緒に動き、面が裂けない）。上限：旗・洗濯物の端 1、日よけと露店の垂れ `town_parts.SWAY_DROP`（0.5）、壁に沿う布 `SWAY_WALL`（0.4。押されても壁に入らない）、枠の帆布 `SWAY_CANVAS`（0.18）、屋内は 0。
- 書き出しは重みのある部品だけ頂点の色をアルファごと（町は `export_vertex_color='NAME'`。`'ACTIVE'` では RGB だけになり重みが消えた）。
- キットの材質に `"sway"`・`"flow"`、キットに `"emitters"`（部品 → `dust`・`steam` の出所。1 部屋 16 か所まで、`AmbientFx`）。町の風は船首（+Z）から吹き、風下は -Z（`"wind": [0, 0, -1]`）。
- 面の向き（法線）は傾けない。傾けた旗にスマホ・ブラウザ版で一瞬白い点が散った。落砂の流れは太い（0.1 m）と柱に見えたので 0.03 m に。
- 確かめ：`--motion_shots`（`--motion_shots=flag,sand` で選ぶ）、テスト `test_kit_motion_materials`・`test_kit_motion_weights`・`test_kit_motion_no_multiply_blend`・`test_ambient_fx_view_only`。
- **オルドの足音の揺れ**（`jolt`。`docs/design/30_レベルデザイン設計.md` の「世界の小さな反応」）：足が着くと、揺れの重みのある材質（キットの `"sway"` のある材質）が振り子のように揺れる。布・旗など重みのある部品は何もしなくても揺れるが、灯の重み・砂ぼこり・弱めた揺れは `godot/content/ordo_steps.json` に**書いた部品だけ**に効く。町に灯・吊り物・壁の布を足すときに要る。
  - 灯は `"hang"`：端の重み `w`（外の灯 0.6、屋内の灯 0.5、置いた携行灯 0.2）。部品を読むとき（`RoomKit.part_mesh` → `OrdoSteps.part_loaded`）に、芯の材質（`amber`・`flame`）の筒で灯を見つけ、吊り金具から下へ重みを足す。
    鎖ごと天井から揺らす灯は `"chains"`（`[x, z, 天井の高さ]`、4 つ目に半径があればその筒の中を 1 つの振り子に）、台に置いた灯は `"stand": true`、吊り灯の部品の中に置いた携行灯は `"stands"`。
  - 砂ぼこりの出る揺れる布の部品は `"puffs"`。すぐ前に梁・壁のある布は `"soft"` で揺れを弱める（`town/goods_cloth_wall` は 0.3 倍。1 倍では 4〜5 cm 押し出されて梁の前に出た）。
  - 足音の鳴り方（`place`：町・屋内・遺構）・オルドの座標・天井の高さは部屋の id で `"rooms"`、無ければキットの id で `"kits"`（遺構の B1〜B4）から引く。どちらにも無い部屋は鳴らない・揺れないので、新しい部屋・キットはここに足す。
  - 確かめ：撮影 `--steps_shots`、テスト `steps`（`tests/test_steps.gd`。灯の重みと壁の布の弱めた揺れも見る）。

---

## 8. 灯：出所（電気・油）と停電の夜

- **飾りの明かり**：`"light": {"at", "color", "range", "energy"}`、`"type": "spot"` なら `"dir"`・`"angle"`・`"shadow"`（影は部屋に 1 つまで）。明かりは重いので部屋に数個まで。
- **出所をデータに書く**（42 の 14.8）：材質に `"source": "electric"`（停電で消える。`"off"` で残す割合）か `"source": "oil"`（いつも灯り、揺らぐ）。Blender では材質の名前で分ける（`amber` は電気、`flame` は油。`town_parts.lantern(…, core='flame')`）。
  部屋の明かりも `"source"`、停電の間だけ置く灯油ランプは `"blackout": true`、本物の光の無い安い光は `"omni": false` と `"glow"`（にじみの半径）・`"pool"`（床の明るい輪）。書くのは `dress_town.py` の `oil()`・`glow()`・`lamp()`・`blackout_*()`。
- 電気が来ているかは**フラグだけ**から決まる（`godot/content/world.json` の `"power"`、部屋の `"grid": "town"` は `dress_town.common()` が書く、`GameSim.powered`）。セーブから戻しても、場面を飛ばしても同じ。遺構は網に乗らない。
- 本物の光（OmniLight3D）はスマホの描き方で照らす物ごとに描画が 1 回増える。**人の顔を照らす所の数個だけ**にし、ほかはにじみと床の輪（部屋の全部で描画 1 回）。中段の本物の光は停電の間 7 → 3 つ。
- 発光は弱めに（琥珀の回路・導光管は emission 1.4〜1.7。4 で白く飛んだ）。屋内の金属は空を映して青く光るので、遺構の `metallic` は 0.1〜0.2。
- 灯ごとのばらつきは置き場所の 2 m の升から決める（前は面のかけらごとで、2 m の境をまたぐ窓が上下に割れて点いた）。
- 確かめ：`tools/godot.sh test power`、撮影 `--blackout_shots [--blackout_view=plaza,market] [--blackout_bench=60]`。

---

## 9. 当たり判定と詰み探し

- `"solid": true` で `tools/dress_solid.py` の表 `SOLID`（部品の中の箱 `B`・`R`・`P`・`NOGO`）を置く。遺構 B2〜B4 の箱は `dress_ruins_deep.solid_table()`。置く形は軸にそろった箱だけ。
  **当たり判定のある部品は 90 度の倍数から数度までしか回さない**（4 度で囲む箱は 0.04 m 外。前は 10〜40 度回した箱の 0.25〜0.5 m 手前に見えない壁があった）。
- **体だけの箱**（`cam=False`）：細い柱・手すり。カメラ・弾は通る（ふつうの箱だと柱が横切るたびにカメラが跳ねた）。ただし**立たせたい面は体だけにしない**（足の接地 `FootIK` は体だけの形を見ない）。
- **乗れない柱**（`NOGO`）：頭の上の張り出し・露店の屋根。上の端は近くの足場から跳んで届く高さ（＋2.2 m）より上（前は工具棚 → 給水塔 → 露店の屋根と登れた）。屋内は天井の板の中まで伸ばす。
- **すき間**：0.35〜0.75 m のすき間を作らない（体の直径 0.7 m が縁の角に載って宙に止まる）。`dress_solid.fill_gaps` が 0.75 m（`GAP`）より狭いすき間をふさぎ、0.3 m（`FILL_WARN`）より広く 3 m（`LEDGE_TOP`）より低いと警告する（見えない棚。置き方を直す）。
- **壁の帯**（遺構）：壁の部品は面から 0.36 m（`dress_solid.LINER`）の帯。溝・すき間に面する壁の部品には `solid` を付けない（r12 の溝が 0.64 m になり、詰み探しで 177 か所）。溝・すき間の口の前に角の柱を置かない（r16 で上から落ちると出られなくなった）。かけらは壁から 1.5 m 以上離す。
- **決まりの距離**（`dress_solid.check`、だめなら書かずに止まる）：出口・トリガーの箱から 0.1 m、目印・チェックポイント・敵の出る所から 0.6 m、調べる物・拾う物・住人から 0.5 m。
- **段差**は 0.17 m 以下か 0.25〜0.35 m（約 0.18〜0.24 m は歩いて上れない）。穴の底は跳んで出られる深さ（1.8 m まで）か奈落（y −30）より下。
- **詰み探し**：置くたびに `tools/godot.sh run --script res://tests/scan_traps.gd -- ch1.r02`（部屋ごと。`--json=`・`--verbose`）。形だけの調べ（`godot/tests/reach_scan.gd`）で、詰み・限界の跳びでしか出られない所・宙づりの候補を出す。候補は `tests/test_traps.gd` が実際のゲームで体を置いて確かめる。新しい部屋・段階は `ReachScan.CH1_STATES` に足す。
  - **テストの名前で選ぶときに注意**：`tools/godot.sh test` の引数は**関数の名前の一部**で、ファイルの名前ではない。`tools/godot.sh test test_traps` は 1 本も走らない（「テスト 0 本」で成功に見える。42 の 14.3.2 は 2026-11-05 に `traps` に直した）。
    `traps`（全部屋の詰みと既知の詰み）・`no_hang`（宙づり 7 本）・`dress`（飾りの当たり判定）・`kit`・`motion`・`power`・`steps`（オルドの足音の揺れ）で選び、最後は引数なしで全部を流す。
- **テストの部屋の一覧に足す**：飾りに当たり判定を付けた部屋は、`tests/test_kit.gd` の `DRESSED`（遺構）か `DRESSED_TOWN`（町）に、箱・樽を必ず置く部屋なら `PROP_ROOMS` にも足す。
  足さないと `test_dress_solid_props` がその部屋の当たり判定の箱・決まりの距離・乗れる棚を見ないまま、全部のテストが通る（遺構の展開では r04〜r20 を足した。43 の 7 章）。

---

## 10. 確認の撮影（Godot はいつも `flock -o /tmp/godot.lock timeout <秒> tools/godot.sh …` で囲む）

| 何を | コマンド（`tools/godot.sh shot --resolution 1280x720 --fixed-fps 60 -- --demo=build/<出力> …`） |
|------|------|
| 点検の向き（基準） | `--town_audit --audit_views=$PWD/tools/audit_views_<名前>.json [--audit_only=a,b] [--audit_state=night] [--jpg]` |
| 遺構の全部屋を 1 枚ずつ | `--ruins_shots`（`ruin_r02`〜`ruin_r20`） |
| 部屋の見た目の基準 | `--stage_shots [--stage_view=r02_entry] [--stage_plain]`（キットを外して比べる）、町は `--town_shots [--town_view=market]` |
| 動き・停電・場面 | `--motion_shots`、`--blackout_shots`、`--opening_shots` |
| キットの一覧 | `--demo` は使わず `mkdir -p build/kit && tools/godot.sh shot --resolution 1800x1100 --script $PWD/tools/blender/kit/godot_kit_review.gd -- $PWD/build/kit/review_ruins_b2.png ruins_b2`（ゲームと同じ材質）。町は `town.py --review`（Cycles）、確認ページの `kit_*` |

- **出力の置き場所**：`tools/godot.sh` は `--path godot` で起動し、Godot はそのフォルダを今いる所にする。だから `--demo=build/<出力>` のような相対の道は `godot/build/<出力>` に入る（`--demo` はフォルダを作る）。
  キットの一覧は出力のフォルダを作らないので、相対の道（`build/kit/…`）だと `godot/build/kit/` が無くて書けない（「Can't save PNG」）。上のように、先にフォルダを作って `$PWD` からの道で渡す（42 の 14.4 と `build.py`・`ruins_build.py` の冒頭も 2026-11-05 にこの書き方に直した）。
- 向きの一覧：`tools/audit_views.json`（中段・r02・r03）、`audit_views_town_rooms.json`（61 向き）・`audit_views_town_rooms_walk.json`（箱・住人・出口へ歩く）、`audit_views_ruins_rollout.json`（52 向き）、`audit_views_props.json`・`audit_views_solid.json`（当たり判定）、`audit_views_props_motion.json`、`audit_views_lookout.json`・`audit_views_ordo.json`。
  項目：必ず `"name"`・`"room"`（`ch1.r02` など）・`"spawn"`（入る所）。そこにプレイヤーのカメラ `"at"`・`"look"`・`"pitch"` か自由なカメラ `"eye"`・`"target"`、`"wait"`、`"walk": true`（歩いて当たって止まった所を撮る）、`"jump": n`、`"back_lights"`。部屋が変わると暗転するので、一覧は部屋ごとにまとめる。
  `"walk"`・`"jump"` の向きがあるのは `audit_views_solid.json`（r02・r03・中段）と `audit_views_town_rooms_walk.json`（町の部屋。町長の家は無し）だけで、遺構の r04〜r20 には無い。ほかの部屋は、当たり判定のある飾りのそばへ歩く・跳ぶ向きを足してから撮る（13 章）。
- 撮るたびに `描画 audit_<名前>：draw N・物 N・三角形 N` の行が出る。飾りの部品が足りないと「飾りの部品がそろっている」の確かめが落ちる（部屋の `missing_parts`）。
- **スマホ**：`shot` の後ろ（`--` の前）に `--rendering-driver opengl3 --rendering-method gl_compatibility --resolution 844x390`、`--` の後ろに `--touch`。
- 前と後は**同じ向き・同じ刻み・同じ描き方と大きさ**で撮り（前は変更前の `godot/` の写しか前のコミットの部屋のデータ。表の大きさ 1280×720 は点検の既定で、停電の夜の数（42 の 14.8）は PC 1600×900。基準の数と比べるなら、基準を撮った大きさにそろえる）、横に並べた画像を `docs/progress_shots/<名前>/` に（日本語の見出し、400 KB 未満）。全部のこまを自分で見てから報告する。
- 壁の帯のある部屋で、プレイヤーを壁から 2 m 以内に立たせると、カメラが上へ回って見下ろしになる（撮る位置を離す）。
- 遠景は、胸壁・縁から外を見る向きと場面のこま（`--opening_shots`）でも撮る。遠景で今残っていることは `docs/dashboard.md` の残課題の表（T9 など）を見る。

---

## 11. 重さ（予算）

- 部品 1 つの目安は `docs/design/40_技術設計.md` §5.4 の**地形の部品 50〜500 三角形**（地域ごとに共有のテクスチャ）。2026-11-05 の実績：遺構の部品 104 個の中央値 328（500 以下は 75 個。いちばん大きいのは大型ファン `b1_fan` 2056）、町の部品 120 個の中央値 383（500 以下は 71 個）。
  500 を超えるのは、いくつもの物をまとめた組（露店 `stall` 2124・露店の組 `market_junk` 5236・工房の正面 `workshop_front` 6020）、部屋の座標の組（`lower_set` 約 2.2 万・`training_set` 約 4.4 万）、遠景（`ordo_town` は 3.4 万まで・`ordo_back` は 1.2 万まで。`test_back_town`）と大きな機械。
  1 つの物は 500 以内を目当てにし、組は部屋の向きの描画の数と三角形で見る。
- **部屋の描画の数**は撮影の行の数（いちばん重い向き）で見る。今までに受け入れた差：

| 変えたこと | 描画の差（いちばん重い向き） | 目安・決まり |
|-----------|---------------------------|--------|
| 町の 9 部屋への展開 | どの部屋も中段の `mid_high`（PC 361・スマホ 392。PC は Forward+ 1280×720、スマホは `gl_compatibility` 844×390）より軽い | 中段のいちばん重い向きを超えない |
| 遺構 r04〜r20 への展開 | 番機のいない部屋は r02 の 1.2 倍の内（PC 227・「スマホ」247）。**この「スマホ」は 844×390 の Forward+ で、`gl_compatibility` ではない**（43 の 6 章）。番機のいる部屋（r04・r09・r10・r13・r15・r19）は灰色のときから r02 より重く、飾りで +38〜79 のあと**1.2 倍を超えたまま**（43 の 8 章の残り。下げるなら番機の描画） | r02 の 1.2 倍 |
| 生活感の小物（10-15） | 遺構 +14〜25（三角形 +1〜8%）・町 +20〜44（+11〜22%） | 影なし |
| 絵から作った小物（10-17） | いちばんきつい r05 で PC +10（上限 +12）、三角形 +0〜2% | 部屋ごとに前の 1.1 倍まで |
| 汚れの層・揺れ・流れ | 0（シェーダーの中だけ）。粒の見える向きで +1〜2 | — |
| 停電の夜 | +1〜3 | 本物の光は顔を照らす数個 |
| 背の町の遠景 | +1、三角形 +0.6 万 | 1 つのメッシュ・材質 1 つ（絵の帳） |

- 表の数は撮った描き方・大きさがばらばら。前と後は**基準と同じ描き方・同じ大きさ**で撮って比べる（`gl_compatibility` の数を遺構の「スマホ 247」と比べない）。
- 軽くする手：同じ部品は MultiMesh、壁・梁の部品は部屋で 1 種類（交互にしない）、部品の中の材質をまとめる、影を落とさない、しみは半透明の 1 回、離れた所に種類を 1 つだけ置かない（MultiMesh は部屋じゅうの置き場所を囲むので、多くの向きで描かれる）。戦いのある部屋（r09・r10）には低い道標を置かない（支柱の足元の灯で足りる）。
- 実機の fps はこの機械では測れない（CPU で描く）。こまの時間は ±10% ほど揺れるので、比べるのは前と後の差だけ。

---

## 12. スマホ・ブラウザ版の描き方（`gl_compatibility`）の決まり

1. **掛け算の半透明（`blend_mul`）は使わない**（真っ黒に塗られた。遺構のしみ・町の汚れの斑）。普通の半透明か足し合わせ。`test_kit_motion_no_multiply_blend` が見るのは面・揺れ・光の筋のシェーダーだけ（しみ `kit_stain`・斑 `kit_decal` は見ないので、足したら目で確かめる）。
2. `discard` を使う網目（`near_fade`）はこの描き方では効かない（`RoomKit` が外す）。網目で消えるのを当てにした置き方をしない（4 章）。
3. 影を落とす光は別の回で描いてトーンマップのあとに足すので、光の当たる床が白っぽくなった。太陽は `EnvironmentSetup.COMPAT_SHADOW_LIGHT`（0.4）倍、部品の影つきのスポットは影なし。
4. 夜は暗い所が真っ黒に詰まった。キットの光の項目に `"compat"`（環境光・`contrast`・人物だけを照らす `char_fill`）を書く。
5. 深さは 24 bit：30 m 先の 2 mm は分けられない。重なる面は 2 cm 以上離す（3 章）。
6. 型の絵は VRAM 圧縮（PC は BC3、スマホは ETC2）で 4×4 画素ごとに近似される。1 枚に型を 2 つまで（5 章）。
7. 揺れで法線を傾けない（7 章）。本物の光は少なく（8 章）。

---

## 13. 比べの輪と報告（外部のスキル集の試しから借りた所）

`docs/art_orders/W1_ハル_blender-skills試作.md` の「結果のまとめ」：スキル集の値打ちは**順番と止めどき**だった。ステージにも使う。

1. **作る前に 1 枚の計画**（1 章）。予算は §5.4 と 11 章の表から。必ず入れる物の一覧を受け入れの表にする。
2. **比べの輪**：雰囲気画・部品の絵と同じ向きの画面を並べ、**違いは 1 回に 5 つまで、3 回まで**。目立つ順に選ぶ。3 回で止め、残った違いは表に理由つきで残す。
3. **報告の前の自動の確かめ**（全部通ってから画像を見せる）：
   - 部品を作り直したら、先に `tools/godot.sh import`（3 章）。
   - 町は `.venv-blender/bin/python tools/dress_town.py --check`（「同じ（流し直しても変わらない）」）。遺構は `python3 tools/dress_ruins.py` を流し直して `git diff --exit-code godot/content/areas/ch1_ruins.json` が何も出さない。道具が `dress_solid.check` で止まらない・`fill_gaps` の警告が無い。
   - `check_coplanar.py`（部屋に置いた形で `--room`）で材質の違う重なりが 0（終わりの値 0）。**町と遺構 B1 の部品しか見ない**（3 章）ので、B2〜B4・しみ・散らかり・`cc0` の部品は撮影で目で見る。
   - 詰み探し（`scan_traps.gd`）で詰み 0・限界の跳びでだけ出られる所 0。宙づりの候補の増減を前と比べる。
   - `tools/godot.sh test`（全部、失敗 0）。新しい部屋が `test_kit.gd` の `DRESSED`・`DRESSED_TOWN` に入っている（9 章）。
   - `tools/godot.sh run --fixed-fps 60 -- --demo=build/ch1 --ch1_full` が「見本の完了（失敗 0 件）」で、ERROR の行が無い。
   - 撮影の行で、部屋ごとのいちばん重い向きが予算の内。飾りの部品の欠けが 0。
   試しで見逃したのは「ゲームとの約束」（原点・床との接地）だった。ステージでは原点・向き・当たり判定の箱と見た目のずれを、撮影の `"walk"`・`"jump"` の向きで必ず見る（r02・r03・中段は `audit_views_solid.json`、町の部屋は `audit_views_town_rooms_walk.json`。遺構の r04〜r20 などは向きを足す。10 章）。
4. **判定**（3 つのうち 1 つ）。止めるものが 1 つでもあれば「直す」、大きいものが残れば「注意つきで出してよい」（理由と残りの表つき）、小さいものだけなら「出してよい」。

```
判定：<部屋・キット>（<段>）
結果：出してよい ／ 注意つきで出してよい ／ 直す
予算：描画 <前> → <後>（上限 <>）、三角形 <前> → <後>、部品の種類 <>
撮った向き：PC <n>・スマホ <n>（一覧 <JSON>）
止めるもの：…（例：詰み・見えない壁・中に入れる飾り・テストの失敗・ERROR・スマホで黒い面・予算超え）
大きい：…
小さい：…
メモ：…
```

報告は「何を変えたか・残りの表・画像・テスト・コミット・時間」だけにする（model-from-art の 6.1）。

---

## 14. 完成の目安

- 決まった向きの全部のこまに、ハリボテ・浮いた板・ちらつき・透けた箱・中に入れる飾り・黒い面が無い（残すものは表に理由つき）。PC とスマホの両方。
- 雰囲気画と並べて、光・物の密度・砂の形・汚れの置き場所が近い。絵の部品だと分かる。
- 詰み 0、当たり判定は見た目どおり、テストと章の通しが失敗 0。
- 部屋ごとの描画の数が予算の内（11 章）。新しい部品は確認ページに載っている。
