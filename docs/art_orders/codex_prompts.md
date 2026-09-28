# Codex への発注プロンプト集

Codex に下のプロンプトをそのまま貼り付けて使う。リポジトリの URL とブランチもプロンプトに含めてあるので、接続から納品（push）まで Codex が行う。

**前提**：Codex 側で GitHub への接続（このリポジトリへの読み書きの権限）を済ませておく。リポジトリを非公開にした場合も、権限があれば同じプロンプトで動く。
`<` `>` で囲んだ部分だけを書き換える。

- 発注書（`docs/art_orders/*.md`）が「何を描くか」、このプロンプトが「どう作業して納品するか」を指示する。
- Codex はブランチ `art/<波>` にコミットする。Claude はそのブランチを取り込んで確認・3D 化する。

---

## 1. W0：アートバイブル（最初に出す）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w0（元にするブランチから新しく作る。すでにあればそれを使う）

【最初に行うこと】
1. 上のリポジトリを取得し、ブランチ claude/busy-bell-oagnck を最新にする。
   git clone https://github.com/hassy0511/project-relic.git
   cd project-relic
   git checkout claude/busy-bell-oagnck
   git pull
2. 作業ブランチを作る：git checkout -b art/w0（すでにあれば git checkout art/w0 と git pull）
3. 下の「必ず読む文書」がリポジトリ内にあることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/00_共通ルール.md（すべての発注に共通するルール。最優先で守る）
2. docs/art_orders/W0_01_アートバイブル.md（今回の発注書）
3. docs/art_orders/README.md の「世界観の要約」

【作業】
- 画像生成機能を使い、発注書の「納品物」をすべて制作する。画風の違う 3 案（a・b・c）× 各 4 点。
- 保存先：art/concepts/W0_art_bible/
- ファイル名：発注書の指定どおり。<案> には a / b / c を入れる（例：artbible_a_keyvisual.png）。
- 説明書き：案ごとに spec_a.md / spec_b.md / spec_c.md を書く。項目は共通ルール 6 章と発注書 5 章。
- 類似チェック：描いたあと、共通ルール 5 章の作品と見比べる。似ている点は描き直し、確認した作品と直した点を spec に書く。

【守ること】
- art/concepts/ 以外のファイルは変更しない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。
- 発注書と違う判断をした場合は、理由を spec に書く。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 変更を 1 つのコミットにまとめ（メッセージ："art: W0 art bible (3 options)"）、git push -u origin art/w0 でリポジトリに送る。
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、各案の狙いを 3 行ずつで報告する。
```

---

## 2. W1・W2：個別の発注（アートバイブルの選定後）

発注書 1 本ごとに使う。`<発注書>`、`<選定案>`、`<波>` を書き換える。

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/<波>（元にするブランチから新しく作る。すでにあればそれを使う）

【最初に行うこと】
1. 上のリポジトリを取得し、ブランチ claude/busy-bell-oagnck を最新にする。
   git clone https://github.com/hassy0511/project-relic.git
   cd project-relic
   git checkout claude/busy-bell-oagnck
   git pull
2. 作業ブランチを作る：git checkout -b art/<波>（すでにあれば git checkout art/<波> と git pull）
3. 下の「必ず読む文書」がリポジトリ内にあることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/00_共通ルール.md（すべての発注に共通するルール。最優先で守る）
2. docs/art_orders/<発注書>（今回の発注書。例：W1_01_ハル.md）
3. 選定されたアートバイブル：art/concepts/W0_art_bible/ の案 <選定案>（artbible_<選定案>_*.png と spec_<選定案>.md）。画風・塗り・頭身・色の決め方は、これに厳密に合わせる。
4. 人物の設定の参考：docs/design/11_キャラクター設定.md の該当人物（人物以外の発注では不要）
5. すでに納品済みの関連する絵（art/concepts/ 内）。同じ人物・物が出てくる場合は、それと一致させる。

【作業】
- 画像生成機能を使い、発注書の「納品物」をすべて制作する。
- 保存先とファイル名：発注書の「納品先」と表の指定どおり。
- 三面図：共通ルール 3 章のとおり、全方向を 1 枚のシートに、同じ縮尺・正投影・基準線つきで描く。
- 顔アイコン：透過 PNG、1024×1024px。全表情で構図・大きさ・顔立ちをそろえ、三面図の顔と一致させる。
- 説明書き：保存先のフォルダに spec.md を書く（共通ルール 6 章の項目）。色は必ず hex で書く。
- 類似チェック：描いたあと、共通ルール 5 章の作品と、発注書の「避けるもの」と見比べる。似ている点は描き直し、結果を spec.md に書く。
- 一貫性の自己確認：納品前に、全ファイルで顔・髪型・色・部品の形が一致しているかを見直し、食い違いは直す。

【守ること】
- art/concepts/ 以外のファイルは変更しない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。
- 発注書と違う判断をした場合は、理由を spec.md に書く。
- 制作できなかった項目は、作らずに spec.md の冒頭に「未納品」と理由を書く。

【完了したら】
- 発注書 1 本につき 1 コミットにし（メッセージ例："art: W1-01 haru"）、git push -u origin art/<波> でリポジトリに送る。
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

---

## 3. 修正の依頼

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。納品済みの絵に修正依頼があります。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/<波>（修正対象を納品したブランチ）
- 最初に git clone（取得済みなら git fetch）し、git checkout art/<波> と git pull で最新にする。

【対象】
- フォルダ：art/concepts/<フォルダ名>/
- 元の発注書：docs/art_orders/<発注書>
- 守るルール：docs/art_orders/00_共通ルール.md

【修正指示】
1. <ファイル名>：<何をどう直すか>
2. <ファイル名>：<何をどう直すか>

【作業】
- 修正版は元のファイル名の末尾に _r2 を付けて追加する（_r2 が既にあれば _r3）。元のファイルは消さない。
- 修正によって他の納品物と食い違いが出る場合は、そのファイルも同じ規則で修正版を作る。
- spec.md の末尾に「修正履歴」を追記する（日付、対象、直した内容）。

【完了したら】
- 1 コミットで追加し（メッセージ例："art: W1-01 haru r2"）、git push で同じブランチに送る。
- 直したファイルの一覧を報告する。
```

---

## 4. W1-00：ハル　3D 変換用の絵（そのまま貼れる）

W0 A案の絵はブランチ `art/w0` にあるので、別のフォルダに取り出して参照する（作業ブランチには取り込まない）。

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w1-haru3d（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ：art/w0（W0 A案の絵。読むだけで、作業ブランチには取り込まない）

【最初に行うこと】
1. リポジトリを取得し、ブランチ claude/busy-bell-oagnck を最新にする。
   git clone https://github.com/hassy0511/project-relic.git
   cd project-relic
   git checkout claude/busy-bell-oagnck
   git pull
2. 作業ブランチを作る：git checkout -b art/w1-haru3d（すでにあれば git checkout art/w1-haru3d と git pull）
3. W0 の絵を別のフォルダに取り出す（参照用）：
   git fetch origin art/w0
   git worktree add ../project-relic-w0 origin/art/w0
   参照するファイル：../project-relic-w0/art/concepts/W0_art_bible/ の artbible_a_lineup_r3.png、artbible_a_keyvisual_r3.png、spec_a.md
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W1_00_ハル_3D変換用.md（今回の発注書。2 章の「3D にしやすい条件」を最優先で守る）
2. docs/art_orders/00_共通ルール.md
3. ../project-relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_lineup_r3.png（ハルのデザインと色の基準）
4. docs/art_orders/W0_ハル3D試作の結果.md（前回の 3D 試作の結果。参考）

【作業】
- 画像生成機能を使い、発注書 3 章の納品物を制作する。必須のものを先に作る。
- 保存先：art/concepts/W1_haru_3d/　ファイル名は発注書の表のとおり。
- デザインは W0 A案 r3 のハルから変えない。姿勢・光・背景・視点だけを、発注書 2 章の条件に合わせる。
- 1〜4（全身の 4 方向）は、同じ人物・同じ服・同じ姿勢・同じ大きさにそろえる。納品前に 4 枚を並べて見比べ、食い違いを直す。
- 説明書き：spec_haru_3d.md（発注書 4 章の項目）。

【守ること】
- art/concepts/W1_haru_3d/ 以外のファイルは変更しない。W0 の絵を作業ブランチにコピーしない。
- 床や影、遠近感、武器を持たせること、文字や寸法線を入れることをしない（発注書 2 章）。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。
- 制作できなかった項目は、作らずに spec_haru_3d.md の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-00 haru for 3D conversion"）、git push -u origin art/w1-haru3d でリポジトリに送る。
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 最後に参照用のフォルダを片付ける：git worktree remove ../project-relic-w0
- 納品したファイルの一覧と、W0 A案から変えた点（あれば）を 5 行以内で報告する。
```

---

## 5. 第1弾（2026-09-28）：ハルの追加の絵・ナゴミ・ヤーナ（そのまま貼れる）

3 本は別々の作業ブランチなので、別々の Codex の作業として同時に出してよい。
ナゴミとヤーナは**設計の絵と 3D 変換用の絵を 1 回で納品**してもらう（往復を減らすため）。

### 5.1 W1-00b：ハルの追加の絵

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/w1-haru3d（前回ハルの 3D 変換用の絵を納品したブランチ。そこに追加する）
- 発注書を読むブランチ：claude/busy-bell-oagnck

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
2. git checkout art/w1-haru3d && git pull
3. 発注書は別のフォルダに取り出して読む：
   git worktree add ../relic-docs origin/claude/busy-bell-oagnck
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. ../relic-docs/docs/art_orders/W1_00b_ハル_追加の絵.md（今回の発注書）
2. ../relic-docs/docs/art_orders/01_3D変換用の絵の条件.md（3D 変換用の絵の条件。最優先で守る）
3. art/concepts/W1_haru_3d/spec_haru_3d.md と、同じフォルダの全身・顔の絵（デザインと色の基準。変えない）
4. ../relic-docs/docs/art_orders/haru_r_trial/compare_views.jpg（前回の絵から作った 3D。どこが足りなかったかの参考）

【作業】
- 画像生成機能を使い、発注書 2 章の納品物をすべて制作する。
- 保存先：art/concepts/W1_haru_3d/（既存の絵は消さない・上書きしない）
- 全身の追加の絵は、既存の haru_3d_front.png と同じ大きさ・同じ位置（足の裏の行、頭のてっぺんの行、体の中心の列）にそろえる。納品前に既存の絵と並べて測り、数値を spec_haru_3d_add.md に書く。
- 斜めの絵はちょうど 45 度にする（左右の足の間隔が正面の約 0.7 倍）。

【守ること】
- art/concepts/W1_haru_3d/ 以外のファイルは変更しない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・文字を入れない。
- 制作できなかった項目は、作らずに spec_haru_3d_add.md の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-00b haru additional views for 3D"）、git push origin art/w1-haru3d で送る。
- 最後に git worktree remove ../relic-docs で片付ける。
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、自己確認の数値（足の裏の行・頭のてっぺんの行・45 度の比）を報告する。
```

### 5.2 W1-02：ナゴミ（設計＋3D 変換用）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w1-nagomi（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案）、art/w1-haru3d（ハルの 3D 変換用の絵）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w1-nagomi（すでにあれば git checkout art/w1-nagomi && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W1_02_ナゴミ.md（今回の発注書。3 章＝設計の絵、4 章＝3D 変換用の絵）
2. docs/art_orders/00_共通ルール.md（設計の絵のルール）
3. docs/art_orders/01_3D変換用の絵の条件.md（3D 変換用の絵のルール。4 章の絵ではこちらを優先）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色の基準）
5. ../relic-haru3d/art/concepts/W1_haru_3d/ の絵と spec_haru_3d.md（ハル。大きさの比較と、琥珀色などの共通の色）
6. docs/design/11_キャラクター設定.md のナゴミ

【作業】
- 画像生成機能を使い、発注書 3 章と 4 章の納品物をすべて制作する。先に 3 章でデザインを決め、同じデザインで 4 章を描く。
- 保存先：art/concepts/W1_nagomi/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（3 章。共通ルール 6 章の項目）と spec_nagomi_3d.md（4 章。01_3D変換用の絵の条件.md 6 章の項目）。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。
- 一貫性の自己確認：3 章と 4 章の絵で、形・分割線・色が一致しているかを見直し、食い違いは直す。

【守ること】
- art/concepts/W1_nagomi/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-02 nagomi (design + 3D)"）、git push -u origin art/w1-nagomi で送る。
- git worktree remove ../relic-w0 と git worktree remove ../relic-haru3d で片付ける。
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

### 5.3 W1-03：ヤーナ（設計＋3D 変換用）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w1-yana（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案）、art/w1-haru3d（ハルの 3D 変換用の絵）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w1-yana（すでにあれば git checkout art/w1-yana && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W1_03_ヤーナ.md（今回の発注書。3 章＝設計の絵、4 章＝3D 変換用の絵）
2. docs/art_orders/00_共通ルール.md（設計の絵のルール）
3. docs/art_orders/01_3D変換用の絵の条件.md（3D 変換用の絵のルール。4 章の絵ではこちらを優先）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色の基準）
5. ../relic-haru3d/art/concepts/W1_haru_3d/ の絵と spec_haru_3d.md（ハル。塗り・光・頭身の決め方をそろえる。並べたときに同じ世界の人物に見えること）
6. docs/design/11_キャラクター設定.md のヤーナ

【作業】
- 画像生成機能を使い、発注書 3 章と 4 章の納品物をすべて制作する。先に 3 章でデザインを決め、同じデザインで 4 章を描く。
- 保存先：art/concepts/W1_yana/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（3 章。共通ルール 6 章の項目）と spec_yana_3d.md（4 章。01_3D変換用の絵の条件.md 6 章の項目）。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。
- 全身の 3D 変換用の絵は、右腕の義手があるので 6 方向（front、back、side_right、side_left、front_right45、front_left45）を描き、足の裏の行・頭のてっぺんの行・体の中心の列を全画像でそろえる。数値を spec_yana_3d.md に書く。
- 一貫性の自己確認：3 章と 4 章の絵で、形・分割線・色が一致しているかを見直し、食い違いは直す。

【守ること】
- art/concepts/W1_yana/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-03 yana (design + 3D)"）、git push -u origin art/w1-yana で送る。
- git worktree remove ../relic-w0 と git worktree remove ../relic-haru3d で片付ける。
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```
