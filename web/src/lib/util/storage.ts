/** Zugriff auf localStorage, der nie wirft (privater Modus, gesperrter Speicher). */

export function readStorage(key: string): string | null {
	try {
		return localStorage.getItem(key);
	} catch {
		return null;
	}
}

export function writeStorage(key: string, value: string | null): void {
	try {
		if (value === null) localStorage.removeItem(key);
		else localStorage.setItem(key, value);
	} catch {
		/* Ohne Speicher gilt der Wert nur für diese Sitzung. */
	}
}

export function readJson<T>(key: string, fallback: T): T {
	const raw = readStorage(key);
	if (!raw) return fallback;
	try {
		return JSON.parse(raw) as T;
	} catch {
		return fallback;
	}
}

export function writeJson(key: string, value: unknown): void {
	writeStorage(key, JSON.stringify(value));
}
