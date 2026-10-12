# Azureハンズオン — 全5回

座学で学んだ構成を、Azureの画面を触りながら確かめるハンズオンです。
VMを作るところから始めて、接続、アプリの更新、ファイルの保存、音声AIの作成へ進みます。使い終わったものを片付けるところまで、各回の手順に入れています。

## 各回の資料

ブラウザーで読む場合はHTML、印刷して配る場合はPDFを使ってください。HTMLには画像とチェック欄を埋め込んであるので、オフラインでも読めます。

| 回 | 内容 | 参加者用 | 講師用・実施記録 |
| --- | --- | --- | --- |
| 1 | VMを作って、Azureの基本操作を覚える | [Markdown](01-vm/guide.md) ／ [HTML](01-vm/guide.html) ／ [PDF](01-vm/guide.pdf) | [講師資料](01-vm/instructor-guide.md) ／ [実施記録](01-vm/run-through.md) ／ [画像の出典](01-vm/screenshots.md) |
| 2 | Bastionを使ってVMにログインする | [Markdown](02-bastion/guide.md) ／ [HTML](02-bastion/guide.html) ／ [PDF](02-bastion/guide.pdf) | [講師資料](02-bastion/instructor-guide.md) ／ [実施記録](02-bastion/run-through.md) ／ [画像の出典](02-bastion/screenshots.md) |
| 3 | 新しい版を試してから、アプリを切り替える | [Markdown](03-containerapps/guide.md) ／ [HTML](03-containerapps/guide.html) ／ [PDF](03-containerapps/guide.pdf) | [講師資料](03-containerapps/instructor-guide.md) ／ [実施記録](03-containerapps/run-through.md) ／ [画像の出典](03-containerapps/screenshots.md) |
| 4 | CSVをBlobに保存して、表とグラフで見る | [Markdown](04-blob/guide.md) ／ [HTML](04-blob/guide.html) ／ [PDF](04-blob/guide.pdf) | [講師資料](04-blob/instructor-guide.md) ／ [実施記録](04-blob/run-through.md) ／ [画像の出典](04-blob/screenshots.md) |
| 5 | Foundryで日本語の音声AIエージェントを作る | [Markdown](05-voice-agent/guide.md) ／ [HTML](05-voice-agent/guide.html) ／ [PDF](05-voice-agent/guide.pdf) | [講師資料](05-voice-agent/instructor-guide.md) ／ [実施記録](05-voice-agent/run-through.md) ／ [画像の出典](05-voice-agent/screenshots.md) |

## 全5回の構成案

| 回 | 内容・所要時間 | 実際に試すこと | 準備・費用の注意 | 資料 |
| --- | --- | --- | --- | --- |
| **1** | VMの基本操作・60分 | Ubuntu VMを1台作り、ディスクやネットワークを見ます。停止したあと、専用RGを削除します。 | 学習用サブスクリプションを使用。公開IP・SSH/RDP・Bastionはなし。VMとディスクには料金がかかります。 | [手順書](01-vm/guide.md) |
| **2** | Bastionでの接続・75〜90分 | VNet・VM・Bastion Basicを作り、ブラウザーでログインします。最後に専用RGを削除します。 | VMの公開IPはなし。Bastion専用/26サブネットとRSA鍵を使用。Bastionと公開IPも削除が必要です。 | [手順書](02-bastion/guide.md) |
| **3** | アプリの更新・切り替え・60〜75分 | Multipleで旧版100%に固定し、previewで新版を試します。同じURLを新版、旧版へ切り替え、専用RGを削除します。 | Microsoftの公開イメージ2版とConsumptionを使用。各版は最小0／最大1。秘密値は入れず、ビルド・ACR・Jobsは扱いません。 | [手順書](03-containerapps/guide.md) |
| **4** | Blobへの保存・表とグラフ・45〜60分 | 架空CSVを保存し、読み直した表・グラフを見ます。開き直し、比較CSV、不正入力、削除も試します。 | 講師がアプリ・MI・コンテナー単位RBAC・PEを準備。鍵・SASは配らず、64 KiB／24行／10件まで。SQL・Redisは作りません。 | [手順書](04-blob/guide.md) |
| **5** | **Foundry Voice Agentの作成・日本語会話**・60〜75分 | Voiceを選んで作り、指示・モデル・声を保存。日本語で会話し、End後に指示を変えて比較。会話・Agentを削除し基盤の終了を確認 | 講師が専用プロジェクト・Foundry User・Voiceプレビュー・対応モデルを準備。Managed、録音標準オフ、合計10分以内の会話試行。電話・アバター・外部操作なし | [手順書](05-voice-agent/guide.md) |

前の回のリソースは残さなくて構いません。

なお、この教材はMicrosoftの公式教材・認定教材ではありません。
