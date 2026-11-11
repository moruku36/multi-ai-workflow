# Alibaba＋Cloudflare レビュー連携

[English](dual-review.md) | [日本語](dual-review.ja.md)

## 自動controllerと手動依頼

[自動PR controller](automatic-dual-review.ja.md)に両系統の実行とPRイベント起動を
実装しました。有効化・実PR受入は未実施です。以下の手動依頼も別経路として残します。

Cloudflare公式の [security-audit-skill](https://github.com/cloudflare/security-audit-skill)
を [.agents/skills/security-audit](../.agents/skills/security-audit/SKILL.md) に改変せず導入しました。
固定コミットは `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`。
[MITライセンス](../third_party/cloudflare-security-audit/LICENSE)、公式README、
SHA256一覧を保持します。導入ツールはGit blobハッシュを照合し、パッケージ管理・
install hook・上流コードの実行を行いません。上流の実行可能スクリプトも通常ファイルとして保存し、
必要な監査が許可された場合だけ所定のNodeコマンドで使います。
リポジトリ内への導入であり、OpenClawへのグローバル登録や全クライアントの自動検出を意味しません。

`tools/dual_review.py` は同一差分の依頼作成と結果の記録状態確認です。
レビュアーの起動、認証設定、Git hook、Actions、コメント公開、マージは行いません。

## 変更ごとの運用契約

このリポジトリのコード変更では、次の流れを目指します。

1. feature commitとcleanな作業ツリーを用意する。
2. 固定base/head SHAで依頼を1つ作る。
3. Alibaba OpenCodeReview＋MiMoでその差分をレビューする。
4. 適格なコーディングエージェントがCloudflareスキルに沿って同じ差分をソースレビューする。
   自動検出されないクライアントはSKILL.mdと該当する補助文書を明示的に読む。
5. 実際の担当者・provider/model・実行根拠・指摘・未解決事項を別々に記録し、headと作業ツリーを再確認する。
6. 指摘解消、必要な別provider独立レビュー、人による受入を行う。新しいcommitでは依頼を作り直す。

通常の差分レビューは上流の **guidance mode** による部分的な確認です。
6段階の完全監査・侵入試験・Cloudflareのサービスではありません。
完全監査には明示した範囲、独立エージェント、validator、予算、sandboxが必要です。
必要な隔離を用意できない状態で対象コードは実行しません。
Cloudflareは手法の提供元であり、実際のモデルproviderではありません。
ツール名が2つあっても独立性の証明にはなりません。

## 依頼作成と確認

40文字の完全なcommit SHAと、既存の非公開親ディレクトリを使います。
出力は対象リポジトリ外の新規ディレクトリにします。

```sh
python3 tools/dual_review.py prepare \
  --repo /absolute/path/to/repository \
  --base FULL_BASE_COMMIT_SHA --head FULL_HEAD_COMMIT_SHA \
  --output /absolute/private/parent/new-dual-review
python3 tools/dual_review.py status --run /absolute/private/parent/new-dual-review
```

準備はキー不要・ローカルのみです。未追跡ファイルも含めcleanであること、
導入ファイルのハッシュを確認し、差分は65,536バイトまでに制限します。
非公開の `plan.json`、`change.diff`、`REQUEST.md`、
`receipt-template.json` を作成します。テンプレートは実行証拠ではありません。
依頼文にも各レーンの未実装部分を記載します。対象コードは実行しません。

実レビュー後、担当コーディネーターがテンプレートの形式で
`alibaba.json` と `cloudflare.json` を別々に記録します。
未実行を完了として埋めてはいけません。
欠落・形式不正・未完了・古い差分は完了扱いしません。
`BOTH_RECORDED_NOT_ACCEPTED` も「両方の記録あり」であって合格ではなく、
重大指摘が残っている場合もあります。記録は操作者の申告で、ハッシュは整合性確認に限られます。
必須マージチェックや信頼されたCI証明として使わないでください。

## 検証と残件

先のOCR試行は **累計10/10件・3回実行** のままです。
今回、追加テスト・上流validatorのテスト・実API呼出しは行っていません。
`tests/check_dual_review.py` に結果ゲートの選択3件を作成済みですが未実行です。
実行前に3件の予算追加が必要です。準備処理のファイル／Git経路も未検証です。

既存の `ocr_mimo_review.py` は合成サンプル専用です。
その実レビュー結果を通常ブランチの証拠にはできません。
PRごとの自動運転には以下が残っています。

- 親プロセスのみがMiMoキーを持つ、上限付き通常差分Alibabaアダプター
- Cloudflareレーンの実エージェント起動経路とprovider/model・担当分離の実証
- 選択検証と上限付きの両レーン受入実行
- 認証注入、継続実行の回数／費用上限
- イベント起動、head単位の重複防止、timeout／結果不明時の照合、非公開成果物管理

継続課金・スケジュール・グローバル設定・保護ルールは有効化していません。
先の合成レビュー品質も最終受入待ちです。
