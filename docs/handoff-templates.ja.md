# 再利用可能なhandoffテンプレート

[English](handoff-templates.md) | [日本語](handoff-templates.ja.md)

ツール間で作業を渡すときは、範囲と受け入れ条件を明確にします。DottieはPMと受け入れ調整、AI Governance Controlは薄いhandoff/artifact/evidence層、AIteamBridgeは別個のローカルcapacity/router/transport開発を担います。live quota取得と自動dispatchは未検証です。

現行の[担当表・配分手順](operating-decisions-2026-10-13.ja.md)に従います。通常の受け渡し失敗は1回で原因を保存し、別の認可済み候補1つへ。権限拒否は停止し迂回しません。不可なら`blocked`／本人handoff待ちで、Codexの全文代行に自動で戻しません。

## 短い進捗受渡し

通常の進捗受渡しは次の4項目に絞ります。詳しい根拠が必要な場合は下の evidence manifest を参照し、会話履歴全体を複製しません。

```text
目的: [達成目標と観測可能な完了条件]
現在の状態: [提案 | 受付 | 実行 | 検証 | 保留。環境も記載]
根拠: [成果物のパス、revision、テスト結果、または UNKNOWN]
次の一歩: [範囲を限定した操作、担当、必要な承認]
```

`受付` は依頼が受理されたことだけを示します。`実行` には実際の成果物、`検証` には指定 revision の完了条件に照らした確認が必要です。オフライン・模擬結果を実接続成功に読み替えません。headless `request-review` の権限拒否は soft denial も含めて `保留` とし、拒否の根拠を保存して正規の判断を求めます。別のID・権限・経路による迂回再試行はしません。公開する受渡しには資格情報、私的な会話、アカウント固有の利用量を含めません。

オフライン例（合成データのみ）:

| 観測 | 報告する状態 | 次の一歩 |
|---|---|---|
| 担当が依頼を受け付けたが成果物がない | `受付` | 結果を確認するかタイムアウトを記録し、完了としない |
| サンプル入力の成果物が得られ、ローカル確認が通った | `検証済み（オフラインのサンプル）` | 必要なら別途承認された実接続確認へ進む |
| headless レビューが権限段階で拒否された | `保留` | 拒否を保存し、具体的な正規の判断を求める |

## Evidence manifest

モデル比較や複数段階の作業では、実行前に入力、prompt、受け入れ条件、rubric、制約、評価手順を固定します。

```text
task_id:
goal / completion criteria:
small input / revision:
worker / one authorized alternative:
planned budget / work limit:
capacity pool / session-weekly observation time / reset time: 不明は unknown
handoff failure / exception reason:
authorization stage / decision / evidence reference: 観測できなければ unknown
input data class / approved destination: 原則として公開・合成データを使用
input revision / paths / hashes:
prompt / rubric / acceptance criteria:
provider / route / environment:
requested model / effort:
observed runtime model / effort: 証拠がなければ UNKNOWN
accepted / executed / verified: それぞれ別の状態と証拠参照
output paths / hashes:
review findings / test results / unresolved items:
reacquire source / revision / hash:
```

依頼がacceptedまたはWorkingと表示されても、完了の証明にはなりません。結果を読み、受け入れ条件を確認します。local/offlineテストはlive provider経路や本番反映を証明しません。

## Product Owner / Dottieから制作・調査・実装担当へ

```markdown
# Goal
[達成したいこと]

## Scope and constraints
- 対象:
- 対象外:
- 環境 / provider制約:

## Acceptance criteria
- [観測可能な結果]

## Requested model/effort
[このタスク固有の指定。全体既定に一般化しない]

## Report back
- 変更ファイル / artifact:
- 実施した確認と結果:
- accepted / executed / verifiedの状態:
- 未確認事項とblocker:
```

## Qwen調査handoff

```markdown
# Research question
[質問]

## Inputs and permitted sources
- Files / URLs:
- Read-onlyか、その他の境界:

## Findings
- 出典付きの所見:
- 確度や曖昧さ:

## Handoff
- Evidence / artifact参照:
- 次の担当への質問:
- 調査結果から実装、稼働成功、権限を推定しない:
```

## 独立レビュー

```text
提示したrevisionを独立にレビューし、実装変更は行わない。
重大度、file/line、根拠、影響、再現または確認方法を記載。
未確認の前提と重要なテスト不足を明示。
重大な指摘がなければ、その旨と残るruntime制約を記す。
```

## 3. PoCから実装への任意の精緻化

PoCが重要な不確実性を減らす場合にだけ使います。既存artifactを保持し、初期実装を重複させません。

```markdown
# Goal and acceptance criteria
[範囲を限定した目標]

## Existing artifact and verification
- revision / files:
- 実行済みテスト:
- 既知の不足:

## Refinement request
- 根拠が変更を支持しない限り、動作中の挙動とarchitectureを保つ。
- 編集、確認、未解決事項、必要な承認を報告する。
```

## 5. 検証済みreview指摘の適用

```text
次の確認済み指摘だけを適用する:
[指摘IDと根拠]

変更範囲を小さく保つ。関連する確認を行い、変更ファイル、確認結果、残る不明点を報告する。
```

## 6. 権限承認が拒否された場合は停止して保持

```text
必要な操作は[承認段階]で拒否された。
繰り返し再試行したり、別経路で拒否を迂回したりしない。
現在の作業を保持し、正確な操作、対象、拒否理由、保存済みartifact、次に許可された手順を報告する。
```
## 4. 独立レビューの範囲と出力

レビュー依頼では、確認するfiles、変更範囲、特に見るrisk領域を指定します。reviewerは実装変更を行わず、次を返します。

- Critical/Majorの指摘はfile/line、根拠、影響、再現または確認方法を含める。
- 未確認の前提を列挙し、確かな事実のように書かない。
- 重要なtest gapを示す。
- 重大な指摘がない場合も、その結論と残るtest/runtime制約を記す。
## 範囲

レビュー対象revision、files／変更箇所、懸念するrisk領域を明示します。reviewerは提示されたrevisionを独立に確認し、実装をしません。

## 出力

- Critical/Majorの指摘にはseverity、file/line、根拠、影響、再現または確認方法を含めます。
- 未確認の前提と重要なテスト不足を列挙します。
- 重大な指摘がなければその旨を述べ、残るtest/runtime gapも記します。
## 7. PR Review Evidence

[PR Review Pipeline](pr-review-pipeline.ja.md)向けに、依頼受付と完了・検証を分けて記録します。

```text
PR URL / base SHA / head SHA:
goal / acceptance criteria / changed files:
risk: low | medium | high | unknown; rationale:
builder tool / observed provider:
reviewer tool / observed provider / independence limitation:
requested review / completed review / reviewed SHA / result URL:
findings: ID / severity / file-line / evidence / impact / reproduction:
fix SHA / disposition / new-head review:
required checks / commands / result / current-head logs:
inapplicable gates / rationale / approved exceptions:
unresolved test and runtime gaps:
work limit / repair cycles / blocker:
merge authorization / human acceptance / decision / decision head SHA:
status: documented | configured | executed | verified
```

## 8. Claude Opus 5.5 Mediumへの限定的な最終エスカレーション（2026-10-15）

本人選択のGPT/Solで難題が停滞した場合（同じ失敗の繰り返し、または合意した作業上限内に具体的な進捗なし）にのみ使います。本人の運用判断であり、Opusが客観的に最良という主張ではありません。[2026-10-15の決定](operating-decisions-2026-10-15.ja.md)に従います。秘密情報、私的な会話、アカウント識別子、quota残高は含めず、最小限の非秘密のソース/revisionを使います。

```markdown
# Goal and acceptance criteria
[範囲を限定した目標]

## Preserved state
- 現象:
- 再現手順:
- 試した方法と結果:
- 未検証事項:
- 制約（権限、TLS検証、秘密情報、有料操作の承認）:
- 最小限の非秘密のソース / revision:

## Delegation bounds
- 作業上限（完了または上限で通常モデルへ戻す）:
- token残量・費用の確認（証拠がなければ unknown / stale）:
- Requested model/effort: Claude Opus 5.5 Medium
- Observed runtime model/effort: 証拠がなければ UNKNOWN

## Rules
- 拒否を迂回せず、runtime・モデル・TLS設定・権限を黙って変更しない。停止して報告する。
- 変更ファイル、確認結果、現在revisionの証拠、未検証事項、blockerを報告する。
```
