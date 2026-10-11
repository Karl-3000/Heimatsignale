import { describe, expect, it } from 'vitest';
import { guardRedirect, isPublicPath, normalizePath, type GuardSession } from './guard';

const guest: GuardSession = { authenticated: false, state: null, isStaff: false };
const active: GuardSession = { authenticated: true, state: 'active', isStaff: false };
const muted: GuardSession = { authenticated: true, state: 'muted', isStaff: false };
const waiting: GuardSession = { authenticated: true, state: 'awaiting_approval', isStaff: false };
const staff: GuardSession = { authenticated: true, state: 'active', isStaff: true };

describe('guardRedirect', () => {
	it('lässt Gäste auf öffentliche Seiten und schickt sie sonst zur Anmeldung', () => {
		for (const path of ['/', '/vorschau', '/registrieren', '/bestaetigen', '/anmelden', '/passwort-vergessen', '/passwort-neu', '/einspruch', '/datenschutz', '/impressum', '/nutzungsbedingungen']) {
			expect(guardRedirect(path, guest)).toBeNull();
			expect(isPublicPath(path)).toBe(true);
		}
		for (const path of ['/umkreis', '/profil/abc', '/anfragen', '/gespraeche', '/gespraeche/1', '/einstellungen', '/status', '/verwaltungskonto']) {
			expect(guardRedirect(path, guest)).toBe('/anmelden');
		}
	});

	it('lässt wartende Konten nur auf die Statusseite und die Rechtstexte', () => {
		expect(guardRedirect('/status', waiting)).toBeNull();
		expect(guardRedirect('/datenschutz', waiting)).toBeNull();
		for (const path of ['/umkreis', '/anfragen', '/einstellungen', '/', '/bestaetigen', '/profil/x']) {
			expect(guardRedirect(path, waiting)).toBe('/status');
		}
	});

	it('zeigt Admin-Konten nur den Hinweis auf die Verwaltung', () => {
		expect(guardRedirect('/verwaltungskonto', staff)).toBeNull();
		expect(guardRedirect('/umkreis', staff)).toBe('/verwaltungskonto');
		expect(guardRedirect('/impressum', staff)).toBeNull();
		expect(guardRedirect('/verwaltungskonto', active)).toBe('/umkreis');
	});

	it('führt aktive Konten von Gastseiten in den Umkreis', () => {
		expect(guardRedirect('/', active)).toBe('/umkreis');
		expect(guardRedirect('/anmelden', active)).toBe('/umkreis');
		expect(guardRedirect('/registrieren', active)).toBe('/umkreis');
		expect(guardRedirect('/umkreis', active)).toBeNull();
		expect(guardRedirect('/gespraeche/42', active)).toBeNull();
		expect(guardRedirect('/bestaetigen', active)).toBeNull();
	});

	it('zeigt die Statusseite nur stummgeschalteten und wartenden Konten', () => {
		expect(guardRedirect('/status', active)).toBe('/umkreis');
		expect(guardRedirect('/status', muted)).toBeNull();
		expect(guardRedirect('/umkreis', muted)).toBeNull();
	});

	it('gibt Entwicklungsrouten nur im Entwicklungsmodus frei', () => {
		expect(guardRedirect('/dev/netz', guest, true)).toBeNull();
		expect(guardRedirect('/dev/netz', guest, false)).toBe('/');
		expect(guardRedirect('/dev/netz', active, false)).toBe('/umkreis');
	});

	it('behandelt abschließende Schrägstriche gleich', () => {
		expect(normalizePath('/umkreis/')).toBe('/umkreis');
		expect(normalizePath('/')).toBe('/');
		expect(guardRedirect('/anmelden/', guest)).toBeNull();
	});
});
