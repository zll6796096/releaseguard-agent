# System Architecture

## 構成概要
ReleaseGuard Agent は、GitHub Actions から `POST /evaluate` を受け取り、PR の preview URL と diff を証拠として検査するステートレスな FastAPI サービスです。対象アプリケーションは Demo Store の Jinja2 checkout UI で、Cloud Run 上のプレビュー環境を想定しています。

## 実装に基づくコンポーネント
- **User / Client**: GitHub PR を作成・確認する developer / reviewer。
- **Frontend**: `apps/demo_store` の FastAPI + Jinja2 + HTML/CSS checkout UI。GitHub PR コメントも結果表示面になる。
- **Backend / API**: `apps/releaseguard` の FastAPI。`GET /healthz` と `POST /evaluate` を提供。
- **AI / LLM / External API**: `google-genai` SDK で Gemini 2.5 Flash を呼び、`GeminiJudgement` schema の structured output を生成。
- **Database / Storage**: 現行 MVP に永続DBはない。Playwright screenshot は `/tmp/releaseguard-artifacts/checkout.png` に一時保存。
- **Authentication**: `RELEASEGUARD_SHARED_TOKEN` が設定されている場合、HTTP Bearer token を要求。GitHub Actions 側は repository secrets / variables を使用。
- **Deployment / Hosting**: Docker コンテナを Google Cloud Run に配置。ローカル検証は Docker network 上の Demo Store と ReleaseGuard Agent で実施。

## 判定フロー
1. GitHub Actions が PR context、changed files、diff、preview URL を `scripts/call_releaseguard.py` で収集する。
2. ReleaseGuard Agent が `ApiProbe`、`SecretScan`、`PlaywrightProbe` を並列実行する。
3. `RiskPolicy` が checkout failure、secret leak、Playwright failure を決定論的に BLOCK する。
4. Gemini が証拠を構造化要約する。Gemini が失敗または未設定の場合は WARN fallback を返す。
5. 最終 risk は policy risk と Gemini risk の最大値。最終 report は Markdown と JSON で返る。
6. GitHub Actions が `actions/github-script` で PR コメントを作成・更新し、BLOCK / ESCALATE なら workflow を fail させる。
