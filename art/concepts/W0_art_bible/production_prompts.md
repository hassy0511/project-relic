# W0 制作プロンプト

内蔵 image_gen を使用。既存作品の画像・写真は生成に入力していない。修正はこの作業で新規生成した絵のみを参照して実施。次の共通文・案別文・納品物別文を連結して初稿を生成した。末尾の出力サイズ等の追加指定、修正指示は各specの修正履歴も参照。

## 共通プロンプト

```text
Original concept art for Japanese game Ark Walker. Bright retrofuturistic adventure, distant future, rust-red desert and enormous remains of a civilization lost 1000 years ago. Ancient technology is smooth porcelain ivory shells, brass joints, amber light in discrete recessed lenses, NEVER luminous patterns on stone. Hero Haru age 15 height155cm, dark umber short blocky hair, brick-red and cream workwear, graphite partial external frame on shoulders hips shins, amber lens accents, open top visor/goggles no helmet, separate compact handheld energy pistol RIGHT hand, LEFT wrist gauntlet emits pale amber blade; no arm cannon, no powered full armor. AI spherical25cm segmented budlike ivory shell amber center. Entirely original forms, large readable low/mid-poly shapes, no brands logos signatures watermarks, no existing artwork tracing or compositing. No blue dominant hero, no green blade.
```

## 案 a

```text
Option A: 5-head proportions for youths, adults around5.5, chunky faceted shapes, modest old 3D game warmth realized at high resolution, hand-painted diffuse textures, restrained worn edges, no black outlines, two broad diffuse light values. Colors brick#B75B43 ivory#F3E9D2 graphite#444641 brass#A98749 umber#594333 amber#FFBC52. Pilgrim400m long: six straight piston legs (three each side), tall rectangular bridged industrial undercarriage, stepped open U-shaped deck, town low modular flatroof blocks in two linear strips bordering central courtyard, no animal head tail shell or castle silhouette.
```

## 案 b

```text
Option B: 5.75-head youths,6-head adults, crisp anime cel render, thin dark umber contour lines, 1-2 shadow bands, small flat highlights, no texture noise. Colors terracotta#C6634A ivory#F6EFDC charcoal#3B3F43 brass#B19357 olive#727859 amber#FFBD45. Pilgrim400m: eight vertically articulated rectangular hydraulic legs (four each side), four separated elevated square deck modules connected by wide bridges along a straight industrial backbone, low town courtyards with small trapezoid roofs, no head tail animal shell castle, no gigantic wheels.
```

## 案 c

```text
Option C: 6.25-head youths6.5-head adults, soft hand-painted gouache illustration, broad matte brush marks, quiet warm contour accents no uniform outline, softened shadow edge but clearly separated silhouette. Colors red earth#AC604E chalk#EEE4CF dark brown#50433E brass#AA885B sage#8B927B amber#F4B85C. Pilgrim400m: four pairs (8 total) broad loadbearing rectangular feet on straight hinged columns, two offset long terraced cargo decks on exposed parallel beams, town low wind sheltered pavilions along a long narrow central public lane, boxlike machinery no head animal shell tail castle.
```

## key

```text
Asset: keyvisual, landscape exact16:9 preferably3840x2160 PNG sRGB. Dawn rust desert, immense pilgrim walking mid stride, ENTIRE machine and all leg systems clearly visible in lower middle distance from elevated rear three-quarter viewpoint. A town is visibly built on its decks. Foreground is the edge of one town deck WITH structural support visibly joining the same machine, Haru and hovering amber spherical AI at shoulder looking outward toward horizon; character small enough to emphasize scale but recognizable frame and visor. Wide endless dunes buried ancient rectangular ruins, luminous hopeful dawn. No text. Scene background exception to neutral design-sheet background.
```


## lineup

```text
Asset: front orthographic full-body lineup on solid #E6E6E6 background, wide landscape4096x2048 or greater long edge2048. Exactly SIX subjects left to right HARU, SPHERICAL AI, YANA, VOLTA, KOU, ALDEN. Five humans same scale, feet on single thin ground baseline, neutral front views entirely head to toe uncropped. Haru155cm, AI diameter25cm floating in its column at Haru shoulder height; Yana38-year woman172cm broad stocky muscular workshop owner with mechanical RIGHT arm (viewer left) warm work apron and tied brown hair; Volta17girl150cm baggy olive coveralls large separate wrench messy short blocky copper curls; Kou45man180cm weathered long umber coat with SAME visor goggles shape as Haru, no sword, understated short hair; Alden40sman185cm platinum SHORT hair, long ivory/gold robe with simple large rectangular seam panels, faint amber ring iris. Ground height common; relative heights accurate 155:172:150:180:185, AI25cm (about1/6 Haru height). Haru pistol separate RIGHT hand (viewer left), inactive amber sword gauntlet LEFT wrist (viewer right). Arms held gently outward for clarity. No extra people, no helmet, no spikes or famous hairstyles, no text except optional small height labels in empty margin. Flat even lighting. All silhouettes distinctly separated. Not a turnaround.
```


## machines

```text
Asset: mechanical style sheet on solid #E6E6E6 neutral background landscape long edge>=2048. LEFT: detailed original autonomous ruin sentry90cm tall, blunt rectangular porcelain prism central housing with brass edge joints, two compact straight articulated legs with broad feet, small offset recessed amber circular sensor, external short fork clamp tools, NO human face NO stone engravings NO tentacles NO guns on arms. Show front and right-side orthographic at equal scale, fine common groundline. RIGHT two thirds: precise solid dark silhouette of the specified400m pilgrim and town, clean SIDE elevation and small FRONT silhouette, all legs visible straight rigid struts and broad feet, bridge truss undercarriage, original industrial architecture, no animal or creature anatomy. Tiny180cm human scale tick beneath. Show town visibly integral to machine silhouette as low modular buildings, far lower than massive undercarriage. Sentry views have their own scale distinct from400m machine, never imply same scale. Only small margin labels if used. Clear modeling reference.
```


## colors

```text
Asset: regional colorscript on #E6E6E6 ground, landscape>=2048 long edge, exactly3x3 grid NINE distinct environment thumbnail panels. Each panel has one clean landscape thumbnail and FIVE equal solid representative color swatches in its own margin below. No extra panels. Read row-major: 1 Ordo back-town low modular pavilions brass beams dawn cozy people-free; 2 rust sand sea red dunes and submerged angular city; 3 mirror salt plain brilliant white salt with giant reflective rectangular tower; 4 swallowed tower huge tall industrial tower piercing clouds through green rainforest; 5 frozen plant ice-enclosed observation facility pale cyan ice dark window slit; 6 floating rock reef rust flat-bottom blocky rocks levitate across sky due gravity disorder; 7 dawn fortress enemy stronghold geometrical fortified terraces coral sunrise; 8 Terminus cliff edge immense congregation of several original pilgrim machines at end of earth; 9 deep archive buried sleep facility with orderly closed ivory sleep bays discrete amber lenses dark-plum interior, no capsules granting armor. Match option rendering. Clearly different palettes and readable spaces. Below each five swatches place hex notation accurately when possible. No brand lettering, no unnecessary written titles; numbering1-9 permitted.
```

## 出力の形式調整

生成器の実出力はキー1672×941、並び図・機械1774×887、地域1536×1024。内蔵生成器への寸法指定・再生成でも実サイズは変わらなかったため、描き直し完了後に高品質bicubicで納品寸法へ補間し、PNGにsRGBチャンクを付与。新しい細部を生成する超解像ではない。画像の創作上の変更はすべてimage_genで実施。

## 3D向け人物改訂（ユーザーの追加指示）

既存の納品画像のみを編集参照。Aは低ポリゴンの面、Bは単純セル陰影、Cはマットな広い色面。肩・腰・すねの部分フレーム、銃とガントレットの左右、人物とAIの実装寸法は維持。並び図の改訂後、それを人物参照にキーを編集。Bの初回改訂でAIが欠落したため6列へ再生成し、部分フレームも補正。Cはコウのゴーグルを補正。採用ファイルは各specの納品物を参照。

```text
Create a replacement CHARACTER LINEUP for original game Arc Walker. Reference is ONLY our own previous design; retain identities/colors and roles but RADICALLY simplify shapes for affordable real-time 3D. Full-body front orthographic, five humans plus one small floating AI in separate column, left to right HARU, AI, YANA, VOLTA, KOU, ALDEN. All feet same baseline; nominal heights 155, sphere diameter25,172,150,180,185 cm. Pale gray #E6E6E6 plain background, no writing required. Large margin, uncropped.
This must look like simplified stylized GAME MODELS, not detailed anime concept paintings. Compact broad block-shaped body parts, broad heads, simplified painted eyes/brows/tiny mouth; NO realistic nose nostrils, lips, skin highlights or anatomical muscle definition. Hair 5-7 solid rounded wedges, no individual strands or spiky starburst. Clothes single broad unwrinkled surfaces, 1 broad fold max per joint, NO stitching/rivets/small buckles/hanging straps/creases/weathering speckles. Shoes simple modest wedges not giant mascot shoes. NO blue armor, arm cannons, pointed helmets, green blades or key weapons. Major 5 colors+amber.
Haru teenage boy short brown hair, brick-red short work jacket cream shirt, red work trousers, open amber goggles on forehead not helmet, THREE simple ivory armor plates shoulder/hip/shin. RIGHT hand(screen LEFT) grips separate small pistol pointed down; LEFT forearm(screen RIGHT) simple gauntlet with amber light blade down. AI small faceted ivory bud sphere with four thick shell panels amber center, actual25cm small scale floating around Haru shoulder height. Yana mature38 sturdy woman warm brown tied hair one simple bun, wide shoulders rectangular apron and olive trousers, RIGHT mechanical arm(screen LEFT) reduced to ivory upperarm, forearm and simple working hand with dark hinge; other arm natural. Volta17 short copper hair in rounded chunks, baggy olive coveralls, big clearly OPEN-JAW spanner in RIGHT hand screenLEFT. Kou45 mature angular face short brown hair simplified painted stubble, same open goggles as Haru, long dark brown coat one rectangular pocket, no decorative harness. Alden40s man short platinum hair swept in 5 blocks, dignified broad face, straight ivory and brass robe with TWO broad rectangular bands no intricate motifs, faint amber iris rings.

```

```text
Edit ONLY Haru and the nearby floating AI in the FIRST image, our original keyvisual. Preserve the scenery, warm dawn, architecture, gigantic machine, camera, railing, and composition as closely as possible. Hero remains back-view standing on deck of SAME machine. SECOND image is our new character design reference: replace foreground boy with its far-left Haru design seen from back. Clearly enlarged head, shorter compact limbs about4-head target, large hair wedges5-7, smooth broad brick workwear surfaces no creases, simple ivory plates, modest simple shoes, no rivets, strap clutter or tiny hardware. Do not simply preserve old detailed silhouette. RIGHT hand screenRIGHT grips separate small energy pistol down, LEFT gauntlet screenLEFT has amber blade pointing down. Goggles open on forehead, no helmet. AI25cm ivory segmented bud sphere at shoulder, about1/6 hero height, simple shell panels amber eye. Warm light on broad planes with no realistic character material texture. Landscape exact16:9. No text/brand/signature/watermark. Preserve background inhabitants as small simple silhouettes.
```
