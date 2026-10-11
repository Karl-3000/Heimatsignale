import { getOrigins, getPeople } from '../api/endpoints';
import type { OriginSource } from './source';

/** Die echte Datenquelle: lädt jede Stufe erst, wenn sie aufgeklappt wird. */
export const apiSource: OriginSource = {
	async districts(scope, stateCode) {
		const response = await getOrigins(scope, 'district', stateCode);
		return response.items;
	},
	async places(scope, districtAgs) {
		const response = await getOrigins(scope, 'place', districtAgs);
		return response.items;
	},
	async people(scope, homeAgs, page) {
		const response = await getPeople(scope, homeAgs, page);
		return { items: response.items, has_more: response.has_more };
	}
};
