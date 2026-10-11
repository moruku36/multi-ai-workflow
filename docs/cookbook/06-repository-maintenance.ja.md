# Cookbook 06: Repository Maintenance

[English](06-repository-maintenance.md) | [日本語](06-repository-maintenance.ja.md)

公開repositoryには再利用可能な運用指針とevidenceの状態だけを置き、privateな作業文脈は含めません。ユーザーが許可した作業の文書化では、一般化した説明を使い、実装、ローカル検証、稼働状態を区別します。

## 編集前

1. repositoryのstatusを確認し、既存のユーザー変更を保持します。
2. 最新のdefault branchと関連する根拠を確認します。
3. 分離されたbranch/worktreeで作業し、無関係な変更を上書きしません。
4. 日英対応ページとリンクを把握します。

## 編集中

- GitHubでコードを変更したときは、影響するREADME、使い方、設計文書と既存の日英対応ページを更新し、両言語の状態を一致させます。
- [routing guide](../routing-guide.ja.md)のタスク別選択基準を使います。
- 本人の運用上のモデル名と明記し、CLI IDや実行可能性を作りません。
- Dottie（PM）、AI Governance Control（薄いhandoff/artifact/evidence）、AIteamBridge（ローカルcapacity/router/transport開発）の責務を分けます。
- verified/merged、local/offline、runtime pending、proposalを一貫して使います。
- 私的会話、認証情報、quota画像、残高、個人・家族情報、接続識別子を公開しません。
- 目標設計をdeploy済み、自動稼働中と説明しません。

## 統合前

リンク、日英参照、空白、古い主張を確認します。変更一覧とdiffに秘密やprivate contextがないか確認し、確認結果とblockerを正確に報告します。方向への承認、依頼受付、実行、ローカルテスト、本番反映は別状態です。
