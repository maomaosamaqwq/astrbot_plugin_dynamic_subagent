# 🐾 Dynamic SubAgent — 日本語

[![Version](https://img.shields.io/github/v/release/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/releases)
[![Stars](https://img.shields.io/github/stars/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent)
[![License](https://img.shields.io/github/license/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/LICENSE)

メインAIエージェントがサブエージェントを動的に作成・管理できるAstrBotプラグイン。**権限分離**と**ネスト深度制限**による安全なマルチエージェントシステムを実現します。

## ✨ 特徴

| 特徴 | 説明 |
|------|------|
| 🧠 動的作成 | `spawn_agent` でサブエージェントをオンデマンド作成（権限/モデル/永続化を指定可能） |
| 🔄 タスク転送 | `transfer_to_agent` で既存サブエージェントにタスクを委任 |
| 🔒 権限分離 | `safe` / `medium` / `full` の3段階権限 — サブエージェントは昇格不可 |
| 🛡 深度制限 | サブエージェントはさらにサブエージェントを作成不可、無限連鎖を防止 |
| 💾 永続メモリ | 永続エージェントは再起動後もコンテキストを保持 + 履歴注入 |
| 🕥 協力トレース | spawn/transfer チェーンの完全な追跡とレポート |

## ⚙️ 権限体系

| レベル | 組み込みツール | プラグインツール | spawn可 | 説明 |
|:------:|:-------------:|:---------------:|:-------:|------|
| `safe` | ❌ | ホワイトリスト | ❌ | 検索+管理のみ |
| `medium` | ファイルR/W | ブラックリスト | ❌ | shell/pythonなし |
| `full` | ✅ 全て | ✅ 全て | ❌ | メインエージェントと同等 |

> サブエージェントはPython/IPython実行器を使用できず、サブエージェントを作成することもできません。

## 📦 インストール

AstrBotプラグインマーケットプレイスで `dynamic_subagent` を検索するか、手動でクローン：

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

## 🚀 クイックスタート

```python
# 1. 即時タスク付きサブエージェント作成
spawn_agent(
    name="code_reviewer",
    description="コードレビューアシスタント",
    permission_level="medium",
    task="以下のコードをレビューしてください：..."
)

# 2. 永続サブエージェント作成、後でタスク転送
spawn_agent(
    name="memory_bot",
    description="会話を記憶するアシスタント",
    persistent=True
)

transfer_to_agent(
    name="memory_bot",
    task="前回の話題を続けてください..."
)

# 3. 協力レポート表示
show_collaboration_report()
```

## ⚙️ 設定

| 設定項目 | デフォルト | 説明 |
|----------|:---------:|------|
| `max_spawns_per_event` | `10` | グローバルサブエージェント作成上限 |
| `max_handoffs_per_event` | `20` | グローバルタスク転送上限 |
| `max_context_turns` | `20` | 永続エージェントが保持するコンテキストターン数 |
| `trace_enabled` | `true` | 協力トレースの有効化 |
| `model_blacklist` | `[]` | 使用禁止モデルリスト |
| `model_filter_mode` | `blacklist` | モデルフィルターモード（blacklist/whitelist） |
| `allowed_models` | `[]` | ホワイトリストモード時の許可モデルリスト |

## 🏗 アーキテクチャ

```
メインエージェント (depth=0, full)
 └─ spawn_agent() → サブエージェント (depth=1, safe/medium/full)
     └─ transfer_to_agent() → サブエージェントがタスク実行
         └─ ❌ spawn不可 (depth>=1 でブロック)
```

- **ネスト深度**: メインエージェント depth=0、サブエージェント depth=1 — それ以上のネスト不可
- **権限継承**: 作成者の権限 ≥ 対象の権限（mediumはfullを作成不可）
- **ツール分離**: `_build_sub_tools` でサブエージェントツールを構築、depth≥1でspawn/deleteを自動削除

## 📝 ライセンス

MIT

---
*この紹介は日本語で書かれています。*
