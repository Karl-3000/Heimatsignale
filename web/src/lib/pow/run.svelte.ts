import { getChallenge } from '../api/endpoints';
import type { ChallengePurpose } from '../api/types';
import { solveInWorker } from './solve';

/**
 * Sichtbarer Zustand eines Proof-of-Work-Laufs. Formulare zeigen ihn über
 * PowProgress an, damit die Wartezeit erklärt und für Screenreader angesagt wird.
 */
export class PowRun {
	active = $state(false);
	progress = $state(0);

	/** Holt eine Aufgabe für den Zweck, löst sie im Worker und liefert den Wert für das Feld `pow`. */
	async solve(purpose: ChallengePurpose): Promise<string> {
		this.active = true;
		this.progress = 0;
		try {
			const challenge = await getChallenge(purpose);
			return await solveInWorker(challenge, (fraction) => {
				this.progress = fraction;
			});
		} finally {
			this.active = false;
		}
	}
}
