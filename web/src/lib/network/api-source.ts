import { getOrigins, getPeople } from '../api/endpoints';
import type { OriginSource } from './source';

/**
 * Die echte Datenquelle: lädt jede Stufe erst, wenn sie aufgeklappt wird.
 * Jede Quelle gehört zu genau einem Umkreis und gibt ihn bei jedem Aufruf mit,
 * damit Netz, Liste und Übersicht immer dieselbe Grundmenge zeigen.
 */
export function createApiSource(radiusKm?: number): OriginSource {
	return {
		async districts(scope, stateCode) {
			const response = await getOrigins(scope, 'district', stateCode, radiusKm);
			return response.items;
		},
		async places(scope, districtAgs) {
			const response = await getOrigins(scope, 'place', districtAgs, radiusKm);
			return response.items;
		},
		async people(scope, homeAgs, page) {
			const response = await getPeople(scope, homeAgs, page, radiusKm);
			return { items: response.items, has_more: response.has_more };
		}
	};
}
