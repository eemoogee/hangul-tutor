const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');

const files = new Map([
  ['/', ['index.html','text/html; charset=utf-8']],
  ['/index.html', ['index.html','text/html; charset=utf-8']],
  ['/style.css', ['style.css','text/css; charset=utf-8']],
  ['/app.js', ['app.js','text/javascript; charset=utf-8']]
]);
const port = Number(process.env.PORT || 8891);
http.createServer((request,response) => {
  const pathname=new URL(request.url,'http://localhost').pathname;
  if(pathname==='/favicon.ico'){response.writeHead(204);response.end();return;}
  const file=files.get(pathname);
  if(!file){response.writeHead(404);response.end('Not found');return;}
  fs.readFile(path.join(__dirname,file[0]),(error,body) => {
    if(error){response.writeHead(500);response.end('Could not read file');return;}
    response.writeHead(200,{'Content-Type':file[1],'Cache-Control':'no-store'});
    response.end(body);
  });
}).listen(port,'0.0.0.0',() => {
  console.log(`Desktop: http://localhost:${port}/`);
  for(const addresses of Object.values(os.networkInterfaces())) for(const address of addresses||[])
    if(address.family==='IPv4'&&!address.internal) console.log(`Same Wi-Fi: http://${address.address}:${port}/`);
});
