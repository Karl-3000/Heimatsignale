import type { NearbyOverview } from '../api/types';
import { SCOPE_ALL } from './source';
import { stateName } from './states';
import type { OriginItem } from './types';

/**
 * Stufe 1 eines Herkunftsnetzes aus der Umkreis-Übersicht.
 * Für einen einzelnen Wohnort sind es dessen Bundesländer; für "Alle im Umkreis"
 * werden die Wohnorte zusammengezählt. Dafür ist kein weiterer API-Aufruf nötig.
 */
export function statesFromOverview(overview: NearbyOverview, scope: string): OriginItem[] {
	const acc = new Map<string, { count: number; weighted: number; hasDistance: boolean }>();
	for (const r of overview.residences) {
		if (scope !== SCOPE_ALL && r.ags !== scope) continue;
		for (const s of r.states) {
			const e = acc.get(s.state_code) ?? { count: 0, weighted: 0, hasDistance: false };
			e.count += s.count;
			if (s.distance_km !== null && s.distance_km !== undefined) {
				e.weighted += s.distance_km * s.count;
				e.hasDistance = true;
			}
			acc.set(s.state_code, e);
		}
	}
	return [...acc.entries()].map(([code, e]) => ({
		key: code,
		name: stateName(code),
		count: e.count,
		distance_km: e.hasDistance && e.count > 0 ? Math.round(e.weighted / e.count) : null
	}));
}

/** Gesamtzahl der Personen eines Geltungsbereichs. */
export function totalForScope(overview: NearbyOverview, scope: string): number {
	if (scope === SCOPE_ALL) return overview.total;
	return overview.residences.find((r) => r.ags === scope)?.total ?? 0;
}

export function scopeName(overview: NearbyOverview, scope: string): string {
	if (scope === SCOPE_ALL) return 'Alle im Umkreis';
	return overview.residences.find((r) => r.ags === scope)?.name ?? 'Wohnort';
}
