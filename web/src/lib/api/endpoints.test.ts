import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { setFetch } from './client';
import { getOrigins, getOverview, getPeople } from './endpoints';

let urls: string[] = [];

beforeEach(() => {
	urls = [];
	setFetch(async (url) => {
		urls.push(url);
		return new Response(JSON.stringify({ items: [] }), { status: 200, headers: { 'Content-Type': 'application/json' } });
	});
});

afterEach(() => {
	setFetch(null);
});

describe('Umkreis-Abfragen', () => {
	it('geben den gewählten Umkreis an alle drei Endpunkte weiter', async () => {
		await getOverview(100);
		await getOrigins('all', 'district', '09', 100);
		await getOrigins('05562024', 'place', '09780', 100);
		await getPeople('all', '09780139', 2, 100);
		expect(urls).toEqual([
			'/api/nearby/overview?radius_km=100',
			'/api/nearby/origins?residence=all&level=district&parent=09&radius_km=100',
			'/api/nearby/origins?residence=05562024&level=place&parent=09780&radius_km=100',
			'/api/nearby/people?residence=all&home=09780139&page=2&radius_km=100'
		]);
	});

	it('lassen den Parameter weg, wenn kein Umkreis gewählt ist (Standard des Servers)', async () => {
		await getOverview();
		await getOrigins('all', 'district', '09');
		await getPeople('all', '09780139', 1);
		expect(urls).toEqual([
			'/api/nearby/overview',
			'/api/nearby/origins?residence=all&level=district&parent=09',
			'/api/nearby/people?residence=all&home=09780139&page=1'
		]);
	});

	it('übergeben nie eine Suchmitte oder Koordinaten', async () => {
		await getOverview(20);
		await getPeople('all', '09780139', 1, 20);
		for (const url of urls) expect(/lat|lon|center/.test(url)).toBe(false);
	});
});
