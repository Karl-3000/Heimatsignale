import { describe, expect, it } from 'vitest';
import { countLabelOverlaps, estimateTextWidth, placeLabels, shortLabel, shortenName, type LabelInput } from './labels';
import { FEDERAL_STATES, stateName, stateShort } from './states';

describe('Bundesländer', () => {
	it('kennt alle 16 mit Namen und Kurzform', () => {
		expect(FEDERAL_STATES).toHaveLength(16);
		const shorts = new Set(FEDERAL_STATES.map((s) => s.short));
		expect(shorts.size).toBe(16);
		for (const s of FEDERAL_STATES) {
			expect(s.code).toMatch(/^\d{2}$/);
			expect(s.short.length).toBeLessThanOrEqual(3);
		}
		expect(stateShort('05')).toBe('NRW');
		expect(stateName('09')).toBe('Bayern');
		expect(stateName('99')).toBe('Bundesland 99');
	});
});

describe('shortenName', () => {
	it('lässt kurze Namen unverändert', () => {
		expect(shortenName('Sonthofen')).toBe('Sonthofen');
		expect(shortenName('Marl')).toBe('Marl');
	});

	it('kürzt Doppelnamen auf den Anfangsbuchstaben des zweiten Teils', () => {
		expect(shortenName('Garmisch-Partenkirchen')).toBe('Garmisch-P.');
		expect(shortenName('Hohenstein-Ernstthal')).toBe('Hohenstein-E.');
		expect(shortenName('Villingen-Schwenningen')).toBe('Villingen-S.');
	});

	it('entfernt Zusätze und kürzt lange Einzelwörter mit Auslassungszeichen', () => {
		expect(shortenName('Landkreis Rosenheim')).toBe('Rosenheim');
		expect(shortenName('Kirchheimbolanden')).toBe('Kirchheimbo…');
		expect(shortenName('Rothenburg ob der Tauber')).toBe('Rothenburg…');
		expect(shortenName('Mecklenburgische Seenplatte').length).toBeLessThanOrEqual(13);
	});

	it('liefert nie einen leeren Text', () => {
		for (const name of ['A', 'Sankt Wendel', 'Neustadt a.d.Aisch-Bad Windsheim', 'Sächsische Schweiz-Osterzgebirge']) {
			const s = shortenName(name);
			expect(s.length).toBeGreaterThan(0);
			expect(s.length).toBeLessThanOrEqual(15);
		}
	});
});

describe('shortLabel', () => {
	it('nimmt beim Bundesland das Kürzel', () => {
		expect(shortLabel('state', '05', 'Nordrhein-Westfalen')).toBe('NRW');
		expect(shortLabel('place', '09180117', 'Garmisch-Partenkirchen')).toBe('Garmisch-P.');
	});
});

describe('estimateTextWidth', () => {
	it('wächst mit der Länge und der Schriftgröße', () => {
		expect(estimateTextWidth('Bayern')).toBeGreaterThan(estimateTextWidth('Bay'));
		expect(estimateTextWidth('Bayern', 16)).toBeGreaterThan(estimateTextWidth('Bayern', 12));
		expect(estimateTextWidth('')).toBe(0);
	});
});

function ring(count: number, radius: number, name: (i: number) => string): LabelInput[] {
	return Array.from({ length: count }, (_, i) => {
		const angle = (i / count) * Math.PI * 2;
		return {
			id: `n${i}`,
			x: radius * Math.cos(angle),
			y: radius * Math.sin(angle),
			r: 8,
			full: name(i),
			short: shortenName(name(i)),
			priority: count - i
		};
	});
}

describe('placeLabels', () => {
	it('platziert bei genug Platz alle vollen Namen ohne Überlappung', () => {
		const labels = placeLabels(ring(8, 150, (i) => `Ort ${i}`));
		expect([...labels.values()].every((l) => l.variant === 'full')).toBe(true);
		expect(countLabelOverlaps(labels.values())).toBe(0);
	});

	it('weicht bei Platzmangel auf Kurzformen aus und blendet notfalls aus, überlappt aber nie', () => {
		const inputs = ring(40, 150, () => 'Garmisch-Partenkirchen');
		const labels = placeLabels(inputs);
		const variants = [...labels.values()].map((l) => l.variant);
		expect(countLabelOverlaps(labels.values())).toBe(0);
		expect(variants.includes('short') || variants.includes('hidden')).toBe(true);
		expect(labels.size).toBe(40);
	});

	it('legt keine Beschriftung über einen fremden Knoten', () => {
		const inputs = ring(24, 150, (i) => `Hohenstein-Ernstthal ${i}`);
		const labels = placeLabels(inputs);
		for (const l of labels.values()) {
			if (!l.box) continue;
			for (const n of inputs) {
				if (n.id === l.id) continue;
				const inside = n.x > l.box.x0 && n.x < l.box.x1 && n.y > l.box.y0 && n.y < l.box.y1;
				expect(inside).toBe(false);
			}
		}
	});

	it('platziert höhere Priorität zuerst', () => {
		const a: LabelInput = { id: 'a', x: 0, y: 0, r: 5, full: 'Langer Name Eins', short: 'Eins', priority: 1 };
		const b: LabelInput = { id: 'b', x: 0, y: 12, r: 5, full: 'Langer Name Zwei', short: 'Zwei', priority: 2 };
		const labels = placeLabels([a, b]);
		expect(labels.get('b')!.variant).toBe('full');
		expect(countLabelOverlaps(labels.values())).toBe(0);
	});

	it('hält die Zeichenfläche ein', () => {
		const labels = placeLabels([{ id: 'a', x: 95, y: 0, r: 4, full: 'Mecklenburg-Vorpommern', short: 'MV', priority: 1 }], { halfExtent: 100 });
		const l = labels.get('a')!;
		expect(l.variant === 'hidden' || (l.box !== null && l.box.x1 <= 100 && l.box.x0 >= -100)).toBe(true);
	});
});
