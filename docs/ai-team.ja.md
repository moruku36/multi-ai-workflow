# AIチームの役割と運用

[English](ai-team.md) | [日本語](ai-team.ja.md)

> 2026-10-10時点の運用。モデル名は本人の運用上の表記です。

| 担当・環境 | 主な担当候補 | 境界 |
|---|---|---|
| 本人 | 目的・優先順位・責任ある承認・最終受入・公開判断 | AIの結果を検証し、必要な専門家を残す |
| Dottie | 短い要件・受入条件・配分・進捗・handoff | 長文制作の常設担当や自律dispatchではない |
| Codex / ChatGPT（Chappy） | 複雑な初期設計、難しい判断、必要時の最終エスカレーション | 全成果物の全文再作成・全面再レビューを標準にしない |
| Claude Code | 実装・修正・試験、技術文書、ブログ初稿・推敲・翻訳、GitHub文書更新・PR整形 | 稼働・適性・新鮮な残量を確認。公開・本番操作には適切な承認 |
| Gemini / Antigravity | 調査・公式出典確認、比較表・要約・図表用データ、PoC / mock、文章の別案、独立一次レビュー | 同じ基準でClaudeと配分。別ツールでも同providerならprovider独立とは限らない |
| Qwen local（Windows / Mac） | 許可済み範囲の専門調査・資料整理。セキュリティ・社会的テーマ等も許可と適性の範囲内 | 環境ごとにモデル機能・ネット検索可否・出典確認を検証。安全制御回避には使わない |
| RunPod A100 Qwen | 将来の独立レビュー候補 | live運用・品質は未受入。現時点の代替はClaude / Antigravity相互レビュー |

## Windowsを基盤にした運用

Windowsを常時稼働のローカル基地かつ第一選択とします。Windowsで作業を続けられない場合、Macへ切り替える前にユーザーへ相談します。Macは補助環境です。CodexBarのquota画像は手動で確認します。quotaの自動取得や完全自動routingは未検証です。

## 役割の境界

- DottieがPMとしてscope、provider／環境選択、進捗、受け入れを調整します。すべての実行が自動とは限りません。
- AI Governance Controlは再利用可能な薄いhandoff、artifact、evidence層です。minimal handoffは[PR #29](https://github.com/moruku36/ai-engineering-factory/pull/29)で検証済みです。
- AIteamBridgeはcapacity、router、transportを扱う別のローカル開発プロジェクトです。live quota取得と自動dispatchは未検証です。

これらは補完関係にあり、完全自律型の重複orchestratorではありません。状態はverified/merged、local/offline、runtime pending、proposalに分けます。

## 実行状況

監督付きAntigravity Webセッション1件でタスク依頼と応答が確認され、取得結果にはunit check 324件、mock browser check 25件が報告されました。これは単一結果であり、CLI稼働、一般的な自動routing、独立したテスト再実行を示すものではありません。

- **Local：** Windows Open WebUI/Ollamaの文章応答は本人操作で確認済み。Mac Open WebUI 0.11.4とQwen2.5 3Bにはローカル応答・Web検索結果の過去観測がある。全環境の検索可否・専門調査品質は別途確認が必要で、自動orchestrationの証明ではない。
- **RunPod Phase 1：** [PR #39](https://github.com/moruku36/qwen-multimodal/pull/39)で小型Qwen2.5-1.5B-Instructの実回答1件とPod削除を記録。A100の独立レビュー品質や全ワークフロー受入ではない。
- **RunPod Phase 2：** mock / offlineの範囲のみ。A100によるlive独立レビュー、品質、継続運用は未受入。現時点はClaude / Antigravity相互レビューを使う。会話上の「3.7ぐらい」は未確定な呼称で、モデルIDとして扱わない。
- **Colab：** 固定Q8チャットnotebookは別環境。[PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35)のCPU CI 287件（2 skip）はColab/GPU inference・モデルdownload・A100品質の確認ではない。
- OpenAI-compatibleはAPI形式で、有料OpenAI利用を意味しない。単回のHTTP応答を自動起動・接続・終了の完成としない。Pod停止と削除は別で、永続storageやデータ保持にも注意する。この文書改訂ではGPUを起動せず実運用設定を変更しない。

ユーザー承認、実行環境の権限承認、ローカルテスト、稼働環境への反映は別段階です。正規の承認が拒否されたら作業を保存して止め、再承認を連打したり別経路で迂回したりしません。

## Dottieとworkflow層

DottieはPMであり、全タスクが自動実行されるという意味ではありません。scopeと受け入れ条件を明確にし、適格なprovider／環境を選び、進捗とhandoffを調整します。

- **AI Governance Control**は薄い再利用可能なhandoff/artifact/evidence層です。minimal handoffは[PR #29](https://github.com/moruku36/ai-engineering-factory/pull/29)（`4fb014a`でmerge）で確認され、Ubuntu/Windows品質ゲートとoffline container-boundary検証を含みます。
- **AIteamBridge**は別のlocal capacity/router/transport開発projectです。246件のlocal/offlineテストが報告されていますが、未commit・未公開で、live quota取得と自動dispatchは未検証です。
- 3つの役割は補完的で、完全自動orchestratorが3つあるという説明はしません。

## ChappyとCodex

Codex / ChatGPTは複雑な初期設計・難しい判断・必要時の最終エスカレーションを中心に使い、全成果物の全文再作成・全面再レビューは標準にしません。通常のOpenAI選定は **GPT-6 Luna / Medium** または **GPT-6.1 Sol / Medium** の2択です。範囲が明確な作業にはLuna Medium、難度や品質要求が高い作業にはSol Mediumを選び、Low/Medium/Highの6段階運用は行いません。ExtraHighは引き続き使いません。Astraは学術研究や特に難しい上級調査で必要な場合のみ、具体的な理由を示して使う例外です。Sol Mediumで十分ならそれを使います。モデル名は本人の運用上の表記であり、CLI IDやruntimeでの利用可能性を証明しません。

workerの実選択とruntime確認ができない場合は、その制約と`UNKNOWN`を報告します。

## Claude Code

実装・修正・試験に加え、技術文書、ブログ初稿・推敲・翻訳、GitHub文書更新・PR整形を担当候補とします。通常Sonnet 5.5、難度に応じOpus 5.5という呼称は継承します。実行可否・適性・新鮮な残量を確認し、deployには適切な承認が別途必要です。直接Claude CodeとAntigravity内Claudeは別poolでも同providerです。

## Gemini / Antigravity

調査・公式出典確認、比較表・要約・図表用データ、PoC / mock、文章の別案、独立一次レビューも担当候補です。Claudeと固定順位を設けず、適性・残量鮮度・稼働で配分します。明示されたタスク固有の選択を尊重し、reviewは可能なら制作者とproviderを分けます。

## 配分と失敗時

1. タスクごとに目的、完了条件、小さな入力、担当、代替1つ、予定予算／作業上限、成果物／evidenceを記録する。
2. 認可済み経路の利用可否と実際の稼働を確認する。subscriptionとAPI、provider別pool、観測時刻付きsession／weekly残量、reset時刻を分ける。不明・古い値は`unknown`。異なるproviderのtoken単位を単純合算して均等化しない。
3. まずClaude / Antigravityの適任かつ余裕ある候補に配分する。役割表は固定割当ではない。残量が古い場合の手動ローテーションは偏りを避ける提案であり、十分な残量の証明ではない。
4. 受け渡し失敗は1回で原因と保存済み成果を記録する。権限拒否は止め、別経路で迂回しない。通常の稼働不良なら別の認可済み候補1つを検討する。不可なら`blocked`／本人handoff待ちとし、自動的にCodexの全文代行へ戻さない。例外は短い理由を記録する。
5. 可能なら制作・実装者とレビュー担当をprovider別にする。Antigravity内ClaudeとClaude Codeは別poolでも同providerなので独立性を区別する。レビューは指定範囲・根拠・重大な不確実性を扱い、Codexは難しい論点だけを必要時に判断する。

## Quotaを考慮した選択

1. sessionとweeklyのquota枠を別々に扱い、各観測時刻を記録します。
2. 直接Claude Code、Antigravity Claude/GPT、Antigravity Gemini、native Codexは別poolです。API課金はsubscription quotaではありません。
3. 5時間利用がなかっただけではquotaが100%に戻ったと判断できません。
4. 欠落または古い観測は`unknown`とし、推測せず明示的または手動選択に戻ります。
5. 難度、品質、環境、観測の新しさ、消費ペース、reset時間、コストを合わせて判断します。固定しきい値だけでは決めません。
6. quota画像、正確な残高、account支出、認証情報、private session dataを公開しません。

## 呼称と報告

Dottie、Chappy、Claude Code、Gemini/Antigravity、Qwenは文脈が明らかな場合の役割名として使います。会話上の依頼はタスク固有のtool選択に落とし込み、指定model/effortと観測runtimeを分けます。CLI IDを作りません。

詳細は[2026-10-10運用判断](operating-decisions-2026-10-10.ja.md)と[routing guide](routing-guide.ja.md)を参照してください。
