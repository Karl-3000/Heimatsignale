import { describe, expect, it } from 'vitest';
import { formatAge, formatCount, formatDate, formatDateTime, formatMemberSince, formatRemaining, formatRetryAfter, isAdult, personen, roundCoordinate, toIsoDate } from './format';

describe('format', () => {
	it('beschriftet das Alter immer mit "etwa"', () => {
		expect(formatAge('25–34')).toBe('etwa 25–34');
		expect(formatAge('25-34')).toBe('etwa 25–34');
		expect(formatAge('65+')).toBe('etwa 65+');
	});

	it('bildet Einzahl und Mehrzahl', () => {
		expect(personen(1)).toBe('1 Person');
		expect(personen(2)).toBe('2 Personen');
		expect(personen(0)).toBe('0 Personen');
		expect(formatCount(1234)).toBe('1.234');
	});

	it('formatiert "Mitglied seit"', () => {
		expect(formatMemberSince('2026-10')).toBe('Oktober 2026');
		expect(formatMemberSince('2026-03')).toBe('März 2026');
		expect(formatMemberSince('')).toBe('');
	});

	it('formatiert Datum und Uhrzeit', () => {
		const now = new Date(2026, 9, 11, 15, 0);
		expect(formatDate(new Date(2026, 2, 7))).toBe('07.03.2026');
		expect(formatDateTime(new Date(2026, 9, 11, 9, 5).toISOString(), now)).toBe('heute, 09:05');
		expect(formatDateTime(new Date(2026, 9, 10, 9, 5).toISOString(), now)).toBe('10.10.2026, 09:05');
		expect(formatDateTime('kein Datum', now)).toBe('');
	});

	it('nennt die Restzeit einer Stummschaltung', () => {
		const now = new Date('2026-10-11T12:00:00Z');
		expect(formatRemaining('2026-10-11T12:30:00Z', now)).toBe('noch 30 Minuten');
		expect(formatRemaining('2026-10-12T11:00:00Z', now)).toBe('noch 23 Stunden');
		expect(formatRemaining('2026-10-13T12:00:00Z', now)).toBe('noch 2 Tage');
		expect(formatRemaining('2026-10-11T11:00:00Z', now)).toBe('abgelaufen');
	});

	it('nennt die Wartezeit bei zu vielen Abfragen', () => {
		expect(formatRetryAfter(30)).toBe('in etwa einer Minute');
		expect(formatRetryAfter(600)).toBe('in etwa 10 Minuten');
		expect(formatRetryAfter(null)).toBe('in Kürze');
	});

	it('prüft die Volljährigkeit taggenau', () => {
		const today = new Date(2026, 9, 11);
		expect(isAdult(2008, 10, 11, today)).toBe(true);
		expect(isAdult(2008, 10, 12, today)).toBe(false);
		expect(isAdult(1990, 1, 1, today)).toBe(true);
	});

	it('baut gültige ISO-Daten und lehnt ungültige ab', () => {
		expect(toIsoDate(1994, 3, 17)).toBe('1994-03-17');
		expect(toIsoDate(2001, 2, 30)).toBeNull();
		expect(toIsoDate(1994, 13, 1)).toBeNull();
		expect(toIsoDate(Number.NaN, 1, 1)).toBeNull();
	});

	it('rundet Koordinaten auf zwei Nachkommastellen', () => {
		expect(roundCoordinate(51.656789)).toBe(51.66);
		expect(roundCoordinate(7.0904)).toBe(7.09);
	});
});
