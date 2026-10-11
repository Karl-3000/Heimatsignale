export type ToastKind = 'info' | 'success' | 'error';

export interface ToastItem {
	id: number;
	kind: ToastKind;
	message: string;
}

/** Kurze Rückmeldungen am Bildschirmrand. Sie verschwinden von selbst und lassen sich schließen. */
class ToastStore {
	items = $state<ToastItem[]>([]);
	private next = 1;

	show(message: string, kind: ToastKind = 'info', duration: number = 6000): number {
		const id = this.next++;
		this.items = [...this.items, { id, kind, message }];
		if (duration > 0 && typeof window !== 'undefined') {
			window.setTimeout(() => this.dismiss(id), duration);
		}
		return id;
	}

	success(message: string): number {
		return this.show(message, 'success');
	}

	error(message: string): number {
		return this.show(message, 'error', 9000);
	}

	dismiss(id: number): void {
		this.items = this.items.filter((t) => t.id !== id);
	}
}

export const toasts = new ToastStore();
