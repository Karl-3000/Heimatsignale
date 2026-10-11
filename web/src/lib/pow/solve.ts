import { encodeSolution, solveChallenge, type PowChallengeInput } from './solver';
import type { PowWorkerRequest, PowWorkerResponse } from './pow.worker';

/**
 * Löst eine Aufgabe im Web Worker. Lässt sich kein Worker starten, wird im
 * Hauptthread gerechnet; das dauert länger, funktioniert aber überall.
 */
export function solveInWorker(challenge: PowChallengeInput, onProgress?: (fraction: number) => void): Promise<string> {
	return new Promise<string>((resolve, reject) => {
		let worker: Worker | null = null;
		try {
			worker = new Worker(new URL('./pow.worker.ts', import.meta.url), { type: 'module' });
		} catch {
			worker = null;
		}

		const fallback = () => {
			solveChallenge(challenge, { onProgress, chunk: 250 })
				.then((n) => {
					if (n === null) reject(new Error('no_solution'));
					else resolve(encodeSolution(challenge, n));
				})
				.catch(reject);
		};

		if (!worker) {
			fallback();
			return;
		}

		const w = worker;
		let started = false;
		w.onmessage = (event: MessageEvent<PowWorkerResponse>) => {
			const message = event.data;
			started = true;
			if (message.type === 'progress') {
				onProgress?.(message.fraction);
			} else if (message.type === 'done') {
				w.terminate();
				resolve(message.pow);
			} else {
				w.terminate();
				reject(new Error(message.reason));
			}
		};
		w.onerror = () => {
			w.terminate();
			// Startfehler (z. B. blockierte Worker): im Hauptthread weiterrechnen.
			if (!started) fallback();
			else reject(new Error('worker_failed'));
		};
		const request: PowWorkerRequest = { type: 'solve', challenge };
		w.postMessage(request);
	});
}
