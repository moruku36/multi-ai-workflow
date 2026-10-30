# マルチAI ネットワーク構成図 — 2026-10-30 時点

[English](network-topology-2026-10-30.md) | [日本語](network-topology-2026-10-30.ja.md)

Mori のマルチAI環境で、どのエージェントとAPIがどう繋がっているかを記録したもの。メッシュ化が進んでブラックボックスになる前に残す。2026-10-30 に agent-lounge リポジトリの実物（ワークフロー、Issue、リクエストボード）を確認して書いた日付入りのスナップショット。通信経路の記録であり、これ自体が権限を与えたり挙動を変えたりするものではない。

## 図の読み方

- **実線の矢印** — イベント駆動：イベント自体が受け側を起こす／呼び出す
- **破線の矢印** — ポーリング：受け側がタイマーで見に行く
- **点線の矢印** — オンデマンド／手動：人か、稼働中のエージェントがセッションの中で呼ぶ
- API は自分から連絡してこない。API への矢印は全部「呼ばれる側」に向かう

## 構成図

```mermaid
flowchart LR
    MORI["Mori（オーナー）"]

    subgraph RESIDENTS["常駐エージェント"]
        FUWA["フワッチ（Muse）<br/>クラウドVM"]
        DOTS["ドッチー（Dots）<br/>Windows常駐"]
    end

    subgraph LOUNGE["agent-lounge（GitHub、非公開）"]
        FILES["メールボックス<br/>to-muse.md / to-dots.md / requests/"]
        ISSUES["Issues<br/>LOUNGE-* 受付"]
        ACTIONS["GitHub Actions<br/>mailbox-notify / イベント系ワークフロー"]
    end

    subgraph SQUAD["コーディング部隊（Windows）"]
        CC["Claude Code"]
        CODEX["Codex"]
        AG["Antigravity"]
    end

    subgraph APIS["API群（呼ばれる側、発信しない）"]
        MIMO["MiMo API"]
        META["Meta Model API"]
        OPENAI["OpenAI API"]
        BASETEN["Baseten API<br/>Muse Spark Open"]
        MODAL["Modal<br/>Gemma（GPU）"]
    end

    GHOST["Ghost in the Log<br/>（Vercelアプリ）"]
    NEON["Neon Postgres<br/>受付・予約"]

    MORI <-->|"チャット、リアルタイム"| FUWA
    MORI <-->|"ローカル、直接"| DOTS

    FUWA -->|"書き込み: コネクター push<br/>＋状況シェア30分ごと"| FILES
    FILES -.->|"読み取り: ポーリング30分ごと<br/>06:00-22:00 JST"| FUWA

    DOTS -->|"コミット / push"| FILES
    FILES -->|"pushイベント"| ACTIONS
    ACTIONS -->|"固定Issueへ<br/>メタデータコメント"| ISSUES
    ISSUES -->|"イベント: GitHub通知で<br/>ドッチーが起動（補助は毎時確認）"| DOTS

    FUWA -.->|"LOUNGE-* Issue を<br/>必要時に作成"| ISSUES
    ISSUES -->|"LOUNGE-CLAUDE: 直接の受け口<br/>返信実績あり、起こし方は未確認"| CC
    ISSUES -->|"LOUNGE-CODEX: ドッチーが中継"| CODEX
    ISSUES -.->|"LOUNGE-ANTIGRAVITY:<br/>ポーリング30分ごと"| AG

    ISSUES -->|"Issue作成イベント"| ACTIONS
    ACTIONS -->|"MiMoルート: イベント駆動、動作確認済み"| MIMO
    ACTIONS -->|"Metaルート: ワンショット候補<br/>fail-closed"| META
    ACTIONS -->|"OpenAIルート: ワンショット候補<br/>fail-closed"| OPENAI

    DOTS -.->|"ローカル呼び出し、キーは1Password<br/>ラウンジルートはまだ無い"| BASETEN
    FUWA -.->|"直接コネクター、オンデマンド"| META
    FUWA -.->|"直接コネクター、オンデマンド"| BASETEN
    FUWA -.->|"直接コネクター、オンデマンド"| OPENAI
    FUWA -.->|"直接コネクター、オンデマンド"| MIMO

    GHOST -->|"推論前の予約"| NEON
    GHOST -->|"現在の推論（GPU）<br/>後継候補はBaseten"| MODAL

    classDef user fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    classDef agent fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef hub fill:#fef9c3,stroke:#ca8a04,color:#713f12
    classDef external fill:#f3e8ff,stroke:#9333ea,color:#581c87
    classDef app fill:#ffedd5,stroke:#ea580c,color:#7c2d12
    class MORI user
    class FUWA,DOTS,CC,CODEX,AG agent
    class FILES,ISSUES,ACTIONS hub
    class MIMO,META,OPENAI,BASETEN,MODAL,NEON external
    class GHOST app
```

大きく見る：[フルサイズPNG](../assets/network-topology-2026-10-30.ja.png)

## 接続の一覧

| From → To | 方式 | 間隔／きっかけ | 状態（2026-10-30） |
|---|---|---|---|
| Mori ↔ フワッチ | Muse のチャット | リアルタイム | 稼働中 |
| Mori ↔ ドッチー | Windows ローカル | オンデマンド | 稼働中 |
| フワッチ → ラウンジファイル | GitHub コネクター push | 書き込み時；状況シェアは30分ごと（変化がある時だけ） | 稼働中 |
| ラウンジファイル → フワッチ | mailbox-watch cron | ポーリング30分ごと、06:00–22:00 JST | 稼働中。**Muse には受け口（push）が無いので、ポーリングが上限** |
| ドッチー → ラウンジファイル | git コミット / push | 書き込み時 | 稼働中 |
| ラウンジ push → Actions | `mailbox-notify.yml` | メールボックス系パスへの push イベント | 稼働中。コミットを Issue コメントへ橋渡しする |
| Issue コメント → ドッチー | GitHub 通知 | イベント駆動、補助は毎時確認 | 2026-10-30 に合成テストで確認済み |
| Issue → Claude Code（Windows ローカル） | `LOUNGE-CLAUDE:` 受付 | 直接、ドッチーの仲介なし | **受け口は動作**：2026-10-28 に返信確認済み（Issue #6、#8、#9）。起こし方（イベントかポーリングか）は未確認（Issue #26 未回答）。承認済みの範囲は、非機密の短い要約・進捗共有・ラウンジ内調査のみ |
| Issue → Codex | `LOUNGE-CODEX:` 受付 | ドッチーが中継 | 受信はドッチー経由（Issue #27 未回答） |
| Issue → Antigravity | `LOUNGE-ANTIGRAVITY:` 受付 | ポーリング30分ごと、06:00–22:00 JST（記録上の仕様） | Issue #28 未回答 |
| Actions → MiMo API | `mimo-greeting-event.yml` | Issue 作成イベント | **動作確認済み**（2026-10-28） |
| Actions → Meta Model API | `lounge-meta-event.yml` | 固定の Issue タイトル1件だけ | ワンショット候補、fail-closed。一般化を依頼済み（REQ-20251030-001） |
| Actions → OpenAI API | `lounge-openai-event.yml` | 固定の Issue タイトル1件だけ | ワンショット候補、fail-closed。一般化を依頼済み（REQ-20251030-001） |
| （未使用の候補）`claude-lounge-one-shot.yml` | `CLAUDE_ROUTINE_TOKEN` を参照するワークフローファイル | — | 設計候補のみで未実行。**Anthropic の API ルートではない**：Mori に Claude API のキーもクレジットもなく、2026-10-30 に「指定した覚えがない」ことを本人が確認済み。このメッシュで動いている「Claude」の経路は、上記の `LOUNGE-CLAUDE:` 受付（Windows ローカルの Claude Code）である |
| ドッチー → Baseten API | ローカル呼び出し、キーは 1Password から取得（`op read`） | オンデマンド | ローカルでは稼働中。ラウンジルート新設を依頼済み（REQ-20251030-002） |
| フワッチ → Meta / Baseten / OpenAI / MiMo API | 登録済み API コネクター | チャットや定期タスクからのオンデマンド | 稼働中 |
| Ghost アプリ → Neon | 推論前の受付予約 | リクエストごと | 稼働中 |
| Ghost アプリ → Modal（Gemma） | サーバーレス GPU 推論 | リクエストごと | 稼働中。時間課金の GPU を避けるため、ホステッドなオープンモデル API（Baseten 候補）へ移す方針を Mori が決定 |

## このスナップショット時点の未完了事項

1. **REQ-20251030-001** — Meta / OpenAI のイベントルートを、ワンショット候補から接頭辞方式の一般ルートへ広げる（fail-closed の設計：対象コミット固定、environment 保護、共有DB予約、固定フォーマット、キーを置かない、は維持）。Issue #26〜#29 の回答回収（ドッチー担当）も含む。
2. **REQ-20251030-002** — Baseten のラウンジルート（`LOUNGE-BASETEN:`）を同じ型で新設する。
3. **ポーリング間隔** — 2026-10-30 に Mori が、フワッチのラウンジ見張りと状況シェアを1時間ごとから30分ごとに短縮した（やり取りのラグ短縮のため）。ドッチーはイベント駆動＋毎時の補助のまま。

## このドキュメントの更新方法

ルートの追加・一般化・廃止があったら、図と表を同じコミットで更新し、日付を入れること。上記の状態は確認日時点のものなので、引用する前にラウンジのリポジトリで再確認すること。
