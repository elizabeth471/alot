// Receives anonymous likes and dislikes from alot. Write only: there is no way to read votes through this address.
// Stored: a random device id made by the browser, the track id, the vote and the time. No names, emails or IP addresses.
const ORIGINS = ['https://alot-indol.vercel.app', 'http://127.0.0.1:8765', 'http://localhost:8765'];
function headers(origin) {
  const h = { 'Vary': 'Origin' };
  if (ORIGINS.includes(origin)) {
    h['Access-Control-Allow-Origin'] = origin;
    h['Access-Control-Allow-Methods'] = 'POST, OPTIONS';
    h['Access-Control-Allow-Headers'] = 'Content-Type';
    h['Access-Control-Max-Age'] = '86400';
  }
  return h;
}
export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const h = headers(origin);
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: h });
    if (request.method !== 'POST' || new URL(request.url).pathname !== '/vote') return new Response('Not found', { status: 404, headers: h });
    if (!ORIGINS.includes(origin)) return new Response('Forbidden', { status: 403, headers: h });
    const text = await request.text();
    if (text.length > 20000) return new Response('Too large', { status: 413, headers: h });
    let body;
    try { body = JSON.parse(text); } catch (e) { return new Response('Bad request', { status: 400, headers: h }); }
    const device = body && body.device;
    const votes = body && body.votes;
    if (typeof device !== 'string' || !/^[a-z0-9-]{16,40}$/.test(device) || !votes || typeof votes !== 'object' || Array.isArray(votes)) {
      return new Response('Bad request', { status: 400, headers: h });
    }
    const entries = Object.entries(votes);
    if (!entries.length || entries.length > 100 || !entries.every(([track, vote]) => /^[a-z0-9-]{1,100}$/.test(track) && [1, -1, 0].includes(vote))) {
      return new Response('Bad request', { status: 400, headers: h });
    }
    const now = new Date().toISOString();
    await env.DB.batch(entries.map(([track, vote]) => vote === 0
      ? env.DB.prepare('DELETE FROM votes WHERE device = ? AND track = ?').bind(device, track)
      : env.DB.prepare('INSERT INTO votes (device, track, vote, updated) VALUES (?, ?, ?, ?) ON CONFLICT (device, track) DO UPDATE SET vote = excluded.vote, updated = excluded.updated').bind(device, track, vote, now)));
    return new Response(null, { status: 204, headers: h });
  }
};
