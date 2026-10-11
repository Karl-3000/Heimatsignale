import type { PublicUser } from '../api/types';
import type { OriginItem } from './types';

/**
 * Datenquelle eines Herkunftsnetzes. Die echte Quelle spricht mit der API,
 * die künstliche (synthetic.ts) liefert Testdaten ohne Backend.
 * `scope` ist der AGS eines Wohnorts oder "all" für den ganzen Umkreis.
 */
export interface OriginSource {
	/** Stufe 2: Landkreise eines Bundeslands. */
	districts(scope: string, stateCode: string): Promise<OriginItem[]>;
	/** Stufe 3: Orte eines Landkreises. */
	places(scope: string, districtAgs: string): Promise<OriginItem[]>;
	/** Personen eines Heimatorts, seitenweise ab 1. */
	people(scope: string, homeAgs: string, page: number): Promise<{ items: PublicUser[]; has_more: boolean }>;
}

export const SCOPE_ALL = 'all';
