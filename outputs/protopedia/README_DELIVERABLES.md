# Proto Pedia deliverables

## 必須成果物
- `demo_video.mp4`: YouTube / Vimeo アップロード用 MP4。日本語テロップ、BGM、実画面スクリーンショット入り。
- `video_script_ja.md`: 動画の日本語ナレーション台本。
- `youtube_vimeo_metadata.md`: アップロード用タイトル、説明文、タグ、サムネイル指定。
- `image_01_main.png`: メインビジュアル。作品名と価値提案。
- `image_02_problem.png`: 課題画像。CI が見逃す透明 checkout ボタン。
- `image_03_demo.png`: デモ画像。実行結果の BLOCK 90/100。
- `image_04_technology.png`: 技術画像。AI と決定論ルールの分離。
- `image_05_impact.png`: 成果画像。導入後の価値。
- `system_architecture.png`: 登録用システムアーキテクチャ図。
- `system_architecture.svg`: 同内容の SVG 版。
- `system_architecture.md`: 技術説明文。
- `protopedia_submission.md`: Proto Pedia 登録欄に貼る本文ドラフト。

## 追加成果物
- `storyboard.md`: 動画構成の簡易 storyboard。
- `raw_screenshots/`: Docker 起動した実アプリから撮影した 1920x1080 PNG。
- `video_assets/`: 評価 JSON、動画スライド、BGM、生成スクリプト。
- `protopedia_upload/`: ProtoPedia の推奨サイズ 880x495px に合わせたアップロード用画像。

## 登録済みURL
- YouTube: https://youtu.be/ZTKjSorZjx8
- ProtoPedia: https://protopedia.net/prototype/8771

## ローカル検証で使った起動方法
既存の `8081` が使用中だったため、提出素材用には次のポートで Docker 起動しました。

```bash
docker network create rg-proto-net
docker run -d --name rg-proto-demo --network rg-proto-net -p 8091:8080 -e BUG_HIDE_CHECKOUT_BUTTON=false releaseguard-demo-store-protopedia:local
docker run -d --name rg-proto-agent --network rg-proto-net -p 8095:8080 -e GEMINI_MODEL=gemini-2.5-flash releaseguard-agent-protopedia:local
```

## 登録時の注意
YouTube へ限定公開アップロード済みです。ProtoPedia には動画 URL、紹介画像 5 枚、システム構成画像、本文、タグ、関連リンクを登録済みです。YouTube のカスタムサムネイルは電話番号確認が必要だったため、動画先頭スライド由来の自動サムネイルを使用しています。
