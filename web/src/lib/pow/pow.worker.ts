/**
 * Web Worker für den Proof-of-Work. Er rechnet abseits des Hauptthreads, damit die
 * Oberfläche bedienbar bleibt, und meldet seinen Fortschritt.
 */
import { encodeSolution, solveChallenge, type PowChallengeInput } from './solver';

export type PowWorkerRequest = { type: 'solve'; challenge: PowChallengeInput };
export type PowWorkerResponse =
	| { type: 'progress'; fraction: number }
	| { type: 'done'; pow: string }
	| { type: 'failed'; reason: string };

const ctx = self as unknown as {
	onmessage: ((event: MessageEvent<PowWorkerRequest>) => void) | null;
	postMessage: (message: PowWorkerResponse) => void;
};

ctx.onmessage = (event) => {
	const message = event.data;
	if (!message || message.type !== 'solve') return;
	const challenge = message.challenge;
	solveChallenge(challenge, {
		chunk: 500,
		onProgress: (fraction) => ctx.postMessage({ type: 'progress', fraction })
	})
		.then((n) => {
			if (n === null) ctx.postMessage({ type: 'failed', reason: 'no_solution' });
			else ctx.postMessage({ type: 'done', pow: encodeSolution(challenge, n) });
		})
		.catch((error: unknown) => {
			ctx.postMessage({ type: 'failed', reason: error instanceof Error ? error.message : 'error' });
		});
};
