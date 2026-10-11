/** Anzeigeformate. Alles hier ist frei von Framework-Code. */

const countFormat = new Intl.NumberFormat('de-DE');

export function formatCount(n: number): string {
	return countFormat.format(n);
}

/** Die Altersspanne heißt überall "etwa 25–34" (Projektplan, Abschnitt 4). */
export function formatAge(ageRange: string | null | undefined): string {
	if (!ageRange) return 'Alter unbekannt';
	return `etwa ${ageRange.replace('-', '–')}`;
}

export function personen(n: number): string {
	return n === 1 ? '1 Person' : `${formatCount(n)} Personen`;
}

const MONTHS = [
	'Januar',
	'Februar',
	'März',
	'April',
	'Mai',
	'Juni',
	'Juli',
	'August',
	'September',
	'Oktober',
	'November',
	'Dezember'
];

/** "2026-10" wird zu "Oktober 2026". */
export function formatMemberSince(value: string | null | undefined): string {
	if (!value) return '';
	const m = /^(\d{4})-(\d{2})/.exec(value);
	if (!m) return value;
	const month = MONTHS[Number(m[2]) - 1];
	return month ? `${month} ${m[1]}` : m[1];
}

function pad(n: number): string {
	return n < 10 ? `0${n}` : String(n);
}

/** "17.03.2026" */
export function formatDate(iso: string | Date | null | undefined): string {
	if (!iso) return '';
	const d = typeof iso === 'string' ? new Date(iso) : iso;
	if (Number.isNaN(d.getTime())) return '';
	return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()}`;
}

/** "14:05" */
export function formatTime(iso: string | Date | null | undefined): string {
	if (!iso) return '';
	const d = typeof iso === 'string' ? new Date(iso) : iso;
	if (Number.isNaN(d.getTime())) return '';
	return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Heute nur die Uhrzeit, sonst Datum und Uhrzeit. */
export function formatDateTime(iso: string | null | undefined, now: Date = new Date()): string {
	if (!iso) return '';
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return '';
	const sameDay =
		d.getFullYear() === now.getFullYear() &&
		d.getMonth() === now.getMonth() &&
		d.getDate() === now.getDate();
	return sameDay ? `heute, ${formatTime(d)}` : `${formatDate(d)}, ${formatTime(d)}`;
}

/** Restzeit in Worten: "noch 2 Tage", "noch 5 Stunden", "noch 12 Minuten". */
export function formatRemaining(untilIso: string | null | undefined, now: Date = new Date()): string {
	if (!untilIso) return '';
	const ms = new Date(untilIso).getTime() - now.getTime();
	if (!(ms > 0)) return 'abgelaufen';
	const minutes = Math.ceil(ms / 60000);
	if (minutes < 60) return minutes === 1 ? 'noch 1 Minute' : `noch ${minutes} Minuten`;
	const hours = Math.ceil(minutes / 60);
	if (hours < 48) return hours === 1 ? 'noch 1 Stunde' : `noch ${hours} Stunden`;
	const days = Math.ceil(hours / 24);
	return `noch ${days} Tage`;
}

/** Wartezeit aus retry_after (Sekunden) in Worten. */
export function formatRetryAfter(seconds: number | null | undefined): string {
	if (!seconds || seconds <= 0) return 'in Kürze';
	if (seconds < 90) return 'in etwa einer Minute';
	const minutes = Math.ceil(seconds / 60);
	if (minutes < 90) return `in etwa ${minutes} Minuten`;
	return `in etwa ${Math.ceil(minutes / 60)} Stunden`;
}

/** Volljährigkeit am Stichtag, aus einem vollständigen Geburtsdatum. */
export function isAdult(year: number, month: number, day: number, today: Date = new Date()): boolean {
	let age = today.getFullYear() - year;
	const m = today.getMonth() + 1;
	if (m < month || (m === month && today.getDate() < day)) age--;
	return age >= 18;
}

/** Prüft ein Datum auf Gültigkeit und liefert "JJJJ-MM-TT" oder null. */
export function toIsoDate(year: number, month: number, day: number): string | null {
	if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) return null;
	if (year < 1900 || month < 1 || month > 12 || day < 1 || day > 31) return null;
	const d = new Date(Date.UTC(year, month - 1, day));
	if (d.getUTCFullYear() !== year || d.getUTCMonth() !== month - 1 || d.getUTCDate() !== day) return null;
	return `${year}-${pad(month)}-${pad(day)}`;
}

/** Rundet Koordinaten auf zwei Nachkommastellen (etwa 1 km), bevor sie das Gerät verlassen. */
export function roundCoordinate(value: number): number {
	return Math.round(value * 100) / 100;
}
