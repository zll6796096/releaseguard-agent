# ReleaseGuard Agent — ProtoPedia Submission Details

## タイトル
ReleaseGuard Agent：Gemini が証拠に基づいてリリース可否を判断する AI Release Gate

---

## 概要
ReleaseGuard Agent は、GitHub PR、Cloud Run プレビュー環境、API/UI プローブ、Playwright による視覚的検証、Secret Scan、Gemini の構造化出力を組み合わせて、リリース可否を判断する DevOps 向け AI Agent です。CI が「定義済みチェックが通ったか」を示すのに対し、ReleaseGuard は「この変更をユーザーに届けるだけの証拠が揃っているか」を判断します。

---

## 課題 (Problem)
CI が成功しても、実際のユーザー導線が壊れていることがあります。例えば、checkout ボタンが DOM には存在していても、CSS（例: opacity: 0 や display: none）によって不可視化されていれば、単純な selector test や unit test は通過してしまいます。小規模チームでは、このようなリリース直前の判断が人間の目視確認に依存しがちです。

---

## ターゲットユーザー (Target User)
GitHub Actions と Cloud Run を使って Web サービスを継続的に開発・デプロイする個人開発者、小規模チーム、スタートアップ。

---

## 主な機能 (Core Features)
- **Cloud Run preview URL validation**: PR に紐づくステージング/プレビュー環境を対象にチェックを実行します。
- **API health probe**: アプリケーションの `/healthz/` エンドポイントの状態を取得します。
- **Playwright visual UI probe**: ヘッドレス Chromium を使用し、対象要素（例: `data-testid="checkout-button"`) が画面上で視覚的にユーザーに見えているか、覆い被さりや不透明度（opacity）を含めて検出します。
- **Secret scan over PR diff**: PR 内の変更差分にシークレットや認証キーが含まれていないかスキャンします。
- **Gemini structured evidence synthesis**: API health、UI 視覚テスト、シークレットスキャンなどのテキスト証拠・差分データを Gemini 2.5 Flash に入力し、人間にとって可読性の高いリスク要約と安全措置の提案を出力します。
- **Deterministic risk policy**: 収集した証拠を決定論的なポリシーエンジンに通し、1つでも異常値があれば確実に `BLOCK` を出す堅牢性を両立します。
- **GitHub PR comment report**: PR コメント上で、グラフィカルかつわかりやすいマークダウンレポートとして結果を通知し、`BLOCK` や `ESCALATE` 判定時には自動的にワークフローを失敗させます。
- **Safety guardrails**: デフォルトでマージブロックを行うのみで、自動マージや自動本番トラフィック切り替えは行いません。

---

## 技術スタック (Tech Stack)
- **Infrastructure**: Google Cloud Run
- **AI**: Gemini API (structured output + evidence synthesis)
- **Backend / Language**: Python 3.12, FastAPI
- **Browser Automation**: Playwright (headless Chromium)
- **CI/CD Integration**: GitHub Actions, GitHub CLI

---

## デモストーリー (Demo Story)
PR ブランチ上で、チェックアウトページの HTML テンプレートを変更し、購入ボタン（Pay ボタン）に対して `hidden-button` CSS クラスを強制的に適用します。これにより、ボタンは DOM 上には存在しますが視覚的には不透明度 0% になりクリックできなくなります。
この PR が作成されると、GitHub Actions がトリガーされて Cloud Run 上の `releaseguard-agent` を呼び出します。Agent は PR プレビュー環境にアクセスして API および Playwright での画面要素確認を行い、ボタンが不可視化されている証拠を検知します。
ReleaseGuard は PR に警告レポートをコメントし、GitHub Actions のステータスチェックを `Failure` にして本番リリースを未然にブロックします。

---

## 既知の制限事項 (Limitations)
この MVP バージョンはステートレスな PR プレビュー検証に焦点を当てています。現時点では、データベースのスキーマ移行の依存分析、ログイン認証を必要とするブラウザ操作フロー、複数テナントごとの認証設定、Cloud Logging のログアノマリ分析などは未対応です。
