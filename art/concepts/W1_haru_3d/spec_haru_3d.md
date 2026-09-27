# ハル：W1-00 3D変換用

未納品：なし。必須5画像・推奨4画像・本説明書を納品。画像生成は内蔵 image_gen を使用。3D変換・メッシュ作成・実機検証は本発注の対象外で、今回実施していない。

## 納品物

| # | ファイル名 | 内容 | 寸法 | 背景 |
|---|---|---|---|---|
| 1 | `haru_3d_front.png` | 正面・全身・Aポーズ | 2048×2048 | 透明・RGBA |
| 2 | `haru_3d_back.png` | 背面・全身・同じAポーズ | 2048×2048 | 透明・RGBA |
| 3 | `haru_3d_side_right.png` | 本人右側の真横・全身 | 2048×2048 | 透明・RGBA |
| 4 | `haru_3d_three_quarter.png` | 本人右前45度・全身 | 2048×2048 | 透明・RGBA |
| 5 | `haru_face_front.png` | 首から上の正面・通常表情 | 2048×2048 | 透明・RGBA |
| 6 | `haru_face_expressions.png` | 2×2：左上通常、右上笑顔、左下驚き、右下痛み | 2048×2048 | 透明・RGBA |
| 7 | `spark_gun_3d.png` | スパーク単体・斜め45度 | 2048×2048 | 透明・RGBA |
| 8 | `spark_gun_side.png` | 同じ銃の真横 | 2048×2048 | 透明・RGBA |
| 9 | `light_blade_gauntlet.png` | 左前腕・空の手・籠手から伸びる琥珀刃 | 2048×2048 | 透明・RGBA |
| 10 | `spec_haru_3d.md` | 本説明書・制作条件と修正記録 | — | — |

全PNGはsRGB。生成器の採用元画像は1254×1254。画像生成後、生成されたアルファを維持して高品質bicubicで2048×2048へ補間し、透明余白と配置を調整した。ネイティブ2048生成や新たな細部を作る超解像ではない。形状・背景の創作上の修正はすべてimage_genで行った。

全身4枚は髪先〜靴底を約1802px（画像高の約88%）へ揃え、上下約123pxの余白を確保。正投影を指示して生成し、胸の高さの視点と同じAポーズを維持した。真横では左右の手足が投影上重なり、斜め前では左右の横位置が変わる。画像は製図や同一3Dメッシュのレンダーではなく、細部の位置に生成上の微差があるため、以下の寸法・左右・取り付け説明を優先する。

## 参照とデザインの説明

- 開発元：`claude/busy-bell-oagnck` の `a49a88e`。作業：`art/w1-haru3d`。
- W0参照：`origin/art/w0` の `0a7434bf65569e4b24d6f77169fb1839cbe7de14`、`artbible_a_lineup_r3.png`、`artbible_a_keyvisual_r3.png`、`spec_a.md`。
- W0は別の参照用worktreeから読み、画像やブランチ履歴を作業ブランチへ取り込んでいない。
- 前回の試作結果 `docs/art_orders/W0_ハル3D試作の結果.md` のH-1・H-2・H-3・H-4に関係する不足情報を補う。
- 茶の短い房、大きいゴーグル、レンガ色の短い上着と太いズボン、白磁風の部分フレームを維持。
- 目・眉・口をはっきり見せ、口を閉じた落ち着いた表情を基本にした。
- 古代技術の白磁・真鍮・琥珀は広い色面として示し、金属の細かな反射や発光グローを焼き込まない。
- 全身では銃と展開した光刃を外し、籠手と固定装備を着けたまま手を軽く開いた。

## W0 A案r3から変えた点と理由

| 点 | 今回の扱い・理由 |
|---|---|
| 姿勢 | 腕を体から約35度開くAポーズ、肘・膝を伸ばし足を肩幅へ。空の手の指を分離。発注2章の変換条件に合わせた。 |
| 頭身 | W0の生成絵は約5頭身に見えるため、発注2章の4.3〜4.5頭身に合わせて頭と胴の比率を約4.4へ補正。15歳・155cm、顔・髪・服のデザインは継続。 |
| 光・背景・視点 | W0の大気感・影を外し、均一で柔らかい正面光、透明背景、正投影に近い視点へ。画像中に床・接地影・輪郭線・文字・寸法線を入れない。 |
| 武器 | 全身から別体の銃と展開刃を外した。籠手の外殻・射出口のレールは残す。単体画像で武器の形を示す。 |
| 発光表現 | 琥珀色は維持し、グロー・リムライト・背景への光漏れを外した。実装時の発光は別に設定する。 |
| 隠れていた部分 | 背中の帯と白い矩形パネルはW0キーに合わせて補足。ゴーグルの帯・後ろ髪・靴の踵と底は正面と矛盾しない形で解釈し、以下に明記。新しい装備や装飾は追加していない。 |
| 右肩 | 正面r3と今回の発注に従い、板は本人右肩1枚。キーで左右に板が見える曖昧さは、正面の設計を優先して統一。 |

## 正面だけでは読めない部分

### 背中の帯

X字に交差させない。左右の肩を回る2本の暗い帯が、背中でも平行に下がる。肩口から上着の下部へ続き、腰のベルトとは別の部品。W0キーに見える白い矩形を上背部の薄い非発光パネルとして、帯の間に置く。角を大きく面取りし、背中に重い機械やバックパックを追加しない。

### ゴーグルの帯と後ろ髪

レンズは額の上に置いたまま。暗い1本の帯がレンズ脇から耳の上を通り、後頭部を水平に回る。帯は髪の大きい房に沿わせ、細い浮遊部品にしない。後頭部は前髪と同じ短い大きな房の重なりで、長い襟足や細い毛束を足さない。

### 右肩・太ももの板

本人右肩だけに白磁の厚い板。前後の肩帯と上腕上部の暗い固定帯で支持し、板自体は剛体部品とする。右太ももの大きい矩形板は外側に配置し、腰帯から短い支持片でつながる。板は腰と大腿の間に追従させる方針で、前回試作のT-4（脚を振るとベルトから離れる問題）を3D側で調整する。画像だけでスキニングの重みを確定しない。

### 膝・靴・底

白い膝当ては膝の前面だけ。背面は暗い固定帯で、左右の琥珀の丸い継ぎ目が側面に見える。すねの中央は暗く、白い部分は細い側面の板。靴の白いブロックは爪先だけで、踵は茶。底は暗い厚いゴムで、上から見た足形は爪先の角を丸めた長方形。接地する下端は平ら、踵と爪先の間には浅い切り欠きを持たせる。細かな溝・鋲は足さない。底面そのものの専用画像は今回の表にはないため作っていない。

### 籠手と銃

籠手は本人左前腕。正面では画面右、背面では画面左。射出口は前腕の外側（小指側）のレール先端、手首付近。刃は前腕と平行に拳の先へ伸ばし、指や掌を貫通させない。光刃を手で握る柄は追加しない。銃は約30cmの独立した部品で、実装時に右手で握る。灰色の角形本体、真鍮のレール、琥珀の窓をW0から継続した。

## 色見本

以下は実装用の基準色。画像には弱い面の明度差とアンチエイリアスがあるため、全画素がhex値そのものという意味ではない。W0の基準色を画像のスポイト値で置き換えない。

| 部位 | 基準hex | 材質・扱い |
|---|---|---|
| 上着・ズボン・足首のカフ | #B75B43 | 帆布、マット |
| シャツ・肩板・太もも板・膝・すねの側板・爪先・背中パネル | #F3E9D2 | シャツは布、板は白磁風の非透過外殻 |
| 帯・手袋・外装の暗い支持部・ゴーグル枠・銃・靴底 | #444641 | 帯は布、手袋と底はゴム／革、枠は金属 |
| バックル・レール・継ぎ目 | #A98749 | つやを抑えた真鍮 |
| 髪・襟・靴・すねの中央 | #594333 | 髪の塊、布、革、暗いフレーム |
| レンズ・膝の継ぎ目・銃の窓・光刃 | #FFBC52 | 琥珀。画像ではグローなし、実装時に発光を別設定 |
| 肌（W0 specに数値がないため補足） | #E7B58D | 非写実的なマット肌色 |
| 虹彩（補足） | #795334 | 目のテクスチャ |
| 白目・歯（補足） | #FFF8EA | 目と表情のテクスチャ |
| 口・口内（補足） | #98684F | 表情のテクスチャ、周囲に輪郭線を足さない |

眉は髪色、瞳孔・目の濃い部分は暗いフレーム色を基準にする。

## 寸法と3D化の注意

- ハル：15歳、155cm、4.3〜4.5頭身（目標約4.4）。
- スパーク：全長約30cm。籠手：約25cm。展開刃の可視長：約45cm（W0提案）。
- 上下と左右は本人基準。正面と背面で画面上の左右が入れ替わる。右側の真横と右前45度で同じ右肩・右太ももの板を読む。
- 上着とシャツ、肩帯と板、太もも板、膝、ゴーグル、籠手、銃、光刃は必要に応じて別部品。銃と腕を一体化しない。
- 袖・肘・膝・股関節の境界を画像の強い影として焼かず、実際の骨と可動域に合わせてメッシュを構成する。
- 全身には表情の通常だけ。4表情の並びでは表情の指定を優先し、笑顔・驚き・痛みで口や瞼を変えている。
- 光刃を展開しているのは9番だけで、全身には描かない。これは納品表の9番の個別指定を優先したもの。
- 画像からTRELLIS.2で変換した結果の関節・指・隠れた側の形は別途確認が必要。今回の画像の見た目の確認を、3D変換の成功確認とは扱わない。

## 整合・形式の確認と修正記録

全身4枚を同じ高さ・余白で横に並べて目視比較。頭頂・顎・肩・腰・膝・靴底、右肩／右太もも／左籠手の左右、帯、爪先と踵を確認した。
初稿で出た光のにじみを除き、Aポーズの腕の開きと指の分離を修正。背面に誤って出た白い膝当てと踵の白い爪先形を除去し、暗い固定帯と茶の踵に修正した。真横と斜め前は本人右側の見え方へ揃えた。
白背景に残った微小な色むらは画像生成でアルファ背景へ修正。採用版をRGBAで保存し、sRGB、2048角、全身の画面高、透明な周囲と部品間の隙間を形式チェックした。比較用の並べ画像は確認後に削除し、納品には単独の指定ファイルを使う。

## 類似チェック

2026-09-28、W0で確認した公開参照と今回の人物・武器の形を再比較。参照作品の画像は生成器へ入力していない。
ロックマンDASH／X／ZERO／EXE系の禁止要素に対して、青いヘルメット・全身装甲・砲身化した腕を使わず、茶の短髪・レンガ色の布・開いたゴーグル・別体銃を維持。光刃は琥珀で、赤い鎧と長い金髪の組み合わせや緑の刃を使わない。
メトロイドの大肩装甲とアームキャノンに対して、右肩の小さい板と空の手、別体の小型銃を確認。FFVIIの放射状の金髪や巨大剣、キングダムハーツの鍵形武器と過大な靴に対して、W0の茶の房・小型銃・作業服を継続。
BotWの発光紋様と石の体は描かない。巨神獣・象主・ハウル・移動都市・ワンダと巨像に関する町／巡礼機は今回の画像に含まれない。追加のデザイン変更ではなく、W0の差分を維持する確認とした。

## 制作プロンプト

内蔵image_genでW0の自作画像を参照し、正面を基準に別方向・顔・単体武器を生成。その後、手・背面部品・背景・方向だけを対象に修正した。以下は全身の共通プロンプト。個別指定は納品物表の方向／表情／単体部品を追加し、透明背景修正では被写体の形と色を固定した。

```text
Use case: identity-preserve. Production image for image-to-3D conversion, NOT a beauty illustration.
Reference1 is our original W0 optionA lineup. ONLY far-left boy HARU is target, ignore other people/AI. Identity/design MUST remain this boy: fifteen years old,155cm,4.4 heads tall; large round cheeked head short chin, large brown eyes dark brows closed neutral small mouth, eyes unobscured. Short dark-brown hair in same large chunky swept wedges, NO individual hair strands. Big graphite-framed twin amber rectangular goggles on FOREHEAD open-head not helmet.
Exact outfit: short brick-red open jacket, dark brown turned collar and dark short sleeve cuffs, ivory undershirt visible in center; two dark vertical shoulder straps ending near waist; dark graphite waist belt single plain brass rectangular buckle; baggy brick-red trousers ending at knee; LARGE IVORY PLATE on person's RIGHT shoulder ONLY (front viewerLEFT), one tall slanted ivory rectangular thigh plate on person's RIGHT outer thigh ONLY (front viewerLEFT), small dark pouch on outer LEFT hip; BOTH knees ivory chunky caps over dark backing with round amber outer hinges; dark-brown slim shin surfaces with narrow ivory outer strips; brick ankle cuffs, umber chunky boots with ivory toe blocks and graphite thick simple soles. Fingerless dark gloves show bare fingers. LEFT forearm (front viewerRIGHT) ivory gauntlet dark end bands and brass narrow outer emitter rail, NO deployed blade. RIGHT forearm has ONLY dark wrist glove/cuff, bare arm otherwise. No pistol/no weapon/no AI.
Palette base colors brick#B75B43 ivory#F3E9D2 graphite#444641 brass#A98749 umber#594333 amber#FFBC52; skin#E7B58D eyeiris#795334 eyeoffwhite#FFF8EA. Flat matte albedo-like colors with VERY slight broad form shading only, bright neutral UNIFORM FRONTAL diffuse illumination, no realistic gloss/specular, no rim/backlight, no warm directional light, no ambient occlusion dark patches, no contours.
A-pose: stand straight, both arms straight and extend35degrees OUT from vertical downwards, elbows knees STRAIGHT, feet shoulder-width toes forward; hands EMPTY slightly open with FIVE clearly separated fingers, palms face in toward thighs (neutral forearm rotation). SAME pose/height in all views. Orthographic camera chestheight, no perspective or foreshortening. Square2048x2048 or larger, full body including hair tip and whole soles centered, subject height88% (top6%, bottom6%), ample symmetric margin. Truly transparent alpha PNG if possible, otherwise exact solid WHITE#FFFFFF, no gradients/paper/checker patterns. NO FLOOR, NO SHADOW underneath or anywhere on background, no groundline, no props, no writing/dimension/labels/logos/watermarks/signatures. No extra design details.
```
