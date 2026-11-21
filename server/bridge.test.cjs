'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { mkdtempSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const path = require('node:path');
const { WhatsAppBridge, StateStore } = require('./bridge.cjs');
const { createServer } = require('./index.cjs');
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
function fixture(t, options = {}) {
    const directory = mkdtempSync(path.join(tmpdir(), 'basket-wa-test-'));
    const group = { id: { _serialized: 'basket@g.us' }, name: 'Basket', isGroup: true };
    const poll = { id: { _serialized: 'poll-1' }, type: 'poll_creation', pollName: 'Présences entraînements', timestamp: 1732000000,
        pollOptions: [{ localId: 0, name: 'Mardi' }, { localId: 1, name: 'Jeudi' }, { localId: 2, name: 'Absent' }] };
    const clients = [];
    class FakeClient extends EventEmitter {
        constructor() { super(); this.calls = []; this.votes = []; }
        async initialize() { this.calls.push('initialize'); }
        async destroy() { this.calls.push('destroy'); }
        async getChats() { return [group, { id: { _serialized: 'person@c.us' }, isGroup: false, name: 'Person' }]; }
        async getChatById(id) { this.calls.push(['getChatById', id]); return id === group.id._serialized ? { ...group, fetchMessages: async config => { this.calls.push(['fetchMessages', config]); return [poll, { ...poll, id: { _serialized: 'unrelated' }, pollName: 'Couleur des maillots', pollOptions: [{ localId: 0, name: 'Bleu' }], timestamp: poll.timestamp + 500 }]; } } : { isGroup: false }; }
        async getPollVotes(id) { this.calls.push(['getPollVotes', id]); if (this.voteError) throw Error('Private provider detail'); return this.votes; }
        async getContactById(id) { return { pushname: id === 'a@lid' ? 'Alex' : 'Sam' }; }
    }
    const store = new StateStore(directory);
    const bridge = new WhatsAppBridge({ store, qrImage: async () => 'data:image/png;base64,AAAA', createClient: () => { const client = new FakeClient(); clients.push(client); return client; }, intervalMs: 25, reconnectMs: 10, ...options });
    t.after(async () => { await bridge.close(); rmSync(directory, { recursive: true, force: true }); });
    return { bridge, store, group, poll, clients, directory };
}
async function ready(context) { await context.bridge.connect(); await pause(0); context.clients.at(-1).emit('ready'); await context.bridge.selectGroup('basket@g.us'); await context.bridge.listPolls(); return context.clients.at(-1); }

test('QR, authentication state, reconnect and private persistent configuration', async t => {
    const ctx = fixture(t); await assert.rejects(ctx.bridge.groups(), /connecté/);
    await ctx.bridge.connect(); const client = ctx.clients[0];
    client.emit('qr', 'sensitive raw QR'); await pause(0);
    assert.equal(ctx.bridge.status().state, 'qr'); assert.equal(ctx.bridge.status().qrImage, 'data:image/png;base64,AAAA');
    client.emit('authenticated'); assert.equal(ctx.bridge.status().qrImage, null);
    client.emit('ready'); assert.equal(ctx.bridge.status().readOnly, true);
    assert.deepEqual(await ctx.bridge.groups(), [{ id: 'basket@g.us', name: 'Basket' }]);
    await ctx.bridge.selectGroup('basket@g.us'); ctx.bridge.saveMapping({ 'a@lid': 'player-1' });
    assert.equal(new StateStore(ctx.directory).get().groupId, 'basket@g.us');
    assert.deepEqual(new StateStore(ctx.directory).get().mapping, { 'a@lid': 'player-1' });
    await assert.rejects(ctx.bridge.selectGroup('not-a-group'), /groupe/);
    client.emit('disconnected', 'NETWORK'); await pause(25);
    assert.equal(ctx.clients.length, 2); assert.equal(ctx.bridge.status().state, 'connecting');
    ctx.clients[1].emit('ready'); ctx.clients[1].emit('disconnected', 'LOGOUT'); await pause(30);
    assert.equal(ctx.clients.length, 2); assert.match(ctx.bridge.status().error, /révoquée/);
});
test('latest presence poll, native localId zero, latest votes, multiselection and withdrawals', async t => {
    const ctx = fixture(t); const client = await ready(ctx);
    const list = await ctx.bridge.listPolls(); assert.deepEqual(list.polls.map(p => p.id), ['poll-1']);
    assert.ok(client.calls.some(call => Array.isArray(call) && call[0] === 'fetchMessages' && call[1].limit === 500));
    client.votes = [
        { voter: 'a@lid', interractedAtTs: 1, selectedOptions: [{ localId: 2 }] },
        { voter: 'a@lid', interractedAtTs: 2, selectedOptions: [{ localId: 0 }, { localId: 1 }, { localId: 1 }] },
        { voter: 'b@c.us', interractedAtTs: 3, selectedOptions: [{ id: 0 }] },
        { voter: 'withdrawn@lid', interractedAtTs: 5, selectedOptions: [] }
    ];
    const result = await ctx.bridge.readPoll('poll-1', true);
    assert.deepEqual(result.options.map(o => o.voters.length), [2, 1, 0]);
    assert.equal(result.options[0].id, '0'); assert.equal(result.options[0].voters[0].name, 'Alex');
    assert.equal(result.withdrawn, 1); assert.equal(result.availability, 'votes_returned');
    await assert.rejects(ctx.bridge.readPoll('unscanned'), /ne fait pas partie/);
    const all = await ctx.bridge.listPolls('maillots'); assert.equal(all.polls[0].id, 'unrelated');
});
test('empty or failed vote reading never turns into inferred absence; unknown options reject', async t => {
    const ctx = fixture(t); const client = await ready(ctx);
    assert.equal((await ctx.bridge.readPoll('poll-1')).availability, 'empty_unverified');
    client.voteError = true;
    await assert.rejects(ctx.bridge.readPoll('poll-1', true), /Aucune absence/);
    await assert.rejects(ctx.bridge.readPoll('poll-1'), /Aucune absence/); // No stale fallback.
    client.voteError = false; client.votes = [{ voter: 'a@lid', selectedOptions: [{ localId: 99 }] }];
    await assert.rejects(ctx.bridge.readPoll('poll-1', true), /Aucune absence/);
});
test('periodic resync reads changed votes even without vote_update', async t => {
    const ctx = fixture(t); const client = await ready(ctx);
    await ctx.bridge.readPoll('poll-1');
    client.votes = [{ voter: 'a@lid', selectedOptions: [{ localId: 1 }], interractedAtTs: 7 }];
    await pause(70);
    const result = await ctx.bridge.readPoll('poll-1'); assert.equal(result.options[1].voters.length, 1);
    assert.ok(client.calls.filter(call => Array.isArray(call) && call[0] === 'getPollVotes').length >= 2);
    client.emit('vote_update', { parentMessage: { id: { _serialized: 'poll-1' } } });
    assert.ok(ctx.bridge.status().lastVoteEventAt);
});
test('HTTP API serves the app and rejects foreign origins, rebinding hosts, forms and unknown routes', async t => {
    const ctx = fixture(t); const server = createServer(ctx.bridge);
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    t.after(() => new Promise(resolve => server.close(resolve)));
    const base = `http://127.0.0.1:${server.address().port}`;
    assert.equal((await fetch(base)).status, 200);
    const status = await fetch(base + '/api/wa/status'); assert.equal(status.headers.get('cache-control'), 'no-store');
    assert.equal((await status.json()).state, 'idle');
    assert.equal((await fetch(base + '/api/wa/status', { headers: { Origin: 'https://untrusted.example' } })).status, 403);
    const rebound = await new Promise(resolve => require('node:http').get(base + '/api/wa/status', { headers: { Host: 'untrusted.example' } }, response => { response.resume(); resolve(response.statusCode); }));
    assert.equal(rebound, 403);
    assert.equal((await fetch(base + '/api/wa/connect', { method: 'POST', body: 'x=1' })).status, 415);
    assert.equal((await fetch(base + '/api/wa/send-message', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })).status, 404);
    assert.equal((await fetch(base + '/api/wa/groups')).status, 409);
    assert.equal((await fetch(base + '/api/wa/connect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })).status, 202);
});
