

---

## 7. 第3弾（2026-09-29）：オルド・町・遺構・小物（そのまま貼れる）

4 本は別々の作業ブランチなので同時に出してよい。町と遺構はオルドに合わせるので、できればオルドの納品のあとに出す（同時の場合は発注書の説明に従って描いてもらう）。

### 7.1 W2-04：巡礼機オルド（設計＋3D 用）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w2-ordo（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案。artbible_a_machines・colorscript も）、art/w1-haru3d（3D 変換用の絵の塗り・光の手本、大きさの基準のハル 155cm）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w2-ordo（すでにあれば git checkout art/w2-ordo && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W2_04_巡礼機オルド.md（今回の発注書。雰囲気・設計の絵と、3D にするための絵の両方）
2. docs/art_orders/00_共通ルール.md
3. docs/art_orders/01_3D変換用の絵の条件.md（3D にするための絵のルール。特に 5 章と 5b 章）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png、artbible_a_colorscript.png、artbible_a_machines.png（画風・色の基準）
5. docs/planning/01_企画概要.md の世界観（巡礼機）と docs/design/10_シナリオ設計.md の冒頭（年表）

【作業】
- 画像生成機能を使い、発注書の納品物をすべて制作する。先に雰囲気・設計の絵で見た目を決め、同じデザインで 3D にするための絵を描く。
- 保存先：art/concepts/W2_ordo/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（共通ルール 6 章の項目）と spec_ordo_3d.md（01_3D変換用の絵の条件.md 6 章の項目。部品の寸法など）。
- 部品は 2m の升目に合わせ、同じキットの 3 枚（正面・真横・真上）は同じ縮尺・同じ並びにする。表面の画像は上下左右の端がつながること、遠景は左右の端がつながることを、並べて確かめる。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。

【守ること】
- art/concepts/W2_ordo/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない（看板の文字は読めない架空の文字）。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-04 ordo (design + 3D)"）、git push -u origin art/w2-ordo で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0、git worktree remove ../relic-haru3d
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

### 7.2 W2-05：オルド背町（雰囲気＋部品・表面・背景）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w2-town（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案。artbible_a_machines・colorscript も）、art/w1-haru3d（3D 変換用の絵の塗り・光の手本、大きさの基準のハル 155cm）、art/w2-ordo（オルド。あれば）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w2-town（すでにあれば git checkout art/w2-town && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   （あれば）git worktree add ../relic-ordo origin/art/w2-ordo
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W2_05_オルド背町.md（今回の発注書。雰囲気・設計の絵と、3D にするための絵の両方）
2. docs/art_orders/00_共通ルール.md
3. docs/art_orders/01_3D変換用の絵の条件.md（3D にするための絵のルール。特に 5 章と 5b 章）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png、artbible_a_colorscript.png、artbible_a_machines.png（画風・色の基準）
5. docs/design/30_レベルデザイン設計.md の第1章の町の配置（U1〜L5）

【作業】
- 画像生成機能を使い、発注書の納品物をすべて制作する。先に雰囲気・設計の絵で見た目を決め、同じデザインで 3D にするための絵を描く。
- 保存先：art/concepts/W2_town/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（共通ルール 6 章の項目）と spec_town_3d.md（01_3D変換用の絵の条件.md 6 章の項目。部品の寸法など）。
- 部品は 2m の升目に合わせ、同じキットの 3 枚（正面・真横・真上）は同じ縮尺・同じ並びにする。表面の画像は上下左右の端がつながること、遠景は左右の端がつながることを、並べて確かめる。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。

【守ること】
- art/concepts/W2_town/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない（看板の文字は読めない架空の文字）。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-05 town (mood + kit)"）、git push -u origin art/w2-town で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0、git worktree remove ../relic-haru3d（relic-ordo を作った場合はそれも）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

### 7.3 W2-06：背中の遺構（雰囲気＋部品・表面）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w2-ruins（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案。artbible_a_machines・colorscript も）、art/w1-haru3d（3D 変換用の絵の塗り・光の手本、大きさの基準のハル 155cm）、art/w2-ordo（オルド。あれば）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w2-ruins（すでにあれば git checkout art/w2-ruins && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   （あれば）git worktree add ../relic-ordo origin/art/w2-ordo
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W2_06_背中の遺構.md（今回の発注書。雰囲気・設計の絵と、3D にするための絵の両方）
2. docs/art_orders/00_共通ルール.md
3. docs/art_orders/01_3D変換用の絵の条件.md（3D にするための絵のルール。特に 5 章と 5b 章）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png、artbible_a_colorscript.png、artbible_a_machines.png（画風・色の基準）
5. docs/design/30_レベルデザイン設計.md の第1章（遺構 B1〜B4 の流れと仕掛け）

【作業】
- 画像生成機能を使い、発注書の納品物をすべて制作する。先に雰囲気・設計の絵で見た目を決め、同じデザインで 3D にするための絵を描く。
- 保存先：art/concepts/W2_back_ruins/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（共通ルール 6 章の項目）と spec_ruins_3d.md（01_3D変換用の絵の条件.md 6 章の項目。部品の寸法など）。
- 部品は 2m の升目に合わせ、同じキットの 3 枚（正面・真横・真上）は同じ縮尺・同じ並びにする。表面の画像は上下左右の端がつながること、遠景は左右の端がつながることを、並べて確かめる。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。

【守ること】
- art/concepts/W2_back_ruins/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない（看板の文字は読めない架空の文字）。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-06 ruins (mood + kit)"）、git push -u origin art/w2-ruins で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0、git worktree remove ../relic-haru3d（relic-ordo を作った場合はそれも）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

### 7.4 W2-07：小物・アイテム（設計＋3D 用）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w2-props（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案。artbible_a_machines・colorscript も）、art/w1-haru3d（3D 変換用の絵の塗り・光の手本、大きさの基準のハル 155cm）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w2-props（すでにあれば git checkout art/w2-props && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W2_07_小物.md（今回の発注書。雰囲気・設計の絵と、3D にするための絵の両方）
2. docs/art_orders/00_共通ルール.md
3. docs/art_orders/01_3D変換用の絵の条件.md（3D にするための絵のルール。特に 5 章と 5b 章）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png、artbible_a_colorscript.png、artbible_a_machines.png（画風・色の基準）
5. docs/design/20_ゲームシステム設計.md のアイテムと特殊武器の項

【作業】
- 画像生成機能を使い、発注書の納品物をすべて制作する。先に雰囲気・設計の絵で見た目を決め、同じデザインで 3D にするための絵を描く。
- 保存先：art/concepts/W2_props/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（共通ルール 6 章の項目）と spec_props_3d.md（01_3D変換用の絵の条件.md 6 章の項目。部品の寸法など）。
- 部品は 2m の升目に合わせ、同じキットの 3 枚（正面・真横・真上）は同じ縮尺・同じ並びにする。表面の画像は上下左右の端がつながること、遠景は左右の端がつながることを、並べて確かめる。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。

【守ること】
- art/concepts/W2_props/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない（看板の文字は読めない架空の文字）。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-07 props (design + 3D)"）、git push -u origin art/w2-props で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0、git worktree remove ../relic-haru3d
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```
