"""Create the learner's private-Blob app in their own, already created RG."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import UUID, uuid4


HERE = Path(__file__).resolve().parent
STATE = HERE / ".lab04-state.json"


class SetupError(RuntimeError):
    pass


def personal_id(value):
    if not re.fullmatch(r"[a-z][a-z0-9]{2,9}", value):
        raise argparse.ArgumentTypeError("識別名は英小文字で始まる3〜10文字の英小文字・数字にしてください。")
    return value


def subscription_id(value):
    try:
        return str(UUID(value))
    except ValueError as error:
        raise argparse.ArgumentTypeError("サブスクリプションIDにはGUIDを入力してください。") from error


def client_ipv4(value):
    try:
        address = ipaddress.ip_address(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("PCのブラウザーで確認したIPv4を入力してください。") from error
    if address.version != 4 or not address.is_global:
        raise argparse.ArgumentTypeError("公開IPv4を1つだけ指定します。範囲や全IPの指定はできません。")
    return str(address)


def guard_preview(preview, subscription, group):
    prefix = f"/subscriptions/{subscription}/resourceGroups/{group}".lower()
    for change in preview["changes"]:
        identifier = change["resourceId"].lower()
        if (
            change["changeType"] not in {"Create", "NoChange", "Ignore"}
            or not identifier.startswith(prefix + "/")
        ):
            raise SetupError("今回のRG以外、または既存リソースの変更がwhat-ifに含まれるため止めました。")


class LearnerSetup:
    def __init__(self, state_path=STATE, bundle_root=HERE):
        self.state_path = state_path
        self.root = bundle_root
        self.state = {}

    def save(self):
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.state_path)

    def az(self, *args, timeout=1800):
        command = ["az", *args, "--subscription", self.state["subscription"], "--output", "json"]
        environment = {**os.environ, "AZURE_DEFAULTS_GROUP": ""}
        try:
            result = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise SetupError("CLIの待ち時間を超えました。同じ段階を再実行して既存の処理を確認してください。") from error
        if result.returncode:
            raise SetupError(f"Azure CLIで止まりました。\n{result.stderr.strip()}")
        if not result.stdout.strip():
            raise SetupError("Azure CLIから確認用のJSONが返りませんでした。成功とは判断せず止めました。")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise SetupError("Azure CLIの応答を読み取れません。Portalで実行結果を確認してください。") from error

    def load(self, require_group=True):
        if not self.state_path.is_file():
            raise SetupError("記録ファイルがありません。initから始めるか、保存した.lab04-state.jsonを戻してください。")
        try:
            self.state = json.loads(self.state_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise SetupError("作業記録を読み取れません。保存した.lab04-state.jsonを戻してください。") from error
        required = ["subscription", "ownerId", "group", "stem", "clientIPv4", "location", "marker"]
        if not isinstance(self.state, dict) or any(
            not isinstance(self.state.get(key), str) or not self.state[key] for key in required
        ):
            raise SetupError("作業記録に必要な項目がありません。バックアップと比べてください。")
        if (
            personal_id(self.state["ownerId"]) != self.state["ownerId"]
            or subscription_id(self.state["subscription"]) != self.state["subscription"]
            or self.state["group"] != f"rg-hol04-{self.state['ownerId']}"
        ):
            raise SetupError("記録された識別名・サブスクリプション・RGの対応が違います。")
        if require_group:
            group = self.az("group", "show", "--name", self.state["group"])
            tags = group.get("tags") or {}
            if any(tags.get(key) != self.state[value] for key, value in [
                ("Participant", "ownerId"), ("ValidationSession", "marker"),
            ]) or tags.get("Purpose") != "AzureHandsOn" or tags.get("Session") != "04":
                raise SetupError("RGの名前・所有タグがこの記録と一致しません。別のRGへは実行しません。")

    def initialize(self, subscription, owner_id, address, location):
        if self.state_path.exists():
            raise SetupError("このフォルダーには作業記録があります。prepare/build/deployから続けてください。")
        self.state = {
            "subscription": subscription, "ownerId": owner_id,
            "group": f"rg-hol04-{owner_id}", "stem": f"hol04-{owner_id}",
            "clientIPv4": address, "location": location, "marker": str(uuid4()),
        }
        group = self.az("group", "show", "--name", self.state["group"])
        tags = group.get("tags") or {}
        if tags.get("Participant") != owner_id or tags.get("Purpose") != "AzureHandsOn" or tags.get("Session") != "04":
            raise SetupError("先にPortalで自分のRGを作り、Purpose・Session・Participantタグを入れてください。")
        if tags.get("ValidationSession"):
            raise SetupError("このRGには前の作業記録があります。記録を戻すか、今回のRGを片付けてから始めてください。")
        if group["location"] != location:
            raise SetupError("RGと指定したリージョンが違います。記録を見直してください。")
        if self.az("resource", "list", "--resource-group", self.state["group"]):
            raise SetupError("RGが空ではありません。既存の環境に上書きせず、今回の空のRGを使ってください。")
        self.save()
        self.az("group", "update", "--name", self.state["group"],
                "--set", f"tags.ValidationSession={self.state['marker']}")
        print(f"今回の対象: {self.state['group']} / {owner_id} / {location}")
        print("記録ファイル: .lab04-state.json。サブスクリプションをもう一度確認してからprepareへ進みます。")

    def template_args(self, stage):
        path = self.root / "infra" / (
            "handson04-self-study.bicep" if stage == "base" else "handson04-app.bicep")
        parameters = [
            f"ownerId={self.state['ownerId']}", f"validationSession={self.state['marker']}",
            f"location={self.state['location']}",
        ]
        if stage == "app":
            parameters += [f"{key}={self.state[key]}" for key in
                           ["stem", "storageName", "registryName", "image", "clientIPv4"]]
        return [
            "--resource-group", self.state["group"], "--name", f"hol04-{stage}",
            "--template-file", str(path), "--parameters", *parameters,
        ]

    def deployment(self, stage):
        arguments = self.template_args(stage)
        started_key = f"{stage}Started"
        if not self.state.get(started_key):
            validated = self.az("deployment", "group", "validate", *arguments)
            if validated["properties"]["provisioningState"] != "Succeeded":
                raise SetupError("ARMの事前チェックに成功していません。デプロイはしていません。")
            preview = self.az("deployment", "group", "what-if", *arguments, "--no-pretty-print")
            guard_preview(preview, self.state["subscription"], self.state["group"])
            print(f"{stage}: 今回のRG内の新規作成だけと確認しました。", flush=True)
            self.state[started_key] = True
            self.save()
            result = self.az("deployment", "group", "create", *arguments)
        else:
            result = self.az("deployment", "group", "show", "--resource-group", self.state["group"],
                             "--name", f"hol04-{stage}")
        deadline = time.monotonic() + 1800
        while result["properties"]["provisioningState"] in {"Accepted", "Running"}:
            if time.monotonic() > deadline:
                raise SetupError("デプロイ処理が続いています。同じ段階を再実行して確認します。重複作成はしません。")
            time.sleep(10)
            result = self.az("deployment", "group", "show", "--resource-group", self.state["group"],
                             "--name", f"hol04-{stage}")
        if result["properties"]["provisioningState"] != "Succeeded":
            raise SetupError("デプロイが失敗しました。Portalのデプロイ詳細を確認し、終了時にRGを片付けてください。")
        return result

    def prepare(self):
        self.load()
        if not self.state.get("baseComplete"):
            result = self.deployment("base")
            self.state.update({key: item["value"] for key, item in result["properties"]["outputs"].items()})
            environment = self.az("containerapp", "env", "show", "--resource-group", self.state["group"],
                                  "--name", self.state["environmentName"])
            managed_group = environment["properties"].get("infrastructureResourceGroup")
            if not isinstance(managed_group, str) or not managed_group:
                raise SetupError("環境の管理用RGを確認できません。Portalで環境の状態を確認してください。")
            self.state["managedGroup"] = managed_group
            self.state["baseComplete"] = True
            self.save()
        for key in ["registryName", "storageName", "identityName", "environmentName"]:
            print(f"{key}: {self.state[key]}")
        print("基盤を作成しました。PortalのRG一覧で自分のリソースを見てからbuildへ進みます。")

    def verify_base_scope(self):
        resources = self.az("resource", "list", "--resource-group", self.state["group"])
        prefix = f"/subscriptions/{self.state['subscription']}/resourceGroups/{self.state['group']}/".lower()
        expected = {
            "registryName": "Microsoft.ContainerRegistry/registries",
            "storageName": "Microsoft.Storage/storageAccounts",
            "identityName": "Microsoft.ManagedIdentity/userAssignedIdentities",
            "environmentName": "Microsoft.App/managedEnvironments",
        }
        for field, resource_type in expected.items():
            matches = [
                item for item in resources if item["name"] == self.state.get(field)
                and item["type"].lower() == resource_type.lower()
                and item["id"].lower().startswith(prefix)
            ]
            if len(matches) != 1 or (matches[0].get("tags") or {}).get("Participant") != self.state["ownerId"]:
                raise SetupError(f"記録した{field}が、自分のRG・Participantタグと一致しません。")

    def build(self, resume_run=None):
        self.load()
        if not self.state.get("baseComplete"):
            raise SetupError("先にprepareで基盤を作ります。")
        self.verify_base_scope()
        if self.state.get("image"):
            print("このビルドは完了済みです。記録したdigestを使ってdeployへ進みます。")
            return
        if resume_run is not None:
            if not self.state.get("buildRequested") or self.state.get("buildRunId"):
                raise SetupError("実行番号の回収は、受付済みで番号未記録のビルドだけに使います。")
            existing = self.az("acr", "task", "show-run", "--registry", self.state["registryName"],
                               "--resource-group", self.state["group"],
                               "--run-id", resume_run)
            if not any(
                item.get("repository") == "blob-viz"
                and item.get("tag") == self.state["imageTag"].split(":", 1)[1]
                for item in existing.get("outputImages") or []
            ):
                raise SetupError("この作業記録のイメージタグに一致する実ビルドではありません。")
            self.state["buildRunId"] = resume_run
            self.save()
        if not self.state.get("buildRunId"):
            if self.state.get("buildRequested"):
                raise SetupError("ビルドは受付確認中です。PortalのACR→Tasks→Runsを確認してください。二重起動はしません。")
            self.state["buildRequested"] = True
            self.state["imageTag"] = f"blob-viz:hol{self.state['marker'].replace('-', '')[:8]}"
            self.save()
            context = (self.root / "app").resolve()
            result = self.az("acr", "build", "--resource-group", self.state["group"],
                             "--registry", self.state["registryName"], "--image", self.state["imageTag"],
                             "--platform", "linux/amd64", "--file", str(context / "Dockerfile"),
                             "--no-logs", str(context))
            self.state["buildRunId"] = result["runId"]
            self.save()
        deadline = time.monotonic() + 900
        while True:
            result = self.az("acr", "task", "show-run", "--registry", self.state["registryName"],
                             "--resource-group", self.state["group"],
                             "--run-id", self.state["buildRunId"])
            if result["status"] == "Succeeded":
                break
            if result["status"] in {"Failed", "Canceled", "Error", "Timeout"}:
                raise SetupError(f"ビルド{self.state['buildRunId']}が{result['status']}です。ACRのRunsで原因を確認してください。")
            if time.monotonic() > deadline:
                raise SetupError("ビルドは処理中です。同じbuildを再実行すると、この実行の続きだけを確認します。")
            time.sleep(5)
        image = self.az("acr", "repository", "show", "--name", self.state["registryName"],
                        "--image", self.state["imageTag"])
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", image["digest"]):
            raise SetupError("実イメージのdigestを確認できません。デプロイはしていません。")
        self.state["image"] = f"{self.state['registryLoginServer']}/blob-viz@{image['digest']}"
        self.save()
        print(f"ビルド{self.state['buildRunId']}が完了しました。deployへ進みます。")

    def deploy(self):
        self.load()
        if not self.state.get("image"):
            raise SetupError("先にbuildでイメージを作ります。")
        self.verify_base_scope()
        if not self.state.get("url"):
            result = self.deployment("app")
            self.state["url"] = "https://" + result["properties"]["outputs"]["appFqdn"]["value"]
            self.save()
        print(f"自分のアプリURL: {self.state['url']}")
        print("作成完了とBlobの読み書きは別の確認です。このURLでサンプルを保存して確かめます。")

    def status(self):
        self.load()
        resources = self.az("resource", "list", "--resource-group", self.state["group"])
        for item in resources:
            print(f"{item['type']}: {item['name']}")
        if self.state.get("url"):
            print(f"自分のアプリURL: {self.state['url']}")
        print("作業記録のバックアップ: Manage files→Downloadで、このフォルダーの.lab04-state.jsonを保存します。")

    def check_cleanup(self):
        self.load(require_group=False)
        if self.az("group", "exists", "--name", self.state["group"]):
            raise SetupError("自分のRGはまだ残っています。Portalの通知と削除状況を確認してください。")
        if (self.state.get("baseStarted") or self.state.get("baseComplete")) and not self.state.get("managedGroup"):
            raise SetupError("自分のRGは削除済みですが、基盤の管理用RGの記録がありません。Portalでも確認し、全体の片付けは未確認としてください。")
        if self.state.get("managedGroup") and self.az("group", "exists", "--name", self.state["managedGroup"]):
            raise SetupError("環境の管理用RGがまだ残っています。直接削除せず、少し待って確認してください。")
        print("自分のRGは削除済みです。")
        if self.state.get("managedGroup"):
            print("この環境が作った管理用RGも削除済みです。")
        else:
            print("基盤作成前に終えたため、管理用RGは作っていません。")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="action", required=True)
    initialize = commands.add_parser("init")
    initialize.add_argument("--subscription", required=True, type=subscription_id)
    initialize.add_argument("--id", required=True, type=personal_id)
    initialize.add_argument("--client-ip", required=True, type=client_ipv4)
    initialize.add_argument("--location", default="japaneast", choices=["japaneast"])
    build = commands.add_parser("build")
    build.add_argument("--resume-run")
    for stage in ["prepare", "deploy", "status", "check-cleanup"]:
        commands.add_parser(stage)
    arguments = parser.parse_args()
    setup = LearnerSetup()
    try:
        if arguments.action == "init":
            setup.initialize(arguments.subscription, arguments.id, arguments.client_ip, arguments.location)
        elif arguments.action == "build":
            setup.build(arguments.resume_run)
        else:
            getattr(setup, arguments.action.replace("-", "_"))()
    except (SetupError, argparse.ArgumentTypeError) as error:
        print(f"止まった理由: {error}", file=sys.stderr)
        print("別のRGや公開設定で回避せず、作成済みのものと作業記録を確認してください。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
