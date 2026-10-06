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

---

## 13. 第5弾（2026-10-06）：直し（r2）・ハルの会話の顔・身長比較・第2章の下書き（そのまま貼れる）

第4弾の点検の結果をもとにした依頼。それぞれ別のブランチ（または前回納品したブランチへの追加）なので、**並行して出してよい**。1 つずつ出すときは、下の表の順に出す。

| 順 | 節 | 内容 | 作業ブランチ | 出す条件 |
|----|----|------|-------------|---------|
| 1 | 13.1 | W1-01b：ハルの会話の顔アイコン 9 枚（新規） | `art/w1-haru3d`（追加） | すぐ |
| 2 | 12.5 | W2-09：エフェクト（第4弾。2026-10-06 の時点でブランチが無い） | `art/w2-vfx` | Codex がまだ手を付けていなければ、12.5 をもう一度出す |
| 3 | 13.2 | W2-08：UI の直し（r2） | `art/w2-ui`（追加） | すぐ |
| 4 | 13.3 | W1-04：ボルタの直し（r2） | `art/w1-volta`（追加） | すぐ |
| 5 | 13.4 | W1-06：アルデンの頭と顔（r2） | `art/w1-arden`（追加） | すぐ |
| 6 | 13.5 | W1-05：コウの直し（r2） | `art/w1-kou`（追加） | すぐ（接続具の金具と、幽閉後のやせ方は、ユーザーの判断が出てから追加で伝える） |
| 7 | 13.6 | W1-99：身長比較 | `art/w1-lineup`（新規） | 13.4 のアルデン r2 の納品の後 |
| 8 | 13.7 | W3-01：黎明機構の幹部 ダグ・ハイナル（下書き） | `art/w3-cadres`（新規） | **ユーザーの了承の後** |
| 9 | 13.9 | W3-03：錆の砂海の雰囲気と目印（下書き） | `art/w3-sandsea`（新規） | **ユーザーの了承の後**（13.7 と並行してよい） |
| 10 | 13.8 | W3-02：カラン・黎明機構の飛行艇・楔（下書き） | `art/w3-machines`（新規） | **ユーザーの了承の後**、13.7 の納品の後 |

- W3（第2章）の 3 本は、CP2 の試遊とユーザーの了承の後に出す（`docs/design/60_開発計画.md`：量産は本気ステージの了承の後）。了承が出たら、発注書の冒頭の「下書き・要ユーザー承認」の行を消して push してから貼る。
- 第4弾では、Codex が途中の保存を `art/<名前>-backup` に push していた。どの依頼も「最後は全部を作業ブランチに入れる」と書いてある。backup のブランチは、本納品を取り込んだあと消してよい。
- W2-08 は、2026-10-06 15:57 に `art/w2-ui`（e46434f、112 ファイル）へ完成版が届いた（未納品だった印・地図・状態異常のアイコンと確認用シートを含む）。13.2 はその版に対する直し。

### 13.1 W1-01b：ハルの会話の顔アイコン

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/w1-haru3d（ハルの 3D 変換用の絵を納品したブランチ。そこに追加する）
- 発注書を読むブランチ：claude/busy-bell-oagnck（最新にすること）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（W0 A案）、art/w1-yana・art/w2-townsfolk・art/w1-volta（会話の顔アイコンの手本）、art/w2-ui（顔の枠）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout art/w1-haru3d && git pull
2. 発注書と参照の絵を別のフォルダに取り出す：
   git worktree add ../relic-docs origin/claude/busy-bell-oagnck
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-yana origin/art/w1-yana
   git worktree add ../relic-townsfolk origin/art/w2-townsfolk
   git worktree add ../relic-volta origin/art/w1-volta
   git worktree add ../relic-ui origin/art/w2-ui
3. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. ../relic-docs/docs/art_orders/W1_01b_ハル_会話の顔.md（今回の発注書）
2. ../relic-docs/docs/art_orders/00_共通ルール.md
3. このブランチの art/concepts/W1_haru_3d/ の haru_face_front.png、haru_face_expressions.png、haru_head_*.png、haru_3d_front.png、haru_3d_front_right45.png、haru_neck.png、spec_haru_3d.md（ハルの顔・服・色の正本）
4. 手本：../relic-yana/art/concepts/W1_yana/yana_face_*.png、../relic-townsfolk/art/concepts/W2_townsfolk/nico_face_*_r2.png、../relic-volta/art/concepts/W1_volta/volta_face_*.png（構図・大きさ・塗り）
5. 顔の枠：../relic-ui/art/concepts/W2_ui/ui_parts_face_frame.png（ゲームではこの枠の窓に入れて使う）
6. ../relic-w0/art/concepts/W0_art_bible/spec_a.md（画風・色の基準）

【作業】
- 画像生成機能を使い、発注書 4 章の 9 枚（haru_face_normal / surprised / smirk / serious / laugh / sad / angry / smile / troubled）を描く。透過 PNG、1024×1024px、胸から上・斜め前。
- 9 枚とも同じ構図・同じ位置・同じ大きさにし、変えるのは目・眉・口だけにする（発注書 3 章）。顔は haru_face_front.png と同じ人物、服は haru_3d_front.png と同じ（右肩だけの白磁の板、額のゴーグル）。
- 納品前に 9 枚を 128px に縮めて並べ、表情が見分けられるか確かめる。見分けにくいものは描き直す。
- 説明書き：art/concepts/W1_haru_3d/spec_haru_face.md（発注書 5 章の項目）。

【守ること】
- 絵は必ず画像生成機能で描く。描いた絵の拡大縮小・切り抜き・位置合わせに画像編集を使うのはよい。3D ソフトで作った画像やプログラムで描いた図形は不可。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と理由を書く。
- art/concepts/W1_haru_3d/ の既存のファイルを変えない・消さない。ほかのフォルダを変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-01b Haru dialogue face icons"）、git push origin art/w1-haru3d で送る。途中で別のブランチに保存した場合も、最後は全部を art/w1-haru3d に入れる。
- 取り出したフォルダを片付ける：git worktree remove ../relic-docs（relic-w0・relic-yana・relic-townsfolk・relic-volta・relic-ui も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、128px で見比べた結果を 5 行以内で報告する。
```

### 13.2 W2-08：UI の直し（r2）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。W2-08（UI）の完成版の納品ありがとうございました。画面の見本・部品・アイコンはどれも質が高く、部品はもうゲーム（Godot）に組み込んで使っています。点検の結果、下の点だけ直し（_r2）をお願いします。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/w2-ui（完成版を納品したブランチ。そこに追加する。art/w2-ui-backup はもう使わない）
- 発注書を読むブランチ：claude/busy-bell-oagnck（最新にすること）
- 参照するブランチ（読むだけ・取り込まない）：art/w2-ordo（巡礼機オルド）、art/w2-props（セルなどのアイテムの形）

【最初に行うこと】
1. git fetch --all、git checkout art/w2-ui && git pull
2. git worktree add ../relic-docs origin/claude/busy-bell-oagnck
   git worktree add ../relic-ordo origin/art/w2-ordo
   git worktree add ../relic-props origin/art/w2-props
3. 必ず読む：../relic-docs/docs/art_orders/W2_08_UI.md、../relic-docs/docs/art_orders/00_共通ルール.md、このブランチの art/concepts/W2_ui/spec.md、../relic-docs/godot/scripts/platform/touch_controls.gd の冒頭（スマホのボタンと配置。読むだけ）

【このまま使うもの】
- 下に挙げたもの以外のすべて（画面の見本 13 枚、部品、アイコン 50 個、確認用シート）。

【直してほしいこと】
1. HP の中身 3 枚（ui_parts_gauge_hp_fill_full_r2.png、_damaged_r2.png、_danger_r2.png。大きさは今と同じ 960×36）：今は満タン #B1563D と危険 #A94C3B がほぼ同じ色で、危険が読めない。また、被弾 #F8B756 が、すぐ隣に並ぶ特殊武器のエネルギーの中身 #FBB43E とほぼ同じ。ゲームでの使い方は次のとおり。full＝通常の中身、damaged＝被弾で減った分が少し遅れて縮む部分（full の後ろに重ねる）、danger＝HP が 3 割を切ったときに full と入れ替えて点滅させる中身。danger は full と明るさ・彩度がはっきり違うこと、damaged は琥珀色（#FBB43E・#FFBC52）を使わないこと（例：白磁寄りの明るい色）。spec.md に 3 つの役割と hex を書く。
2. チャージと解析中の表示を「枠（トラック）と中身」に分ける（どれも 256×256、今の絵と同じ中心）：ui_parts_gauge_charge_track.png（空の輪）、ui_parts_gauge_charge_fill_stage1.png と ui_parts_gauge_charge_fill_stage2.png（360 度ぐるりと一周した輪。平らな色で、暗い区切りなどを焼き込まない。ゲームが輪を回る向きに少しずつ見せて進み具合を出す）、ui_parts_lockon_analyzing_track.png（解析中の照準。進み具合の輪は空）と ui_parts_lockon_analyzing_fill.png（照準のまわりの輪だけ。一周した輪）。今の stage2 は輪に暗い区切りが焼き込まれ、解析の弧も止まった絵なので、進み具合を出せない。
3. ui_parts_panel_button_focus_r2.png：今は _pressed とほとんど同じ（同じれんが色の面）で、選んでいるボタンと押したボタンの区別がつかない。focus は normal の面のまま、琥珀 #FFBC52 の縁取りなどで目立たせる。pressed はれんが色の面のまま。
4. ui_parts_panel_choice_r2.png（960×120）：四隅の飾りが上下それぞれ約 53px あり、縦に伸ばせる所が約 14px しかない。飾りの高さを 24px 以下にして、120px のうち 40px 以上を伸ばせるようにする。
5. spec.md の 9 分割の角の大きさ：今の値は多くの部品で飾りより小さい（測った飾りの幅／高さ：small 45／48（spec 40）、dialogue 38／39（32）、name 24／38（24）、choice 38／53（24）、tabs 23／30（24）、buttons 30／39（32）、large 40／44（48））。すべてのパネル・タブ・ボタン・ゲージの枠について、左右と上下を分けて、角の飾りがすべて入る値を測って書く。ゲージの枠は、中身が収まる窓の位置と大きさ（x、y、幅、高さ px）も書く。
6. ui_title_r2.png：後ろの巡礼機が、背の高い箱形の歩く機械に城が載った形になっていて、オルドと違う（共通ルール 5 章の「歩く城」の作品にも近い）。W2-04 のオルド（../relic-ordo/art/concepts/W2_ordo/ordo_mood_dawn.png、ordo_3d_side_right.png：長く低い船体、4 対の脚、背中に 3 段の町）で描き直す。ロゴは画面に焼き込まず、左上のロゴの場所を空ける。ロゴは別の透過 PNG で納品する：ui_title_logo.png（ARKWALKER、アークウォーカー、サブタイトル「―方舟は夜明けを歩く―」）と ui_title_logo_nosub.png（サブタイトルなし）。日本語の文字の形が崩れて描けない場合は、ARKWALKER の英字だけのロゴにして、そのことを spec に書く（日本語はゲームで文字として出す）。
7. ui_worldmap_r2.png：今は雲の上の島と巨大な機械の脚に見え、必須の「父の信号の範囲円」が無い（点線の円が「未調査エリア」になっている）。大陸を上から見た地図にして、巡礼路（線とノードの点）、地域の区切り、凡例つきの「父の信号の範囲円」をはっきり描く。地図の印は今回の icon_map_*.png の形を使う。オルドの今いる所と砂海（次の地域）の辺りだけを明るく、先と海の向こうは霞ませる。
8. 画面の見本の中身を設定に合わせる（_r2）：ui_menu_status_r2.png は「冒険ランク 3」と月桂樹のバッジをやめ、回収屋の印のバッジ（icon_rank_descent.png など）を出す。セルは青い結晶ではなく、W2-07 の琥珀色の白磁の筒（icon_item_cell_small.png）で出す。ui_menu_pause_r2.png・ui_menu_status_r2.png・ui_menu_workshop_r2.png の特殊武器「ナビボール」（ナゴミの球）を、本物の特殊武器（例：ブレイクドリルと icon_we_break_drill.png）に替える。工房は、主武器スパークの 5 つの能力（攻撃力・連射・射程・弾速・チャージ）を出す（今は剣の数値）。ui_menu_guild_r2.png は「ギルドランク C」「ギルド通貨」の金貨・「魔導装置」の依頼をやめ、回収屋の印とギルドポイント、第1章らしい依頼にする。どの見本にも、白地に赤い十字（赤十字のしるし）を使わない。
9. （任意・低）ui_hud_touch_r2.png：今は操作のボタンが 6 個で「特殊」が無く、配置もゲームと違う。touch_controls.gd の配置に合わせ、7 個（ジャンプ・調べる、撃つ、斬る、ダッシュ、特殊、ロック、回復）を描く：いちばん大きいジャンプ・調べるを右下の角に、撃つはその左、斬るは左上、ダッシュは上、特殊とロックはさらに左、回復は弧のいちばん上。右上の目的の表示の下に、ポーズと背後。記号は納品済みの ui_parts_touch_symbol_*.png を使う。HUD の文字（目的・戦闘中のひと言・通知・操作の案内）は 1920×1080 の画面で 48px 以上（高さ 360px の画面で 16px）にする。縦向きの案内は右下の差し込みをやめ、別の全画面の見本 ui_hud_portrait.png にする。
10. （任意・低）icon_rank_apprentice_r2.png、icon_rank_descent_r2.png：見習いと降下許可の枠が真鍮で、銅の印より上等に見え、金の印とも近い。見習い・降下許可は黒鉄や革などのつつましい材質にして、見習い → 降下許可 → 銅 → 銀 → 金 → 一人前 → 白磁 の順に上等になることが 48px でも読めるようにする。

【作業】
- 修正版は元のファイル名の末尾に _r2 を付けて追加する。元のファイルは消さない・変えない。新しい名前のファイル（_track、_fill、ui_title_logo など）は _r2 を付けずにその名前で追加する。
- 部品の大きさは今の版と同じにする（ゲームの部品をそのまま差し替えるため）。
- spec.md を直し、末尾に「修正履歴（2026-10-06）」として、直したファイルと内容を書く。

【守ること】
- 絵は必ず画像生成機能で描く。描いた絵の拡大縮小・切り抜き・位置合わせ・透過の余白の調整に画像編集を使うのはよい。プログラムで描いた図形の画像や 3D ソフトの画像は不可。描けないときは代わりの方法を取らず、spec の冒頭の「未納品」に書く。
- 実在のゲーム機のボタンの記号・ロゴ・商標を描かない。
- art/concepts/W2_ui/ 以外のファイルを変更しない（godot/ のファイルも変更しない）。参照した絵を作業ブランチにコピーしない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W2-08 UI r2"）、git push origin art/w2-ui で送る。途中で別のブランチに保存した場合も、最後は全部を art/w2-ui に入れる。
- git worktree remove で ../relic-docs、../relic-ordo、../relic-props を片付ける。
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 直したファイルと新しく足したファイルの一覧を報告する。
```

### 13.3 W1-04：ボルタの直し（r2）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。W1-04（ボルタ）の納品ありがとうございました。全身 7 方向は大きさと位置がぴったりそろい、ハルともニコともはっきり見分けられる、良いデザインです。点検の結果、下の点だけ直し（_r2）をお願いします。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/w1-volta（前回納品したブランチ。そこに追加する。art/w1-volta-backup は使わない）
- 発注書を読むブランチ：claude/busy-bell-oagnck（最新にすること）

【最初に行うこと】
1. git fetch --all、git checkout art/w1-volta && git pull
2. git worktree add ../relic-docs origin/claude/busy-bell-oagnck
3. 必ず読む：../relic-docs/docs/art_orders/W1_04_ボルタ.md、00_共通ルール.md、01_3D変換用の絵の条件.md（3 章と 5 章）。手本：このブランチの art/concepts/W1_volta/ の既存の絵、spec.md、spec_volta_3d.md

【このまま使うもの】
- 下に挙げたもの以外のすべて（全身の正面・背面・右側面・左右 45 度、顔と表情、頭の 4 方向、首・手・靴、会話の顔アイコン、三面図、ポーズ、ハルとの比較、各道具の _3q）。

【直してほしいこと】
1. volta_3d_side_left_r2.png：左腿に生成り色の当て布が描かれている。当て布は本人の右腿だけ（正面・右側面・45 度・三面図・spec と同じ）なので、左腿の当て布を消す。ルーペは volta_face_front.png と頭の 4 方向と同じく、左こめかみの短い支点に付ける（耳の後ろへ回る黒いバンドを描かない）。頭頂 114px・足裏 1915px・中心 1024 列は今の 7 枚にそろえる。
2. volta_3d_side_right_noarms_r2.png：腕は取り除かれているが、カメラの方へ突き出した袖の筒（生成り色の折り返しの輪）が残り、脇の下と胴の横を隠している。袖は肩の付け根で切り、脇の下から胸の横のツナギの面、肩ひも、背嚢の横が見えるようにする。行と列は今の 7 枚と同じ。
3. 道具の正投影を _r2 で描き直す（spanner_side/top/front、wire_launcher_side/top/front、deploy_bridge_side/top/front、probe_side/top/front、smoke_side/top/front/back）：
   (a) 1 つの道具の中では、真横・真上・正面を同じ縮尺（1 px が同じ長さ）で描く。今は 1 枚ごとに画像いっぱいまで拡大していて、たとえば発煙具は真横の高さ 14cm が 1555px、背面・底の直径 6cm が約 1600px になっている。道具ごとに、いちばん大きい向きで全長が画像の約 85% になる縮尺を決め、ほかの向きもその縮尺にする（描いた絵を拡大縮小してそろえてよい）。
   (b) 真横は本当の真横で描く。wire_launcher_side と deploy_bridge_side は今 _3q とほぼ同じ斜めの絵になっている。spanner_side は柄を水平にして描く（今は 45 度傾いている）。
   (c) 探査機は、円盤の厚み（約 6cm）と横から見た形が分かる、縁から見た真横と正面を描く（今は 6 枚とも円の面が見えている）。
   (d) smoke_back は、円筒の側面を反対側から見た絵にする（今は端面の絵で、真上とほぼ同じ）。
   (e) spec_volta_3d.md に、道具ごとの全長（cm）と 1cm あたりの px を書く。
   _back・_bottom・_3q は描き直さなくてよい（描き直す場合は同じ縮尺にする）。
4. wire_launcher_back_r2.png：腕輪の右にある余分な切れ端（2 つの向きを並べた絵を切り抜いた残り）を消し、1 枚に 1 つの向きだけにする。
5. volta_gadgets_r2.png（設計の絵）：探査機（使う前・使っているところ）の羽根を 3 枚にそろえる（今は 4 枚・4 分割で、3D 用の絵と spec の 3 枚と違う）。
6. deploy_bridge_parts_r2.png：伸びる板（展開した正面の明るい茶色の板）が、箱のどこにどう畳まれて入るかを分解図で示す。さらに、展開した状態を遠近感なしの真横で描き、板の全長（約 240cm）が読める deploy_bridge_open_side.png を 1 枚足す（今の deploy_bridge_open_front.png は手前ほど板が広がる遠近の絵で、長さが読めない）。
7. volta_head_r2.png（設計の絵）：真ん中の側面は顔が左を向いている（本人の左側が見える）のに、ヘアクリップが手前に描かれている。左側面ならクリップは見えない形にし、ルーペを手前に描く。首元を、ほかの絵と同じからし色のツナギの襟と、中の生成りの下着にする（今は生成りの襟付きシャツと胸当てに見える）。
8. spec の直し（絵は描かない）：
   - spec_volta_3d.md：靴先の補強とクリップの中央は、絵では黄土色（#C88F3E〜#D99E43 くらい）なのに、部品の一覧では #A98749 になっている。どちらが正しいか決めて表を直す。足場の板の上面の色（今の絵の明るい茶色）を部品の一覧に足す。
   - spec.md：三面図の並び順の説明を、実際の並び（正面・右側面・背面・左側面・右前）に合わせる。

【作業】
- 修正版は元のファイル名の末尾に _r2 を付けて追加する。元のファイルは消さない・変えない。新しいファイル（deploy_bridge_open_side.png）は _r2 を付けずにその名前で追加する。
- 3D 変換用の絵は、01_3D変換用の絵の条件.md の条件（2048×2048、透過、正投影、均一な光、1 枚 1 方向）を守る。
- spec.md と spec_volta_3d.md を直し、それぞれの末尾に「修正履歴（2026-10-06）」として、直したファイルと内容を書く。

【守ること】
- 絵は必ず画像生成機能で描く。描いた絵の拡大縮小・切り抜き・位置合わせに画像編集を使うのはよい（形や色を描き足すのは画像生成で）。3D ソフトで作った画像やプログラムで描いた図形は不可。描けないときは代わりの方法を取らず、spec の冒頭の「未納品」に書く。
- 機甲・ロボットの手下・相棒の AI・顔のある道具を描かない。
- art/concepts/W1_volta/ 以外のファイルを変更しない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-04 Volta r2"）、git push origin art/w1-volta で送る。途中で別のブランチに保存した場合も、最後は全部を art/w1-volta に入れる。
- git worktree remove ../relic-docs で片付ける。
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 直したファイルの一覧と、道具ごとの 1cm あたりの px を報告する。
```

### 13.4 W1-06：アルデンの頭と顔（r2）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。W1-06（アルデン）の納品ありがとうございました。白と金の長衣のシルエット、青緑の光の色、ハルとの見分けやすさは良く、体と長衣はこのまま使います。点検の結果、顔と頭を中心に直し（_r2）をお願いします。

【直す理由】
- 発注は「40 代に見える男性」「静かな威厳」「白金色の整った短髪」ですが、顔がどの絵でも 10 代後半〜20 代前半に見え、髪はハルと同じ系統の跳ねた房になっています。顔アイコンはゲームの画面にそのまま使うので、影響が大きい所です。
- 全身の絵の瞳が茶色（光の輪なし）で、顔の拡大の深灰＋青緑の輪と食い違っています。
- arden_3d_side_right_noarms が side_right と別の絵になっています（裾が 24% 広く短い、顔の向きも違う）。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/w1-arden（前回納品したブランチ。そこに追加する。art/w1-arden-backup は使わない）
- 発注書を読むブランチ：claude/busy-bell-oagnck（最新にすること）

【最初に行うこと】
1. git fetch --all、git checkout art/w1-arden && git pull
2. git worktree add ../relic-docs origin/claude/busy-bell-oagnck
3. 必ず読む：../relic-docs/docs/art_orders/W1_06_アルデン.md（1 章「どんな人物か」と 2 章「デザインの条件」）、00_共通ルール.md、01_3D変換用の絵の条件.md。手本：このブランチの art/concepts/W1_arden/ の既存の絵、spec.md、spec_arden_3d.md

【直してほしいこと】
1. 顔と頭を 40 代にする（_r2）：arden_face_front、arden_face_expressions、arden_head_side_right／_back／_top／_front_right45、arden_head.png、顔アイコン 6 枚（arden_face_normal／smile／cold／shaken／grief／resolve）。
   - 年齢の手がかり：目をやや細く、頬骨とあごをはっきり、まぶたと口元の線をごく控えめに。静かな威厳と、悲しみを背負った落ち着き。
   - 髪：「整った短髪」。後ろへなでつけるか横分けにし、大きく滑らかな房 3〜5 個にまとめる。跳ねた先端を作らない（ハルの「跳ねた短髪」と見分けるため）。色は spec の白金色。
   - 瞳：深灰 #40484C と、平らな光の輪 #91D5D8（グローを描かない）。
   - arden_head_back の襟の背は、arden_neck.png と同じく中央の金の帯 1 本にする（今は 2 本）。
   - 大きさ・位置・構図は今の版と同じにする。
2. 全身の _r2：arden_3d_front／_back／_side_right／_side_left／_front_right45／_front_left45、arden_turnaround、arden_vs_haru。体の形と位置（頭頂 123〜125 行・足裏 1922〜1925 行・中心 1024 列）は変えず、頭だけを 1 と同じ顔・髪・瞳の色に描き替える。同時に、靴の配色を arden_shoes.png（白い甲・金の横帯・金のつま先とかかと・濃い底）にそろえる（今の全身は金の地に白い甲と濃い横帯）。side_left_r2 は、side_right_r2 を左右反転した形に合わせる（今は裾の後ろが約 14% 太い。spec のとおり左右対称）。
3. arden_3d_side_right_noarms_r2.png：side_right_r2 と同じ絵から、腕と袖だけを取り除いたものにする。裾の幅と長さ・顔・向きは side_right_r2 と同じ。肩の切り口は穴にせず、長衣の布の色の平らな面で塗る。
4. spec_arden_3d.md の追記（絵は描かない）：長衣の内張りの色を 1 つに決めて hex を書く（今は正面の前開きの内側が茶 約 #855F37、arden_robe_hem.png が濃い灰 約 #30302F）。前の閉じた部分の下端の金の横帯（足裏から約 55cm）を部品の一覧に加える。描いた色と spec の hex のずれ（金 約 #C59753 と #A98749、長衣 約 #EFD8BA と #F3E9D2、肌 約 #F8BA8A と #E7B58D、髪 約 #F8E3C6 と #E9E2D3）について、どちらを正とするかを書く。

【作業】
- 修正版は元のファイル名の末尾に _r2 を付けて追加する。元のファイルは消さない・変えない。arden_poses.png と arden_final_rough.png は描き直さなくてよい。
- 3D 変換用の絵は、01_3D変換用の絵の条件.md の条件（2048×2048、透過、正投影、均一な光、1 枚 1 方向）を守る。人物の不透明な部分は完全に不透明（アルファ 255）にする。
- 納品前に、顔アイコン 6 枚と全身 7 枚を並べ、顔・髪・瞳の色が全部で一致しているか確かめる。
- spec.md と spec_arden_3d.md を直し、それぞれの末尾に「修正履歴（2026-10-06）」として、直したファイルと内容を書く。

【守ること】
- 絵は必ず画像生成機能で描く。描いた絵の拡大縮小・切り抜き・位置合わせに画像編集を使うのはよい（形や色を描き足すのは画像生成で）。3D ソフトで作った画像やプログラムで描いた図形は不可。描けないときは代わりの方法を取らず、spec の冒頭の「未納品」に書く。
- 長い銀髪に黒いコートなど、有名な悪役の定番の組み合わせにしない。
- art/concepts/W1_arden/ 以外のファイルを変更しない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-06 Arden r2 (age 40s head, matching full body)"）、git push origin art/w1-arden で送る。途中で別のブランチに保存した場合も、最後は全部を art/w1-arden に入れる。
- git worktree remove ../relic-docs で片付ける。
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 直したファイルの一覧と、顔・髪で変えた点を 5 行以内で報告する。
```

（ユーザーが長衣の発光ラインを望んだ場合だけ、上の【直してほしいこと】に次の 5 を足して出す）

```text
5. 長衣に、発注どおりの発光のラインを足す：太く単純な平らな線を 1〜2 本（#91D5D8。例：前の金の縦帯 2 本の内側と、背の縦帯）。全身 7 枚・arden_neck・arden_robe_hem のすべてで同じ位置に描き（_r2）、部品の一覧にも加える。グローを描かない。
```

### 13.5 W1-05：コウの直し（r2）

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。W1-05（コウ）の納品ありがとうございました。全身 11 枚の大きさと位置がそろい、ハルとの縮尺も正しく、父の印も W2-07 の目印と同じ描き方で、そのまま使えます。点検の結果、下の点だけ直し（_r2）をお願いします。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 作業ブランチ：art/w1-kou（前回納品したブランチ。そこに追加する。art/w1-kou-backup は使わない）
- 発注書を読むブランチ：claude/busy-bell-oagnck（最新にすること）
- 参照するブランチ（読むだけ・取り込まない）：art/w1-haru3d（ハルのゴーグルと顔アイコンの形）

【最初に行うこと】
1. git fetch --all、git checkout art/w1-kou && git pull
2. git worktree add ../relic-docs origin/claude/busy-bell-oagnck
   git worktree add ../relic-haru3d origin/art/w1-haru3d
3. 必ず読む：../relic-docs/docs/art_orders/W1_05_コウ.md、00_共通ルール.md、01_3D変換用の絵の条件.md。手本：このブランチの art/concepts/W1_kou/ の既存の絵、spec.md、spec_kou_3d.md

【直してほしいこと（必須）】
1. kou_captive_3d_front_left45_r2.png：裾の大きな破れが本人の左の前身頃（この向きでは手前）に描かれている。破れは本人の右だけ（正面・右前 45・背面・spec と同じ）なので、本人の左の前身頃は小さなほつれだけにする。頭頂 123px・足裏 1924px・中心 1024 列は今のまま。角度はちょうど 45 度にする（足の間隔 ÷ 正面の足の間隔 ≒ 0.70。今は 0.63）。
2. 首と左前腕の接続痕を、すべての絵で 1 つの描き方にそろえる。今は、顔・頭・アイコン・三面図・全身では ‡ 形の縫い傷、kou_neck.png では正面に無く真横は 2 つの点、kou_hands.png の前腕は 2 つの点、全身の前腕はひっかき傷、とばらばら。顔の絵の ‡ 形を正とし、kou_neck_r2.png の正面に本人の右首の痕を描き、真横と kou_hands_r2.png の前腕の痕を同じ形にする。spec_kou_3d.md に、痕の大きさと位置（cm）を書く（全身の絵の前腕のひっかき傷は描き直さなくてよい。spec の形を正とする）。kou_hands_r2.png では、手のひらの図を手の甲の図と同じ手にする（今の手のひらは親指の向きが逆で、反対の手に見える）。
3. kou_neck_r2.png と kou_neck_normal_r2.png の背面を、全身と頭の背面図（kou_3d_back、kou_captive_3d_back、kou_head_back、kou_captive_head_back）に合わせる：スカーフの大きな結び目と長い 2 本の垂れをやめ、えりの下に隠れる小さな結び目（本人の左後ろ）にする。
4. spec の直し（絵は描かない）：spec.md と spec_kou_3d.md のスカーフの hex を、描いた橙（絵から測った値で約 #B87432）に直す。色見本に kou_mark.png の地の色（アイボリー 約 #F1E5CF、真鍮 約 #B3945D）を足す。ゴーグルのヒモの背面（本人の左）にある四角い留め具はハルに無いので、3D では付けない（ハルの部品を使う）ことを spec に書く。

【直してほしいこと（任意）】
5. （任意・低）kou_poses_r2.png：頭をなでるポーズの幼いハルは 5 歳前後に見えるようにし、外装フレームの部品・籠手・ゴーグルを着けない普通の子どもの服で描く（フレームは 10 年前に封印されたため）。肩を借りるポーズは、ハルの頭がコウのあご〜肩の高さに来るようにする（155cm 対 180cm）。
6. （任意）顔アイコン 9 枚（kou_face_*.png、kou_face_captive_*.png）の _r2：ゴーグルのレンズの輪郭を ../relic-haru3d/art/concepts/W1_haru_3d/haru_face_front.png と同じ形（横長で、内側の下の角を切る）にし、背面のヒモの留め具を描かない。あわせて、128px に縮めたときに smile・proud と normal、captive_smile と captive_normal の違いが分かるように、口元と目元の差を少し大きくする。

【作業】
- 修正版は元のファイル名の末尾に _r2 を付けて追加する。元のファイルは消さない・変えない。
- 3D 変換用の絵は、01_3D変換用の絵の条件.md の条件を守る。
- spec.md と spec_kou_3d.md を直し、それぞれの末尾に「修正履歴（2026-10-06）」として、直したファイルと内容を書く。
- 接続痕に小さな金具（接続具の名残り）を足すか、幽閉後の姿をもっとやせた姿にするかは、いまユーザーが判断している。決まったら追って伝えるので、今回は描かない。

【守ること】
- 絵は必ず画像生成機能で描く。描いた絵の拡大縮小・切り抜き・位置合わせに画像編集を使うのはよい（形や色を描き足すのは画像生成で）。3D ソフトで作った画像やプログラムで描いた図形は不可。描けないときは代わりの方法を取らず、spec の冒頭の「未納品」に書く。
- art/concepts/W1_kou/ 以外のファイルを変更しない。参照した絵を作業ブランチにコピーしない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-05 Kou r2"）、git push origin art/w1-kou で送る。途中で別のブランチに保存した場合も、最後は全部を art/w1-kou に入れる。
- git worktree remove で ../relic-docs、../relic-haru3d を片付ける。
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 直したファイルの一覧を報告する。
```

### 13.6 W1-99：身長比較

**13.4（アルデンの頭と顔の r2）が `art/w1-arden` に届いてから出す。**

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck（発注書はここで読む。最新にすること）
- 作業ブランチ：art/w1-lineup（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（W0 A案）、art/w1-nagomi、art/w1-volta、art/w1-haru3d、art/w1-yana、art/w1-kou、art/w1-arden（6 人の最新の絵。_r2 があれば _r2 を正とする）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w1-lineup（すでにあれば git checkout art/w1-lineup && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-nagomi origin/art/w1-nagomi
   git worktree add ../relic-volta origin/art/w1-volta
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-yana origin/art/w1-yana
   git worktree add ../relic-kou origin/art/w1-kou
   git worktree add ../relic-arden origin/art/w1-arden
4. ../relic-arden/art/concepts/W1_arden/ に arden_face_front_r2.png（40 代の顔の描き直し）があることを確かめる。無い場合は作業を止めて報告する。
5. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W1_99_身長比較.md（今回の発注書）
2. docs/art_orders/00_共通ルール.md
3. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_lineup_r3.png（画風の基準）
4. 発注書 2 章の表の手本の絵と spec（6 人分）

【作業】
- 画像生成機能を使い、発注書 3 章の lineup_front.png と lineup_side.png を描く。6 人のデザイン・色は手本の最新の版と同じにし、変えない。
- 縮尺は 1cm = 8px、床の線は上から 1880px の行（発注書 3 章）。人物は 1 人ずつ描いてから、身長どおりの大きさに拡大縮小して並べてよい。物差し・目盛り・横線・床の線は、正確な直線として画像編集で重ねてよい。
- 説明書き：art/concepts/W1_lineup/spec.md（発注書 4 章の項目）。手本の絵との食い違いは、絵を直さずに spec に書く。

【守ること】
- 絵は必ず画像生成機能で描く。3D ソフトで作った画像やプログラムで描いた人物は不可。手本の 3D 変換用の絵を切り貼りして並べない。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と理由を書く。
- art/concepts/W1_lineup/ 以外のファイルを変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W1-99 character lineup"）、git push -u origin art/w1-lineup で送る。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-nagomi・relic-volta・relic-haru3d・relic-yana・relic-kou・relic-arden も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、見つけた食い違いを 5 行以内で報告する。
```

### 13.7 W3-01：黎明機構の幹部 ダグ・ハイナル（下書き・要ユーザー承認）

**CP2 の試遊とユーザーの了承の後に出す。** 発注書 `W3_01_幹部_ダグとハイナル.md` の冒頭の「下書き・要ユーザー承認」の行を消して push してから貼る。

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck（発注書はここで読む。最新にすること）
- 作業ブランチ：art/w3-cadres（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（W0 A案）、art/w1-haru3d（ハル。大きさの基準 155cm、3D 変換用の絵の手本）、art/w1-arden（総帥アルデン。黎明機構の気品と光の色）、art/w1-yana（ヤーナの右の義手。似せない相手）、art/w2-townsfolk（バートン。似せない相手）、art/w1-volta（ボルタのルーペ。似せない相手）、art/w1-kou（コウのコート。似せない相手）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w3-cadres（すでにあれば git checkout art/w3-cadres && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-arden origin/art/w1-arden
   git worktree add ../relic-yana origin/art/w1-yana
   git worktree add ../relic-townsfolk origin/art/w2-townsfolk
   git worktree add ../relic-volta origin/art/w1-volta
   git worktree add ../relic-kou origin/art/w1-kou
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W3_01_幹部_ダグとハイナル.md（今回の発注書。ダグは設計の絵と 3D 変換用の絵、ハイナルは設計の絵と会話の顔だけ）
2. docs/art_orders/00_共通ルール.md
3. docs/art_orders/01_3D変換用の絵の条件.md（ダグの 3D 変換用の絵のルール）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png（画風・色の基準）
5. docs/design/11_キャラクター設定.md の「黎明機構」「幹部4人」、docs/design/10_シナリオ設計.md の 2 章と 4 章の第2章
6. 手本と似せない相手の絵：../relic-haru3d/art/concepts/W1_haru_3d/、../relic-arden/art/concepts/W1_arden/、../relic-yana/art/concepts/W1_yana/、../relic-townsfolk/art/concepts/W2_townsfolk/（burton_*）、../relic-volta/art/concepts/W1_volta/、../relic-kou/art/concepts/W1_kou/

【作業】
- 画像生成機能を使い、発注書 5 章の設計の絵と、6 章のダグの 3D 変換用の絵をすべて制作する。先に黎明機構の紋章と色の決まり（発注書 2 章）を決め、設計の絵で 2 人のデザインを決め、比較の絵（dag_vs_haru.png、hainal_vs_haru.png）で似せない相手と見分けられることを確かめてから、同じデザインでダグの 3D 変換用の絵を描く。
- 保存先：art/concepts/W3_dag/（ダグと紋章）、art/concepts/W3_hainal/（ハイナル）。ファイル名は発注書の表のとおり。
- 説明書き：W3_dag/spec.md、W3_dag/spec_dag_3d.md（自己確認の数値、部品の一覧）、W3_hainal/spec.md。
- 3D 変換用の絵は、向きごとに大きさと位置をそろえ、納品前に測って数値を spec に書く。45 度の絵は、足の間隔が正面の約 0.7 倍になっているか確かめる。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。

【守ること】
- 絵は必ず画像生成機能で描く。描いた絵の拡大縮小・切り抜き・位置合わせに画像編集を使うのはよい。3D ソフトで作った画像やプログラムで描いた図形は不可。.blend・スクリプトなどのファイルも納品しない。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と理由を書く。
- art/concepts/W3_dag/、art/concepts/W3_hainal/ 以外のファイルを変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W3-01 Dawn cadres Dag (design + 3D) and Hainal (design)"）、git push -u origin art/w3-cadres で送る。途中で別のブランチに保存した場合も、最後は全部を art/w3-cadres に入れる。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-haru3d・relic-arden・relic-yana・relic-townsfolk・relic-volta・relic-kou も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点（似せない相手との見分け方を含む）を 5 行以内で報告する。
```

### 13.8 W3-02：カラン・黎明機構の飛行艇・楔（下書き・要ユーザー承認）

**ユーザーの了承の後、13.7（W3-01）の納品の後に出す。** 発注書 `W3_02_カラン_飛行艇_楔.md` の冒頭の「下書き・要ユーザー承認」の行を消して push してから貼る。

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck（発注書はここで読む。最新にすること）
- 作業ブランチ：art/w3-machines（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（W0 A案）、art/w2-ordo（オルドとカランのシルエット）、art/w3-cadres（黎明機構の紋章と色、ダグとハイナル）、art/w1-volta（ボルタの色）、art/w2-ruins（遺構の先史の技術とノードの光）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w3-machines（すでにあれば git checkout art/w3-machines && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-ordo origin/art/w2-ordo
   git worktree add ../relic-cadres origin/art/w3-cadres
   git worktree add ../relic-volta origin/art/w1-volta
   git worktree add ../relic-ruins origin/art/w2-ruins
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W3_02_カラン_飛行艇_楔.md（今回の発注書）
2. docs/art_orders/00_共通ルール.md
3. docs/art_orders/01_3D変換用の絵の条件.md（2 章と 5 章）
4. ../relic-w0/art/concepts/W0_art_bible/spec_a.md と artbible_a_*_r3.png、artbible_a_machines.png（画風・色・機械の基準）
5. ../relic-ordo/art/concepts/W2_ordo/（spec.md、spec_ordo_3d.md、ordo_*.png、karan_*.png）
6. ../relic-cadres/art/concepts/W3_dag/dawn_emblem.png と spec.md（黎明機構の紋章と色の決まり）、W3_hainal/hainal_poses.png（後ろ姿）
7. docs/design/10_シナリオ設計.md の 2 章（楔）と 4 章の第1章の章末・第2章

【作業】
- 画像生成機能を使い、発注書 5 章の設計の絵と 6 章の 3D にするための絵をすべて制作する。
- 保存先：art/concepts/W3_machines/　ファイル名は発注書の表のとおり。
- 説明書き：spec.md（共通ルール 6 章の項目、全長・高さ m）と spec_machines_3d.md（01_3D変換用の絵の条件.md 6 章の項目、動く部分と回転軸、発光の hex）。
- 3D にするための絵は、物ごとに同じ縮尺（1 px が同じ長さ）にし、spec に 1m あたりの px を書く。
- 類似チェック：共通ルール 5 章の作品と発注書の「避けるもの」と見比べ、結果を spec.md に書く。

【守ること】
- 絵は必ず画像生成機能で描く。描いた絵の拡大縮小・切り抜き・位置合わせに画像編集を使うのはよい。3D ソフトで作った画像やプログラムで描いた図形は不可。.blend・スクリプトなどのファイルも納品しない。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と理由を書く。
- art/concepts/W3_machines/ 以外のファイルを変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W3-02 Karan, Dawn airship and wedge (design + 3D)"）、git push -u origin art/w3-machines で送る。途中で別のブランチに保存した場合も、最後は全部を art/w3-machines に入れる。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-ordo・relic-cadres・relic-volta・relic-ruins も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、デザインの要点（オルドとカランの見分け方を含む）を 5 行以内で報告する。
```

### 13.9 W3-03：錆の砂海の雰囲気と目印（下書き・要ユーザー承認）

**CP2 の試遊とユーザーの了承の後に出す（13.7 と並行してよい）。** 発注書 `W3_03_錆の砂海_雰囲気.md` の冒頭の「下書き・要ユーザー承認」の行を消して push してから貼る。3D 用の部品組（W3-03b）は、第2章の部屋の設計ができてから別に出す。

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。下のリポジトリに接続し、発注書を読み、指示どおりに画像を制作して納品してください。

【リポジトリ】
- URL：https://github.com/hassy0511/project-relic
- 元にするブランチ：claude/busy-bell-oagnck（発注書はここで読む。最新にすること）
- 作業ブランチ：art/w3-sandsea（元にするブランチから新しく作る。すでにあればそれを使う）
- 参照するブランチ（読むだけ・取り込まない）：art/w0（W0 A案。色見本の 2 番「錆の砂海」とキービジュアル）、art/w2-ordo（オルドとカラン）、art/w2-ruins（遺構の先史の技術）、art/w1-haru3d（ハル。大きさの基準）、art/w1-volta（ボルタ）、art/w1-kou（父の印 kou_mark.png）

【最初に行うこと】
1. git clone https://github.com/hassy0511/project-relic.git（取得済みなら git fetch --all）
   cd project-relic
   git checkout claude/busy-bell-oagnck && git pull
2. git checkout -b art/w3-sandsea（すでにあれば git checkout art/w3-sandsea && git pull）
3. 参照する絵を別のフォルダに取り出す：
   git worktree add ../relic-w0 origin/art/w0
   git worktree add ../relic-ordo origin/art/w2-ordo
   git worktree add ../relic-ruins origin/art/w2-ruins
   git worktree add ../relic-haru3d origin/art/w1-haru3d
   git worktree add ../relic-volta origin/art/w1-volta
   git worktree add ../relic-kou origin/art/w1-kou
4. 下の「必ず読む文書」がそろっていることを確認する。見つからない場合は作業を止め、見つからないファイル名を報告する。

【必ず読む文書】
1. docs/art_orders/W3_03_錆の砂海_雰囲気.md（今回の発注書。雰囲気の絵と目印・部品の方向だけ）
2. docs/art_orders/00_共通ルール.md
3. ../relic-w0/art/concepts/W0_art_bible/spec_a.md、artbible_a_colorscript.png、artbible_a_keyvisual_r3.png
4. ../relic-ordo/art/concepts/W2_ordo/spec.md と ordo_mood_*.png、karan_*.png
5. ../relic-ruins/art/concepts/W2_back_ruins/spec.md と ruins_mood_*.png（同じ先史の技術。砂と錆で違いを出す）
6. docs/design/10_シナリオ設計.md の 4 章の第2章、docs/design/30_レベルデザイン設計.md の 2 章

【作業】
- 画像生成機能を使い、発注書 2 章の納品物をすべて制作する。
- 保存先：art/concepts/W3_sandsea/　ファイル名は発注書の表のとおり。雰囲気画は 4096×2048 以上を推奨。
- 説明書き：spec.md（共通ルール 6 章の項目と、発注書 2 章の 8 の追加の項目）。
- 類似チェック：共通ルール 5 章の作品と、発注書 3 章の砂漠の作品と見比べ、結果を spec.md に書く。

【守ること】
- 絵は必ず画像生成機能で描く。3D ソフトで作った画像やプログラムで描いた図形は不可。描けないときは代わりの方法を取らず、spec の冒頭に「未納品」と理由を書く。
- art/concepts/W3_sandsea/ 以外のファイルを変更しない。参照した絵を作業ブランチにコピーしない。
- 既存の絵や写真をなぞったり合成したりしない。署名・透かし・実在ブランドの文字やロゴを入れない。

【完了したら】
- 1 コミットにまとめ（メッセージ："art: W3-03 Rust Sand Sea mood and landmarks"）、git push -u origin art/w3-sandsea で送る。途中で別のブランチに保存した場合も、最後は全部を art/w3-sandsea に入れる。
- 取り出したフォルダを片付ける：git worktree remove ../relic-w0（relic-ordo・relic-ruins・relic-haru3d・relic-volta・relic-kou も同じく）
- 送れなかった場合は、エラーの内容をそのまま報告する。
- 納品したファイルの一覧と、地域の見せ方の要点を 5 行以内で報告する。
```

### 13.10 Codex に貼る短い依頼文（ダッシュボード 7 章と同じ形）

上の全文の代わりに、次の短い文を貼ってもよい（Codex がこのファイルを開いて全文を読む）。`<節>`・`<見出し>`・`<ブランチ>` を書き換える。

```text
あなたはゲーム開発プロジェクト『アークウォーカー』の作画担当です。リポジトリ https://github.com/hassy0511/project-relic を取得し、ブランチ claude/busy-bell-oagnck の docs/art_orders/codex_prompts.md を開いて、「<節> <見出し>」のコードブロックを最後まで読み、その指示どおりに作業して納品（<ブランチ> へ push）してください。
指示の中で読むよう書かれている文書と絵は必ず読んでください。見つからないファイルがあれば作業を止めて報告してください。
絵は必ず画像生成機能で描いてください。3D ソフトで作った画像やプログラムで描いた図形は不可です。描けないときは、spec の冒頭に「未納品」と書いてください。
```
