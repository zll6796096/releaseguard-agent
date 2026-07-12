# Proto Pedia submission draft

## 作品ステータス案
開発中（MVP はローカル・Cloud Run 想定構成で動作確認済み。今後の拡張余地があるため）

## 作品タイトル案
ReleaseGuard Agent：証拠で止めるAIリリースゲート

## 概要
PRのプレビュー環境をAPI・UI・秘密情報・AIで検証し、本番前に危険な変更をBLOCKするリリースゲート。

## 動画URL欄
https://youtu.be/ZTKjSorZjx8

## ProtoPedia 登録済みURL
https://protopedia.net/prototype/8771

## システム構成説明
ReleaseGuard Agent は GitHub Actions から `POST /evaluate` を受ける FastAPI サービスです。PR の changed files、diff、commit SHA、preview URL を入力に、API health check、checkout DOM 検査、Playwright の実レンダリング検査、Secret Scan を並列実行します。Gemini 2.5 Flash は収集証拠を `GeminiJudgement` schema で要約し、最終判定は決定論的な `RiskPolicy` が統合します。checkout ボタン不可視化や秘密情報漏洩は、AI の判断に関係なく `BLOCK` します。現行 MVP は永続DBを持たず、Playwright screenshot はコンテナ内 `/tmp/releaseguard-artifacts` に一時保存します。Cloud Run / Docker / GitHub Actions での運用を想定しています。

## 開発素材一覧
- Python 3.12
- FastAPI
- Pydantic / pydantic-settings
- HTTPX
- structlog
- Playwright / headless Chromium
- Google GenAI SDK
- Gemini 2.5 Flash
- Jinja2 / HTML / CSS
- Docker
- Google Cloud Run
- GitHub Actions
- actions/github-script / GitHub REST API
- pytest / pytest-asyncio

## タグ一覧
findy_hackathon, AI, 生成AI, DevOps, GitHubActions, CloudRun, FastAPI, Playwright, リリース管理, セキュリティ

## ストーリー
## ① 本作品で解決したい課題とその背景
CI は「書かれたテストが通ったか」を確認できますが、「その変更をユーザーに届けるだけの証拠が揃っているか」までは判断しません。今回のデモでは、checkout ボタンが DOM には存在するのに CSS の `opacity: 0` でユーザーから見えなくなる regression を扱います。selector ベースのテストや health check は通っても、実際の購入導線は止まります。小規模チームほどリリース前の目視確認が属人化しやすく、見逃しがそのまま本番障害につながります。

## ② 想定する利用ユーザー
GitHub Actions と Google Cloud Run を使って Web サービスを継続的に開発・デプロイする個人開発者、小規模チーム、スタートアップを想定しています。特に、PR のたびにプレビュー環境は作っているものの、UI の視覚的な壊れ方や PR 差分のリスクを毎回十分にレビューしきれないチームに向いています。

## ③ プロダクトの特徴
ReleaseGuard Agent は、PR の changed files / diff / commit SHA / preview URL を受け取り、API health、checkout DOM、Playwright による実レンダリング、Secret Scan を並列に実行します。収集した証拠は Gemini 2.5 Flash の構造化出力で人間に読みやすく要約し、最終判定は決定論的な Risk Policy が安全側に統合します。たとえば checkout ボタン不可視化や秘密情報漏洩は、AI の判断に関係なく `BLOCK` します。自動マージや本番トラフィック切替は行わず、PR コメントとして証拠と安全な次アクションを返す点が特徴です。

## 関連URL候補
- GitHub Repository: https://github.com/zll6796096/releaseguard-agent
- Demo Store URL: https://demo-store-788259830737.asia-northeast1.run.app
- ReleaseGuard Agent URL: https://releaseguard-agent-788259830737.asia-northeast1.run.app
- Demo PR: https://github.com/zll6796096/releaseguard-agent/pull/2
- YouTube Demo: https://youtu.be/ZTKjSorZjx8
- ProtoPedia: https://protopedia.net/prototype/8771

## YouTube / Vimeo 用タイトル
ReleaseGuard Agent - 証拠でリリース可否を判断するAI Release Gate

## YouTube / Vimeo 用説明文
ReleaseGuard Agent は、GitHub PR と Google Cloud Run のプレビュー環境を対象に、API health、Playwright による実画面検証、Secret Scan、Gemini 2.5 Flash の構造化要約を組み合わせて、危険なリリースを本番前に BLOCK する AI Release Gate です。

この動画では、checkout ボタンが DOM に存在するにもかかわらず CSS の opacity: 0 によりユーザーから見えなくなる regression をデモします。通常の CI が見逃し得るユーザー導線の破損を、ReleaseGuard が証拠つきで検出し、PR 上に BLOCK 判定を返します。

## YouTube / Vimeo 用タグ
findy_hackathon, ReleaseGuard, AI, 生成AI, DevOps, GitHub Actions, Google Cloud Run, FastAPI, Playwright, Gemini, リリース管理, セキュリティ

## サムネイルに使う画像ファイル名
`image_01_main.png`
