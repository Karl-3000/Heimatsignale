/**
 * Tastaturbedienung nach dem ARIA-Muster "Tree View". Netz und Liste benutzen
 * dieselbe Funktion, damit sich beide Ansichten gleich bedienen lassen.
 */

export interface KeyRow {
	id: string;
	depth: number;
	parentId: string | null;
	/** true, wenn sich der Knoten aufklappen lässt (auch wenn er gerade zu ist). */
	expandable: boolean;
	expanded: boolean;
}

export type TreeKeyAction =
	| { type: 'focus'; id: string }
	| { type: 'expand'; id: string }
	| { type: 'collapse'; id: string }
	| { type: 'activate'; id: string };

export function treeKeyAction(
	key: string,
	rows: readonly KeyRow[],
	focusedId: string
): TreeKeyAction | null {
	if (rows.length === 0) return null;
	let index = rows.findIndex((r) => r.id === focusedId);
	if (index < 0) index = 0;
	const row = rows[index];

	switch (key) {
		case 'ArrowDown':
			return index < rows.length - 1 ? { type: 'focus', id: rows[index + 1].id } : null;
		case 'ArrowUp':
			return index > 0 ? { type: 'focus', id: rows[index - 1].id } : null;
		case 'Home':
			return { type: 'focus', id: rows[0].id };
		case 'End':
			return { type: 'focus', id: rows[rows.length - 1].id };
		case 'ArrowRight': {
			if (!row.expandable) return null;
			if (!row.expanded) return { type: 'expand', id: row.id };
			const next = rows[index + 1];
			return next && next.depth > row.depth ? { type: 'focus', id: next.id } : null;
		}
		case 'ArrowLeft': {
			if (row.expandable && row.expanded) return { type: 'collapse', id: row.id };
			return row.parentId ? { type: 'focus', id: row.parentId } : null;
		}
		case 'Enter':
		case ' ':
		case 'Spacebar':
			return { type: 'activate', id: row.id };
		default:
			return null;
	}
}
