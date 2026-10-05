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

---

## 6. 第2弾（2026-09-29）：番機・閂・第1章の住人（そのまま貼れる）

3 本は別々の作業ブランチなので、同時に出してよい。閂は番機のデザイン言語に合わせるので、できれば番機の納品のあとに出す（同時に出した場合は、発注書の「デザイン言語」に従って描いてもらう）。

### 6.1 W2-02：番機 5 種（設計＋3D 変換用）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w2-banki（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案）、art/w1-haru3d・art/w1-yana・art/w1-nagomi（3D 変換用の絵の塗り・光の手本）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w2-banki（すでにあれば git checkout art/w2-banki && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-yana origin/art/w1-yana
   git worktree add ../relic-nagomi origin/art/w1-nagomi
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W2_02_番機_第1章.md（今回の発注書。設計の絵と 3D 変換用の絵の両方）
2. docs/art_orders/00_共通ルール.md（設計の絵のルール）
3. docs/art_orders/01_3D変換用の絵の条件.md（3D 変換用の絵のルール。3D 変換用の絵ではこちらを優先）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色の基準）
5. ../relic-haru3d/art/concepts/W1_haru_3d/、../relic-yana/art/concepts/W1_yana/、../relic-nagomi/art/concepts/W1_nagomi/ の 3D 変換用の絵と spec（塗り・光・頭身の手本。大きさの比較の基準はハル 155cm）
6. docs/design/30_レベルデザイン設計.md の第1章（番機が出てくる場所と戦い方。参考）

【作業】
- 画像生成機能を使い、発注書の設計の絵と 3D 変換用の絵をすべて制作する。先に設計の絵でデザインを決め、同じデザインで 3D 変換用の絵を描く。
- 保存先：art/concepts/W2_banki/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（設計の絵。共通ルール 6 章の項目）と spec_banki_3d.md（3D 変換用の絵。01_3D変換用の絵の条件.md 6 章の項目。自己確認の数値を含む）。
- 3D 変換用の絵は、向きごとに大きさと位置をそろえ（01_3D変換用の絵の条件.md）、納品前に測って数値を spec に書く。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。
- 一貫性の自己確認：設計の絵と 3D 変換用の絵で、形・部品の数・色が一致しているかを見直し、食い違いは直す。

【守ること】
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトでモデルを作って撮った画像や、プログラムで描いた図形の画像は不可。.blend・スクリプトなどのファイルも納品しない。
- art/concepts/W2_banki/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-02 banki (design + 3D)"）、git push -u origin art/w2-banki で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-haru3d・relic-yana・relic-nagomi も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

### 6.2 W2-03：大番機「閂」（設計＋3D 変換用）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w2-kannuki（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案）、art/w1-haru3d・art/w1-yana・art/w1-nagomi（3D 変換用の絵の塗り・光の手本）、art/w2-banki（番機。あれば）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w2-kannuki（すでにあれば git checkout art/w2-kannuki && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-yana origin/art/w1-yana
   git worktree add ../relic-nagomi origin/art/w1-nagomi
   （あれば）git worktree add ../relic-banki origin/art/w2-banki
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W2_03_大番機_閂.md（今回の発注書。設計の絵と 3D 変換用の絵の両方）
2. docs/art_orders/00_共通ルール.md（設計の絵のルール）
3. docs/art_orders/01_3D変換用の絵の条件.md（3D 変換用の絵のルール。3D 変換用の絵ではこちらを優先）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色の基準）
5. ../relic-haru3d/art/concepts/W1_haru_3d/、../relic-yana/art/concepts/W1_yana/、../relic-nagomi/art/concepts/W1_nagomi/ の 3D 変換用の絵と spec（塗り・光・頭身の手本。大きさの比較の基準はハル 155cm）
6. 番機のデザイン言語：ブランチ art/w2-banki がすでにあれば ../relic-banki/art/concepts/W2_banki/ の banki_family.png と spec.md に合わせる。まだ無ければ、発注書 W2_02_番機_第1章.md の「デザイン言語」に従う

【作業】
- 画像生成機能を使い、発注書の設計の絵と 3D 変換用の絵をすべて制作する。先に設計の絵でデザインを決め、同じデザインで 3D 変換用の絵を描く。
- 保存先：art/concepts/W2_kannuki/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（設計の絵。共通ルール 6 章の項目）と spec_kannuki_3d.md（3D 変換用の絵。01_3D変換用の絵の条件.md 6 章の項目。自己確認の数値を含む）。
- 3D 変換用の絵は、向きごとに大きさと位置をそろえ（01_3D変換用の絵の条件.md）、納品前に測って数値を spec に書く。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。
- 一貫性の自己確認：設計の絵と 3D 変換用の絵で、形・部品の数・色が一致しているかを見直し、食い違いは直す。

【守ること】
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトでモデルを作って撮った画像や、プログラムで描いた図形の画像は不可。.blend・スクリプトなどのファイルも納品しない。
- art/concepts/W2_kannuki/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-03 kannuki (design + 3D)"）、git push -u origin art/w2-kannuki で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-haru3d・relic-yana・relic-nagomi・relic-banki も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

### 6.3 W2-01：第1章の住人（設計＋3D 変換用）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck
- 作業ブランチ：art/w2-townsfolk（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案）、art/w1-haru3d・art/w1-yana・art/w1-nagomi（3D 変換用の絵の塗り・光の手本）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w2-townsfolk（すでにあれば git checkout art/w2-townsfolk && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-yana origin/art/w1-yana
   git worktree add ../relic-nagomi origin/art/w1-nagomi
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W2_01_第1章の住人.md（今回の発注書。設計の絵と 3D 変換用の絵の両方）
2. docs/art_orders/00_共通ルール.md（設計の絵のルール）
3. docs/art_orders/01_3D変換用の絵の条件.md（3D 変換用の絵のルール。3D 変換用の絵ではこちらを優先）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色の基準）
5. ../relic-haru3d/art/concepts/W1_haru_3d/、../relic-yana/art/concepts/W1_yana/、../relic-nagomi/art/concepts/W1_nagomi/ の 3D 変換用の絵と spec（塗り・光・頭身の手本。大きさの比較の基準はハル 155cm）
6. docs/design/11_キャラクター設定.md の「オルド背町の住人（第1章）」

【作業】
- 画像生成機能を使い、発注書の設計の絵と 3D 変換用の絵をすべて制作する。先に設計の絵でデザインを決め、同じデザインで 3D 変換用の絵を描く。
- 保存先：art/concepts/W2_townsfolk/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（設計の絵。共通ルール 6 章の項目）と spec_townsfolk_3d.md（3D 変換用の絵。01_3D変換用の絵の条件.md 6 章の項目。自己確認の数値を含む）。
- 3D 変換用の絵は、向きごとに大きさと位置をそろえ（01_3D変換用の絵の条件.md）、納品前に測って数値を spec に書く。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。
- 一貫性の自己確認：設計の絵と 3D 変換用の絵で、形・部品の数・色が一致しているかを見直し、食い違いは直す。

【守ること】
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトでモデルを作って撮った画像や、プログラムで描いた図形の画像は不可。.blend・スクリプトなどのファイルも納品しない。
- art/concepts/W2_townsfolk/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-01 townsfolk (design + 3D)"）、git push -u origin art/w2-townsfolk で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-haru3d・relic-yana・relic-nagomi も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

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
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトでモデルを作って撮った画像や、プログラムで描いた図形の画像は不可。.blend・スクリプトなどのファイルも納品しない。
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
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトでモデルを作って撮った画像や、プログラムで描いた図形の画像は不可。.blend・スクリプトなどのファイルも納品しない。
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
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトでモデルを作って撮った画像や、プログラムで描いた図形の画像は不可。.blend・スクリプトなどのファイルも納品しない。
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
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトでモデルを作って撮った画像や、プログラムで描いた図形の画像は不可。.blend・スクリプトなどのファイルも納品しない。
- art/concepts/W2_props/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない（看板の文字は読めない架空の文字）。
- 制作できなかった項目は、作らずに spec の冒頭に「未納品」と理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-07 props (design + 3D)"）、git push -u origin art/w2-props で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0、git worktree remove ../relic-haru3d
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

---

## 8. 描き直しの依頼（2026-09-29）：番機・閂

W2-02・W2-03 は、Codex が画像生成ではなく Blender で単純なモデルを作って撮った画像を納品したため、描き直しを依頼する。番機を先に出し、閂は番機の描き直しが届いてから出すのがよい。

### 8.1 W2-02：番機 5 種の描き直し

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。前回の納品（W2-02 番機 5 種）は、発注の意図と違うため**描き直し**をお願いします。

【前回の納品の問題】
- 発注書と作業指示には「画像生成機能を使い、設計の絵（デザイン）を描いてから、同じデザインで 3D 変換用の絵を描く」とありました。
  ところが納品物は、Blender で単純な立体を組んだモデルを作り、それを撮った画像でした（banki_models.blend・generate_banki.py など も入っていました）。
- これでは困ります。理由：
  1. **デザインの段階が抜けています**。箱と円柱を組んだだけの形で、アートバイブル（W0 A案）の手描きの絵の味・世界観がありません。とくに歩哨型は箱に脚が付いただけに見え、敵として魅力も種類の見分けやすさも足りません。
  2. 3D にするのは Claude の役割です。作画担当にお願いしているのは「形と色が正確に読み取れる、魅力のあるデザインの絵」です。
  3. 発注にない作り方に変えたのに、その理由も確認もありませんでした。発注と違う判断をするときは、必ず spec の冒頭に書き、できないことは「未納品」として報告してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/w2-banki（前回納品したブランチ。そこに追加する）
- 発注書を読むブランチ：claude/busy-bell-oagnck（最新にすること。発注書と共通ルールに「3D ソフトの画像は不可」を追記した）
- 参照するブランチ（読むだけ）：art/w0（W0 A案。特に artbible_a_machines.png、artbible_a_colorscript.png）、art/w1-haru3d・art/w1-nagomi（3D 変換用の絵の塗り・光の手本）

【最初に行うこと】
1. git fetch --all、git checkout art/w2-banki && git pull
2. 発注書と参照の絵を別のフォルダに取り出す：
   git worktree add ../relic-docs origin/claude/busy-bell-oagnck
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-nagomi origin/art/w1-nagomi
3. 必ず読む：../relic-docs/docs/art_orders/W2_02_番機_第1章.md、../relic-docs/docs/art_orders/00_共通ルール.md、../relic-docs/docs/art_orders/01_3D変換用の絵の条件.md（2 章の「描き方」の行を必ず読む）、../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png・artbible_a_machines.png

【作業】
- **画像生成機能で描く**。Blender などの 3D ソフト、プログラムで描いた図形は使わない。
- まず設計の絵（発注書の設計の絵の表：三面図・大きさの比較・関節の図解・攻撃の流れ・状態・5 種の並び（banki_family））を描き、アートバイブルの機械の絵と並べて、同じ世界の機械に見えるかを確かめる。5 種それぞれに、ひと目で分かるシルエットと、生き物のような愛嬌・不気味さ（千年命令を守り続ける機械らしさ）を持たせる。
- 次に、同じデザインで 3D 変換用の絵（発注書の「3D 変換用の絵」の表）を描く。向きごとの大きさ・位置をそろえ、斜めは 45 度にする（01_3D変換用の絵の条件.md）。測った数値を spec に書く。
- ファイル名は発注書どおりに、末尾に _r2 を付ける（例：sentry_turnaround_r2.png、sentry_3d_front_r2.png）。前回のファイルは消さない。
- spec_r2.md と spec_banki_3d_r2.md に、共通ルール 6 章と 01 の 6 章の項目を書く。冒頭に「前回（3D ソフトの画像）からの描き直し」と書く。

【守ること】
- 絵は必ず画像生成機能で描く。3D ソフトの画像、プログラムで描いた図形の画像、.blend・スクリプトなどのファイルは納品しない。
- art/concepts/W2_banki/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。
- 発注書と違う判断をする場合、描けないものがある場合は、作業を進める前に spec の冒頭に理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-02 banki r2 (hand-drawn redo)"）、git push origin art/w2-banki で送る。
- 取り出したフォルダを片付ける：git worktree remove で ../relic-docs、../relic-w0、../relic-haru3d、../relic-nagomi
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。前回の作り方を選んだ理由も 1 行で報告する。
```

### 8.2 W2-03：大番機「閂」の描き直し

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。前回の納品（W2-03 大番機「閂」）は、発注の意図と違うため**描き直し**をお願いします。

【前回の納品の問題】
- 発注書と作業指示には「画像生成機能を使い、設計の絵（デザイン）を描いてから、同じデザインで 3D 変換用の絵を描く」とありました。
  ところが納品物は、Blender で単純な立体を組んだモデルを作り、それを撮った画像でした（kannuki_source.blend・generate_kannuki.py など も入っていました）。
- これでは困ります。理由：
  1. **デザインの段階が抜けています**。箱と円柱を組んだだけの形で、アートバイブル（W0 A案）の手描きの絵の味・世界観がありません。円筒に腕を付けただけの形で、第1章のボスとしての迫力と、「閂（扉のかんぬき）」「錠前核」らしさが足りません。
  2. 3D にするのは Claude の役割です。作画担当にお願いしているのは「形と色が正確に読み取れる、魅力のあるデザインの絵」です。
  3. 発注にない作り方に変えたのに、その理由も確認もありませんでした。発注と違う判断をするときは、必ず spec の冒頭に書き、できないことは「未納品」として報告してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/w2-kannuki（前回納品したブランチ。そこに追加する）
- 発注書を読むブランチ：claude/busy-bell-oagnck（最新にすること。発注書と共通ルールに「3D ソフトの画像は不可」を追記した）
- 参照するブランチ（読むだけ）：art/w0（W0 A案。特に artbible_a_machines.png、artbible_a_colorscript.png）、art/w1-haru3d・art/w1-nagomi（3D 変換用の絵の塗り・光の手本）、art/w2-banki（番機。描き直しの _r2 が納品されていればそれに合わせる）

【最初に行うこと】
1. git fetch --all、git checkout art/w2-kannuki && git pull
2. 発注書と参照の絵を別のフォルダに取り出す：
   git worktree add ../relic-docs origin/claude/busy-bell-oagnck
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-nagomi origin/art/w1-nagomi
   git worktree add ../relic-banki origin/art/w2-banki
3. 必ず読む：../relic-docs/docs/art_orders/W2_03_大番機_閂.md、../relic-docs/docs/art_orders/00_共通ルール.md、../relic-docs/docs/art_orders/01_3D変換用の絵の条件.md（2 章の「描き方」の行を必ず読む）、../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png・artbible_a_machines.png

【作業】
- **画像生成機能で描く**。Blender などの 3D ソフト、プログラムで描いた図形は使わない。
- まず設計の絵（発注書の設計の絵の表：三面図・大きさの比較・関節の図解・攻撃の流れ・状態・段階・部屋の雰囲気画）を描き、アートバイブルの機械の絵と並べて、同じ世界の機械に見えるかを確かめる。ボスらしい迫力（巨大さ、重さ、削岩腕の凶暴さ）と、閂・錠前のモチーフがひと目で分かる形にする。番機の描き直し（_r2）が届いていれば、そのデザイン言語に合わせる。
- 次に、同じデザインで 3D 変換用の絵（発注書の「3D 変換用の絵」の表）を描く。向きごとの大きさ・位置をそろえ、斜めは 45 度にする（01_3D変換用の絵の条件.md）。測った数値を spec に書く。
- ファイル名は発注書どおりに、末尾に _r2 を付ける（例：kannuki_turnaround_r2.png、kannuki_3d_front_r2.png）。前回のファイルは消さない。
- spec_r2.md と spec_kannuki_3d_r2.md に、共通ルール 6 章と 01 の 6 章の項目を書く。冒頭に「前回（3D ソフトの画像）からの描き直し」と書く。

【守ること】
- 絵は必ず画像生成機能で描く。3D ソフトの画像、プログラムで描いた図形の画像、.blend・スクリプトなどのファイルは納品しない。
- art/concepts/W2_kannuki/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。
- 発注書と違う判断をする場合、描けないものがある場合は、作業を進める前に spec の冒頭に理由を書く。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-03 kannuki r2 (hand-drawn redo)"）、git push origin art/w2-kannuki で送る。
- 取り出したフォルダを片付ける：git worktree remove で ../relic-docs、../relic-w0、../relic-haru3d、../relic-nagomi、../relic-banki
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。前回の作り方を選んだ理由も 1 行で報告する。
```

## 9. 描き直しの依頼（2026-09-30）：ニコ（W2-01 の一部）

W2-01 の納品のうち、トルーデ・バートン・店主・ジャンク屋はそのまま使う。ニコだけ、設定を「女の子」に改め、ハルとはっきり見分けられるデザインで描き直してもらう。

### 9.1 W2-01：ニコの描き直し

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。W2-01（第1章の住人）の納品ありがとうございました。トルーデ・バートン・店主・ジャンク屋はこのまま使います。**ニコだけ描き直し**をお願いします。

【描き直しの理由】
1. 設定の変更：ニコは **8 歳の女の子**（ボーイッシュでよい）に改めました。発注書 W2_01_第1章の住人.md を更新しています。
2. 前回のニコは、**主人公ハルの小さな複製**に見えます。茶色のとがった髪、額のゴーグル、赤い上着と生成りのシャツ、茶色の半ズボン、手袋とブーツまでハルと同じ組み合わせで、ゲームの画面で並ぶとどちらがハルか分かりません。
   「ハルに憧れている」はデザインの一部分（小物）で表し、全体はニコ自身の見た目にしてください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/w2-townsfolk（前回納品したブランチ。そこに追加する）
- 発注書を読むブランチ：claude/busy-bell-oagnck（最新にすること）
- 参照するブランチ（読むだけ）：art/w0（W0 A案）、art/w1-haru3d（ハル。**似せないための比較**に使う）

【最初に行うこと】
1. git fetch --all、git checkout art/w2-townsfolk && git pull
2. git worktree add ../relic-docs origin/claude/busy-bell-oagnck
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
3. 必ず読む：../relic-docs/docs/art_orders/W2_01_第1章の住人.md（ニコの行と「ニコのデザインの決まり」）、00_共通ルール.md、01_3D変換用の絵の条件.md

【ニコのデザインの決まり】
- 8 歳の女の子、120cm。元気で好奇心が強く、少年っぽい動きやすい服装でよい。女の子だと分かる顔立ち（丸い輪郭、まつ毛、少し大きめの目など）。
- **ハルと違えること（必須）**：
  - 髪：色も形もハルと変える。例：明るい麦わら色の短めのボブを後ろで短く一つに結ぶ、など。茶色のとがった髪は不可。
  - 服の色：ハルの「れんが色の上着＋生成り＋茶色」の組み合わせを避ける。町の色（砂色・生成り）を土台に、くすんだ青緑などニコだけの差し色を 1 つ決める。
  - 服の形：例：大人のお下がりの大きめの上着の袖をまくる、つなぎ・オーバーオール、長めの首巻き、など、輪郭（シルエット）でハルと見分けられるもの。
  - ゴーグル：ハルを真似た手作りのおもちゃ（木の筒と縫い目の見える布の帯。前回の作りは良い）。ただし**額に着けない**。首に下げる、または帽子に付けるなど、ハルと違う位置にする。
- 仕上げに、ハルとニコを同じ縮尺で並べた比較の絵（nico_vs_haru_r2.png）を描き、遠くから見ても髪・色・輪郭で見分けられることを確かめる。

【作業】
- **画像生成機能で描く**。3D ソフトの画像、プログラムで描いた図形は不可。画像生成が利用の上限などで使えない場合は、代わりの方法を取らずに、描けた分だけ納品して spec の冒頭に「未納品」として書く。
- 前回と同じ一式をニコについて描き直す：三面図（nico_turnaround）、会話の顔 4 表情（nico_face_normal/smile/angry/surprised）、3D 変換用の絵（発注書 4 章の nico の行：全身・顔・表情・頭の 4 方向・首・手・靴）。
- ファイル名は前回と同じ名前の末尾に _r2 を付ける（例：nico_turnaround_r2.png、nico_3d_front_r2.png）。前回のファイルは消さない。
- spec_nico_r2.md に、共通ルール 6 章と 01 の 6 章の項目（色見本の hex、自己確認の数値など）を書く。冒頭に「女の子への設定変更と、ハルと見分けるための描き直し」と書き、ハルと変えた点を箇条書きにする。

【守ること】
- art/concepts/W2_townsfolk/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-01 nico r2 (girl, distinct from Haru)"）、git push origin art/w2-townsfolk で送る。
- git worktree remove で ../relic-docs、../relic-w0、../relic-haru3d を片付ける。
- 納品したファイルの一覧と、ハルと変えた点を 5 行以内で報告する。
```

## 10. W1-00c：ハルの銃を握る手（2026-10-01）

3D のハルの右手が銃を握る形を正確に作るための、参考の拡大の絵。

### 10.1 W1-00c：ハルの銃を握る手

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。主人公ハルの右手が銃を握っている拡大の絵（3D 用の参考）を描いてください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/w1-haru3d（W1-00・W1-00b を納品したブランチ。そこに追加する）
- 発注書を読むブランチ：claude/busy-bell-oagnck（最新にすること）

【最初に行うこと】
1. git fetch --all、git checkout art/w1-haru3d && git pull
2. git worktree add ../relic-docs origin/claude/busy-bell-oagnck
3. 必ず読む：../relic-docs/docs/art_orders/W1_00c_ハル_銃を握る手.md、00_共通ルール.md、01_3D変換用の絵の条件.md
4. 手本として見る（このブランチにある）：art/concepts/W1_haru3d/ の haru_hands.png、haru_gun_*.png（銃の絵）、haru_3d_front.png

【作業】
- 発注書 2 章の表の 6 枚（haru_grip_side_right / side_left / back / front / 3q / bottom）を、画像生成機能で描く。手首から先と銃だけ。撃つときのしっかりした握り方で、指 1 本ずつの位置が読み取れるように。
- 銃と手袋のデザイン・色は既存の絵と同じにする。
- spec_haru_grip.md を書く（発注書 2 章の項目）。

【守ること】
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトで作った画像、プログラムで描いた図形は不可。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と書く。
- art/concepts/W1_haru3d/ 以外を変更しない。既存の絵を消さない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-00c haru grip reference"）、git push origin art/w1-haru3d で送る。
- git worktree remove ../relic-docs で片付ける。
- 納品したファイルの一覧を報告する。
```

## 11. W2-01b：住人とヤーナの追加の絵（2026-10-01）

### 11.1 W2-01b：住人とヤーナの追加の絵

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。W2-01（第1章の住人）とヤーナの 3D 化のための、追加の拡大の絵を描いてください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：住人は art/w2-townsfolk、ヤーナは art/w1-yana（どちらも前回納品したブランチ。そこに追加する）
- 発注書を読むブランチ：claude/busy-bell-oagnck（最新にすること）

【最初に行うこと】
1. git fetch --all
2. git worktree add ../relic-docs origin/claude/busy-bell-oagnck
3. 必ず読む：../relic-docs/docs/art_orders/W2_01b_住人の追加の絵.md、00_共通ルール.md、01_3D変換用の絵の条件.md（2 章「描き方」と 4 章）
4. 手本：art/w2-townsfolk の art/concepts/W2_townsfolk/（店主・ジャンク屋・トルーデの既存の絵と spec）、art/w1-yana の art/concepts/W1_yana/（ヤーナの絵と spec）

【作業】
- 発注書 2 章の表の絵を、画像生成機能で描く。既存の絵と同じデザイン・色・縮尺。
- 住人の分は art/w2-townsfolk に、ヤーナの分は art/w1-yana に、それぞれ 1 コミットで追加する。spec も書く（発注書 2 章）。
- トルーデの左前 45 度は、足の間隔が正面の約 0.7 倍になるよう角度を確かめる（0.8 倍より広ければ描き直す）。

【守ること】
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトで作った画像、プログラムで描いた図形は不可。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と書く。
- 既存の絵を消さない・変えない。指定のフォルダ以外を変更しない。

【完了したら】
- コミットのメッセージ："art: W2-01b townsfolk extra views"（art/w2-townsfolk）、"art: W2-01b yana grip and hip"（art/w1-yana）。それぞれ push する。
- git worktree remove ../relic-docs で片付ける。
- 納品したファイルの一覧を報告する。
```

---

## 12. 第4弾（2026-10-05）：ボルタ・コウ・アルデン・UI・エフェクト（そのまま貼れる）

5 つは別々のブランチに納品するので、**並行して出しても、1 つずつ出してもよい**（1 つずつなら、第2章のライバルのボルタを最初に）。
身長比較（W1-99）は、この 3 人の納品の後に出す。

### 12.1 W1-04：ボルタ（設計＋3D 変換用）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck（発注書はここで読む。最新にすること）
- 作業ブランチ：art/w1-volta（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案）、art/w1-haru3d（ハル。3D 変換用の絵の塗り・光・頭身の手本、大きさの基準 155cm、見分けるべき相手）、art/w1-yana・art/w2-townsfolk（3D 変換用の絵の手本。ニコの r2 は「ハルと別の見た目」の手本）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w1-volta（すでにあれば git checkout art/w1-volta && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-yana origin/art/w1-yana
   git worktree add ../relic-townsfolk origin/art/w2-townsfolk
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W1_04_ボルタ.md（今回の発注書。設計の絵と 3D 変換用の絵の両方）
2. docs/art_orders/00_共通ルール.md（設計の絵のルール）
3. docs/art_orders/01_3D変換用の絵の条件.md（3D 変換用の絵のルール。3D 変換用の絵ではこちらを優先）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色の基準）
5. ../relic-haru3d/art/concepts/W1_haru_3d/ の絵と spec_haru_3d.md（ハルの色と形。ボルタはこれと遠目で見分けられること）
6. ../relic-yana/art/concepts/W1_yana/、../relic-townsfolk/art/concepts/W2_townsfolk/ の 3D 変換用の絵と spec（塗り・光・頭身の手本）
7. docs/design/11_キャラクター設定.md の「ボルタ」「ボルタの道具」

【作業】
- 画像生成機能を使い、発注書の設計の絵と 3D 変換用の絵をすべて制作する。先に設計の絵でデザインを決め、ハルとの比較の絵（volta_vs_haru.png）で見分けられることを確かめてから、同じデザインで 3D 変換用の絵を描く。
- 保存先：art/concepts/W1_volta/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（設計の絵。共通ルール 6 章の項目）と spec_volta_3d.md（3D 変換用の絵。01_3D変換用の絵の条件.md 6 章の項目、自己確認の数値、発注書 4 章の「部品の一覧」）。
- 3D 変換用の絵は、向きごとに大きさと位置をそろえ、納品前に測って数値を spec に書く。45 度の絵は、足の間隔が正面の約 0.7 倍になっているか確かめる（0.8 倍より広ければ描き直す）。
- 硬い物（ヘアクリップ、ルーペ、手袋、靴、ベルト、工具、背嚢、スパナ、道具）は輪郭をはっきり描き、1 部品を 1 色の平らな面で塗る。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」（特にトロン・ボーン）と見比べ、結果を spec.md に書く。
- 一貫性の自己確認：設計の絵と 3D 変換用の絵で、形・部品の数・色が一致しているかを見直し、食い違いは直す。

【守ること】
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトでモデルを作って撮った画像や、プログラムで描いた図形の画像は不可。.blend・スクリプトなどのファイルも納品しない。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と理由を書く。
- 機甲・ロボットの手下・相棒の AI・顔のある道具を描かない。
- art/concepts/W1_volta/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-04 Volta (design + 3D)"）、git push -u origin art/w1-volta で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-haru3d・relic-yana・relic-townsfolk も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点（ハルとの見分け方を含む）を 5 行以内で報告する。
```

### 12.2 W1-05：コウ（設計＋3D 変換用）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck（発注書はここで読む。最新にすること）
- 作業ブランチ：art/w1-kou（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案）、art/w1-haru3d（ハル。ゴーグルの形と色の正本、目元の手本、大きさの基準 155cm、見分けるべき相手）、art/w1-yana・art/w2-townsfolk（3D 変換用の絵の手本）、art/w2-props（壊せる目印 mark_*.png。父の印の描き方の手本）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w1-kou（すでにあれば git checkout art/w1-kou && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-yana origin/art/w1-yana
   git worktree add ../relic-townsfolk origin/art/w2-townsfolk
   git worktree add ../relic-props origin/art/w2-props
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W1_05_コウ.md（今回の発注書。設計の絵と 3D 変換用の絵の両方）
2. docs/art_orders/00_共通ルール.md（設計の絵のルール）
3. docs/art_orders/01_3D変換用の絵の条件.md（3D 変換用の絵のルール。3D 変換用の絵ではこちらを優先）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色の基準）
5. ../relic-haru3d/art/concepts/W1_haru_3d/ の絵と spec_haru_3d.md（ゴーグルの形と色、目元。コウはゴーグルと目元以外でハルと見分けられること）
6. ../relic-yana/art/concepts/W1_yana/、../relic-townsfolk/art/concepts/W2_townsfolk/ の 3D 変換用の絵と spec（塗り・光・頭身の手本）
7. ../relic-props/art/concepts/W2_props/mark_*.png（父の印 kou_mark.png の描き方の手本）
8. docs/design/11_キャラクター設定.md の「コウ」、docs/design/10_シナリオ設計.md の 2 章（裏設定の年表）

【作業】
- 画像生成機能を使い、発注書の設計の絵と 3D 変換用の絵をすべて制作する。先に設計の絵で 2 つの姿（通常・幽閉後）を決め、ハルとの比較の絵（kou_vs_haru.png）で見分けられることを確かめてから、同じデザインで 3D 変換用の絵を描く。
- 保存先：art/concepts/W1_kou/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（設計の絵。共通ルール 6 章の項目）と spec_kou_3d.md（3D 変換用の絵。01_3D変換用の絵の条件.md 6 章の項目、自己確認の数値、発注書 4 章の「部品の一覧」）。
- 3D 変換用の絵は、幽閉後の姿を全部、通常の姿を少なめに（発注書 4 章）。向きごとに大きさと位置をそろえ、納品前に測って数値を spec に書く。45 度の絵は、足の間隔が正面の約 0.7 倍になっているか確かめる。
- ゴーグルは、ハルの絵と形・色を完全に合わせる。
- 硬い物（髪、ゴーグルとヒモ、スカーフ、えり、袖口、ベルト、ポーチ、手袋、靴、接続具の痕の金具）は輪郭をはっきり描き、1 部品を 1 色の平らな面で塗る。
- 類似チェック：共通ルール 5 章の作品と見比べ、結果を spec.md に書く。
- 一貫性の自己確認：設計の絵と 3D 変換用の絵で、形・部品の数・色が一致しているかを見直し、食い違いは直す。

【守ること】
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトでモデルを作って撮った画像や、プログラムで描いた図形の画像は不可。.blend・スクリプトなどのファイルも納品しない。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と理由を書く。
- art/concepts/W1_kou/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-05 Kou (design + 3D)"）、git push -u origin art/w1-kou で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-haru3d・relic-yana・relic-townsfolk・relic-props も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点（ハルとの見分け方を含む）を 5 行以内で報告する。
```

### 12.3 W1-06：アルデン（設計＋3D 変換用）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck（発注書はここで読む。最新にすること）
- 作業ブランチ：art/w1-arden（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案。先史の技術の質感：白磁・真鍮・発光）、art/w1-haru3d（3D 変換用の絵の塗り・光・頭身の手本、大きさの基準のハル 155cm、見分けるべき相手）、art/w1-yana・art/w2-townsfolk（3D 変換用の絵の手本）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w1-arden（すでにあれば git checkout art/w1-arden && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-yana origin/art/w1-yana
   git worktree add ../relic-townsfolk origin/art/w2-townsfolk
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W1_06_アルデン.md（今回の発注書。設計の絵と 3D 変換用の絵の両方）
2. docs/art_orders/00_共通ルール.md（設計の絵のルール）
3. docs/art_orders/01_3D変換用の絵の条件.md（3D 変換用の絵のルール。3D 変換用の絵ではこちらを優先）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色・先史の質感の基準）
5. ../relic-haru3d/art/concepts/W1_haru_3d/ の絵と spec_haru_3d.md（ハルの色と形。アルデンは回収屋の服装の要素を使わない）
6. ../relic-yana/art/concepts/W1_yana/、../relic-townsfolk/art/concepts/W2_townsfolk/ の 3D 変換用の絵と spec（塗り・光・頭身の手本）
7. docs/design/11_キャラクター設定.md の「アルデン」、docs/design/10_シナリオ設計.md の冒頭の改訂の注記と「アルデンの計画（整理）」

【作業】
- 画像生成機能を使い、発注書の設計の絵と 3D 変換用の絵をすべて制作する。先に設計の絵でデザインを決め、ハルとの比較の絵（arden_vs_haru.png）を描いてから、同じデザインで 3D 変換用の絵を描く。
- 保存先：art/concepts/W1_arden/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（設計の絵。共通ルール 6 章の項目）と spec_arden_3d.md（3D 変換用の絵。01_3D変換用の絵の条件.md 6 章の項目、自己確認の数値、発注書 4 章の「部品の一覧」）。
- 3D 変換用の絵は、向きごとに大きさと位置をそろえ、納品前に測って数値を spec に書く。45 度の絵は、足の間隔が正面の約 0.7 倍になっているか確かめる（長衣で足が見えにくい場合は、裾の幅と肩の幅の比で確かめ、方法を spec に書く）。
- 硬い物（髪、金の縁取り、金具、帯、袖口、靴、装飾の板）は輪郭をはっきり描き、1 部品を 1 色の平らな面で塗る。幾何学文様は大きく単純な形にとどめる。瞳の光の輪と光る文様は平らな色で塗る（グローを描かない）。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」（長い銀髪に黒いコートの悪役など）と見比べ、結果を spec.md に書く。
- 一貫性の自己確認：設計の絵と 3D 変換用の絵で、形・部品の数・色が一致しているかを見直し、食い違いは直す。

【守ること】
- 絵は必ず画像生成機能で描く。Blender などの 3D ソフトでモデルを作って撮った画像や、プログラムで描いた図形の画像は不可。.blend・スクリプトなどのファイルも納品しない。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と理由を書く。
- art/concepts/W1_arden/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-06 Arden (design + 3D)"）、git push -u origin art/w1-arden で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-haru3d・relic-yana・relic-townsfolk も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

### 12.4 W2-08：UI

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck（発注書はここで読む。最新にすること）
- 作業ブランチ：art/w2-ui（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案）、art/w2-props（壊せる目印 mark_*.png と拾えるアイテム。アイコンの絵柄をそろえる基準）、art/w1-yana・art/w1-nagomi・art/w2-townsfolk（会話の顔アイコン）、art/w1-haru3d（ハルの顔 haru_face_expressions.png）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w2-ui（すでにあれば git checkout art/w2-ui && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-props origin/art/w2-props
   git worktree add ../relic-yana origin/art/w1-yana
   git worktree add ../relic-nagomi origin/art/w1-nagomi
   git worktree add ../relic-townsfolk origin/art/w2-townsfolk
   git worktree add ../relic-haru3d origin/art/w1-haru3d
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W2_08_UI.md（今回の発注書）
2. docs/art_orders/00_共通ルール.md
3. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色の基準）
4. ../relic-props/art/concepts/W2_props/mark_*.png、props_marks.png、props_items.png、spec.md（アイコンの絵柄と色の基準）
5. 顔アイコン：../relic-yana/art/concepts/W1_yana/yana_face_*.png、../relic-nagomi/art/concepts/W1_nagomi/nagomi_face_*.png、../relic-townsfolk/art/concepts/W2_townsfolk/*_face_*.png、../relic-haru3d/art/concepts/W1_haru_3d/haru_face_expressions.png
6. docs/design/20_ゲームシステム設計.md の 2 章（操作）、14 章（回収屋の印）、19 章（UI の機能要件）、20 章（会話と演出の仕組み）
7. godot/scripts/platform/touch_controls.gd の冒頭（スマホの操作のボタンと配置。読むだけ）

【作業】
- 画像生成機能を使い、発注書の画面の見本・部品・アイコンをすべて制作する。先に画面の見本で見た目を決め、同じデザインで部品とアイコンを 1 つずつ描く。
- 保存先：art/concepts/W2_ui/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（共通ルール 6 章の項目と、発注書 5 章の追加の項目：UI の色の一覧、角の丸み・線の太さ・余白、9 分割の角の大きさ、書体の提案、スマホで縮めたときの最小の大きさ）。
- 部品は Godot で伸ばして使う。四隅の飾りは角に収め、辺の中ほどはどこで切っても同じ模様にする（発注書 3 章）。
- アイコンは 256×256px、透明の背景、1 つずつ別の PNG。特殊武器のアイコンは W2-07 の目印 mark_*.png と対応が分かる形・色にする。
- 顔アイコンは新しく描かない。会話の見本では、納品済みの顔アイコンを枠に入れて使う（ハルだけは見本の中で haru_face_expressions.png を元に描いてよい）。
- 類似チェック：共通ルール 5 章の作品（特に『ロックマン』シリーズの HUD）と見比べ、結果を spec.md に書く。

【守ること】
- 絵は必ず画像生成機能で描く。プログラムで描いた図形の画像や、3D ソフトで作った画像は不可。スクリプトなどのファイルも納品しない。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と理由を書く。
- 実在のゲーム機のボタンの記号・ロゴ・商標を描かない。
- art/concepts/W2_ui/ 以外のファイルは変更しない（godot/ のファイルも変更しない）。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-08 UI"）、git push -u origin art/w2-ui で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-props・relic-yana・relic-nagomi・relic-townsfolk・relic-haru3d も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```

### 12.5 W2-09：エフェクト

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck（発注書はここで読む。最新にすること）
- 作業ブランチ：art/w2-vfx（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（画風の基準 W0 A案）、art/w1-haru3d（ハル・光刃の琥珀色）、art/w1-nagomi（ナゴミの殻と光）、art/w2-banki（番機のセンサー・核の色と壊れ方）、art/w2-kannuki（閂の攻撃・錠前核・段階の見た目）、art/w2-props（目印 mark_*.png、セーブビーコン、宝箱、拾えるアイテム）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w2-vfx（すでにあれば git checkout art/w2-vfx && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-nagomi origin/art/w1-nagomi
   git worktree add ../relic-banki origin/art/w2-banki
   git worktree add ../relic-kannuki origin/art/w2-kannuki
   git worktree add ../relic-props origin/art/w2-props
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W2_09_エフェクト.md（今回の発注書）
2. docs/art_orders/00_共通ルール.md
3. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色の基準）
4. docs/art_orders/W2_02_番機_第1章.md と ../relic-banki/art/concepts/W2_banki/（spec_r2.md、<ID>_attack・<ID>_states の絵。r2 を正とする）
5. docs/art_orders/W2_03_大番機_閂.md と ../relic-kannuki/art/concepts/W2_kannuki/（spec_r2.md、攻撃と段階の絵。r2 を正とする）
6. ../relic-props/art/concepts/W2_props/（mark_*.png、props_ruins.png、props_items.png、spec.md）
7. ../relic-haru3d/art/concepts/W1_haru_3d/spec_haru_3d.md（琥珀色）、../relic-nagomi/art/concepts/W1_nagomi/（ナゴミの殻と光）
8. docs/design/20_ゲームシステム設計.md の 6〜8 章（主武器・光刃・特殊武器）、10〜12 章（戦闘・番機・ボス）

【作業】
- 画像生成機能を使い、発注書の 2 章のエフェクトのキーフレームと、3 章の粒子の素材をすべて制作する。
- 保存先：art/concepts/W2_vfx/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（共通ルール 6 章の項目と、各エフェクトの色 hex・明るさの変化・持続時間・大きさ m）。
- ハルの光（琥珀）と敵の光（番機・閂の spec の色）が一瞬で見分けられることを、並べて確かめる。
- 類似チェック：共通ルール 5 章の作品と発注書 5 章の「似せない」ものと見比べ、結果を spec.md に書く。

【守ること】
- 絵は必ず画像生成機能で描く。プログラムで描いた図形の画像や、3D ソフトで作った画像は不可。スクリプトなどのファイルも納品しない。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と理由を書く。
- 光刃を緑にしない。フレームの装着をカプセルの中の演出にしない。
- art/concepts/W2_vfx/ 以外のファイルは変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-09 VFX (chapter 1)"）、git push -u origin art/w2-vfx で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-haru3d・relic-nagomi・relic-banki・relic-kannuki・relic-props も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点を 5 行以内で報告する。
```
