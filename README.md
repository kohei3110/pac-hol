# Azureハンズオン — 座学後に進める全5回の自習

座学で聞いたサービスを、実際に作って確かめるための手順書です。
**Microsoftから付与されたAzureサブスクリプションを使い、各回の座学後に自分のペースで進めます。**
講師が準備するのはサブスクリプションの案内と教材だけです。RG・アプリ・ネットワーク・Foundryプロジェクトを事前に作って配る方式ではありません。

毎回、参加者本人が、個人識別名を使って新しいRGとリソースを作り、終わったら削除します。
まず[共通の始め方・名前・権限](self-study.md)を読んでください。
例の`ksaito73`は、自分のイニシャルやニックネームに数字を足した識別名へ置き換えます。

更新日: 2026-10-13。Portalだけの全工程、まだ撮影できていない画面、初学者の試行は各回の実施記録に分けています。

## 各回の資料

ブラウザーで読むならHTML、印刷するならPDFを使ってください。HTMLは画像・チェック欄・配布データを内蔵しています。

| 回 | 内容 | 参加者用 | 講師向け・記録 |
| --- | --- | --- | --- |
| 1 | VMの作成、状態確認、停止、削除 | [Markdown](01-vm/guide.md) ／ [HTML](01-vm/guide.html) ／ [PDF](01-vm/guide.pdf) | [案内](01-vm/instructor-guide.md) ／ [実施記録](01-vm/run-through.md) ／ [画像](01-vm/screenshots.md) |
| 2 | Bastionで非公開VMへログインする | [Markdown](02-bastion/guide.md) ／ [HTML](02-bastion/guide.html) ／ [PDF](02-bastion/guide.pdf) | [案内](02-bastion/instructor-guide.md) ／ [実施記録](02-bastion/run-through.md) ／ [画像](02-bastion/screenshots.md) |
| 3 | 新版を先に試し、同じURLを切り替える | [Markdown](03-containerapps/guide.md) ／ [HTML](03-containerapps/guide.html) ／ [PDF](03-containerapps/guide.pdf) | [案内](03-containerapps/instructor-guide.md) ／ [実施記録](03-containerapps/run-through.md) ／ [画像](03-containerapps/screenshots.md) |
| 4 | 自分のアプリを展開し、Blobへ保存して表示する | [Markdown](04-blob/guide.md) ／ [HTML](04-blob/guide.html) ／ [PDF](04-blob/guide.pdf) | [案内](04-blob/instructor-guide.md) ／ [実施記録](04-blob/run-through.md) ／ [画像](04-blob/screenshots.md) |
| 5 | 自分のFoundryを作り、日本語の音声AIを試す | [Markdown](05-voice-agent/guide.md) ／ [HTML](05-voice-agent/guide.html) ／ [PDF](05-voice-agent/guide.pdf) | [案内](05-voice-agent/instructor-guide.md) ／ [実施記録](05-voice-agent/run-through.md) ／ [画像](05-voice-agent/screenshots.md) |

## 何を自分で作るか

| 回 | 本人が作成・確認・削除するもの | 時間の目安 |
| --- | --- | --- |
| 1 | RG、Ubuntu VM、ディスク、VNet/NIC/NSG、SSHキー。公開IP・公開ポートなし | 60〜75分 |
| 2 | 新しいRG、VNet、VM、鍵、NSG、Bastion Basicと公開IP。接続を切るだけで終わらずRG削除 | 75〜90分＋予備15分 |
| 3 | RG、Consumption環境、Container App、旧版・新版。MCRの公開サンプルを使用 | 60〜75分＋予備15分 |
| 4 | RG、Storage、uploads、MI/RBAC、ACR、VNet/PE/DNS、環境、Container App。配布ソースを本人のACRでビルド | 120〜150分＋削除待ち30分程度 |
| 5 | RG、Foundryリソース、プロジェクト、データ権限、Voice。Managedモデルで会話し、指示を変えて比較 | 90〜120分＋予備15分 |

前の回のRGは使い回しません。第4回のビルド用[作成ファイル一式](04-blob/assets/handson04-self-study.zip)も教材として配布します。
それはソースと設定であって、講師が展開済みのアプリやリソースではありません。

第4・5回ではRBACのロール割り当ても本人が行います。Contributorだけでは通常できないため、付与環境の権限を先に確認してください。
費用、利用期限、地域の制限もMicrosoftからの案内に従います。

## 読み方と、まだ残っている確認

画像は設定欄を探すために使い、入力値は本文の表を見てください。以前の画像の`p01`などをそのまま使う必要はありません。
HTMLでは画像をクリックすると拡大できます。

実Azureで試したこと、作成前のフォームだけを撮ったこと、独自に描いた図は別に記録しています。
第4回の新しい本人構築フロー、第5回のPortal作成・人のマイク会話など、実施できていない部分は完了扱いにしません。
初学者に手順書だけで試してもらい、時間や迷った箇所をもう一度見直す必要があります。

本文・図は、このコースのために新しく作成しています。
構成は[指定のAzure Functionsハンズオン](https://github.com/kohei3110/Serverless-Computing-using-Azure-Functions)の事前準備／Exercise／Taskを参考にし、
製品アイコンは[Microsoft公式配布版](https://learn.microsoft.com/en-us/azure/architecture/icons/)を使用しています。
この教材はMicrosoftの公式教材・認定教材ではありません。
