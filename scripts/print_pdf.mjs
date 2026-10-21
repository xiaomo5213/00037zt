/**
 * 用 Chrome DevTools Protocol 把排版好的 HTML 打成 A4 PDF，并带上页码页脚。
 *
 * 用法：
 *   node scripts/print_pdf.mjs pdf/paper-1.html pdf/paper-2.html ...
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const CHROME = process.env.CHROME_PATH || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9333;
const files = process.argv.slice(2);
if (!files.length) {
  console.error("usage: node print_pdf.mjs <html> [html...]");
  process.exit(1);
}

const profile = fs.mkdtempSync(path.join(os.tmpdir(), "meixue-pdf-"));
const chrome = spawn(
  CHROME,
  [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${profile}`,
    "about:blank",
  ],
  { stdio: "ignore" }
);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitForChrome() {
  for (let i = 0; i < 100; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (res.ok) return await res.json();
    } catch (e) {
      /* 还没起来 */
    }
    await sleep(150);
  }
  throw new Error("Chrome 没能在调试端口上启动");
}

function cdp(ws) {
  let seq = 0;
  const pending = new Map();
  const waiters = new Map();

  ws.addEventListener("message", (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message));
      else resolve(msg.result);
      return;
    }
    const list = waiters.get(msg.method);
    if (list && list.length) {
      const fn = list.shift();
      fn(msg.params);
    }
  });

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });

  const once = (method) =>
    new Promise((resolve) => {
      if (!waiters.has(method)) waiters.set(method, []);
      waiters.get(method).push(resolve);
    });

  return { send, once };
}

const FOOTER = `<div style="width:100%;padding:0 16mm;font-family:'Microsoft YaHei','PingFang SC',sans-serif;font-size:7.6pt;color:#8b8275;display:flex;justify-content:space-between;align-items:center;">
<span>00037《美学》 · 考前押题卷</span>
<span><span class="pageNumber"></span> / <span class="totalPages"></span></span>
</div>`;

async function main() {
  await waitForChrome();
  const tab = await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: "PUT" }).then((r) => r.json());
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve);
    ws.addEventListener("error", reject);
  });

  const { send, once } = cdp(ws);
  await send("Page.enable");
  await send("Emulation.setEmulatedMedia", { media: "print" });

  for (const file of files) {
    const abs = path.resolve(file);
    const url = pathToFileURL(abs).href;
    const loaded = once("Page.loadEventFired");
    await send("Page.navigate", { url });
    await loaded;
    await sleep(450);

    const { data } = await send("Page.printToPDF", {
      printBackground: true,
      displayHeaderFooter: true,
      headerTemplate: "<div></div>",
      footerTemplate: FOOTER,
      marginTop: 0.62,
      marginBottom: 0.55,
      marginLeft: 0.6,
      marginRight: 0.6,
      paperWidth: 8.27,
      paperHeight: 11.69,
      preferCSSPageSize: false,
    });
    const out = abs.replace(/\.html?$/i, ".pdf");
    fs.writeFileSync(out, Buffer.from(data, "base64"));
    console.log("pdf", out, Buffer.byteLength(data, "base64"));
  }

  ws.close();
  chrome.kill();
  await sleep(300);
  try {
    fs.rmSync(profile, { recursive: true, force: true });
  } catch (e) {
    /* 忽略 */
  }
}

main().catch((err) => {
  console.error(err);
  chrome.kill();
  process.exit(1);
});
