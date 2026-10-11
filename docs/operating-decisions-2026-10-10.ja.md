# AIチーム業務配分の更新 — 2026-10-10

[English](operating-decisions-2026-10-10.md) | [日本語](operating-decisions-2026-10-10.ja.md)

調査・文章・GitHub文書作業もClaude / Antigravityへ広く配分する。Dottieは短いPM、Codex / ChatGPTは複雑な初期設計・難しい判断・必要時の最終エスカレーションを中心とし、全成果物の全文代行・全面再レビューを標準にしない。これは本人指示に基づく文書上の配分方針で、自動dispatchの実装や稼働証明ではない。

## 担当表：制作・調査を含む業務一覧

| 担当・環境 | 主な担当候補 | 境界 |
|---|---|---|
| 本人 | 目的・優先順位・責任ある承認・最終受入・公開判断 | AIの結果を検証し、必要な専門家を残す |
| Dottie | 短い要件・受入条件・配分・進捗・handoff | 長文制作の常設担当や自律dispatchではない |
| Codex / ChatGPT（Chappy） | 複雑な初期設計、難しい判断、必要時の最終エスカレーション | 全成果物の全文再作成・全面再レビューを標準にしない |
| Claude Code | 実装・修正・試験、技術文書、ブログ初稿・推敲・翻訳、GitHub文書更新・PR整形 | 稼働・適性・新鮮な残量を確認。公開・本番操作には適切な承認 |
| Gemini / Antigravity | 調査・公式出典確認、比較表・要約・図表用データ、PoC / mock、文章の別案、独立一次レビュー | 同じ基準でClaudeと配分。別ツールでも同providerならprovider独立とは限らない |
| Qwen local（Windows / Mac） | 許可済み範囲の専門調査・資料整理。セキュリティ・社会的テーマ等も許可と適性の範囲内 | 環境ごとにモデル機能・ネット検索可否・出典確認を検証。安全制御回避には使わない |
| RunPod A100 Qwen | 将来の独立レビュー候補 | live運用・品質は未受入。現時点の代替はClaude / Antigravity相互レビュー |

## 配分と失敗時の扱い

1. タスクごとに目的、完了条件、小さな入力、担当、代替1つ、予定予算／作業上限、成果物／evidenceを記録する。
2. 認可済み経路の利用可否と実際の稼働を確認する。subscriptionとAPI、provider別pool、観測時刻付きsession／weekly残量、reset時刻を分ける。不明・古い値は`unknown`。異なるproviderのtoken単位を単純合算して均等化しない。
3. まずClaude / Antigravityの適任かつ余裕ある候補に配分する。役割表は固定割当ではない。残量が古い場合の手動ローテーションは偏りを避ける提案であり、十分な残量の証明ではない。
4. 受け渡し失敗は1回で原因と保存済み成果を記録する。権限拒否は止め、別経路で迂回しない。通常の稼働不良なら別の認可済み候補1つを検討する。不可なら`blocked`／本人handoff待ちとし、自動的にCodexの全文代行へ戻さない。例外は短い理由を記録する。
5. 可能なら制作・実装者とレビュー担当をprovider別にする。Antigravity内ClaudeとClaude Codeは別poolでも同providerなので独立性を区別する。レビューは指定範囲・根拠・重大な不確実性を扱い、Codexは難しい論点だけを必要時に判断する。

quota観測は手動。live quota取得・自動dispatchは未検証。CodexBar画像を自動読取済みとしない。正規の権限・安全制御を尊重し、担当変更を拒否回避に使わない。Windowsを第一選択とし、利用不可ならMacへ切り替える前に本人へ相談する。

## ルーティング例

| 業務 | 配分例 | 根拠と受入 |
|---|---|---|
| 調査・ブログ・文書 | Antigravity調査／公式出典 → Claude初稿・推敲・翻訳 → Antigravity図表用データ → 別provider担当review → 本人承認 → 許可された公開担当 | 出典URL・取得日、初稿revision、図表の数値、指摘と修正。4媒体のブログ下書きも本人レビュー前は公開しない |
| コード・修正・試験 | Dottieの短い仕様 → 必要ならCodex初期設計 → ClaudeまたはAntigravity実装・試験 → 別provider review → 担当が修正・再検証 → 本人受入 | 差分、試験結果、未検証runtime。reviewを全面再実装にしない |
| 一般repo編集・PR整形 | 小さな入力＋編集範囲 → Claude文書編集／PR整形（代替Antigravity） → 別担当の差分・リンク確認 → 許可されたアップロード | 対象branch、変更files、既存変更保持、内容readback。mergeは別途明示された範囲のみ |
| 許可済み専門調査 | Local Qwenで資料整理 → 検索可能な担当が公式出典を確認 → Claude / Antigravityが限定review → 本人判断 | 環境・モデルの観測、許可範囲、出典と不確実性。担当変更で安全機能を回避しない |

例は担当候補であり実行済みの主張ではない。入力と受入条件を絞り、必要な成果物・根拠だけを受け渡す。作成、review、本人承認、公開、mergeを別段階にする。

## Qwenの2系統と確認範囲

- **Local：** Windows Open WebUI/Ollamaの文章応答は本人操作で確認済み。Mac Open WebUI 0.11.4とQwen2.5 3Bにはローカル応答・Web検索結果の過去観測がある。全環境の検索可否・専門調査品質は別途確認が必要で、自動orchestrationの証明ではない。
- **RunPod Phase 1：** [PR #39](https://github.com/moruku36/qwen-multimodal/pull/39)で小型Qwen2.5-1.5B-Instructの実回答1件とPod削除を記録。A100の独立レビュー品質や全ワークフロー受入ではない。
- **RunPod Phase 2：** mock / offlineの範囲のみ。A100によるlive独立レビュー、品質、継続運用は未受入。現時点はClaude / Antigravity相互レビューを使う。会話上の「3.7ぐらい」は未確定な呼称で、モデルIDとして扱わない。
- **Colab：** 固定Q8チャットnotebookは別環境。[PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35)のCPU CI 287件（2 skip）はColab/GPU inference・モデルdownload・A100品質の確認ではない。
- OpenAI-compatibleはAPI形式で、有料OpenAI利用を意味しない。単回のHTTP応答を自動起動・接続・終了の完成としない。Pod停止と削除は別で、永続storageやデータ保持にも注意する。この文書改訂ではGPUを起動せず実運用設定を変更しない。

## 継承する方針と公開境界

- [2026-10-06](operating-decisions-2026-10-06.ja.md)のOpenAI Medium 2択・モデル呼称の留保を保持。OpenAIへ仕事を戻す基準は本書の限定した役割と例外理由。モデルID・runtimeを推測しない。
- AI Governance Controlは薄いhandoff／artifact／evidence層、AIteamBridgeは別のlocal開発project。どちらもlive自動配分の完成とは扱わない。
- 私的会話、個人・家族事情、資格情報、ログイン先、account・quota詳細、識別子を公開しない。新規課金・認証・設定変更は本改訂の対象外。
- 過去の[10月2日](operating-decisions-2026-10-02.ja.md)・[10月5日](operating-decisions-2026-10-05.ja.md)・[10月6日](operating-decisions-2026-10-06.ja.md)記録を保存し、当時の検証や方針を遡って書き換えない。

[Routing Guide](routing-guide.ja.md)と[AI Team](ai-team.ja.md)、[handoffテンプレート](handoff-templates.ja.md)も本方針に合わせる。
