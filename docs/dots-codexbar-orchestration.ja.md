# Dottie、CodexBar、handoffの境界

[English](dots-codexbar-orchestration.md) | [日本語](dots-codexbar-orchestration.ja.md)

> 2026-10-05時点。quotaは手動確認であり、live quota取得や完全自動dispatchは未検証です。

この文書ではPM調整、capacity観測、再利用可能なhandoffの役割を区別します。DottieはPM、AI Governance Controlは薄いhandoff/artifact/evidence層、AIteamBridgeはcapacity/router/transportを扱う別のローカル開発プロジェクトです。3つは相互補完的で、完全自動orchestratorが重複しているわけではありません。

## 実行環境

- Windowsを常時稼働のローカル基地かつ第一選択とします。Windowsで進められない場合はMacへ切り替える前にユーザーへ相談します。
- Macは補助環境です。
- Dottieはscope、provider／環境選択、進捗、受け入れ、レビュー調整を担います。
- 選ばれた担当が範囲を限定して作業します。AI Governance Controlはhandoffとevidenceを再利用できる形で保持します。

## quota観測

CodexBar画像は手動で確認します。自動画像読取やlive quota feedを稼働中と説明しません。sessionとweeklyのquota枠を分け、provider pool、観測時刻、新しさを記録します。5時間操作がないことはquota全回復の根拠になりません。直接Claude Code、Antigravity内Claude/GPT、Antigravity Gemini、native Codexは別poolです。API課金とsubscription quotaも別です。不明・古い観測は`unknown`として手動判断に戻します。

## 確認状況

AI Governance Controlのminimal handoffは[PR #29](https://github.com/moruku36/ai-engineering-factory/pull/29)で検証済みです。Bridgeの246件というテスト報告はlocal/offline、未commit/未公開であり、live quota取得と自動dispatchは未検証です。

監督付きAntigravity Webセッション1件で依頼と応答を確認し、結果にはunit check 324件とmock browser check 25件が報告されました。これはWebでの単発タスク観測です。CLI稼働、一般的な自動routing、テストの独立再現を示しません。個別の会話、接続先、識別子、logは公開しません。

正規の承認、実行環境の権限、ローカルテスト、live環境への反映を別々に記録します。承認拒否時は保存して止め、再承認を繰り返したり他経路で迂回したりしません。

## 個人情報と今後の作業

providerのcredential、cookie、account内容をrouterへ渡しません。正確な残高・課金値、quota画像、私的会話、接続先の識別情報、logを公開しません。今後quota/routerを開発する場合は古い値や`unknown`でfail-closedとし、logは秘匿情報を除いた根拠だけにします。provider経路、権限、結果の読み戻し、受け入れ確認が揃う前に自動実行中と主張しません。