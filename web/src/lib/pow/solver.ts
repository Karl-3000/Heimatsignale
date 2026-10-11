/**
 * Proof-of-Work nach dem Altcha-Protokoll (docs/API.md):
 * Gesucht ist die Zahl n in 0..maxnumber mit sha256(salt + n) == challenge.
 * Reine Funktionen ohne DOM; laufen im Web Worker, im Hauptthread und in Node.
 */

export interface PowChallengeInput {
	algorithm: string;
	challenge: string;
	salt: string;
	signature: string;
	maxnumber: number;
}

export interface SolveOptions {
	/** Wird regelmäßig mit dem Fortschritt zwischen 0 und 1 aufgerufen. */
	onProgress?: (fraction: number) => void;
	signal?: { aborted: boolean };
	/** Nach so vielen Versuchen wird der Fortschritt gemeldet und kurz Luft gelassen. */
	chunk?: number;
}

const HEX = Array.from({ length: 256 }, (_, i) => i.toString(16).padStart(2, '0'));

export function toHex(buffer: ArrayBuffer): string {
	const bytes = new Uint8Array(buffer);
	let out = '';
	for (let i = 0; i < bytes.length; i++) out += HEX[bytes[i]];
	return out;
}

export async function sha256Hex(text: string): Promise<string> {
	const data = new TextEncoder().encode(text);
	return toHex(await crypto.subtle.digest('SHA-256', data));
}

/** Sucht die Lösung. Liefert null, wenn es in 0..maxnumber keine gibt oder abgebrochen wurde. */
export async function solveChallenge(c: PowChallengeInput, options: SolveOptions = {}): Promise<number | null> {
	if (c.algorithm !== 'SHA-256') throw new Error(`Nicht unterstützter Algorithmus: ${c.algorithm}`);
	const target = c.challenge.toLowerCase();
	const max = Math.max(0, Math.floor(c.maxnumber));
	const chunk = Math.max(1, options.chunk ?? 1000);
	for (let n = 0; n <= max; n++) {
		if ((await sha256Hex(c.salt + n)) === target) {
			options.onProgress?.(1);
			return n;
		}
		if (n % chunk === chunk - 1) {
			if (options.signal?.aborted) return null;
			options.onProgress?.(Math.min(0.99, (n + 1) / (max + 1)));
		}
	}
	return null;
}

function base64(text: string): string {
	const bytes = new TextEncoder().encode(text);
	let binary = '';
	for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
	return btoa(binary);
}

/** Der Wert für das Feld `pow`: Base64 des JSON mit Lösung, in der vom Vertrag genannten Feldfolge. */
export function encodeSolution(c: PowChallengeInput, number: number): string {
	return base64(
		JSON.stringify({
			algorithm: c.algorithm,
			challenge: c.challenge,
			number,
			salt: c.salt,
			signature: c.signature
		})
	);
}
