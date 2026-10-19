import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {networkInterfaces} from 'node:os';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT || 8765);
const files = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/style.css', ['style.css', 'text/css; charset=utf-8']],
  ['/app.mjs', ['app.mjs', 'text/javascript; charset=utf-8']],
  ['/model.mjs', ['model.mjs', 'text/javascript; charset=utf-8']],
]);

createServer(async (request, response) => {
  const entry = files.get(new URL(request.url, 'http://localhost').pathname);
  if (!entry) { response.writeHead(404).end(); return; }
  try {
    const data = await readFile(join(root, entry[0]));
    response.writeHead(200, {'Content-Type': entry[1], 'Cache-Control': 'no-store'}).end(data);
  } catch { response.writeHead(500).end('Prototype file unavailable'); }
}).listen(port, '0.0.0.0', () => {
  console.log(`Desktop: http://127.0.0.1:${port}/`);
  for (const addresses of Object.values(networkInterfaces())) {
    for (const address of addresses || []) {
      if (address.family === 'IPv4' && !address.internal)
        console.log(`Same-Wi-Fi phone: http://${address.address}:${port}/`);
    }
  }
});
