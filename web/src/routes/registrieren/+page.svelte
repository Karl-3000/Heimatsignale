<script lang="ts">
	import { tick } from 'svelte';
	import LocateFixed from '@lucide/svelte/icons/locate-fixed';
	import { ApiError, errorMessage } from '$lib/api/client';
	import { nearestPlace, register, resendVerification } from '$lib/api/endpoints';
	import { session } from '$lib/api/session.svelte';
	import type { Place } from '$lib/api/types';
	import { PowRun } from '$lib/pow/run.svelte';
	import Brand from '$lib/ui/Brand.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
	import Field from '$lib/ui/Field.svelte';
	import FormPage from '$lib/ui/FormPage.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import PlaceSearch from '$lib/ui/PlaceSearch.svelte';
	import PowProgress from '$lib/ui/PowProgress.svelte';
	import { isAdult, roundCoordinate, toIsoDate } from '$lib/util/format';

	const STEPS = ['Konto', 'Geburtsdatum', 'Heimatort', 'Wohnort', 'Zusammenfassung'] as const;
	const FIELD_STEP: Record<string, number> = { email: 1, password: 1, birth_date: 2, home_ags: 3, residence_ags: 4, invite_code: 5, accept_terms: 5 };

	let step = $state(1);
	let sent = $state(false);
	let heading = $state<HTMLElement | null>(null);

	let email = $state('');
	let password = $state('');
	let day = $state('');
	let month = $state('');
	let year = $state('');
	let home = $state<Place | null>(null);
	let residence = $state<Place | null>(null);
	let inviteCode = $state('');
	let acceptTerms = $state(false);

	let errors = $state<Record<string, string>>({});
	let failure = $state<string | null>(null);
	let busy = $state(false);
	const pow = new PowRun();

	// Standortfreigabe: nur zum Vorbelegen. Die Koordinaten bleiben in dieser Funktion,
	// werden auf zwei Nachkommastellen gerundet gesendet und nirgends gespeichert.
	let locating = $state(false);
	let locateError = $state<string | null>(null);
	let suggestion = $state<Place | null>(null);

	let resending = $state(false);
	let resent = $state(false);

	const birthDate = $derived(toIsoDate(Number(year), Number(month), Number(day)));

	async function goTo(next: number): Promise<void> {
		step = next;
		failure = null;
		await tick();
		heading?.focus();
	}

	function validate(current: number): boolean {
		const next: Record<string, string> = {};
		if (current === 1) {
			if (!/^\S+@\S+\.\S+$/.test(email.trim())) next.email = 'Bitte gib eine gültige E-Mail-Adresse ein.';
			if (password.length < 12) next.password = 'Das Passwort braucht mindestens 12 Zeichen.';
		} else if (current === 2) {
			if (!birthDate) next.birth_date = 'Bitte gib ein gültiges Datum ein, zum Beispiel 17 3 1994.';
			else if (!isAdult(Number(year), Number(month), Number(day))) next.birth_date = 'Der Dienst ist erst ab 18 Jahren nutzbar.';
		} else if (current === 3) {
			if (!home) next.home_ags = 'Bitte wähle deinen Heimatort aus der Liste.';
		} else if (current === 4) {
			if (!residence) next.residence_ags = 'Bitte wähle deinen Wohnort aus der Liste.';
		} else if (current === 5) {
			if (!acceptTerms) next.accept_terms = 'Bitte stimme den Nutzungsbedingungen zu.';
		}
		errors = next;
		return Object.keys(next).length === 0;
	}

	async function next(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (!validate(step)) return;
		if (step < 5) await goTo(step + 1);
		else await submit();
	}

	async function send(): Promise<void> {
		const solved = await pow.solve('register');
		await register({
			email: email.trim(),
			password,
			birth_date: birthDate as string,
			home_ags: (home as Place).ags,
			residence_ags: (residence as Place).ags,
			invite_code: inviteCode.trim() || null,
			accept_terms: acceptTerms,
			pow: solved
		});
	}

	async function submit(): Promise<void> {
		if (busy) return;
		busy = true;
		failure = null;
		try {
			try {
				await send();
			} catch (error) {
				// Über dem IP-Limit verlangt der Server eine schwerere Aufgabe: neu holen, einmal wiederholen.
				if (error instanceof ApiError && (error.code === 'pow_harder_required' || error.code === 'pow_invalid')) await send();
				else throw error;
			}
			sent = true;
			await tick();
			heading?.focus();
		} catch (error) {
			if (error instanceof ApiError && Object.keys(error.fields).length > 0) {
				errors = error.fields;
				const target = Math.min(...Object.keys(error.fields).map((key) => FIELD_STEP[key] ?? 5));
				if (target !== step) {
					await goTo(target);
					failure = 'Bitte prüfe die markierte Angabe.';
				}
			} else {
				failure = errorMessage(error);
			}
		} finally {
			busy = false;
		}
	}

	function locate(): void {
		locateError = null;
		suggestion = null;
		if (!('geolocation' in navigator)) {
			locateError = 'Dein Browser bietet keine Standortfreigabe an. Bitte suche deinen Wohnort über das Feld.';
			return;
		}
		locating = true;
		navigator.geolocation.getCurrentPosition(
			(position) => {
				const lat = roundCoordinate(position.coords.latitude);
				const lon = roundCoordinate(position.coords.longitude);
				nearestPlace(lat, lon)
					.then((result) => {
						suggestion = result.place;
					})
					.catch((error: unknown) => {
						locateError = errorMessage(error);
					})
					.finally(() => {
						locating = false;
					});
			},
			() => {
				locating = false;
				locateError = 'Der Standort ließ sich nicht bestimmen. Bitte suche deinen Wohnort über das Feld.';
			},
			{ enableHighAccuracy: false, maximumAge: 600000, timeout: 15000 }
		);
	}

	function acceptSuggestion(): void {
		residence = suggestion;
		suggestion = null;
		errors = {};
	}

	async function resend(): Promise<void> {
		resending = true;
		failure = null;
		try {
			const solved = await pow.solve('resend');
			await resendVerification(email.trim(), solved);
			resent = true;
		} catch (error) {
			failure = errorMessage(error);
		} finally {
			resending = false;
		}
	}
</script>

<svelte:head>
	<title>Registrieren – {session.siteName}</title>
</svelte:head>

{#if sent}
	<FormPage title="E-Mail unterwegs" wide>
		<div class="grid gap-5" data-testid="register-sent">
			<div class="hs-stage sent-stage" aria-hidden="true"><Brand href={null} tone="stage" markOnly size="lg" /></div>
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<p tabindex="-1" bind:this={heading} class="outline-none">
				Wir haben einen Bestätigungslink an <strong class="break-all">{email.trim()}</strong> geschickt. Öffne ihn, um dein Konto zu aktivieren. Danach
				bekommst du deinen Nickname.
			</p>
			<Notice tone="info">
				<p>Ohne Bestätigung wird das Konto nach 48 Stunden gelöscht. Sieh auch im Spam-Ordner nach.</p>
				<p>Gibt es zu dieser Adresse schon ein Konto, bekommst du stattdessen einen Hinweis per E-Mail.</p>
			</Notice>
			{#if resent}
				<Notice tone="success" testid="register-resent"><p>Die E-Mail wurde noch einmal gesendet.</p></Notice>
			{/if}
			{#if failure}<Notice tone="danger" live><p>{failure}</p></Notice>{/if}
			<PowProgress run={pow} />
			<div class="flex flex-wrap gap-3">
				<Button onclick={resend} loading={resending} testid="register-resend">E-Mail erneut senden</Button>
				<Button href="/anmelden" variant="ghost">Zur Anmeldung</Button>
			</div>
		</div>
	</FormPage>
{:else}
	<FormPage title="Registrieren" wide quietTitle>
		<p class="progress hs-num" data-testid="register-progress">Schritt {step} von {STEPS.length}</p>
		<ol class="dots" aria-hidden="true">
			{#each STEPS as name, index (name)}
				<li class:done={index + 1 < step} class:current={index + 1 === step}></li>
			{/each}
		</ol>

		<form class="grid gap-5" onsubmit={next} novalidate data-testid="register-form" data-step={step}>
			<h2 tabindex="-1" bind:this={heading} class="step-title" data-testid="register-step-title">{STEPS[step - 1]}</h2>

			{#if step === 1}
				<Field label="E-Mail-Adresse" type="email" bind:value={email} autocomplete="email" inputmode="email" required error={errors.email} hint="Nur für Anmeldung und Benachrichtigungen. Niemand sonst sieht sie." testid="register-email" />
				<Field
					label="Passwort"
					type="password"
					bind:value={password}
					autocomplete="new-password"
					required
					error={errors.password}
					hint="Mindestens 12 Zeichen. Ein Satz aus mehreren Wörtern ist gut zu merken."
					testid="register-password"
				/>
			{:else if step === 2}
				<fieldset class="date" aria-describedby="geburt-hinweis{errors.birth_date ? ' geburt-fehler' : ''}">
					<legend>Geburtsdatum</legend>
					<p id="geburt-hinweis" class="text-sm text-ink-muted">
						Wir prüfen damit, ob du 18 bist. Gespeichert wird nur das Geburtsjahr. Andere sehen eine ungefähre Altersspanne, zum Beispiel „etwa 25–34“.
					</p>
					<div class="date-fields">
						<label>
							<span>Tag</span>
							<input type="text" inputmode="numeric" maxlength="2" autocomplete="bday-day" bind:value={day} aria-invalid={errors.birth_date ? 'true' : undefined} data-testid="register-day" />
						</label>
						<label>
							<span>Monat</span>
							<input type="text" inputmode="numeric" maxlength="2" autocomplete="bday-month" bind:value={month} aria-invalid={errors.birth_date ? 'true' : undefined} data-testid="register-month" />
						</label>
						<label class="year">
							<span>Jahr</span>
							<input type="text" inputmode="numeric" maxlength="4" autocomplete="bday-year" bind:value={year} aria-invalid={errors.birth_date ? 'true' : undefined} data-testid="register-year" />
						</label>
					</div>
					{#if errors.birth_date}<p id="geburt-fehler" class="field-error" role="alert">{errors.birth_date}</p>{/if}
				</fieldset>
			{:else if step === 3}
				<p class="text-ink-muted">Der Ort, aus dem du stammst: eine Gemeinde oder Stadt in Deutschland, kein Landkreis und kein Bundesland.</p>
				<PlaceSearch label="Heimatort" bind:value={home} error={errors.home_ags} testid="register-home" />
			{:else if step === 4}
				<p class="text-ink-muted">Die Gemeinde oder Stadt, in der du jetzt lebst. Um diesen Ort liegt dein Umkreis: zuerst {session.defaultRadius} km, auf Wunsch bis {session.maxRadius} km.</p>
				<PlaceSearch label="Wohnort" bind:value={residence} error={errors.residence_ags} testid="register-residence" />
				{#if !residence}
					<Card tone="sunken">
						<div class="grid gap-3">
							<p class="text-sm">
								Du kannst den Wohnort mit deinem Standort vorbelegen. Der Standort wird dafür einmal auf etwa einen Kilometer gerundet abgefragt und
								nicht gespeichert. Den Ort bestätigst du selbst.
							</p>
							<div><Button icon={LocateFixed} size="sm" onclick={locate} loading={locating} testid="register-locate">Standort zum Vorbelegen verwenden</Button></div>
							{#if suggestion}
								<div class="grid gap-2" role="group" aria-label="Vorschlag für den Wohnort" data-testid="register-suggestion">
									<p>
										Vorschlag: <strong>{suggestion.name}</strong> ({suggestion.district_name}, {suggestion.state_name}). Stimmt das?
									</p>
									<div class="flex flex-wrap gap-2">
										<Button variant="primary" size="sm" onclick={acceptSuggestion} testid="register-suggestion-accept">Ja, {suggestion.name} ist mein Wohnort</Button>
										<Button size="sm" onclick={() => (suggestion = null)}>Nein, selbst suchen</Button>
									</div>
								</div>
							{/if}
							{#if locateError}<p class="field-error" role="alert">{locateError}</p>{/if}
						</div>
					</Card>
				{/if}
			{:else}
				<dl class="summary" data-testid="register-summary">
					<div>
						<dt>E-Mail</dt>
						<dd class="break-all">{email.trim()}</dd>
					</div>
					<div>
						<dt>Heimatort</dt>
						<dd>{home?.name} <span class="quiet">({home?.district_name}, {home?.state_name})</span></dd>
					</div>
					<div>
						<dt>Wohnort</dt>
						<dd>{residence?.name} <span class="quiet">({residence?.district_name}, {residence?.state_name})</span></dd>
					</div>
				</dl>
				<Notice tone="warning" title="Heimatort und Wohnort legst du einmal fest" testid="register-places-note">
					<p>Nach der Registrierung kannst du beide nicht mehr selbst ändern. Eine Änderung geht nur über einen Antrag, den ein Admin prüft.</p>
				</Notice>
				<Field label="Einladungscode" bind:value={inviteCode} autocomplete="off" autocapitalize="characters" error={errors.invite_code} hint="Nur nötig, wenn du einen Code von einer Veranstaltung hast." testid="register-invite" />
				<div class="grid gap-1">
					<label class="check">
						<input type="checkbox" bind:checked={acceptTerms} aria-invalid={errors.accept_terms ? 'true' : undefined} aria-describedby={errors.accept_terms ? 'agb-fehler' : undefined} data-testid="register-terms" />
						<span>
							Ich stimme den <a href="/nutzungsbedingungen" target="_blank" rel="noopener">Nutzungsbedingungen</a> zu und habe die
							<a href="/datenschutz" target="_blank" rel="noopener">Datenschutzerklärung</a> gelesen. Ich bin mindestens 18 Jahre alt.
						</span>
					</label>
					{#if errors.accept_terms}<p id="agb-fehler" class="field-error" role="alert">{errors.accept_terms}</p>{/if}
				</div>
			{/if}

			{#if failure}<Notice tone="danger" live testid="register-error"><p>{failure}</p></Notice>{/if}
			<PowProgress run={pow} />

			<div class="actions">
				{#if step > 1}
					<Button onclick={() => void goTo(step - 1)} disabled={busy} testid="register-back">Zurück</Button>
				{:else}
					<span></span>
				{/if}
				<Button type="submit" variant="primary" loading={busy} testid="register-next">{step < 5 ? 'Weiter' : 'Konto anlegen'}</Button>
			</div>
		</form>

		<p class="text-sm text-ink-muted">
			Schon registriert? <a href="/anmelden">Anmelden</a>. Was andere von dir sehen, zeigt die <a href="/vorschau">Vorschau</a>.
		</p>
	</FormPage>
{/if}

<style>
	.progress {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
		margin-bottom: calc(var(--hs-space-4) * -1);
	}

	/* Dünne Fortschrittslinie in fünf Abschnitten. */
	.dots {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: var(--hs-space-1);
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.dots li {
		height: 3px;
		border-radius: var(--hs-radius-full);
		background: var(--hs-sunken);
		transition: background-color var(--hs-duration-base) var(--hs-ease-standard);
	}

	.dots li.done,
	.dots li.current {
		background: var(--hs-accent);
	}

	.step-title {
		font-size: clamp(2rem, 5vw, 2.75rem);
		line-height: var(--hs-leading-display);
		letter-spacing: var(--hs-tracking-display);
		outline: none;
	}

	.date {
		display: grid;
		gap: var(--hs-space-3);
		border: 0;
		margin: 0;
		padding: 0;
		min-width: 0;
	}

	.date legend {
		padding: 0;
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
	}

	.date-fields {
		display: flex;
		gap: var(--hs-space-3);
	}

	.date-fields label {
		display: grid;
		gap: var(--hs-space-2);
		width: 5rem;
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.date-fields label.year {
		width: 7.5rem;
	}

	.date-fields input {
		min-height: 3.5rem;
		width: 100%;
		padding: 0 var(--hs-space-4);
		border: 0;
		border-radius: var(--hs-radius-md);
		background: var(--hs-field);
		box-shadow: inset 0 0 0 1px var(--hs-line-strong);
		color: var(--hs-ink);
		font-family: var(--hs-font-display);
		font-weight: var(--hs-weight-display);
		font-size: var(--hs-text-xl);
		font-variant-numeric: tabular-nums;
	}

	.date-fields input:focus-visible {
		outline: none;
		background: var(--hs-raised);
		box-shadow: inset 0 0 0 2px var(--hs-focus);
	}

	.date-fields input[aria-invalid='true'] {
		box-shadow: inset 0 0 0 2px var(--hs-danger);
	}

	.field-error {
		font-size: var(--hs-text-sm);
		color: var(--hs-danger);
		font-weight: var(--hs-weight-strong);
	}

	/* Zusammenfassung als saubere Definitionsliste, ohne Kasten. */
	.summary {
		display: grid;
	}

	.summary > div {
		display: grid;
		gap: 0.125rem;
		padding: var(--hs-space-4) 0;
		border-top: 1px solid var(--hs-line);
	}

	.summary > div:last-child {
		border-bottom: 1px solid var(--hs-line);
	}

	.summary dt {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.summary dd {
		font-size: var(--hs-text-lg);
		font-weight: var(--hs-weight-strong);
	}

	.check {
		display: grid;
		grid-template-columns: 1.375rem minmax(0, 1fr);
		gap: var(--hs-space-3);
		align-items: start;
		cursor: pointer;
	}

	.check input {
		width: 1.375rem;
		height: 1.375rem;
		margin-top: 0.15rem;
		accent-color: var(--hs-accent);
	}

	.actions {
		display: flex;
		justify-content: space-between;
		gap: var(--hs-space-3);
		padding-top: var(--hs-space-2);
	}

	/* Der Moment nach dem Absenden: ein kleines Bühnenbild mit dem Zeichen. */
	.sent-stage {
		display: grid;
		place-items: center;
		min-height: 11rem;
	}

	.quiet {
		color: var(--hs-ink-muted);
	}
</style>
