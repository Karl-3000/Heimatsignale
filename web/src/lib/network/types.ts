/**
 * Gemeinsame Typen des Herkunftsnetzes. Dieses Modul und alle Module ohne
 * ".svelte" im Namen sind frei von Framework-Code und werden mit Vitest geprüft.
 */

export type Level = 'root' | 'state' | 'district' | 'place';
export type ChildLevel = Exclude<Level, 'root'>;
export type SortMode = 'distance' | 'count';

/** Ein Knoten des Herkunftsnetzes: Wohnort (Mitte), Bundesland, Landkreis oder Ort. */
export interface OriginNode {
	/** Stabile Kennung: "root", "s09", "d09780", "p09780139". */
	id: string;
	level: Level;
	/** state_code, district_ags oder ags; beim Wohnort der Geltungsbereich. */
	key: string;
	name: string;
	count: number;
	/** Entfernung vom eigenen Heimatort zum Schwerpunkt der Gruppe, nur für die Sortierung. */
	distanceKm: number | null;
	parentId: string | null;
	/** Gehört zum eigenen Heimatort, Landkreis oder Bundesland. */
	own: boolean;
}

/** Die eigene Herkunft, abgeleitet aus dem AGS des Heimatorts. */
export interface OwnOrigin {
	stateCode: string;
	districtAgs: string;
	ags: string;
}

/** Eine Gruppe, wie sie die API auf einer Stufe liefert. */
export interface OriginItem {
	key: string;
	name: string;
	count: number;
	distance_km: number | null;
}

export const LEVEL_DEPTH: Record<Level, number> = { root: 0, state: 1, district: 2, place: 3 };

export const LEVEL_LABEL: Record<Level, string> = {
	root: 'Wohnort',
	state: 'Bundesland',
	district: 'Landkreis',
	place: 'Ort'
};

const PREFIX: Record<ChildLevel, string> = { state: 's', district: 'd', place: 'p' };

export const ROOT_ID = 'root';

export function nodeId(level: Level, key: string): string {
	return level === 'root' ? ROOT_ID : PREFIX[level] + key;
}

export function childLevel(level: Level): ChildLevel | null {
	if (level === 'root') return 'state';
	if (level === 'state') return 'district';
	if (level === 'district') return 'place';
	return null;
}

export function ownOriginFromAgs(ags: string | null | undefined): OwnOrigin | null {
	if (!ags || ags.length < 5) return null;
	return { stateCode: ags.slice(0, 2), districtAgs: ags.slice(0, 5), ags };
}

export function isOwn(level: Level, key: string, own: OwnOrigin | null): boolean {
	if (!own) return false;
	if (level === 'state') return key === own.stateCode;
	if (level === 'district') return key === own.districtAgs;
	if (level === 'place') return key === own.ags;
	return false;
}

export function toNode(
	item: OriginItem,
	level: ChildLevel,
	parentId: string,
	own: OwnOrigin | null
): OriginNode {
	return {
		id: nodeId(level, item.key),
		level,
		key: item.key,
		name: item.name,
		count: item.count,
		distanceKm: item.distance_km,
		parentId,
		own: isOwn(level, item.key, own)
	};
}
