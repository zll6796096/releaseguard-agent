# Storyboard

1. タイトル: ReleaseGuard Agent / 証拠で判断するAIリリースゲート
2. 課題: CIは緑だが、checkoutボタンが透明で購入できない
3. 解決策: PR previewをAPI・UI・Secret・AIで検査
4. デモ1: 正常なcheckout入力画面
5. デモ2: hidden-button regression
6. デモ3: BLOCK 90/100 の実行結果
7. 技術: GitHub Actions、FastAPI、Playwright、Gemini、Cloud Run
8. 価値: 本番前に止める、人間が最終判断する
9. 今後: 認証つきE2E、ログ異常、DB migrationチェック
