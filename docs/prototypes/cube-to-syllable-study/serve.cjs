const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');

const files = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/style.css', ['style.css', 'text/css; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']]
]);

http.createServer((request, response) => {
  const pathname = new URL(request.url, 'http://localhost').pathname;
  if (pathname === '/favicon.ico') { response.writeHead(204); response.end(); return; }
  const file = files.get(pathname);
  if (!file) { response.writeHead(404); response.end('Not found'); return; }
  fs.readFile(path.join(__dirname, file[0]), (error, body) => {
    if (error) { response.writeHead(500); response.end('Could not read file'); return; }
    response.writeHead(200, {'Content-Type': file[1], 'Cache-Control': 'no-store'});
    response.end(body);
  });
}).listen(8892, '127.0.0.1', () => console.log('Cube study: http://127.0.0.1:8892/'));
