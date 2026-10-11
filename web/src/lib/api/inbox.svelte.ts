import { getInboxSummary } from './endpoints';
import type { InboxSummary } from './types';
import { readJson, writeJson } from '../util/storage';

const SEEN_KEY = 'hs:gelesen';

type SeenMap = Record<string, string>;

/**
 * Posteingang für die Navigation: Zahl offener Anfragen und ungelesene Gespräche.
 * Ob ein Gespräch "ungelesen" ist, entscheidet nur dieses Gerät (localStorage);
 * der Server kennt keinen Lesestatus und zeigt ihn niemandem.
 */
class InboxStore {
	summary = $state<InboxSummary | null>(null);
	seen = $state<SeenMap>(readJson<SeenMap>(SEEN_KEY, {}));
	private timer: ReturnType<typeof setInterval> | null = null;
	private busy = false;

	get incomingRequests(): number {
		return this.summary?.incoming_requests ?? 0;
	}

	get unreadIds(): string[] {
		const out: string[] = [];
		for (const c of this.summary?.conversations ?? []) {
			if (this.isUnread(c.id, c.last_message_at, c.last_message_mine)) out.push(c.id);
		}
		return out;
	}

	get unreadCount(): number {
		return this.unreadIds.length;
	}

	isUnread(id: string, lastMessageAt: string | null | undefined, mine: boolean): boolean {
		if (!lastMessageAt || mine) return false;
		const seenAt = this.seen[id];
		return !seenAt || new Date(lastMessageAt).getTime() > new Date(seenAt).getTime();
	}

	/** Merkt sich lokal, bis zu welchem Zeitpunkt ein Gespräch gelesen ist. */
	markSeen(id: string, at: string | null | undefined): void {
		const value = at ?? new Date().toISOString();
		const current = this.seen[id];
		if (current && new Date(current).getTime() >= new Date(value).getTime()) return;
		this.seen = { ...this.seen, [id]: value };
		writeJson(SEEN_KEY, this.seen);
	}

	async refresh(): Promise<void> {
		if (this.busy) return;
		this.busy = true;
		try {
			this.summary = await getInboxSummary();
		} catch {
			/* Beim nächsten Durchlauf erneut versuchen; ein 401 leitet der Client um. */
		} finally {
			this.busy = false;
		}
	}

	/** Startet das Polling. Ruht, solange der Tab im Hintergrund ist. */
	start(seconds: number): void {
		this.stop();
		void this.refresh();
		const interval = Math.max(10, seconds) * 1000;
		this.timer = setInterval(() => {
			if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
			void this.refresh();
		}, interval);
	}

	stop(): void {
		if (this.timer) clearInterval(this.timer);
		this.timer = null;
	}

	reset(): void {
		this.stop();
		this.summary = null;
	}
}

export const inbox = new InboxStore();
