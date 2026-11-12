# 上限付き受入の草案 — 2026-11-12

[English](bounded-hub-draft.md)

ソースのみの変更。定期実行config・フラグは無効のままです。
`Hub.prepare_one_shot` は1件のrepo/PR/base/head、有効期限（現在から最大1時間）、
信頼済みlauncher revision、承認証拠digest、lane別試行上限を検証します。
既存の予約台帳、適格性・現在binding、日次・実行上限、対象receiptを照合します。
過去の予約・unknownも重複抑止対象で、hub自身を含む除外は維持します。
準備結果の予約・対象receipt識別子は既存namespaceを使用します。

独立したoperator証拠検証器と信頼済みone-shot launcherは未提供です。
digestは整合性のみを表し、`run_one_shot` は実行を拒否します。
manifest boolean・注入callback・要求fieldに課金権限はありません。
将来の統合では独立認証、controller revisionとrelay内試行上限の強制、同じhub全体の
同時実行制御、既存の全体予約→対象receipt→永続unknown→lane順序の再利用が必要です。
各有料lane直前に現在binding・期限を再確認します。force・reset・返金・unknown再実行は追加しません。

`automatic_dual_review.py` はdiff（65,536 bytes）、snapshot累計（65,536）、
Alibabaの実serialize済み要求（65,536）、Alibaba送信累計（524,288）、呼出回数
（Alibaba最大8・guidance 1）、出力token（2,048）、既存のprovider応答・出力file上限を
分離します。失敗送信も転送前に計上します。guidanceとJSON escapeも要求サイズに含みます。
guidance bodyは従来の196,608 bytesを維持し、1呼出の累計上限も同値です。
Alibaba累計は従来の最大8要求分と同じで、laneの要求上限は拡大していません。
収集可能でもJSON化・guidance追加後には送信不可の場合があります。

既存の信頼済み設定に大容量ソース承認はなく、opt-inは未提供です。
将来の別途レビュー済みpolicyには、承認・controller revisionに束縛した収集・serialize済み要求・
累計bytes・呼出・出力の独立上限が必要です。ソースサイズから要求上限を引き上げません。
PR52のmergeはmain c2a49f87e13a9a7c8eea2a3299a3bb8aba90cb05として独立確認済みであり、hub除外対象です。現行上限下で自身を自動レビューできるとは主張しません。

offline 3ケースを作成、**未実行**。テスト・import・コンパイル・build・readiness script・
通信・有料レビュー・対象コード実行なし。live権限、上限付き受入、同じ固定base/headの2系統レビュー、
異provider独立性・指摘解消・人の受入・merge gateは未完了です。過去の試行回数は変更しません。
