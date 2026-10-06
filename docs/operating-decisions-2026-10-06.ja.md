# OpenAIモデル選定の更新 — 2026-10-06

[English](operating-decisions-2026-10-06.md) | [日本語](operating-decisions-2026-10-06.ja.md)

本人の最新指示に基づく文書上の運用方針です。認証設定や実モデルのruntime configを変更・検証するものではありません。

通常のOpenAI選定は **GPT-6 Luna / Medium** または **GPT-6.1 Sol / Medium** の2択です。範囲が明確な作業にはLuna Medium、難度や品質要求が高い作業にはSol Mediumを選び、Low/Medium/Highの6段階運用は行いません。ExtraHighは引き続き使いません。Astraは学術研究や特に難しい上級調査で必要な場合のみ、具体的な理由を示して使う例外です。Sol Mediumで十分ならそれを使います。モデル名は本人の運用上の表記であり、CLI IDやruntimeでの利用可能性を証明しません。

指定worker model/effortと観測runtime model/effortを分けます。実選択や確認ができなければ制約を記載し、観測値は`UNKNOWN`とします。指示されたモデルが実際に選択・実行されたと根拠なく報告しません。

[2026-10-02](operating-decisions-2026-10-02.ja.md)と[2026-10-05](operating-decisions-2026-10-05.ja.md)はlegacyの履歴です。当時の選定段階、実験条件、観測結果を保持し、現在の2択を過去に遡って適用しません。

他AIの役割、Windows第一選択、quotaのsession/weekly区別、provider poolの分離、古い観測を`unknown`とする運用、手動CodexBar確認、安全・公開範囲の境界は従来どおりです。旧記録の検証件数やruntime状態は今回再確認していません。

現行の使い分けは[Routing Guide](routing-guide.ja.md)、役割は[AI Team](ai-team.ja.md)、根拠の記録は[handoffテンプレート](handoff-templates.ja.md)を参照してください。
