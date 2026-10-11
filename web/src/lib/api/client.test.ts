import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { ApiError, api, errorMessage, fetchSession, getCsrfToken, onUnauthorized, setCsrfToken, setFetch } from './client';

interface Call {
	url: string;
	init: RequestInit;
}

function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
	return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
}

const SESSION = {
	authenticated: false,
	csrf_token: 'tok-1',
	state: null,
	user: null,
	site: { name: 'Heimatsignale', radius_km: 20, request_body_max: 500, message_body_max: 2000, poll_seconds: 30 }
};

let calls: Call[] = [];

function mock(handler: (url: string, init: RequestInit) => Response): void {
	setFetch(async (url, init) => {
		calls.push({ url, init: init ?? {} });
		return handler(url, init ?? {});
	});
}

function header(call: Call, name: string): string | undefined {
	return (call.init.headers as Record<string, string>)[name];
}

beforeEach(() => {
	calls = [];
	setCsrfToken('');
	onUnauthorized(null);
});

afterEach(() => {
	setFetch(null);
});

describe('API-Client', () => {
	it('sendet GET mit Cookies der gleichen Origin und Abfrageparametern', async () => {
		mock(() => json(200, { items: [] }));
		const data = await api.get<{ items: unknown[] }>('/api/places/search', { q: 'sonth', leer: undefined });
		expect(data.items).toEqual([]);
		expect(calls[0].url).toBe('/api/places/search?q=sonth');
		expect(calls[0].init.credentials).toBe('same-origin');
		expect(calls[0].init.method).toBe('GET');
		expect(header(calls[0], 'X-CSRFToken')).toBeUndefined();
	});

	it('merkt sich den CSRF-Token aus der Sitzung und sendet ihn bei POST und DELETE', async () => {
		mock((url) => (url === '/api/session' ? json(200, SESSION) : new Response(null, { status: 204 })));
		await fetchSession();
		expect(getCsrfToken()).toBe('tok-1');
		await api.post('/api/blocks', { user_id: 'u1' });
		await api.delete('/api/blocks/u1');
		expect(header(calls[1], 'X-CSRFToken')).toBe('tok-1');
		expect(calls[1].init.body).toBe('{"user_id":"u1"}');
		expect(header(calls[1], 'Content-Type')).toBe('application/json');
		expect(calls[2].init.method).toBe('DELETE');
		expect(header(calls[2], 'X-CSRFToken')).toBe('tok-1');
	});

	it('holt vor dem ersten schreibenden Aufruf selbst die Sitzung', async () => {
		mock((url) => (url === '/api/session' ? json(200, SESSION) : json(202, { ok: true })));
		await api.post('/api/auth/password-reset', { email: 'a@example.org', pow: 'x' });
		expect(calls.map((c) => c.url)).toEqual(['/api/session', '/api/auth/password-reset']);
		expect(header(calls[1], 'X-CSRFToken')).toBe('tok-1');
	});

	it('erneuert den Token einmal nach csrf_failed', async () => {
		setCsrfToken('alt');
		let posts = 0;
		mock((url) => {
			if (url === '/api/session') return json(200, { ...SESSION, csrf_token: 'neu' });
			posts++;
			return posts === 1 ? json(403, { code: 'csrf_failed', message: 'CSRF-Prüfung fehlgeschlagen.' }) : new Response(null, { status: 204 });
		});
		await api.post('/api/auth/logout');
		expect(posts).toBe(2);
		expect(header(calls[2], 'X-CSRFToken')).toBe('neu');
	});

	it('bildet Fehlerkörper auf ApiError ab', async () => {
		setCsrfToken('t');
		mock(() => json(422, { code: 'validation', message: 'Bitte prüfe deine Eingaben.', fields: { body: 'Der Text enthält einen Link.' } }));
		let caught: unknown;
		try {
			await api.post('/api/requests', { to_user_id: 'u', body: 'http://x' });
		} catch (error) {
			caught = error;
		}
		expect(caught).toBeInstanceOf(ApiError);
		const e = caught as ApiError;
		expect(e.status).toBe(422);
		expect(e.code).toBe('validation');
		expect(e.fields.body).toBe('Der Text enthält einen Link.');
		expect(errorMessage(e)).toBe('Bitte prüfe deine Eingaben.');
	});

	it('liest retry_after bei 429', async () => {
		mock(() => json(429, { code: 'rate_limited', message: 'Zu viele Abfragen.', retry_after: 240 }));
		let caught: ApiError | null = null;
		try {
			await api.get('/api/nearby/overview');
		} catch (error) {
			caught = error as ApiError;
		}
		expect(caught!.isRateLimited).toBe(true);
		expect(caught!.retryAfter).toBe(240);
	});

	it('ruft bei 401 not_authenticated den Handler, bei quiet401 nicht', async () => {
		let redirects = 0;
		onUnauthorized(() => redirects++);
		mock(() => json(401, { code: 'not_authenticated', message: 'Nicht angemeldet.' }));
		await api.get('/api/requests').catch(() => undefined);
		expect(redirects).toBe(1);
		await api.get('/api/places/search', { q: 'ab' }, { quiet401: true }).catch(() => undefined);
		expect(redirects).toBe(1);
	});

	it('leitet bei falschen Zugangsdaten (401 invalid_credentials) nicht um', async () => {
		setCsrfToken('t');
		let redirects = 0;
		onUnauthorized(() => redirects++);
		mock(() => json(401, { code: 'invalid_credentials', message: 'E-Mail oder Passwort stimmen nicht.' }));
		const error = await api.post('/api/auth/login', { email: 'a', password: 'b', pow: null }).catch((e: unknown) => e);
		expect((error as ApiError).code).toBe('invalid_credentials');
		expect(redirects).toBe(0);
	});

	it('liefert bei 204 nichts und bei Netzfehlern einen verständlichen Fehler', async () => {
		setCsrfToken('t');
		mock(() => new Response(null, { status: 204 }));
		expect(await api.post('/api/requests/1/decline')).toBeUndefined();
		setFetch(async () => {
			throw new TypeError('failed to fetch');
		});
		const error = (await api.get('/api/session').catch((e: unknown) => e)) as ApiError;
		expect(error.status).toBe(0);
		expect(error.code).toBe('network');
	});

	it('kommt mit Fehlern ohne JSON-Körper zurecht', async () => {
		mock(() => new Response('<html>Bad Gateway</html>', { status: 502 }));
		const error = (await api.get('/api/requests').catch((e: unknown) => e)) as ApiError;
		expect(error.status).toBe(502);
		expect(error.message.length).toBeGreaterThan(10);
	});
});
