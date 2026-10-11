import { readStorage, writeStorage } from './storage';

export type ThemeChoice = 'system' | 'light' | 'dark';

const KEY = 'hs:theme';

function initial(): ThemeChoice {
	const stored = readStorage(KEY);
	return stored === 'light' || stored === 'dark' ? stored : 'system';
}

/** Farbschema: Systemeinstellung oder ausdrückliche Wahl, gespeichert im Browser. */
class ThemeStore {
	choice = $state<ThemeChoice>(initial());

	set(choice: ThemeChoice): void {
		this.choice = choice;
		writeStorage(KEY, choice === 'system' ? null : choice);
		if (typeof document !== 'undefined') {
			if (choice === 'system') document.documentElement.removeAttribute('data-theme');
			else document.documentElement.setAttribute('data-theme', choice);
		}
	}

	/** Das tatsächlich wirksame Schema, z. B. für den Kartenstil. */
	get effective(): 'light' | 'dark' {
		if (this.choice !== 'system') return this.choice;
		if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
		return 'light';
	}
}

export const theme = new ThemeStore();
