import { fetchSession, setCsrfToken } from './client';
import { DEFAULT_SITE, type EffectiveState, type Me, type SessionResponse, type SiteInfo } from './types';

/**
 * Die Sitzung, wie sie GET /api/session liefert. Einzige Quelle für Anmeldezustand,
 * eigenes Profil, CSRF-Token und Seitenkonfiguration.
 */
class SessionStore {
	data = $state<SessionResponse | null>(null);
	loaded = $state(false);
	failed = $state(false);

	get authenticated(): boolean {
		return this.data?.authenticated === true;
	}

	get user(): Me | null {
		return this.data?.user ?? null;
	}

	get state(): EffectiveState | null {
		return this.data?.state ?? null;
	}

	get site(): SiteInfo {
		return this.data?.site ?? DEFAULT_SITE;
	}

	get siteName(): string {
		return this.data?.site?.name || DEFAULT_SITE.name;
	}

	get adminPath(): string {
		return this.data?.site?.admin_path || '/verwaltung/';
	}

	/** Holt die Sitzung neu. Nach Login, Logout und E-Mail-Bestätigung Pflicht (neuer CSRF-Token). */
	async refresh(): Promise<SessionResponse | null> {
		try {
			const data = await fetchSession();
			this.data = data;
			this.failed = false;
			return data;
		} catch {
			this.failed = true;
			return null;
		} finally {
			this.loaded = true;
		}
	}

	/** Setzt die Sitzung lokal auf "abgemeldet", z. B. nach einem 401. */
	clear(): void {
		setCsrfToken('');
		if (this.data) {
			this.data = { ...this.data, authenticated: false, state: null, user: null, csrf_token: '' };
		}
	}

	/** Aktualisiert Felder des eigenen Profils ohne neuen Abruf (z. B. nach dem Neuwürfeln). */
	patchUser(patch: Partial<Me>): void {
		if (this.data?.user) {
			this.data = { ...this.data, user: { ...this.data.user, ...patch } };
		}
	}
}

export const session = new SessionStore();
