# AIチームの役割と運用

[English](ai-team.md) | [日本語](ai-team.ja.md)

> 2026-10-06時点の運用。モデル名は本人の運用上の表記です。

| 担当 | ツール／役割 | 主な責務 |
|---|---|---|
| Owner | 人間 / Product Owner | 目標、優先順位、受け入れ判断 |
| Dottie | OpenAI Dots / PM | タスク定義、providerと環境選択、進捗、受け入れ、handoff |
| Chappy | ChatGPT + Codex | アーキテクチャ、レビュー、調査、文章、割り当てられたrepo作業 |
| Claude | Claude Code | 通常の実装・deploy担当。通常Sonnet 5.5、難しい作業はOpus 5.5 |
| Gemini | Gemini + Antigravity | PoC、mock、適合する実装。固定の優先経路ではない |
| Qwen | Open WebUI/Ollama、別のColab構成 | ローカル文章処理とマルチモーダル調査 |

## Windowsを基盤にした運用

Windowsを常時稼働のローカル基地かつ第一選択とします。Windowsで作業を続けられない場合、Macへ切り替える前にユーザーへ相談します。Macは補助環境です。CodexBarのquota画像は手動で確認します。quotaの自動取得や完全自動routingは未検証です。

## 役割の境界

- DottieがPMとしてscope、provider／環境選択、進捗、受け入れを調整します。すべての実行が自動とは限りません。
- AI Engineering Factoryは再利用可能な薄いhandoff、artifact、evidence層です。minimal handoffは[PR #29](https://github.com/moruku36/ai-engineering-factory/pull/29)で検証済みです。
- AIteamBridgeはcapacity、router、transportを扱う別のローカル開発プロジェクトです。live quota取得と自動dispatchは未検証です。

これらは補完関係にあり、完全自律型の重複orchestratorではありません。状態はverified/merged、local/offline、runtime pending、proposalに分けます。

## 実行状況

監督付きAntigravity Webセッション1件でタスク依頼と応答が確認され、取得結果にはunit check 324件、mock browser check 25件が報告されました。これは単一結果であり、CLI稼働、一般的な自動routing、独立したテスト再実行を示すものではありません。

QwenのWindowsローカル文章応答は本人操作で確認済みです。Colabの[PR #35](https://github.com/moruku36/qwen-multimodal-colab/pull/35)はCPU CI 287件（2件skip）を報告し、Colab/GPU inferenceとモデルdownloadは実行していません。A100での品質、速度、VRAM、計算使用量は延期中です。RunPodの起動、HTTP接続、自動終了は目標設計であり、未検証です。

ユーザー承認、実行環境の権限承認、ローカルテスト、稼働環境への反映は別段階です。正規の承認が拒否されたら作業を保存して止め、再承認を連打したり別経路で迂回したりしません。

## Dottieとworkflow層

DottieはPMであり、全タスクが自動実行されるという意味ではありません。scopeと受け入れ条件を明確にし、適格なprovider／環境を選び、進捗とhandoffを調整します。

- **AI Engineering Factory**は薄い再利用可能なhandoff/artifact/evidence層です。minimal handoffは[PR #29](https://github.com/moruku36/ai-engineering-factory/pull/29)（`4fb014a`でmerge）で確認され、Ubuntu/Windows品質ゲートとoffline container-boundary検証を含みます。
- **AIteamBridge**は別のlocal capacity/router/transport開発projectです。246件のlocal/offlineテストが報告されていますが、未commit・未公開で、live quota取得と自動dispatchは未検証です。
- 3つの役割は補完的で、完全自動orchestratorが3つあるという説明はしません。

## ChappyとCodex

Codexはタスクに適する場合または明示的に割り当てられた場合に使います。通常のOpenAI選定は **GPT-6 Luna / Medium** または **GPT-6.1 Sol / Medium** の2択です。範囲が明確な作業にはLuna Medium、難度や品質要求が高い作業にはSol Mediumを選び、Low/Medium/Highの6段階運用は行いません。ExtraHighは引き続き使いません。Astraは学術研究や特に難しい上級調査で必要な場合のみ、具体的な理由を示して使う例外です。Sol Mediumで十分ならそれを使います。モデル名は本人の運用上の表記であり、CLI IDやruntimeでの利用可能性を証明しません。

workerの実選択とruntime確認ができない場合は、その制約と`UNKNOWN`を報告します。

## Claude Code

通常のコーディング・deploy作業ではSonnet 5.5を使い、難度が高い場合はOpus 5.5を選びます。deployには適切な権限承認が別途必要です。直接Claude CodeとAntigravity内Claudeは別々のquota poolを使います。

## Gemini / Antigravity

PoC、mock、または適した実装での候補ですが、常に最初に使う固定経路ではありません。タスクの難度・品質・環境・新しいcapacity根拠・コストでモデルとeffortを選びます。明示されたタスク固有の選択は尊重しますが、全体の既定には広げません。

## Quotaを考慮した選択

1. sessionとweeklyのquota枠を別々に扱い、各観測時刻を記録します。
2. 直接Claude Code、Antigravity Claude/GPT、Antigravity Gemini、native Codexは別poolです。API課金はsubscription quotaではありません。
3. 5時間利用がなかっただけではquotaが100%に戻ったと判断できません。
4. 欠落または古い観測は`unknown`とし、推測せず明示的または手動選択に戻ります。
5. 難度、品質、環境、観測の新しさ、消費ペース、reset時間、コストを合わせて判断します。固定しきい値だけでは決めません。
6. quota画像、正確な残高、account支出、認証情報、private session dataを公開しません。

## 呼称と報告

Dottie、Chappy、Claude Code、Gemini/Antigravity、Qwenは文脈が明らかな場合の役割名として使います。会話上の依頼はタスク固有のtool選択に落とし込み、指定model/effortと観測runtimeを分けます。CLI IDを作りません。

詳細は[2026-10-06運用判断](operating-decisions-2026-10-06.ja.md)と[routing guide](routing-guide.ja.md)を参照してください。
追加確認: MacのOpen WebUI 0.11.4とローカルQwen2.5 3Bはローカル応答とWeb検索結果を返しましたが、自動orchestrationではありません。WebUI → OpenAI-compatible API → on-demand RunPod Qwenは目標設計です。Podの自動起動、HTTP接続、自動終了は未確認です。OpenAI-compatibleはAPI形式を指し、有料OpenAI利用を意味しません。Pod停止と削除は異なり、停止中も永続storageに費用が発生することがあり、削除はデータを失う可能性があります。