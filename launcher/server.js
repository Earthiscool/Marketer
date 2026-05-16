import http from "node:http";
import { createReadStream, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const port = Number(process.env.PORT || 5190);

function contentType(file) {
  if (file.endsWith(".css")) return "text/css";
  if (file.endsWith(".js")) return "text/javascript";
  if (file.endsWith(".html")) return "text/html";
  return "application/octet-stream";
}

function serve(file, res) {
  const full = path.normalize(path.join(root, file));
  if (!full.startsWith(root) || !existsSync(full)) {
    res.writeHead(404, { "content-type": "text/plain" });
    res.end("Not found");
    return;
  }
  res.writeHead(200, { "content-type": contentType(full) });
  createReadStream(full).pipe(res);
}

http.createServer((req, res) => {
  const url = new URL(req.url, `http://localhost:${port}`);
  if (url.pathname === "/") return serve("launcher/index.html", res);
  if (url.pathname === "/launcher.css") return serve("launcher/launcher.css", res);
  if (url.pathname.startsWith("/growth-studio/")) {
    const file = url.pathname.replace("/growth-studio/", "apps/summit-growth-studio/") || "apps/summit-growth-studio/index.html";
    return serve(file.endsWith("/") ? `${file}index.html` : file, res);
  }
  return serve(url.pathname.slice(1), res);
}).listen(port, () => {
  console.log(`Marketer launcher running at http://localhost:${port}`);
});

