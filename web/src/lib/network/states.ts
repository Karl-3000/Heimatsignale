/**
 * Die 16 Bundesländer mit amtlichem Schlüssel (erste zwei Ziffern des AGS),
 * vollem Namen und gebräuchlicher Kurzform für enge Beschriftungen.
 */

export interface FederalState {
	code: string;
	name: string;
	short: string;
}

export const FEDERAL_STATES: readonly FederalState[] = [
	{ code: '01', name: 'Schleswig-Holstein', short: 'SH' },
	{ code: '02', name: 'Hamburg', short: 'HH' },
	{ code: '03', name: 'Niedersachsen', short: 'NI' },
	{ code: '04', name: 'Bremen', short: 'HB' },
	{ code: '05', name: 'Nordrhein-Westfalen', short: 'NRW' },
	{ code: '06', name: 'Hessen', short: 'HE' },
	{ code: '07', name: 'Rheinland-Pfalz', short: 'RP' },
	{ code: '08', name: 'Baden-Württemberg', short: 'BW' },
	{ code: '09', name: 'Bayern', short: 'BY' },
	{ code: '10', name: 'Saarland', short: 'SL' },
	{ code: '11', name: 'Berlin', short: 'BE' },
	{ code: '12', name: 'Brandenburg', short: 'BB' },
	{ code: '13', name: 'Mecklenburg-Vorpommern', short: 'MV' },
	{ code: '14', name: 'Sachsen', short: 'SN' },
	{ code: '15', name: 'Sachsen-Anhalt', short: 'ST' },
	{ code: '16', name: 'Thüringen', short: 'TH' }
];

const BY_CODE = new Map(FEDERAL_STATES.map((s) => [s.code, s]));

export function stateName(code: string): string {
	return BY_CODE.get(code)?.name ?? `Bundesland ${code}`;
}

export function stateShort(code: string): string {
	return BY_CODE.get(code)?.short ?? code;
}
