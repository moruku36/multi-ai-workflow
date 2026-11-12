# レビュー事前判定の追補

[English](review-preflight.md)

2026-11-12：PR53追補、base `87a22a5`。上限付き固定SHA fetch/collectを永続予約前へ移し、
両レーンは予約後を維持。事前判定前にreportを作成し、finallyで保持します。
`PREFLIGHT_REJECTED` は予約なし。`RESERVATION_FAILED_OR_UNKNOWN` は全レーン停止。
診断に例外文・秘密・ソース・モデル内容を含めません。既存check・予約は変更せず、
過去の不明な結果・試行数・費用は不明のまま。再実行は許可しません。

SHA／差分束縛、byte・token・timeout・並列・課金上限は維持。
central・OIDC・署名・有効化・キー・方針は変更せず、既存レビュー／マージゲートを維持。

独立unittest 2メソッド：collect上限超過拒否と正常時の順序／束縛。
作成済み **UNEXECUTED（未実行）**、subcaseなし。外部I/O・API・暗号・providerはモック、
一時receipt I/Oだけ実体。ブランチ限定CIはPR opened/synchronizeで2件だけ選択。
試行は8件／CI 2回、残り2件を親が手配するCI 1回に充て、再実行なし。
今回のテスト・ソース実行はゼロ。同一実差分の両レビューとlive受入は未完了。
モックはその証明になりません。
