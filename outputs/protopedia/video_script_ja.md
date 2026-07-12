# ReleaseGuard Agent demo video script

想定尺: 84秒。動画内テロップは日本語。音声合成は使わず、BGMと画面テロップで完結する構成。

| 時間 | 画面 | ナレーション台本 |
|---|---|---|
| 0-5秒 | タイトル | ReleaseGuard Agent は、CI の先でリリース可否を証拠から判断する AI Release Gate です。Findy Hackathon / Proto Pedia 提出作品です。 |
| 5-15秒 | 課題 | CI はテストが通ったことを示します。しかし、checkout ボタンが CSS で透明になっていても、DOM に残っていれば selector test は通ることがあります。ユーザーには購入ボタンが見えません。 |
| 15-25秒 | 解決策 | ReleaseGuard は PR の preview URL、変更差分、commit 情報を受け取り、API、UI、秘密情報、AI 要約を組み合わせて判断します。 |
| 25-33秒 | 正常画面デモ | まず正常な checkout 画面です。入力欄と Pay ボタンが表示され、ユーザー導線は成立しています。 |
| 33-41秒 | regression デモ | 次に、PR で `hidden-button` が入った状態です。ボタンは HTML に存在しますが、画面上は見えずクリックできません。 |
| 41-51秒 | BLOCK 結果 | ReleaseGuard は Playwright で computed opacity を確認し、checkout button invisible として Risk 90 の BLOCK を返しました。 |
| 51-61秒 | 技術構成 | Backend は FastAPI、ブラウザ検証は Playwright、AI 要約は Gemini 2.5 Flash、デプロイ先は Google Cloud Run です。GitHub Actions から `/evaluate` を呼びます。 |
| 61-71秒 | 安全設計 | Gemini は説明を補強しますが、重大リスクの BLOCK は決定論ルールが優先します。自動マージや本番トラフィック切替は行いません。 |
| 71-84秒 | 価値と今後 | 小規模チームでも、目視に頼りきらず、証拠つきで危険な PR を止められます。今後は認証つき E2E、Cloud Logging、DB migration リスク分析へ拡張します。 |
