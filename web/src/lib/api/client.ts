/**
 * Der eine API-Client der Oberfläche (docs/API.md).
 *
 * - Gleiche Origin, Session-Cookie: fetch mit credentials "same-origin".
 * - Jeder zustandsändernde Aufruf (POST, DELETE) trägt X-CSRFToken aus der
 *   letzten Antwort von GET /api/session.
 * - Fehlerkörper {code, message, fields} werden zu einem typisierten ApiError.
 * - 401 not_authenticated ruft den registrierten Handler (Weiterleitung zu /anmelden).
 *
 * Das Modul ist frei von Framework-Code und wird mit einem nachgebauten fetch getestet.
 */

import type { SessionResponse } from './types';

export type FieldErrors = Record<string, string>;

export class ApiError extends Error {
	readonly status: number;
	readonly code: string;
	readonly fields: FieldErrors;
	/** Wartezeit in Sekunden bei 429. */
	readonly retryAfter: number | null;

	constructor(status: number, code: string, message: string, fields: FieldErrors = {}, retryAfter: number | null = null) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.code = code;
		this.fields = fields;
		this.retryAfter = retryAfter;
	}

	get isRateLimited(): boolean {
		return this.status === 429;
	}

	get isNotFound(): boolean {
		return this.status === 404;
	}
}

export function isApiError(error: unknown): error is ApiError {
	return error instanceof ApiError;
}

/** Fertiger deutscher Satz für beliebige Fehler. */
export function errorMessage(error: unknown): string {
	if (error instanceof ApiError) return error.message;
	return 'Das hat nicht geklappt. Bitte versuche es noch einmal.';
}

const FALLBACK_MESSAGES: Record<number, string> = {
	0: 'Keine Verbindung zum Server. Bitte prüfe deine Internetverbindung.',
	400: 'Die Anfrage ist so nicht möglich.',
	401: 'Du bist nicht mehr angemeldet.',
	403: 'Das ist mit deinem Konto gerade nicht möglich.',
	404: 'Das gibt es nicht oder es ist für dich nicht sichtbar.',
	409: 'Das passt nicht mehr zum aktuellen Stand. Bitte lade die Seite neu.',
	422: 'Bitte prüfe deine Eingaben.',
	429: 'Zu viele Anfragen in kurzer Zeit. Bitte warte einen Moment.'
};

const FALLBACK_CODES: Record<number, string> = {
	0: 'network',
	401: 'not_authenticated',
	404: 'not_found',
	422: 'validation',
	429: 'rate_limited'
};

type Query = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
	query?: Query;
	body?: unknown;
	/** Bei 401 nicht zur Anmeldung weiterleiten (z. B. beim Login selbst). */
	quiet401?: boolean;
	signal?: AbortSignal;
}

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

let csrfToken = '';
let unauthorizedHandler: (() => void) | null = null;
let fetchImpl: FetchLike | null = null;
let pendingSession: Promise<SessionResponse> | null = null;

export function setCsrfToken(token: string | null | undefined): void {
	csrfToken = token ?? '';
}

export function getCsrfToken(): string {
	return csrfToken;
}

/** Wird bei 401 not_authenticated aufgerufen. */
export function onUnauthorized(handler: (() => void) | null): void {
	unauthorizedHandler = handler;
}

/** Nur für Tests: ersetzt fetch. */
export function setFetch(impl: FetchLike | null): void {
	fetchImpl = impl;
}

function buildUrl(path: string, query?: Query): string {
	if (!query) return path;
	const params = new URLSearchParams();
	for (const [key, value] of Object.entries(query)) {
		if (value === null || value === undefined) continue;
		params.set(key, String(value));
	}
	const qs = params.toString();
	return qs ? `${path}?${qs}` : path;
}

async function parseError(response: Response): Promise<ApiError> {
	let code = FALLBACK_CODES[response.status] ?? 'error';
	let message = FALLBACK_MESSAGES[response.status] ?? 'Der Server meldet einen Fehler. Bitte versuche es später noch einmal.';
	let fields: FieldErrors = {};
	let retryAfter: number | null = null;
	try {
		const data: unknown = await response.json();
		if (data && typeof data === 'object') {
			const body = data as Record<string, unknown>;
			if (typeof body.code === 'string' && body.code) code = body.code;
			if (typeof body.message === 'string' && body.message) message = body.message;
			if (body.fields && typeof body.fields === 'object') {
				for (const [key, value] of Object.entries(body.fields as Record<string, unknown>)) {
					if (typeof value === 'string') fields[key] = value;
					else if (Array.isArray(value) && typeof value[0] === 'string') fields[key] = value[0];
				}
			}
			if (typeof body.retry_after === 'number') retryAfter = body.retry_after;
		}
	} catch {
		fields = {};
	}
	if (retryAfter === null) {
		const header = response.headers.get('Retry-After');
		if (header && /^\d+$/.test(header)) retryAfter = Number(header);
	}
	return new ApiError(response.status, code, message, fields, retryAfter);
}

async function rawRequest<T>(method: 'GET' | 'POST' | 'DELETE', path: string, options: RequestOptions): Promise<T> {
	const headers: Record<string, string> = { Accept: 'application/json' };
	const init: RequestInit = { method, credentials: 'same-origin', headers, cache: 'no-store', signal: options.signal };
	if (method !== 'GET') {
		headers['X-CSRFToken'] = csrfToken;
		if (options.body !== undefined) {
			headers['Content-Type'] = 'application/json';
			init.body = JSON.stringify(options.body);
		}
	}

	const doFetch: FetchLike = fetchImpl ?? ((input, i) => fetch(input, i));
	let response: Response;
	try {
		response = await doFetch(buildUrl(path, options.query), init);
	} catch (cause) {
		if (cause instanceof DOMException && cause.name === 'AbortError') throw cause;
		throw new ApiError(0, 'network', FALLBACK_MESSAGES[0]);
	}

	if (!response.ok) {
		const error = await parseError(response);
		if (error.status === 401 && error.code === 'not_authenticated' && !options.quiet401) {
			unauthorizedHandler?.();
		}
		throw error;
	}

	if (response.status === 204) return undefined as T;
	const text = await response.text();
	if (!text) return undefined as T;
	try {
		return JSON.parse(text) as T;
	} catch {
		throw new ApiError(response.status, 'invalid_response', 'Der Server hat unerwartet geantwortet.');
	}
}

/** Holt die Sitzung und merkt sich den CSRF-Token. Parallele Aufrufe teilen sich eine Anfrage. */
export function fetchSession(): Promise<SessionResponse> {
	if (!pendingSession) {
		pendingSession = rawRequest<SessionResponse>('GET', '/api/session', { quiet401: true })
			.then((data) => {
				setCsrfToken(data.csrf_token);
				return data;
			})
			.finally(() => {
				pendingSession = null;
			});
	}
	return pendingSession;
}

async function request<T>(method: 'GET' | 'POST' | 'DELETE', path: string, options: RequestOptions = {}): Promise<T> {
	// Ohne Token würde jeder schreibende Aufruf an der CSRF-Prüfung scheitern.
	if (method !== 'GET' && !csrfToken) await fetchSession();
	try {
		return await rawRequest<T>(method, path, options);
	} catch (error) {
		// Ein veralteter Token (z. B. nach Sitzungswechsel in einem anderen Tab): einmal erneuern.
		if (method !== 'GET' && error instanceof ApiError && error.code === 'csrf_failed') {
			await fetchSession();
			return rawRequest<T>(method, path, options);
		}
		throw error;
	}
}

export const api = {
	get<T>(path: string, query?: Query, options: Omit<RequestOptions, 'query' | 'body'> = {}): Promise<T> {
		return request<T>('GET', path, { ...options, query });
	},
	post<T>(path: string, body?: unknown, options: Omit<RequestOptions, 'body'> = {}): Promise<T> {
		return request<T>('POST', path, { ...options, body: body === undefined ? {} : body });
	},
	delete<T>(path: string, options: Omit<RequestOptions, 'body'> = {}): Promise<T> {
		return request<T>('DELETE', path, options);
	}
};
