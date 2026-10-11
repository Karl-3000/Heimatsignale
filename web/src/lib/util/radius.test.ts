import { describe, expect, it } from 'vitest';
import { largestRadius, radiusOptions, resolveRadius } from './radius';

describe('Umkreis-Wahl', () => {
	it('bereinigt und sortiert die Auswahl und nimmt den Standardwert auf', () => {
		expect(radiusOptions([100, 20], 20)).toEqual([20, 100]);
		expect(radiusOptions(undefined, 20)).toEqual([20]);
		expect(radiusOptions([100, 100, -5, Number.NaN], 20)).toEqual([20, 100]);
	});

	it('übernimmt eine gespeicherte Wahl nur, wenn der Server sie anbietet', () => {
		expect(resolveRadius('100', [20, 100], 20)).toBe(100);
		expect(resolveRadius(100, [20, 100], 20)).toBe(100);
		expect(resolveRadius('50', [20, 100], 20)).toBe(20);
		expect(resolveRadius('100', [20], 20)).toBe(20);
		expect(resolveRadius(null, [20, 100], 20)).toBe(20);
		expect(resolveRadius('unsinn', [20, 100], 20)).toBe(20);
	});

	it('kennt den größten Umkreis', () => {
		expect(largestRadius([20, 100], 20)).toBe(100);
		expect(largestRadius([], 20)).toBe(20);
	});
});
