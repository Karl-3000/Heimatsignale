/**
 * Künstliche Daten für den Netz-Prototyp (Projektplan, Abschnitt 5).
 * Sie decken die geforderten Fälle ab: 5, 50 und 300 Knoten, lange Ortsnamen,
 * sehr ungleiche Gruppen, drei dicht benachbarte Wohnorte, eigene Herkunft
 * außerhalb der fünf größten Gruppen und einen leeren Umkreis.
 *
 * Alle Personen sind erfunden. Die Daten entstehen deterministisch aus einem
 * festen Startwert, damit Tests und Entwicklungsansicht dasselbe zeigen.
 */

import type { NearbyOverview, PlacePoint, PublicUser, ResidenceOverview } from '../api/types';
import type { OriginSource } from './source';
import { SCOPE_ALL } from './source';
import { stateName } from './states';
import type { OriginItem } from './types';

export interface SyntheticGroup {
	stateCode: string;
	districtAgs: string;
	districtName: string;
	ags: string;
	placeName: string;
	residenceAgs: string;
	count: number;
	/** Entfernung des Orts vom eigenen Heimatort in km. */
	distanceKm: number;
}

export interface SyntheticDataset {
	id: string;
	title: string;
	description: string;
	overview: NearbyOverview;
	groups: SyntheticGroup[];
	source: OriginSource;
	/** Anzahl der Herkunftsknoten bei vollständig aufgeklapptem Gesamtnetz. */
	nodeCount: number;
}

interface ResidenceSeed {
	ags: string;
	name: string;
	lat: number;
	lon: number;
}

const MARL: ResidenceSeed = { ags: '05562024', name: 'Marl', lat: 51.6567, lon: 7.0904 };
const HERTEN: ResidenceSeed = { ags: '05562020', name: 'Herten', lat: 51.5959, lon: 7.1376 };
const RECKLINGHAUSEN: ResidenceSeed = { ags: '05562032', name: 'Recklinghausen', lat: 51.6141, lon: 7.1979 };
const OER: ResidenceSeed = { ags: '05562028', name: 'Oer-Erkenschwick', lat: 51.6422, lon: 7.2508 };
const DORSTEN: ResidenceSeed = { ags: '05562012', name: 'Dorsten', lat: 51.6604, lon: 6.9647 };
const HALTERN: ResidenceSeed = { ags: '05562016', name: 'Haltern am See', lat: 51.7429, lon: 7.1869 };
const GELSENKIRCHEN: ResidenceSeed = { ags: '05513000', name: 'Gelsenkirchen', lat: 51.5177, lon: 7.0857 };

const ME_RESIDENCE: PlacePoint = {
	ags: MARL.ags,
	name: MARL.name,
	district_ags: '05562',
	district_name: 'Recklinghausen',
	state_code: '05',
	state_name: 'Nordrhein-Westfalen',
	lat: MARL.lat,
	lon: MARL.lon
};

const ME_HOME: PlacePoint = {
	ags: '09780139',
	name: 'Sonthofen',
	district_ags: '09780',
	district_name: 'Oberallgäu',
	state_code: '09',
	state_name: 'Bayern',
	lat: 47.5142,
	lon: 10.2817
};

/** Ungefähre Entfernung der Bundesländer vom Oberallgäu, nur für die Sortierung. */
const STATE_DISTANCE: Record<string, number> = {
	'09': 90,
	'08': 140,
	'06': 330,
	'16': 340,
	'07': 350,
	'10': 330,
	'14': 420,
	'05': 480,
	'15': 470,
	'03': 560,
	'11': 550,
	'12': 540,
	'04': 640,
	'02': 660,
	'13': 700,
	'01': 730
};

/** Echte Kreisnamen je Bundesland, als Rohstoff für die erzeugten Datensätze. */
const DISTRICTS: Record<string, string[]> = {
	'09': ['Oberallgäu', 'Rosenheim', 'Garmisch-Partenkirchen', 'Passau', 'Ansbach', 'Bamberg'],
	'05': ['Recklinghausen', 'Borken', 'Siegen-Wittgenstein', 'Höxter', 'Kleve', 'Soest'],
	'14': ['Zwickau', 'Bautzen', 'Erzgebirgskreis', 'Meißen', 'Görlitz', 'Vogtlandkreis'],
	'08': ['Ravensburg', 'Ortenaukreis', 'Schwarzwald-Baar-Kreis', 'Tübingen', 'Biberach', 'Calw'],
	'03': ['Emsland', 'Göttingen', 'Cuxhaven', 'Harburg', 'Celle', 'Leer'],
	'06': ['Fulda', 'Main-Kinzig-Kreis', 'Marburg-Biedenkopf', 'Bergstraße', 'Gießen', 'Kassel'],
	'07': ['Ahrweiler', 'Mayen-Koblenz', 'Bad Kreuznach', 'Trier-Saarburg', 'Germersheim', 'Kusel'],
	'16': ['Gotha', 'Eichsfeld', 'Saale-Orla-Kreis', 'Ilm-Kreis', 'Greiz', 'Sonneberg'],
	'15': ['Harz', 'Börde', 'Saalekreis', 'Wittenberg', 'Stendal', 'Burgenlandkreis'],
	'12': ['Uckermark', 'Barnim', 'Oberhavel', 'Spree-Neiße', 'Prignitz', 'Havelland'],
	'13': ['Rostock', 'Vorpommern-Rügen', 'Mecklenburgische Seenplatte', 'Ludwigslust-Parchim', 'Nordwestmecklenburg', 'Vorpommern-Greifswald'],
	'01': ['Nordfriesland', 'Dithmarschen', 'Ostholstein', 'Plön', 'Steinburg', 'Segeberg'],
	'10': ['Saarlouis', 'Neunkirchen', 'Merzig-Wadern', 'St. Wendel'],
	'11': ['Berlin'],
	'02': ['Hamburg'],
	'04': ['Bremen', 'Bremerhaven']
};

const NAME_HEAD = ['Alten', 'Neu', 'Ober', 'Unter', 'Wald', 'Stein', 'Eichen', 'Linden', 'Mühl', 'Kirch', 'Hohen', 'Nieder', 'Sand', 'Wiesen', 'Birken', 'Markt', 'Burg', 'Tal', 'Rot', 'Weiß', 'Schön', 'Lang', 'Breit', 'Groß', 'Klein'];
const NAME_TAIL = ['bach', 'berg', 'dorf', 'hausen', 'heim', 'feld', 'stadt', 'kirchen', 'tal', 'rode', 'hofen', 'ingen', 'au', 'born', 'brück', 'furt', 'stein', 'weiler', 'see', 'wald'];

const NICK_ADJECTIVES = ['Stiller', 'Grauer', 'Heller', 'Ruhiger', 'Wacher', 'Leiser', 'Klarer', 'Weiter', 'Sanfter', 'Flinker', 'Kühler', 'Milder'];
const NICK_NOUNS = ['Leuchtturm', 'Kranich', 'Ahorn', 'Kiesel', 'Falter', 'Dachs', 'Kompass', 'Reiher', 'Giebel', 'Anker', 'Biber', 'Wacholder'];
const AGE_RANGES = ['18–24', '25–34', '35–44', '45–54', '55–64', '65+'];

/** Kleiner deterministischer Zufallsgenerator (mulberry32). */
export function seededRandom(seed: number): () => number {
	let a = seed >>> 0;
	return () => {
		a = (a + 0x6d2b79f5) >>> 0;
		let t = a;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

function pad(n: number, width: number): string {
	return String(n).padStart(width, '0');
}

function inScope(g: SyntheticGroup, scope: string): boolean {
	return scope === SCOPE_ALL || g.residenceAgs === scope;
}

function aggregate(
	groups: readonly SyntheticGroup[],
	key: (g: SyntheticGroup) => string,
	name: (g: SyntheticGroup) => string
): OriginItem[] {
	const acc = new Map<string, { name: string; count: number; weighted: number }>();
	for (const g of groups) {
		const k = key(g);
		const entry = acc.get(k) ?? { name: name(g), count: 0, weighted: 0 };
		entry.count += g.count;
		entry.weighted += g.distanceKm * g.count;
		acc.set(k, entry);
	}
	return [...acc.entries()].map(([k, e]) => ({
		key: k,
		name: e.name,
		count: e.count,
		distance_km: e.count > 0 ? Math.round(e.weighted / e.count) : null
	}));
}

function buildPeople(groups: readonly SyntheticGroup[], residences: readonly ResidenceSeed[]): Map<string, PublicUser[]> {
	const byResidence = new Map(residences.map((r) => [r.ags, r]));
	const people = new Map<string, PublicUser[]>();
	const rand = seededRandom(4711);
	let serial = 0;
	for (const g of groups) {
		const list = people.get(g.ags) ?? [];
		for (let i = 0; i < g.count; i++) {
			serial++;
			const adjective = NICK_ADJECTIVES[Math.floor(rand() * NICK_ADJECTIVES.length)];
			const noun = NICK_NOUNS[Math.floor(rand() * NICK_NOUNS.length)];
			list.push({
				id: `00000000-0000-4000-8000-${pad(serial, 12)}`,
				nickname: `${adjective}-${noun}-${100 + Math.floor(rand() * 900)}`,
				age_range: AGE_RANGES[Math.floor(rand() * AGE_RANGES.length)],
				home: {
					ags: g.ags,
					name: g.placeName,
					district_ags: g.districtAgs,
					district_name: g.districtName,
					state_code: g.stateCode,
					state_name: stateName(g.stateCode)
				},
				residence: { ags: g.residenceAgs, name: byResidence.get(g.residenceAgs)?.name ?? '' },
				member_since: `2026-${pad(1 + Math.floor(rand() * 10), 2)}`
			});
		}
		people.set(g.ags, list);
	}
	return people;
}

function buildOverview(groups: readonly SyntheticGroup[], residences: readonly ResidenceSeed[]): NearbyOverview {
	const out: ResidenceOverview[] = [];
	for (const r of residences) {
		const mine = groups.filter((g) => g.residenceAgs === r.ags);
		if (mine.length === 0) continue;
		const states = aggregate(mine, (g) => g.stateCode, (g) => stateName(g.stateCode))
			.map((s) => ({ state_code: s.key, count: s.count, distance_km: s.distance_km }))
			.sort((a, b) => b.count - a.count || a.state_code.localeCompare(b.state_code));
		out.push({
			ags: r.ags,
			name: r.name,
			lat: r.lat,
			lon: r.lon,
			total: mine.reduce((a, g) => a + g.count, 0),
			states
		});
	}
	return {
		radius_km: 20,
		me: { residence: ME_RESIDENCE, home: ME_HOME },
		total: out.reduce((a, r) => a + r.total, 0),
		residences: out
	};
}

function makeSource(groups: readonly SyntheticGroup[], people: Map<string, PublicUser[]>): OriginSource {
	const PAGE = 50;
	return {
		async districts(scope, stateCode) {
			return aggregate(
				groups.filter((g) => inScope(g, scope) && g.stateCode === stateCode),
				(g) => g.districtAgs,
				(g) => g.districtName
			);
		},
		async places(scope, districtAgs) {
			return aggregate(
				groups.filter((g) => inScope(g, scope) && g.districtAgs === districtAgs),
				(g) => g.ags,
				(g) => g.placeName
			);
		},
		async people(scope, homeAgs, page) {
			const all = (people.get(homeAgs) ?? []).filter((p) => scope === SCOPE_ALL || p.residence.ags === scope);
			const start = (Math.max(1, page) - 1) * PAGE;
			return { items: all.slice(start, start + PAGE), has_more: start + PAGE < all.length };
		}
	};
}

function finish(
	id: string,
	title: string,
	description: string,
	groups: SyntheticGroup[],
	residences: readonly ResidenceSeed[]
): SyntheticDataset {
	const people = buildPeople(groups, residences);
	const states = new Set(groups.map((g) => g.stateCode));
	const districts = new Set(groups.map((g) => g.districtAgs));
	const places = new Set(groups.map((g) => g.ags));
	return {
		id,
		title,
		description,
		overview: buildOverview(groups, residences),
		groups,
		source: makeSource(groups, people),
		nodeCount: states.size + districts.size + places.size
	};
}

function g(
	stateCode: string,
	districtNo: number,
	districtName: string,
	placeNo: number,
	placeName: string,
	residence: ResidenceSeed,
	count: number,
	distanceKm: number
): SyntheticGroup {
	const districtAgs = `${stateCode}${pad(districtNo, 3)}`;
	return {
		stateCode,
		districtAgs,
		districtName,
		ags: `${districtAgs}${pad(placeNo, 3)}`,
		placeName,
		residenceAgs: residence.ags,
		count,
		distanceKm
	};
}

/** Erzeugt ein Netz mit genau states + states*districts + states*districts*places Knoten. */
function generated(
	id: string,
	title: string,
	description: string,
	stateCodes: string[],
	districtsPerState: number,
	placesPerDistrict: number,
	seed: number
): SyntheticDataset {
	const rand = seededRandom(seed);
	const residences = [MARL, HERTEN, RECKLINGHAUSEN, DORSTEN, HALTERN, GELSENKIRCHEN, OER];
	const used = new Set<string>(['Sonthofen', 'Immenstadt']);
	const groups: SyntheticGroup[] = [];

	const inventName = (): string => {
		for (let attempt = 0; attempt < 500; attempt++) {
			const name = NAME_HEAD[Math.floor(rand() * NAME_HEAD.length)] + NAME_TAIL[Math.floor(rand() * NAME_TAIL.length)];
			if (!used.has(name)) {
				used.add(name);
				return name;
			}
		}
		const fallback = `Ort ${used.size + 1}`;
		used.add(fallback);
		return fallback;
	};

	for (const stateCode of stateCodes) {
		const names = DISTRICTS[stateCode] ?? [];
		for (let d = 0; d < districtsPerState; d++) {
			const own = stateCode === '09' && d === 0;
			const districtNo = own ? 780 : 100 + d * 7 + 1;
			const districtName = names[d] ?? `${stateName(stateCode)} ${d + 1}`;
			const base = STATE_DISTANCE[stateCode] ?? 400;
			for (let p = 0; p < placesPerDistrict; p++) {
				const ownPlace = own && p === 0;
				const placeNo = ownPlace ? 139 : 100 + p * 3 + 1;
				const placeName = ownPlace ? 'Sonthofen' : own && p === 1 ? 'Immenstadt' : inventName();
				const residence = residences[Math.floor(rand() * residences.length)];
				// Schiefe Verteilung: viele kleine, wenige große Gruppen.
				const count = 1 + Math.floor(Math.pow(rand(), 3) * 9);
				const distance = ownPlace ? 0 : own ? 8 + p * 6 : Math.max(20, Math.round(base - 40 + rand() * 80));
				groups.push(g(stateCode, districtNo, districtName, placeNo, placeName, residence, count, distance));
			}
		}
	}
	return finish(id, title, description, groups, residences);
}

export function datasetKlein(): SyntheticDataset {
	return finish(
		'klein',
		'5 Knoten',
		'Ein Bundesland, ein Landkreis, drei Orte. Der einfachste Fall.',
		[
			g('09', 780, 'Oberallgäu', 139, 'Sonthofen', MARL, 2, 0),
			g('09', 780, 'Oberallgäu', 124, 'Immenstadt', MARL, 1, 8),
			g('09', 780, 'Oberallgäu', 133, 'Oberstdorf', MARL, 1, 13)
		],
		[MARL]
	);
}

export function datasetMittel(): SyntheticDataset {
	return generated('mittel', '50 Knoten', 'Fünf Bundesländer mit je drei Landkreisen und zwei Orten.', ['09', '05', '14', '08', '03'], 3, 2, 50);
}

export function datasetGross(): SyntheticDataset {
	return generated(
		'gross',
		'300 Knoten',
		'Zwölf Bundesländer mit je vier Landkreisen und fünf Orten. Obergrenze für die Messung auf dem Referenzgerät.',
		['09', '05', '14', '08', '03', '06', '07', '16', '15', '12', '13', '01'],
		4,
		5,
		300
	);
}

export function datasetLangeNamen(): SyntheticDataset {
	return finish(
		'lange-namen',
		'Lange Ortsnamen',
		'Namen wie Hohenstein-Ernstthal und Garmisch-Partenkirchen müssen lesbar bleiben oder sauber gekürzt werden.',
		[
			g('09', 180, 'Garmisch-Partenkirchen', 117, 'Garmisch-Partenkirchen', MARL, 4, 70),
			g('09', 180, 'Garmisch-Partenkirchen', 124, 'Mittenwald', MARL, 1, 85),
			g('09', 575, 'Neustadt a.d.Aisch-Bad Windsheim', 112, 'Bad Windsheim', MARL, 2, 230),
			g('09', 571, 'Ansbach', 193, 'Rothenburg ob der Tauber', HERTEN, 3, 220),
			g('09', 780, 'Oberallgäu', 139, 'Sonthofen', MARL, 2, 0),
			g('14', 524, 'Zwickau', 120, 'Hohenstein-Ernstthal', MARL, 5, 410),
			g('14', 524, 'Zwickau', 180, 'Limbach-Oberfrohna', HERTEN, 2, 415),
			g('14', 628, 'Sächsische Schweiz-Osterzgebirge', 100, 'Dippoldiswalde', MARL, 1, 470),
			g('13', 71, 'Mecklenburgische Seenplatte', 107, 'Neubrandenburg', MARL, 2, 720),
			g('13', 73, 'Vorpommern-Rügen', 75, 'Ribnitz-Damgarten', HERTEN, 1, 760),
			g('07', 131, 'Ahrweiler', 7, 'Bad Neuenahr-Ahrweiler', MARL, 3, 390),
			g('07', 333, 'Donnersbergkreis', 39, 'Kirchheimbolanden', MARL, 1, 300),
			g('08', 326, 'Schwarzwald-Baar-Kreis', 74, 'Villingen-Schwenningen', HERTEN, 4, 130),
			g('15', 84, 'Burgenlandkreis', 550, 'Weißenfels', MARL, 1, 400),
			g('05', 970, 'Siegen-Wittgenstein', 4, 'Bad Berleburg', MARL, 2, 420)
		],
		[MARL, HERTEN]
	);
}

export function datasetUngleich(): SyntheticDataset {
	return finish(
		'ungleich',
		'Sehr ungleiche Gruppen',
		'Eine Gruppe von 80 direkt neben einer einzelnen Person. Die Fläche der Knoten folgt der Anzahl.',
		[
			g('05', 562, 'Recklinghausen', 14, 'Gladbeck', MARL, 46, 480),
			g('05', 562, 'Recklinghausen', 4, 'Castrop-Rauxel', MARL, 30, 485),
			g('05', 554, 'Borken', 8, 'Bocholt', MARL, 4, 520),
			g('01', 54, 'Nordfriesland', 56, 'Husum', MARL, 1, 760),
			g('09', 780, 'Oberallgäu', 139, 'Sonthofen', MARL, 2, 0),
			g('09', 780, 'Oberallgäu', 124, 'Immenstadt', MARL, 1, 8),
			g('14', 524, 'Zwickau', 330, 'Zwickau', MARL, 1, 410),
			g('03', 454, 'Emsland', 32, 'Lingen', MARL, 6, 590)
		],
		[MARL]
	);
}

export function datasetDreiWohnorte(): SyntheticDataset {
	return finish(
		'drei-wohnorte',
		'Drei dicht benachbarte Wohnorte',
		'Herten, Recklinghausen und Oer-Erkenschwick liegen wenige Kilometer auseinander. Auf der Karte werden sie unter 48 px Abstand zu einem Sammelknoten.',
		[
			g('09', 780, 'Oberallgäu', 139, 'Sonthofen', HERTEN, 2, 0),
			g('09', 187, 'Rosenheim', 150, 'Rosenheim', HERTEN, 3, 150),
			g('14', 524, 'Zwickau', 330, 'Zwickau', HERTEN, 2, 410),
			g('09', 780, 'Oberallgäu', 124, 'Immenstadt', RECKLINGHAUSEN, 1, 8),
			g('08', 436, 'Ravensburg', 64, 'Ravensburg', RECKLINGHAUSEN, 4, 60),
			g('03', 454, 'Emsland', 32, 'Lingen', RECKLINGHAUSEN, 5, 590),
			g('06', 631, 'Fulda', 9, 'Fulda', RECKLINGHAUSEN, 2, 320),
			g('14', 625, 'Bautzen', 20, 'Bautzen', OER, 3, 500),
			g('09', 780, 'Oberallgäu', 139, 'Sonthofen', OER, 1, 0),
			g('12', 73, 'Uckermark', 452, 'Prenzlau', DORSTEN, 2, 640),
			g('09', 262, 'Passau', 0, 'Passau', DORSTEN, 1, 260),
			g('16', 67, 'Gotha', 29, 'Gotha', GELSENKIRCHEN, 6, 330),
			g('05', 554, 'Borken', 8, 'Bocholt', GELSENKIRCHEN, 3, 520)
		],
		[HERTEN, RECKLINGHAUSEN, OER, DORSTEN, GELSENKIRCHEN]
	);
}

export function datasetHerkunftAusserhalb(): SyntheticDataset {
	return finish(
		'herkunft-ausserhalb',
		'Eigene Herkunft außerhalb der fünf größten',
		'Bayern ist nur die siebtgrößte Gruppe. Die Miniatur auf der Karte muss sie trotzdem zeigen.',
		[
			g('05', 554, 'Borken', 8, 'Bocholt', MARL, 14, 520),
			g('03', 454, 'Emsland', 32, 'Lingen', MARL, 11, 590),
			g('14', 524, 'Zwickau', 330, 'Zwickau', MARL, 9, 410),
			g('06', 631, 'Fulda', 9, 'Fulda', MARL, 8, 320),
			g('12', 73, 'Uckermark', 452, 'Prenzlau', MARL, 6, 640),
			g('16', 67, 'Gotha', 29, 'Gotha', MARL, 4, 330),
			g('09', 780, 'Oberallgäu', 139, 'Sonthofen', MARL, 1, 0),
			g('13', 72, 'Rostock', 43, 'Güstrow', MARL, 1, 700),
			g('07', 131, 'Ahrweiler', 7, 'Bad Neuenahr-Ahrweiler', MARL, 1, 390)
		],
		[MARL]
	);
}

export function datasetLeer(): SyntheticDataset {
	return finish('leer', 'Leerer Umkreis', 'Niemand im Umkreis von 20 km. Statt einer leeren Karte erscheint eine Erklärung.', [], [MARL]);
}

/** Beispielnetz der Startseite: klein genug zum Erfassen, groß genug zum Ausprobieren. */
export function datasetBeispiel(): SyntheticDataset {
	return finish(
		'beispiel',
		'Beispiel',
		'Ein kleines Netz mit erfundenen Daten.',
		[
			g('09', 780, 'Oberallgäu', 139, 'Sonthofen', MARL, 2, 0),
			g('09', 780, 'Oberallgäu', 124, 'Immenstadt', MARL, 1, 8),
			g('09', 780, 'Oberallgäu', 133, 'Oberstdorf', MARL, 1, 13),
			g('09', 187, 'Rosenheim', 150, 'Rosenheim', MARL, 3, 150),
			g('09', 262, 'Passau', 0, 'Passau', MARL, 2, 260),
			g('09', 564, 'Nürnberg', 0, 'Nürnberg', MARL, 3, 240),
			g('05', 554, 'Borken', 8, 'Bocholt', MARL, 4, 520),
			g('05', 970, 'Siegen-Wittgenstein', 40, 'Siegen', MARL, 3, 420),
			g('14', 524, 'Zwickau', 330, 'Zwickau', MARL, 2, 410),
			g('14', 625, 'Bautzen', 20, 'Bautzen', MARL, 1, 500),
			g('08', 436, 'Ravensburg', 64, 'Ravensburg', MARL, 2, 60),
			g('03', 454, 'Emsland', 32, 'Lingen', MARL, 2, 590),
			g('16', 67, 'Gotha', 29, 'Gotha', MARL, 1, 330)
		],
		[MARL]
	);
}

export function allDatasets(): SyntheticDataset[] {
	return [
		datasetKlein(),
		datasetMittel(),
		datasetGross(),
		datasetLangeNamen(),
		datasetUngleich(),
		datasetDreiWohnorte(),
		datasetHerkunftAusserhalb(),
		datasetLeer()
	];
}
