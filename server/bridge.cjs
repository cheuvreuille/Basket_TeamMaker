'use strict';
const fs = require('node:fs');
const path = require('node:path');

class BridgeError extends Error {
    constructor(message, status = 400) { super(message); this.status = status; }
}
const idOf = value => typeof value === 'string' ? value : value?._serialized;
const clean = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const optionType = label => /bless|injur/.test(clean(label)) ? 'injury' : /absen|indispo|pas present/.test(clean(label)) ? 'absence' : /lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche|present|entrain/.test(clean(label)) ? 'training' : 'other';

class StateStore {
    constructor(directory) {
        fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
        this.file = path.join(directory, 'settings.json');
        this.value = fs.existsSync(this.file) ? JSON.parse(fs.readFileSync(this.file, 'utf8')) : { groupId: null, mapping: {} };
        if (!this.value || typeof this.value.mapping !== 'object' || Array.isArray(this.value.mapping) || this.value.mapping === null) throw new Error('Configuration WhatsApp locale invalide.');
    }
    get() { return structuredClone(this.value); }
    save(value) {
        const temporary = this.file + '.tmp';
        fs.writeFileSync(temporary, JSON.stringify(value), { mode: 0o600 });
        fs.renameSync(temporary, this.file); this.value = structuredClone(value);
    }
}

class WhatsAppBridge {
    constructor({ createClient, qrImage, store, intervalMs = 60000, reconnectMs = 5000 }) {
        this.createClient = createClient; this.qrImage = qrImage; this.store = store;
        this.client = null; this.state = 'idle'; this.qr = null; this.error = null;
        this.polls = new Map(); this.contacts = new Map(); this.selectedPoll = null;
        this.intervalMs = intervalMs; this.reconnectMs = reconnectMs; this.retries = 0;
        this.stopped = false; this.syncing = null; this.lastSyncAt = null; this.lastVoteEventAt = null;
    }
    status() {
        return { state: this.state, qrImage: this.qr, error: this.error, groupId: this.store.get().groupId,
            selectedPoll: this.selectedPoll, lastSyncAt: this.lastSyncAt, lastVoteEventAt: this.lastVoteEventAt,
            version: '1.34.8', readOnly: true };
    }
    requireReady() { if (this.state !== 'ready') throw new BridgeError('WhatsApp doit être connecté avant cette opération.', 409); }
    async connect() {
        if (['connecting', 'qr', 'authenticated', 'ready'].includes(this.state)) return this.status();
        this.stopped = false; clearTimeout(this.reconnectTimer);
        this.state = 'connecting'; this.error = null; this.qr = null;
        if (this.client) { const old = this.client; this.client = null; await old.destroy().catch(() => {}); }
        const client = this.createClient(); this.client = client;
        const active = () => this.client === client && !this.stopped;
        client.on('qr', async value => {
            try { const image = await this.qrImage(value); if (active() && ['connecting', 'qr'].includes(this.state)) { this.qr = image; this.state = 'qr'; } }
            catch { if (active()) { this.error = 'Impossible de générer le QR code.'; this.state = 'error'; } }
        });
        client.on('authenticated', () => { if (active()) { this.state = 'authenticated'; this.qr = null; } });
        client.on('ready', () => {
            if (!active()) return;
            this.state = 'ready'; this.qr = null; this.error = null; this.retries = 0;
            clearInterval(this.syncTimer);
            this.syncTimer = setInterval(() => this.resync().catch(() => {}), this.intervalMs); this.syncTimer.unref?.();
        });
        client.on('auth_failure', () => { if (active()) { this.state = 'error'; this.qr = null; this.error = 'Authentification expirée ou refusée : reconnectez WhatsApp.'; clearInterval(this.syncTimer); } });
        client.on('disconnected', reason => {
            if (!active()) return;
            this.state = 'disconnected'; this.qr = null; this.polls.clear(); this.contacts.clear(); clearInterval(this.syncTimer);
            if (String(reason).toUpperCase().includes('LOGOUT')) { this.error = 'Session révoquée : reconnectez WhatsApp et scannez le QR code.'; return; }
            this.error = 'Connexion interrompue. Reconnexion automatique en cours.';
            this.reconnectTimer = setTimeout(() => this.connect().catch(() => {}), Math.min(60000, this.reconnectMs * 2 ** this.retries++)); this.reconnectTimer.unref?.();
        });
        client.on('vote_update', vote => {
            if (!active() || this.state !== 'ready') return;
            const messageId = idOf(vote.parentMessage?.id) || idOf(vote.parentMsgKey);
            if (messageId !== this.selectedPoll) return;
            this.lastVoteEventAt = new Date().toISOString(); clearTimeout(this.voteTimer);
            this.voteTimer = setTimeout(() => this.resync().catch(() => {}), 300); this.voteTimer.unref?.();
        });
        Promise.resolve().then(() => client.initialize()).catch(() => {
            if (active()) { this.state = 'error'; this.qr = null; this.error = 'Démarrage WhatsApp impossible. Vérifiez Chromium et la connexion réseau du service.'; }
        });
        return this.status();
    }
    async groups() {
        this.requireReady();
        const chats = await this.client.getChats();
        return chats.filter(chat => chat.isGroup).map(chat => ({ id: idOf(chat.id), name: chat.name || 'Groupe sans nom' })).sort((a, b) => a.name.localeCompare(b.name, 'fr'));
    }
    async selectGroup(groupId) {
        this.requireReady();
        if (typeof groupId !== 'string' || !groupId || groupId.length > 250) throw new BridgeError('Identifiant de groupe invalide.');
        const chat = await this.client.getChatById(groupId);
        if (!chat?.isGroup) throw new BridgeError('Choisissez un groupe WhatsApp.');
        const state = this.store.get(); state.groupId = groupId; this.store.save(state);
        this.polls.clear(); this.contacts.clear(); this.selectedPoll = null; this.lastSyncAt = null;
        return { id: groupId, name: chat.name };
    }
    async listPolls(query = '') {
        this.requireReady(); const groupId = this.store.get().groupId;
        if (!groupId) throw new BridgeError('Choisissez un groupe avant de récupérer les sondages.', 409);
        const chat = await this.client.getChatById(groupId);
        if (!chat?.isGroup) throw new BridgeError('Le groupe enregistré n’est plus accessible.', 409);
        const messages = await chat.fetchMessages({ limit: 500 });
        if (this.store.get().groupId !== groupId) throw new BridgeError('Le groupe a changé pendant la lecture. Réessayez.', 409);
        const polls = messages.filter(message => message.type === 'poll_creation' && !message.pollInvalidated).sort((a, b) => b.timestamp - a.timestamp);
        const search = clean(query).trim();
        const filtered = polls.filter(message => search ? clean(message.pollName).includes(search) : /presen|entrain|dispo/.test(clean(message.pollName)) || (message.pollOptions || []).some(option => ['absence', 'injury', 'training'].includes(optionType(option.name || option))));
        this.polls.clear(); this.contacts.clear(); this.selectedPoll = null;
        for (const message of filtered) this.polls.set(idOf(message.id), { message, groupId, groupName: chat.name, data: null, readError: null });
        return { polls: filtered.map(message => ({ id: idOf(message.id), question: message.pollName || 'Sondage sans titre', createdAt: new Date(message.timestamp * 1000).toISOString() })), scannedMessages: messages.length, limit: 500, limitedHistory: true };
    }
    async contact(voterId) {
        if (!this.contacts.has(voterId)) {
            let name = voterId;
            try { const c = await this.client.getContactById(voterId); name = c.pushname || c.name || c.shortName || voterId; } catch {}
            this.contacts.set(voterId, { id: voterId, name });
        }
        return this.contacts.get(voterId);
    }
    async readPoll(pollId, force = false) {
        this.requireReady();
        const entry = this.polls.get(pollId);
        if (!entry || entry.groupId !== this.store.get().groupId) throw new BridgeError('Ce sondage ne fait pas partie de la lecture du groupe sélectionné.', 404);
        this.selectedPoll = pollId;
        if (entry.data && !force && !entry.readError) return structuredClone(entry.data);
        if (this.syncing) { await this.syncing.catch(() => {}); if (!force && entry.data && !entry.readError) return structuredClone(entry.data); }
        const client = this.client;
        const promise = (async () => {
            try {
                const votes = await client.getPollVotes(pollId);
                if (!Array.isArray(votes)) throw new Error('Invalid vote list');
                const rawOptions = entry.message.pollOptions;
                if (!Array.isArray(rawOptions) || !rawOptions.length) throw new Error('Missing poll options');
                const options = rawOptions.map((option, i) => ({ id: String(typeof option === 'string' ? i : option.localId ?? option.id ?? i), label: typeof option === 'string' ? option : option.name, voters: [] }));
                if (options.some(option => typeof option.label !== 'string') || new Set(options.map(option => option.id)).size !== options.length) throw new Error('Invalid options');
                const latest = new Map();
                for (const vote of votes) {
                    const id = idOf(vote.voter);
                    if (!id || !Array.isArray(vote.selectedOptions)) throw new Error('Missing voter identity');
                    if (!latest.has(id) || Number(vote.interractedAtTs || 0) >= Number(latest.get(id).interractedAtTs || 0)) latest.set(id, vote);
                }
                let withdrawn = 0;
                for (const [voterId, vote] of latest) {
                    if (!vote.selectedOptions.length) { withdrawn++; continue; }
                    const voter = await this.contact(voterId), seen = new Set();
                    for (const selected of vote.selectedOptions) {
                        const localId = selected.localId ?? selected.id;
                        const matches = options.filter(option => localId !== undefined ? option.id === String(localId) : option.label === selected.name);
                        if (matches.length !== 1) throw new Error('Unknown voted option');
                        if (!seen.has(matches[0].id)) matches[0].voters.push(voter);
                        seen.add(matches[0].id);
                    }
                }
                if (this.client !== client || this.state !== 'ready' || this.store.get().groupId !== entry.groupId || this.polls.get(pollId) !== entry) throw new BridgeError('La connexion ou le groupe a changé. Actualisez la lecture.', 409);
                const data = { id: pollId, groupId: entry.groupId, groupName: entry.groupName, question: entry.message.pollName || 'Sondage', createdAt: new Date(entry.message.timestamp * 1000).toISOString(), options: options.map(option => ({ ...option, type: optionType(option.label) })), withdrawn, checkedAt: new Date().toISOString(), source: 'whatsapp-web.js', availability: votes.length ? 'votes_returned' : 'empty_unverified' };
                entry.data = data; entry.readError = null; this.lastSyncAt = data.checkedAt; this.error = null;
                return structuredClone(data);
            } catch (error) {
                entry.readError = 'Impossible de vérifier les votes. Aucune absence ne doit être déduite de cet échec.';
                if (!(error instanceof BridgeError)) throw new BridgeError(entry.readError, 502);
                throw error;
            }
        })();
        this.syncing = promise;
        try { return await promise; } finally { if (this.syncing === promise) this.syncing = null; }
    }
    async resync() {
        if (this.state !== 'ready' || !this.selectedPoll || this.syncing) return;
        try { await this.readPoll(this.selectedPoll, true); }
        catch { this.error = 'Votes non vérifiés : dernière synchronisation échouée. Actualisez avant d’appliquer les présences.'; }
    }
    saveMapping(mapping) {
        if (!mapping || typeof mapping !== 'object' || Array.isArray(mapping) || Object.entries(mapping).some(([id, player]) => !id || id.length > 250 || typeof player !== 'string' || player.length > 250)) throw new BridgeError('Correspondance des joueurs invalide.');
        const state = this.store.get(); state.mapping = Object.fromEntries(Object.entries(mapping).filter(([, player]) => player)); this.store.save(state); return state.mapping;
    }
    async close() {
        this.stopped = true; clearInterval(this.syncTimer); clearTimeout(this.voteTimer); clearTimeout(this.reconnectTimer);
        const client = this.client; this.client = null;
        if (client) await client.destroy().catch(() => {});
        this.state = 'idle'; this.qr = null;
    }
}
module.exports = { WhatsAppBridge, StateStore, BridgeError, optionType };
