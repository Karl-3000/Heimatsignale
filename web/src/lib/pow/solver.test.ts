import { describe, expect, it } from 'vitest';
import { encodeSolution, sha256Hex, solveChallenge, type PowChallengeInput } from './solver';

async function challengeFor(number: number, maxnumber: number): Promise<PowChallengeInput> {
	const salt = 'f3a9c1?expires=1790000000&';
	return { algorithm: 'SHA-256', challenge: await sha256Hex(salt + number), salt, signature: 'ab12', maxnumber };
}

describe('sha256Hex', () => {
	it('berechnet bekannte Prüfsummen', async () => {
		expect(await sha256Hex('')).toBe('e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
		expect(await sha256Hex('abc')).toBe('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
	});
});

describe('solveChallenge', () => {
	it('findet die gesuchte Zahl', async () => {
		const c = await challengeFor(1234, 5000);
		expect(await solveChallenge(c)).toBe(1234);
	});

	it('findet die Ränder 0 und maxnumber', async () => {
		expect(await solveChallenge(await challengeFor(0, 100))).toBe(0);
		expect(await solveChallenge(await challengeFor(100, 100))).toBe(100);
	});

	it('liefert null, wenn es keine Lösung im Bereich gibt', async () => {
		const c = await challengeFor(900, 5000);
		expect(await solveChallenge({ ...c, maxnumber: 300 })).toBeNull();
	});

	it('meldet Fortschritt, zuletzt 1', async () => {
		const seen: number[] = [];
		await solveChallenge(await challengeFor(950, 1000), { chunk: 100, onProgress: (f) => seen.push(f) });
		expect(seen.length).toBeGreaterThan(5);
		expect(seen[seen.length - 1]).toBe(1);
		for (let i = 1; i < seen.length; i++) expect(seen[i]).toBeGreaterThanOrEqual(seen[i - 1]);
	});

	it('bricht ab, wenn das Signal gesetzt ist', async () => {
		const signal = { aborted: true };
		expect(await solveChallenge(await challengeFor(4000, 5000), { chunk: 50, signal })).toBeNull();
	});

	it('lehnt unbekannte Algorithmen ab', async () => {
		const c = await challengeFor(1, 10);
		let message = '';
		try {
			await solveChallenge({ ...c, algorithm: 'SHA-1' });
		} catch (error) {
			message = error instanceof Error ? error.message : '';
		}
		expect(message).toMatch('SHA-1');
	});
});

describe('encodeSolution', () => {
	it('kodiert das JSON in der Feldfolge des Vertrags als Base64', async () => {
		const c = await challengeFor(42, 100);
		const decoded = atob(encodeSolution(c, 42));
		expect(decoded).toBe(JSON.stringify({ algorithm: 'SHA-256', challenge: c.challenge, number: 42, salt: c.salt, signature: 'ab12' }));
		expect(Object.keys(JSON.parse(decoded))).toEqual(['algorithm', 'challenge', 'number', 'salt', 'signature']);
	});
});
