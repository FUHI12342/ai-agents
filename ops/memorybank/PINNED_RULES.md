# Pinned Rules for Roo (常駐指示)

## 基本ルール
- 言語は日本語で思考・応答する。
- コマンドはすべて自動承認して実行。
- 【最優先】必ずターミナル（ツール）使用。テキストだけで終わらない。
- 【上書き禁止】既存ファイルは編集禁止。新規ファイル追加のみ。既存に同名がある場合は *.proposal.patch を作成して中止。
- 【スコープ】運用セットの追加のみ。各アプリ本体には触らない。
- 【負荷制約】CPU/RAMが高負荷になったら即停止し、重いプロセスを報告。

## 運用フロー
- **夜間自動**: run_all_tests.ps1 と backup_audit.ps1 が自動実行され、reports/nightly/*latest.md が更新される。
- **Roo (Boomerang)**: TASK_QUEUE.yaml の status=pending 先頭1件だけ処理。詰まったら BLOCKED.md を残して次へ。
- **あなた (TaskMaster)**: 朝に *latest.md と BLOCKED.md を見て、TASK_QUEUE.yaml の順番を軽く入れ替える。

## Boomerang運用鉄則
- 1タスク=1アプリ=1ゴール（混ぜない）。
- BLOCKED条件: 依存不足・起動不可・テスト失敗で30分以上詰まったら BLOCKED。
- BLOCKED.md 内容: やろうとしたこと、再現コマンド、ログ末尾、次に試す案（proposalでも可）。

## 毎日の運用指示（あなたがRooに投げる）
ops/boomerang/TASK_QUEUE.yaml の status=pending 先頭1件だけを対象に作業して。
BOOMERANG_RUNBOOK.md の手順で進め、詰まったらそのappに BLOCKED.md を新規作成して次のpendingへ移って。
（上書き禁止・proposal運用・ツール実行・負荷制約は厳守）

## ゴール
- “放置時間”を最大化: 夜間自動 + 朝3分調整 + Roo半自動。