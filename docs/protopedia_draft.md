# ProtoPedia Submission Draft — ReleaseGuard Agent

---

## 🛠️ プロダクト名 (Title)
**ReleaseGuard Agent：Gemini が証拠に基づいてリリース可否を判断する AI Release Gate**

---

## 📝 概要 (Overview)
GitHub PR、Cloud Run プレビュー環境、API/UI プローブ、スクリーンショット、Cloud Logging、リスクポリシーを Gemini が統合的に分析し、`APPROVE` / `WARN` / `BLOCK` / `ESCALATE` / `FIX_PR` を判断する DevOps 向け AI Agent。

---

## 🚨 課題・背景 (Problem Background)
「テスト（CI）はパスしたのに、本番環境にデプロイしたらユーザー画面の一部（購入ボタンなど）が崩れていて使えなかった」「誤ってAPIキーなどの機密情報をPRに含めてコミットしてしまい、情報漏洩のリスクが発生した」といったトラブルは絶えません。
従来のCIは主に静的なチェックや単体テストを行うものであり、以下のような課題があります。
1. レンダリング結果（CSSでの要素非表示など）といった「動的なUXレイアウトの不具合」を検知しにくい。
2. コミットされたシークレット情報の自動検知が不十分。
3. リリース判定（マージ判定）には、CI結果、コードの意図、外部連携の変更などの「多角的な証拠の合成」が必要であるにもかかわらず、ルール記述が固定的。

ReleaseGuard Agent は、単なるCIの代替品ではなく、収集されたすべての「動的・静的証拠」を合成し、安全なリリース判断を行う **意思決定レイヤー（AI Release Gate）** です。

---

## 🎯 ターゲットユーザー (Target User)
GitHub Actions と Google Cloud Run を活用する個人開発者、小規模チーム、スタートアップ開発者。

---

## ✨ プロダクトの特徴 (Product Features)
- **証拠に基づく多角的なリリース評価 (Evidence-Based Judgement)**:
  APIのヘルスチェック結果、PlaywrightによるUIの描画状況（要素の不透明度・位置情報を含む）、コード変更の差分、漏洩スキャンといった複数の結果を自動収集。
- **AI による証拠の合成判定 (AI Release Judgement Synthesis)**:
  Gemini 2.5 Flash を活用し、収集された全ての証拠を分析して、構造化されたリスク分析結果を出力します。
- **決定論的リスクポリシーによる安全ガードレール (Deterministic Safety Overrides)**:
  「認証情報（シークレット）の漏洩」や「購入ボタンの非表示化」が検知された場合、AIの判定結果にかかわらず決定論的にリリースを強制的に **BLOCK** します。
- **PR自動レポート連携 (PR Comment Report)**:
  GitHub Actions と連携し、PRのコメントとしてAI分析（危険箇所の警告、安全な次のアクション、回避すべき行動など）を常に最新の状態に上書き更新し、デベロッパーの作業を妨げません。

---

## 🏗️ 開発素材・使用技術 (Development Materials)
- **Google Cloud AI**: Gemini API (gemini-2.5-flash) - 証拠の合成・構造化評価
- **Google Cloud Runtime**: Google Cloud Run - Agent サービスおよびデモアプリのホスティング
- **Application Engine**: Playwright Async API - ブラウザ自動化・UI/UXレイアウト視覚プローブ
- **CI/CD Integration**: GitHub Actions - PR イベント検知および自動評価キック、GitHub Script コメント連携
- **Backend Framework**: Python FastAPI - 非同期処理対応の高速 API サービス
- **Observability**: Cloud Logging & Structlog - 構造化ログ監視とトレース
