# レビュー依頼の互換性

[English](review-request-compat.md)

2026-11-12: ソース修正、mock3件は **未実行**。
[MiMo API](https://mimo.mi.com/docs/en-US/api/chat/openai-api-post)では
`mimo-v2.6-pro`のthinkingは既定enabled、disabledも指定可能です。
[Deep thinking](https://mimo.mi.com/docs/en-US/quick-start/usage-guide/text-generation/deep-thinking)
は回答と出力枠を共有します。両自動レーンで非思考を明示し、Alibabaは
CLI設定を上書き後の送信byteを課算。会話／tools、全上限（出力2048）、
検証／length拒否、再試行禁止、既存予約を維持。単体接続／合成は変更なし。
推論は浅くなり得ます。live復旧／品質受入は未完了です。

PR55はAlibaba CLI失敗とCloudflare検証失敗を記録していますが、生の
finish reason／上流statusはなく真因 **UNKNOWN**。出力2048だけでは
打切りを証明できません。固定Alibaba v1.13.7はnative reasoning履歴を保持。
新テストには実行枠と対応する隔離環境が必要です。
