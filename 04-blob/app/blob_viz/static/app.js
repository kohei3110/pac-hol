"use strict";

const elements = {
  form: document.querySelector("#upload-form"),
  file: document.querySelector("#file"),
  upload: document.querySelector("#upload-button"),
  select: document.querySelector("#saved-files"),
  reload: document.querySelector("#reload-button"),
  feedback: document.querySelector("#feedback"),
  view: document.querySelector("#visualization"),
  remove: document.querySelector("#delete-button"),
};
let csrf = "";
let selected = null;
let busy = false;

function message(text, error = false) {
  elements.feedback.textContent = text;
  elements.feedback.classList.toggle("error", error);
}

function setBusy(value) {
  busy = value;
  elements.upload.disabled = value || !csrf || elements.file.files.length !== 1;
  elements.reload.disabled = value || !csrf;
  elements.select.disabled = value || elements.select.options.length === 0;
  elements.remove.disabled = value || !selected;
}

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", cache: "no-store", ...options });
  let body;
  try {
    body = await response.json();
  } catch {
    throw new Error("アプリの応答を読み取れませんでした。主催者に連絡してください。");
  }
  if (!response.ok) {
    const detail = body.error?.message || "要求を処理できませんでした。";
    throw new Error(`${detail}\n要求ID: ${body.requestId || "確認できません"}`);
  }
  if (body.source !== document.body.dataset.source) {
    throw new Error("保存先の種類が変わりました。ページを再読み込みしてから操作してください。");
  }
  return body;
}

function render(data) {
  const dataset = data.dataset;
  if (!dataset || !Array.isArray(dataset.rows) || dataset.rows.length !== dataset.rowCount) {
    throw new Error("表とグラフに使うデータの形式が正しくありません。");
  }
  const values = dataset.rows.map(row => row.value);
  if (values.some(value => !Number.isSafeInteger(value) || value < 0) ||
      values.reduce((sum, value) => sum + value, 0) !== dataset.total ||
      Math.max(...values) !== dataset.maximum) {
    throw new Error("表と集計値が一致しません。主催者へ連絡してください。");
  }
  selected = data.file;
  document.querySelector("#selected-name").textContent = `${selected.filename}（${selected.id}）`;
  document.querySelector("#row-count").textContent = dataset.rowCount;
  document.querySelector("#total").textContent = dataset.total.toLocaleString("ja-JP");
  document.querySelector("#maximum").textContent = dataset.maximum.toLocaleString("ja-JP");
  document.querySelector("#blob-name").textContent = selected.blobName;
  document.querySelector("#sha256").textContent = selected.sha256;
  document.querySelector("#read-source").textContent = data.readFrom === "blob"
    ? "表示元: Azure Blob。保存先から読み直したデータです。"
    : "表示元: ローカルテスト用データ。Azureから取得したものではありません。";
  document.querySelector("#download-link").href = `/api/files/${selected.id}/download`;
  const body = document.querySelector("#data-table tbody");
  body.replaceChildren();
  const chart = document.querySelector("#chart");
  chart.replaceChildren();
  chart.setAttribute("viewBox", `0 0 1000 ${dataset.rows.length * 48 + 28}`);
  const svg = (tag, attributes, text) => {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
    if (text !== undefined) node.textContent = text;
    return node;
  };
  chart.append(svg("title", {}, `${selected.filename}の月別データ`));
  dataset.rows.forEach((row, index) => {
    const tr = document.createElement("tr");
    for (const value of [row.month, row.value]) {
      const td = document.createElement("td");
      td.textContent = value;
      if (typeof value === "number") td.className = "numeric";
      tr.append(td);
    }
    body.append(tr);
    const width = dataset.maximum === 0 ? 0 : row.value / dataset.maximum * 720;
    chart.append(svg("text", { x: 8, y: index * 48 + 35, "font-size": 24 }, row.month));
    chart.append(svg("rect", { x: 160, y: index * 48 + 14, width, height: 28, rx: 4,
      "data-month": row.month, "data-value": row.value }));
    chart.append(svg("text", { x: 172 + width, y: index * 48 + 35, "font-size": 22 }, row.value));
  });
  elements.view.hidden = false;
}

async function readSelected() {
  const identifier = elements.select.value;
  selected = null;
  elements.view.hidden = true;
  if (!identifier) {
    return;
  }
  const data = await api(`/api/files/${identifier}/data`);
  render(data);
}

async function refresh(preferred = elements.select.value) {
  selected = null;
  elements.view.hidden = true;
  const body = await api("/api/files");
  elements.select.replaceChildren();
  for (const file of body.files) {
    const option = document.createElement("option");
    option.value = file.id;
    option.textContent = `${file.filename}（${file.id}・${file.size} bytes）`;
    elements.select.append(option);
  }
  document.querySelector("#file-count").textContent = `保存済み ${body.files.length} / 10件`;
  if (body.files.some(file => file.id === preferred)) elements.select.value = preferred;
  await readSelected();
}

elements.file.addEventListener("change", () => setBusy(busy));
elements.form.addEventListener("submit", async event => {
  event.preventDefault();
  const file = elements.file.files[0];
  if (!file || file.size === 0 || file.size > 65536) {
    message("データが入った64 KiB以内のCSVを1つ選んでください。", true);
    return;
  }
  let saved = null;
  setBusy(true);
  message("Blobに保存しています。");
  try {
    const form = new FormData();
    form.append("file", file);
    const result = await api("/api/files", { method: "POST", body: form, headers: { "X-CSRF-Token": csrf } });
    saved = result.file.id;
    message(`Blobに保存しました（${saved}）。保存先から読み込んでいます。`);
    await refresh(saved);
    message(`Blobに保存し、表とグラフを表示しました（${saved}）。開き直しや、別のCSVとの比較も試してみましょう。`);
  } catch (error) {
    message(`${saved ? `Blobには保存できています（${saved}）。表とグラフの表示に失敗したので、再保存せず一覧を読み直してください。\n` : ""}${error.message}`, true);
  } finally {
    setBusy(false);
  }
});

for (const [node, event] of [[elements.reload, "click"], [elements.select, "change"]]) {
  node.addEventListener(event, async () => {
    setBusy(true);
    message("保存済みBlobから読み直しています。");
    try {
      await refresh();
      message(selected ? "Blobから読み直し、表とグラフを更新しました。" : "保存済みファイルはありません。");
    } catch (error) {
      message(error.message, true);
    } finally {
      setBusy(false);
    }
  });
}

elements.remove.addEventListener("click", async () => {
  if (!selected || !confirm(`${selected.filename}（${selected.id}）をBlobから削除しますか？`)) return;
  setBusy(true);
  try {
    await api(`/api/files/${selected.id}`, { method: "DELETE",
      headers: { "X-CSRF-Token": csrf, "If-Match": selected.etag } });
    selected = null;
    elements.view.hidden = true;
    await refresh("");
    message("選んだファイルをBlobから削除しました。アプリやStorageの片付けは、主催者の案内に従ってください。");
  } catch (error) {
    message(error.message, true);
  } finally {
    setBusy(false);
  }
});

(async () => {
  setBusy(true);
  try {
    const session = await api("/api/session");
    csrf = session.csrf;
    await refresh();
    message(selected ? "Blobから保存済みデータを読み込みました。" : "準備できました。まずは基本CSVをダウンロードして、保存してみましょう。");
  } catch (error) {
    message(error.message, true);
  } finally {
    setBusy(false);
  }
})();
