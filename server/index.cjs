'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { WhatsAppBridge, StateStore, BridgeError } = require('./bridge.cjs');

function createServer(bridge, { port = 8787, allowedOrigins = [] } = {}) {
    const origins = new Set(allowedOrigins);
    return http.createServer(async (request, response) => {
        response.setHeader('Cache-Control', 'no-store'); response.setHeader('X-Content-Type-Options', 'nosniff');
        const host = request.headers.host, localPort = response.socket.localPort;
        if (![ `127.0.0.1:${localPort}`, `localhost:${localPort}` ].includes(host)) { response.writeHead(403); response.end('Host refused'); return; }
        const origin = request.headers.origin;
        if (origin && !origins.has(origin) && ![`http://127.0.0.1:${localPort}`, `http://localhost:${localPort}`].includes(origin)) { response.writeHead(403); response.end('Origin refused'); return; }
        if (origin) { response.setHeader('Access-Control-Allow-Origin', origin); response.setHeader('Vary', 'Origin'); }
        response.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'); response.setHeader('Access-Control-Allow-Headers', 'Content-Type');
        const json = (code, data) => { response.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' }); response.end(JSON.stringify(data)); };
        if (request.method === 'OPTIONS') { response.writeHead(204); response.end(); return; }
        try {
            const url = new URL(request.url, `http://127.0.0.1:${port}`), route = url.pathname;
            if (request.method === 'GET' && ['/','/index.html','/basket-equipes-autonome.html'].includes(route)) {
                response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); response.end(fs.readFileSync(path.join(__dirname, '..', 'basket-equipes-autonome.html'))); return;
            }
            let body = {};
            if (request.method === 'POST') {
                if (!request.headers['content-type']?.startsWith('application/json')) throw new BridgeError('Content-Type application/json requis.', 415);
                let raw = ''; for await (const chunk of request) { raw += chunk; if (Buffer.byteLength(raw) > 65536) throw new BridgeError('Requête trop grande.', 413); }
                try { body = JSON.parse(raw || '{}'); } catch { throw new BridgeError('JSON invalide.'); }
            }
            if (request.method === 'GET' && route === '/api/wa/status') return json(200, bridge.status());
            if (request.method === 'POST' && route === '/api/wa/connect') return json(202, await bridge.connect());
            if (request.method === 'GET' && route === '/api/wa/groups') return json(200, { groups: await bridge.groups() });
            if (request.method === 'POST' && route === '/api/wa/group') return json(200, await bridge.selectGroup(body.groupId));
            if (request.method === 'GET' && route === '/api/wa/polls') return json(200, await bridge.listPolls(url.searchParams.get('q') || ''));
            if (request.method === 'GET' && route === '/api/wa/poll') return json(200, await bridge.readPoll(url.searchParams.get('id'), url.searchParams.get('refresh') === '1'));
            if (request.method === 'GET' && route === '/api/wa/mapping') return json(200, { mapping: bridge.store.get().mapping });
            if (request.method === 'POST' && route === '/api/wa/mapping') return json(200, { mapping: bridge.saveMapping(body.mapping) });
            json(404, { error: 'Route inconnue.' });
        } catch (error) { json(error instanceof BridgeError ? error.status : 502, { error: error instanceof BridgeError ? error.message : 'Lecture WhatsApp indisponible. Vérifiez le groupe, la connexion et réessayez.' }); }
    });
}
if (require.main === module) {
    const { Client, LocalAuth } = require('whatsapp-web.js');
    const qrcode = require('qrcode');
    const directory = path.resolve(process.env.WA_DATA_DIR || path.join(__dirname, '..', '.whatsapp-data'));
    const port = Number(process.env.PORT || 8787);
    const executablePath = process.env.WA_CHROMIUM_PATH || (fs.existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);
    const bridge = new WhatsAppBridge({
        store: new StateStore(directory), qrImage: value => qrcode.toDataURL(value),
        createClient: () => new Client({ authStrategy: new LocalAuth({ dataPath: path.join(directory, 'auth') }),
            webVersionCache: { type: 'local', path: path.join(directory, 'web-cache') },
            puppeteer: { headless: true, ...(executablePath ? { executablePath } : {}), args: process.env.WA_NO_SANDBOX === '1' ? ['--no-sandbox'] : [] } })
    });
    const server = createServer(bridge, { port, allowedOrigins: (process.env.WA_ALLOWED_ORIGINS || '').split(',').map(s => s.trim()).filter(Boolean) });
    server.listen(port, '127.0.0.1', () => {
        console.log(`Team Maker et sa passerelle de lecture écoutent sur le port local ${port}.`);
        if (fs.existsSync(path.join(directory, 'auth', 'session'))) bridge.connect().catch(() => {});
    });
    for (const signal of ['SIGINT','SIGTERM']) process.on(signal, async () => { await bridge.close(); server.close(() => process.exit(0)); });
}
module.exports = { createServer };
