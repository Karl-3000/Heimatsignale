/**
 * Routenschutz als reine Funktion: Aus Pfad und Sitzung ergibt sich, ob die Seite
 * gezeigt wird oder wohin umgeleitet wird. Das Wurzel-Layout wendet das Ergebnis an.
 * Der Schutz ist Bedienführung; durchgesetzt werden die Regeln vom Server.
 */

import type { EffectiveState } from './types';

export interface GuardSession {
	authenticated: boolean;
	state: EffectiveState | null;
	isStaff: boolean;
}

/** Ohne Anmeldung erreichbar. */
const PUBLIC_PATHS = [
	'/',
	'/vorschau',
	'/registrieren',
	'/bestaetigen',
	'/anmelden',
	'/passwort-vergessen',
	'/passwort-neu',
	'/einspruch',
	'/datenschutz',
	'/impressum',
	'/nutzungsbedingungen'
];

/** Für jeden Zustand lesbar. */
const LEGAL_PATHS = ['/datenschutz', '/impressum', '/nutzungsbedingungen'];

/** Seiten, die ein angemeldetes, aktives Konto nicht mehr braucht. */
const GUEST_ONLY_PATHS = ['/', '/anmelden', '/registrieren', '/passwort-vergessen', '/passwort-neu'];

export const HOME_PATH = '/umkreis';
export const LOGIN_PATH = '/anmelden';
export const STATUS_PATH = '/status';
export const STAFF_PATH = '/verwaltungskonto';

export function normalizePath(pathname: string): string {
	if (pathname.length > 1 && pathname.endsWith('/')) return pathname.slice(0, -1);
	return pathname || '/';
}

function matches(path: string, list: readonly string[]): boolean {
	return list.includes(path);
}

export function isPublicPath(pathname: string): boolean {
	return matches(normalizePath(pathname), PUBLIC_PATHS);
}

export function isDevPath(pathname: string): boolean {
	const path = normalizePath(pathname);
	return path === '/dev' || path.startsWith('/dev/');
}

/**
 * Liefert das Umleitungsziel oder null, wenn die Seite gezeigt werden darf.
 * `dev` schaltet die Entwicklungsrouten unter /dev frei.
 */
export function guardRedirect(pathname: string, session: GuardSession, dev: boolean = false): string | null {
	const path = normalizePath(pathname);

	if (isDevPath(path)) return dev ? null : session.authenticated ? HOME_PATH : '/';

	if (!session.authenticated) {
		if (matches(path, PUBLIC_PATHS)) return null;
		return LOGIN_PATH;
	}

	if (matches(path, LEGAL_PATHS)) return null;

	if (session.isStaff) return path === STAFF_PATH ? null : STAFF_PATH;
	if (path === STAFF_PATH) return HOME_PATH;

	if (session.state === 'awaiting_approval') return path === STATUS_PATH ? null : STATUS_PATH;

	// Direkt nach der E-Mail-Bestätigung wird hier der Nickname festgelegt.
	if (path === '/bestaetigen' || path === '/vorschau' || path === '/einspruch') return null;

	if (matches(path, GUEST_ONLY_PATHS)) return HOME_PATH;
	if (path === STATUS_PATH && session.state !== 'muted') return HOME_PATH;

	return null;
}
