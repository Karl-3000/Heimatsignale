import { expect, test, type Page } from '@playwright/test';
import { mkdirSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const OUT = process.env.E2E_OUT ?? './bilder';
const MAILS = process.env.E2E_MAIL_DIR ?? '/tmp/heimatsignale-mails';
const DEMO = { email: 'demo@example.org', password: process.env.E2E_DEMO_PASSWORD ?? 'demo-passwort-123' };
const PASSWORD = 'ein-wirklich-langes-passwort';
mkdirSync(OUT, { recursive: true });

let shot = 0;
async function bild(page: Page, name: string) {
	shot += 1;
	await page.screenshot({ path: join(OUT, `${String(shot).padStart(2, '0')}-${name}.jpg`), type: 'jpeg', quality: 70, fullPage: false });
}

const id = (page: Page, testid: string) => page.getByTestId(testid);

function linkAusMail(empfaenger: string, muster: RegExp): string {
	const dateien = readdirSync(MAILS).sort().reverse();
	for (const datei of dateien) {
		const text = readFileSync(join(MAILS, datei), 'utf8').replace(/=\r?\n/g, '').replace(/=3D/g, '=');
		if (!text.includes(empfaenger)) continue;
		const treffer = text.match(muster);
		if (treffer) return treffer[0];
	}
	throw new Error(`Keine E-Mail an ${empfaenger} gefunden`);
}

async function anmelden(page: Page, email: string, password: string) {
	await page.goto('/anmelden');
	await id(page, 'login-email').fill(email);
	await id(page, 'login-password').fill(password);
	await id(page, 'login-submit').click();
	await expect(id(page, 'umkreis-page')).toBeVisible();
}

// Gleichnamige Gemeinden gibt es mehrfach (Marl liegt auch im Landkreis Diepholz),
// deshalb wird die Option über den Landkreis gewählt.
async function ortWaehlen(page: Page, feld: string, suche: string, name: string, kreis: string) {
	await id(page, `${feld}-input`).fill(suche);
	await page.getByTestId(`${feld}-option`).filter({ hasText: name }).filter({ hasText: kreis }).first().click();
	await expect(id(page, `${feld}-selected`)).toContainText(name);
}

test('Durchstich: Registrierung, Herkunftsnetz, Kontaktanfrage, Gespräch, Meldung, Blockierung, Löschung', async ({ browser }) => {
	const email = `neu-${Date.now()}@example.org`;
	const neu = await browser.newContext({ locale: 'de-DE' });
	const page = await neu.newPage();
	const fehler: string[] = [];
	page.on('pageerror', (e) => fehler.push(String(e)));

	// Startseite und Vorschau: vor der Registrierung sichtbar, was andere sehen werden.
	await page.goto('/');
	await expect(id(page, 'landing-register')).toBeVisible();
	await bild(page, 'start');
	await page.goto('/vorschau');
	await expect(id(page, 'preview-card')).toBeVisible();
	await expect(id(page, 'preview-risk')).toBeVisible();
	await bild(page, 'vorschau');

	// Registrierung in fünf Schritten.
	await page.goto('/registrieren');
	await id(page, 'register-email').fill(email);
	await id(page, 'register-password').fill(PASSWORD);
	await id(page, 'register-next').click();
	await expect(id(page, 'register-form')).toHaveAttribute('data-step', '2');
	await id(page, 'register-day').fill('17');
	await id(page, 'register-month').fill('3');
	await id(page, 'register-year').fill('1994');
	await id(page, 'register-next').click();
	await expect(id(page, 'register-form')).toHaveAttribute('data-step', '3');
	await ortWaehlen(page, 'register-home', 'Sonth', 'Sonthofen', 'Oberallgäu');
	await bild(page, 'registrierung-heimatort');
	await id(page, 'register-next').click();
	await expect(id(page, 'register-form')).toHaveAttribute('data-step', '4');
	await ortWaehlen(page, 'register-residence', 'Marl', 'Marl', 'Recklinghausen');
	await id(page, 'register-next').click();
	await expect(id(page, 'register-form')).toHaveAttribute('data-step', '5');
	await expect(id(page, 'register-summary')).toContainText('Sonthofen');
	await expect(id(page, 'register-summary')).toContainText('Recklinghausen');
	await expect(id(page, 'register-places-note')).toBeVisible();
	await id(page, 'register-terms').check();
	await bild(page, 'registrierung-zusammenfassung');
	await id(page, 'register-next').click();
	await expect(id(page, 'register-sent')).toBeVisible({ timeout: 60_000 });
	await bild(page, 'registrierung-gesendet');

	// Bestätigungslink aus der E-Mail, Nickname mit einmaligem Neuwürfeln.
	const link = linkAusMail(email, /\/bestaetigen\?token=[^\s"<>]+/);
	await page.goto(link);
	await expect(id(page, 'nickname')).toBeVisible();
	const ersterName = (await id(page, 'nickname').innerText()).trim();
	expect(ersterName).toMatch(/^[A-ZÄÖÜ][a-zäöüß]+-[A-ZÄÖÜ][a-zäöüß]+-\d{2,3}$/);
	await id(page, 'nickname-reroll').click();
	await expect(id(page, 'nickname')).not.toHaveText(ersterName);
	await bild(page, 'nickname');
	await id(page, 'nickname-confirm').click();

	// Umkreis: Karte mit Wohnort-Knoten, darunter das Herkunftsnetz.
	await expect(id(page, 'umkreis-page')).toBeVisible();
	await expect(id(page, 'network')).toBeVisible();
	await expect(id(page, 'radius-hint')).toBeVisible();
	await page.waitForTimeout(1500);
	await bild(page, 'umkreis');

	// Stufenweise hineinzoomen: Bundesland, Landkreis, Ort. Die eigene Herkunft ist markiert.
	for (const level of ['state', 'district', 'place']) {
		const knoten = page.locator(`[data-testid="network-node"][data-level="${level}"][data-own="true"]`).first();
		await expect(knoten).toBeVisible();
		await knoten.click();
		await page.waitForTimeout(600);
	}
	await expect(id(page, 'people-panel')).toBeVisible();
	await expect(id(page, 'people-link').first()).toBeVisible();
	await id(page, 'network').scrollIntoViewIfNeeded();
	await bild(page, 'netz-aufgeklappt');

	// Listenansicht mit denselben Daten; Auswahl und aufgeklappte Stufen bleiben erhalten.
	await id(page, 'view-toggle-liste').click();
	await expect(id(page, 'origin-tree')).toBeVisible();
	await expect(page.locator('[data-testid="tree-item"][data-level="place"][data-own="true"]').first()).toBeVisible();
	await bild(page, 'listenansicht');
	await id(page, 'view-toggle-netz').click();
	await expect(page.locator('[data-testid="network-node"][data-level="place"][data-own="true"]').first()).toBeVisible();

	// Zweite Person (Demo-Konto) in eigenem Browser-Kontext.
	const zweiter = await browser.newContext({ locale: 'de-DE' });
	const demo = await zweiter.newPage();
	await anmelden(demo, DEMO.email, DEMO.password);
	const sitzung = await (await demo.request.get('/api/session')).json();
	const demoId: string = sitzung.user.id;
	const demoName: string = sitzung.user.nickname;

	// Profil öffnen und Kontaktanfrage senden.
	await expect(id(page, 'people-panel')).toContainText(demoName);
	await id(page, 'people-link').filter({ hasText: demoName }).click();
	await expect(id(page, 'profile-card')).toContainText(demoName);
	await expect(id(page, 'profile-card')).toContainText('etwa');
	await expect(page).toHaveURL(new RegExp(`/profil/${demoId}`));
	await id(page, 'request-body').fill('Hallo, ich komme auch aus Sonthofen und bin neu in Marl.');
	await bild(page, 'profil-anfrage');
	await id(page, 'request-submit').click();
	await expect(id(page, 'profile-outgoing')).toBeVisible();

	// Die Demo-Person nimmt an und antwortet.
	await demo.goto('/anfragen');
	await expect(id(demo, 'request-incoming').first()).toContainText('Sonthofen');
	await bild(demo, 'anfrage-eingegangen');
	await id(demo, 'request-accept').first().click();
	await expect(id(demo, 'conversation-page')).toBeVisible();
	await id(demo, 'message-input').fill('Schön, von dir zu lesen. Wie lange bist du schon hier?');
	await id(demo, 'message-send').click();
	await expect(id(demo, 'message')).toHaveCount(2);

	// Gespräch auf der ersten Seite: lesen, antworten.
	await page.goto('/gespraeche');
	await id(page, 'conversation-item').first().click();
	await expect(id(page, 'message')).toHaveCount(2);
	await id(page, 'message-input').fill('Seit zwei Wochen.');
	await id(page, 'message-send').click();
	await expect(id(page, 'message')).toHaveCount(3);
	await bild(page, 'gespraech');

	// Nachricht melden (Schnappschuss) und danach blockieren.
	await id(page, 'message-report').first().click();
	await expect(id(page, 'report-dialog')).toBeVisible();
	await id(page, 'report-reason-other').check();
	await id(page, 'report-note').fill('Nur ein Test des Meldewegs.');
	await bild(page, 'melden');
	await id(page, 'report-submit').click();
	await expect(id(page, 'report-dialog')).toBeHidden();

	await id(page, 'conversation-block').click();
	await expect(id(page, 'block-dialog')).toBeVisible();
	await id(page, 'block-ok').click();
	await expect(id(page, 'conversations-page')).toBeVisible();
	await expect(id(page, 'conversations-page')).toContainText('nicht mehr verfügbar');

	// Für die blockierte Seite ist das Gespräch sofort beendet und das Profil verschwunden.
	await demo.reload();
	await expect(id(demo, 'conversation-unavailable')).toBeVisible();
	const meineId = (await (await page.request.get('/api/session')).json()).user.id;
	expect((await demo.request.get(`/api/users/${meineId}`)).status()).toBe(404);

	// Einstellungen: Blockliste, dann Konto löschen.
	await page.goto('/einstellungen');
	await expect(id(page, 'block-item')).toHaveCount(1);
	await bild(page, 'einstellungen');
	await id(page, 'delete-open').click();
	await id(page, 'delete-password').fill(PASSWORD);
	await id(page, 'delete-confirm').click();
	await expect(page).toHaveURL(/\/$/);
	expect((await (await page.request.get('/api/session')).json()).authenticated).toBe(false);

	// Das gelöschte Konto kann sich nicht mehr anmelden.
	await page.goto('/anmelden');
	await id(page, 'login-email').fill(email);
	await id(page, 'login-password').fill(PASSWORD);
	await id(page, 'login-submit').click();
	await expect(id(page, 'login-error')).toBeVisible();

	expect(fehler, 'Fehler in der Browser-Konsole').toEqual([]);
	await neu.close();
	await zweiter.close();
});

test('Umkreis auf dem Handy, dunkles Thema, Listenansicht als Standard', async ({ browser }) => {
	const kontext = await browser.newContext({ locale: 'de-DE', viewport: { width: 390, height: 844 }, colorScheme: 'dark', deviceScaleFactor: 2 });
	const page = await kontext.newPage();
	await anmelden(page, DEMO.email, DEMO.password);
	await expect(id(page, 'origin-tree')).toBeVisible();
	await page.waitForTimeout(1000);
	await bild(page, 'handy-umkreis-dunkel');
	await id(page, 'origin-tree').scrollIntoViewIfNeeded();
	await page.locator('[data-testid="tree-item"][data-own="true"]').first().click();
	await bild(page, 'handy-liste-dunkel');
	// Kein waagerechtes Scrollen bei 390 px.
	expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
	await kontext.close();
});

test('Ohne Anmeldung gibt es keine Nutzerdaten, und der Admin-Bereich verlangt den zweiten Faktor', async ({ page }) => {
	await page.goto('/umkreis');
	await expect(page).toHaveURL(/\/anmelden/);
	expect((await page.request.get('/api/nearby/overview')).status()).toBe(401);
	const admin = await page.request.get('/verwaltung/login/');
	expect(admin.status()).toBe(200);
	expect(await admin.text()).toContain('otp_token');
	for (const pfad of ['/datenschutz', '/impressum', '/nutzungsbedingungen']) {
		await page.goto(pfad);
		await expect(id(page, 'legal-draft')).toBeVisible();
	}
	await bild(page, 'rechtstexte-entwurf');
});

test('Umkreis umschalten: 20 km als Standard, 100 km auf Wunsch, Auswahl bleibt erhalten', async ({ browser }) => {
	const kontext = await browser.newContext({ locale: 'de-DE' });
	const page = await kontext.newPage();
	await anmelden(page, DEMO.email, DEMO.password);
	await expect(id(page, 'radius-toggle')).toBeVisible();
	await expect(id(page, 'umkreis-summary')).toContainText('20 km');
	const eng = await (await page.request.get('/api/nearby/overview')).json();

	const antwort = page.waitForResponse((r) => r.url().includes('/api/nearby/overview') && r.url().includes('radius_km=100'));
	await id(page, 'radius-100').click();
	const weit = await (await antwort).json();
	expect(weit.radius_km).toBe(100);
	expect(weit.total).toBeGreaterThan(eng.total);
	expect(weit.residences.length).toBeGreaterThan(eng.residences.length);
	await expect(id(page, 'umkreis-summary')).toContainText('100 km');
	await expect(id(page, 'radius-hint')).toContainText('100 km');
	await page.waitForTimeout(1200);
	await bild(page, 'umkreis-100-km');

	// Auch in der weiten Ansicht lässt sich bis zur Person hineinzoomen.
	for (const level of ['state', 'district', 'place']) {
		await page.locator(`[data-testid="network-node"][data-level="${level}"][data-own="true"]`).first().click();
		await page.waitForTimeout(600);
	}
	await expect(id(page, 'people-panel')).toBeVisible();

	// Die Auswahl bleibt nach dem Neuladen erhalten und lässt sich zurückstellen.
	await page.reload();
	await expect(id(page, 'umkreis-summary')).toContainText('100 km');
	await id(page, 'radius-20').click();
	await expect(id(page, 'umkreis-summary')).toContainText('20 km');
	expect((await page.request.get('/api/nearby/overview?radius_km=55')).status()).toBe(422);
	await kontext.close();
});
