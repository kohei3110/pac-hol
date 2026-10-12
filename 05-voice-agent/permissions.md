# 自分のFoundryプロジェクトの権限を確認する

これは[手順書](guide.md)のTask 3で、プロジェクトのリソースリンクが見つからない場合の補足です。
Microsoftから付与された環境で、自分が今作ったプロジェクトだけを確認します。

Azure Portal上部のCloud Shellを**Bash**で開き、次の4つの値を、自分の控えへ置き換えます。
一時Cloud Shellを使う場合は、ストレージを新しく作らず開始できます。

```bash
SUBSCRIPTION="自分のサブスクリプションID"
RG="rg-hol05-自分の識別名"
FOUNDRY="自分のFoundryリソース名"
PROJECT="proj-hol05-自分の識別名"
```

説明の日本語を残したまま実行しないでください。サブスクリプションの既定値を変更する必要はありません。

自分のプロジェクトと、自分のEntra Object IDを取得します。

```bash
PROJECT_ID=$(az cognitiveservices account project show \
  --subscription "$SUBSCRIPTION" --resource-group "$RG" \
  --name "$FOUNDRY" --project-name "$PROJECT" --query id --output tsv)
ME=$(az ad signed-in-user show --query id --output tsv)
```

どちらかがエラーになった場合は、次を実行せず、名前・アカウント・権限を見直してください。
空のまま変数を使わないよう、値があることを確認してから、現在の割り当てを調べます。

```bash
test -n "$PROJECT_ID" && test -n "$ME" && \
az role assignment list --subscription "$SUBSCRIPTION" \
  --assignee "$ME" --scope "$PROJECT_ID" --include-inherited \
  --query "[].{Role:roleDefinitionName,Scope:scope}" --output table
```

Foundry User、Foundry Ownerなどの必要なデータ権限があるなら、新しく付ける必要はありません。
ContributorやReaderだけで操作できるとは限らないので、FoundryでのAgent作成も確かめます。

**必要な権限がなく、かつロール割り当ての許可がある場合だけ**、自分のプロジェクトへFoundry Userを付けます。
次はそのプロジェクトを対象にしており、サブスクリプション全体への付与ではありません。

```bash
test -n "$PROJECT_ID" && test -n "$ME" && \
az role assignment create --subscription "$SUBSCRIPTION" \
  --assignee-object-id "$ME" --assignee-principal-type User \
  --role "53ca6127-db72-4b80-b1b0-d745d6d5456d" --scope "$PROJECT_ID"
```

完了後、Foundryを更新して反映を待ちます。`AuthorizationFailed`が出たら、自分で権限を広げず付与元へ相談してください。
このGUIDはFoundry UserのロールIDです。表示名が旧名Azure AI Userでも、IDは同じです。
Object IDやプロジェクトIDを、提出物へ載せる必要はありません。
