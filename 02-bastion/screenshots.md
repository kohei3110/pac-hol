# 第2回 — 画面と図の出典・更新方法

Portalを撮影した画面と、接続経路を描いた図を掲載しています。
画像の種類、撮影日、状態、隠した範囲、寸法、SHA-256は `assets/manifest.json` に記録しています。

## 収録する画像

| ファイル | 画像の種類 | 説明していること |
| --- | --- | --- |
| `assets/bastion-path.png` | 公式アイコンを使った教材独自の説明用図 | 443と22、2つのサブネット、VMとBastionの公開IPの違い |
| `assets/bastion-path.excalidraw` | 図解の編集可能な元ファイル | PNGと同じ関係図。Portal画面ではない |
| `assets/portal/02-bastion-create.png` | 実際のBastion作成フォームを撮影 | 作成画面の選択肢。デプロイ成功・ログイン成功の証拠ではない |
| `assets/portal/01a-vm-subnet.png` | 新しいVNet内のサブネット入力欄 | Task 2。VM用の名前と `/24` |
| `assets/portal/01b-bastion-subnet.png` | 新しいVNet内のBastion専用サブネット入力欄 | Task 2。Azure Bastionの目的と `/26` |
| `assets/portal/01-vnet-subnets.png` | 作成前のサブネット一覧 | Task 2。2つの区画と、重なっていない範囲 |
| `../01-vm/assets/portal/02-basics-os-size.png` | 第1回と共通のVM作成前の基本情報 | Task 3。Ubuntu 24.04 x64 Gen2・Trusted launch・D2alds_v6（2 vCPU・4 GiB）。VM名は第2回用に読み替える |
| `../01-vm/assets/portal/05-private-network.png` | 第1回と共通のVM作成前のネットワーク設定 | Task 4。公開IPなし・受信ポートなし・高速ネットワーク有効 |

作成画面を撮ったPortalは、検証CLIとは別のアカウント・サブスクリプションです。
Basicを選んだ、作成前の画面を撮影し、既存RG・契約名・アカウントなどを隠しています。設定値を学習用に描き替えてはいません。
最初にPremiumなどが選ばれることもあるので、本文ではBasicを自分で選ぶ手順を案内しています。

2026-10-12に、VNetの作成フォームで3枚を追加撮影しました。フォームの中でサブネットを編集・追加していますが、VNetの「作成」は実行していません。
既存のネットワークは変更せず、設定値を画像の上で描き替えることもしていません。
VMのRSAと公開IPの欄は、第1回の作成前の画像を共通の参考として載せています。キー名は第2回用に読み替える説明を添えており、Bastion接続後の画像としては使っていません。

2026-10-28に第1回で撮り直した、D2alds_v6の基本情報と高速ネットワーク有効の画像も共通の参考として使用しています。出典・切り出し範囲・SHA-256は `../01-vm/assets/manifest.json` に記録しています。第2回でのデプロイやBastion接続を示す画像ではありません。

## 配布前に撮っておく画面

現行版のTask 1で、本人がRGを作り、個人識別名とParticipantタグを付ける画面も追加します。
これはまだ撮影できていません。既存の写真の名前は撮影時の例なので、本文の自分の控えへ読み替えます。

| 番号 | 対象 | 必ず見せる項目 |
| --- | --- | --- |
| 03 | 第2回専用のVM基本情報と認証 | Ubuntu x64 Gen2、D2alds_v6、RSA、パブリック受信なし |
| 04 | VMネットワーク | VM区画、VMの公開IPなし |
| 05 | VM側NSG | AllowSshFromBastion 300とDenyOtherSsh 310 |
| 06 | Bastion作成の確認画面 | Basic、専用サブネット、Standard Static公開IP |
| 07 | Bastion接続・認証選択 | ローカルファイルからの秘密キー、`azureuser`。鍵の中身は表示しない |
| 08 | 接続後のLinux画面 | VM内でwhoami、hostname、OS確認。実IP・個人情報は除去 |
| 09 | 今回のRGのリソース | VM・ディスク・NIC・VNet・NSG・SSHキー・Bastion・公開IP |
| 10 | RG削除確認 | 自分のRG名、削除対象、確認欄 |
| 11 | 削除完了 | 更新後のRG・VM・Bastion一覧で今回の名前がない |

まだ撮れていない画面は、`assets/manifest.json` の `pendingScreenshots` に残します。
Microsoft Learnの画像を参照するときも、自分が撮った画面とは分けて出典を書いてください。第1回の画像を、第2回でログインした画面として流用することはしません。

## 撮影・マスク

撮影用のウィンドウだけを写し、メール、Teams、他のタブ、デスクトップは入れません。
個人情報、契約名、実際のID、既存RG名、IPは不透明な矩形で隠し、PNGのメタデータも除去します。
鍵の中身、Portalのトークン、パスワードは画面に出さないでください。注釈はUIの値を変えず、1枚につき1〜3個の矢印や番号に絞ります。

元画像はローカルの一時領域に置き、公開用画像を確認したあとに削除します。
Portalの画面が変わったら、撮り直し、手順を直して、もう一度試します。

## 再生成

文章は `guide.md` と講師用Markdown、画像の出典は `assets/manifest.json` を編集します。
ルートで `python3 tools/build_handson.py --lesson 02` を実行し、図と画像入りHTMLを作ります。
PDFも、HTMLの「手順書を印刷・PDF保存」から作り直してください。第2回だけを更新する場合、第1回のファイルを作り直す必要はありません。
HTMLの画像はクリックまたはEnterで拡大できます。

公式アイコンは[Microsoftの配布版V24](https://learn.microsoft.com/en-us/azure/architecture/icons/)を、形や色を変えず、縦横比を保って使っています。
枠・線・説明文は教材用に描いたもので、Microsoftの公式構成図ではありません。
