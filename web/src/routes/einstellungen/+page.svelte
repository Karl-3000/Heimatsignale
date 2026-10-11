<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import LogOut from '@lucide/svelte/icons/log-out';
	import { errorMessage, isApiError } from '$lib/api/client';
	import { changePassword, createPlaceChange, deleteAccount, listBlocks, listPlaceChanges, logout, unblockUser } from '$lib/api/endpoints';
	import { inbox } from '$lib/api/inbox.svelte';
	import { session } from '$lib/api/session.svelte';
	import type { BlockEntry, Place, PlaceChange, PlaceChangeField, PublicUser } from '$lib/api/types';
	import { umkreis } from '$lib/network/umkreis.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
	import Dialog from '$lib/ui/Dialog.svelte';
	import Field from '$lib/ui/Field.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import PersonSummary from '$lib/ui/PersonSummary.svelte';
	import PlaceSearch from '$lib/ui/PlaceSearch.svelte';
	import ReportDialog from '$lib/ui/ReportDialog.svelte';
	import ThemeToggle from '$lib/ui/ThemeToggle.svelte';
	import { toasts } from '$lib/ui/toast.svelte';
	import { formatDate } from '$lib/util/format';

	const me = $derived(session.user);
	const asOthersSee = $derived<PublicUser | null>(
		me && me.home && me.residence
			? { id: me.id, nickname: me.nickname, age_range: me.age_range, home: me.home, residence: { ags: me.residence.ags, name: me.residence.name }, member_since: me.member_since }
			: null
	);

	/* Ortsänderungen */
	let changes = $state.raw<PlaceChange[]>([]);
	let changeField = $state<PlaceChangeField | null>(null);
	let newPlace = $state<Place | null>(null);
	let changeBusy = $state(false);
	let changeError = $state<string | null>(null);

	const pending = $derived(new Set(changes.filter((c) => c.decision === null).map((c) => c.field)));

	/* Blockliste */
	let blocks = $state.raw<BlockEntry[]>([]);
	let blocksError = $state<string | null>(null);
	let unblockingId = $state<string | null>(null);
	let reportTarget = $state<BlockEntry | null>(null);
	let reportOpen = $state(false);

	/* Passwort */
	let currentPassword = $state('');
	let newPassword = $state('');
	let repeatPassword = $state('');
	let passwordBusy = $state(false);
	let passwordErrors = $state<Record<string, string>>({});
	let passwordFailure = $state<string | null>(null);

	/* Abmelden und Löschen */
	let loggingOut = $state(false);
	let deleteOpen = $state(false);
	let deletePassword = $state('');
	let deleteBusy = $state(false);
	let deleteError = $state<string | null>(null);

	async function loadChanges(): Promise<void> {
		try {
			changes = (await listPlaceChanges()).items;
		} catch {
			/* Die Liste ist eine Zusatzinformation; die Seite bleibt benutzbar. */
		}
	}

	async function loadBlocks(): Promise<void> {
		try {
			blocks = (await listBlocks()).items;
			blocksError = null;
		} catch (error) {
			blocksError = errorMessage(error);
		}
	}

	onMount(() => {
		void loadChanges();
		void loadBlocks();
	});

	function openChange(field: PlaceChangeField): void {
		changeField = changeField === field ? null : field;
		newPlace = null;
		changeError = null;
	}

	async function submitChange(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (!changeField || changeBusy) return;
		if (!newPlace) {
			changeError = 'Bitte wähle die neue Gemeinde aus der Liste.';
			return;
		}
		changeBusy = true;
		changeError = null;
		try {
			await createPlaceChange(changeField, newPlace.ags);
			toasts.success('Antrag gestellt. Ein Admin prüft ihn.');
			changeField = null;
			newPlace = null;
			await loadChanges();
		} catch (error) {
			if (isApiError(error) && error.code === 'change_pending') {
				changeError = 'Für diesen Ort läuft bereits ein Antrag. Bitte warte die Entscheidung ab.';
				await loadChanges();
			} else if (isApiError(error) && error.fields.new_ags) changeError = error.fields.new_ags;
			else changeError = errorMessage(error);
		} finally {
			changeBusy = false;
		}
	}

	async function unblock(entry: BlockEntry): Promise<void> {
		unblockingId = entry.user_id;
		try {
			await unblockUser(entry.user_id);
			toasts.success(entry.nickname ? `Blockierung von ${entry.nickname} aufgehoben.` : 'Blockierung aufgehoben.');
			umkreis.reset();
		} catch (error) {
			toasts.error(errorMessage(error));
		} finally {
			unblockingId = null;
			await loadBlocks();
		}
	}

	async function submitPassword(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (passwordBusy) return;
		passwordErrors = {};
		passwordFailure = null;
		const next: Record<string, string> = {};
		if (!currentPassword) next.current_password = 'Bitte gib dein aktuelles Passwort ein.';
		if (newPassword.length < 12) next.new_password = 'Das neue Passwort braucht mindestens 12 Zeichen.';
		else if (newPassword !== repeatPassword) next.repeat = 'Die beiden Eingaben stimmen nicht überein.';
		if (Object.keys(next).length > 0) {
			passwordErrors = next;
			return;
		}
		passwordBusy = true;
		try {
			await changePassword(currentPassword, newPassword);
			currentPassword = '';
			newPassword = '';
			repeatPassword = '';
			toasts.success('Passwort geändert.');
			// Ein Passwortwechsel kann die Sitzung erneuern; der CSRF-Token wird neu gelesen.
			await session.refresh();
		} catch (error) {
			if (isApiError(error) && Object.keys(error.fields).length > 0) passwordErrors = error.fields;
			else passwordFailure = errorMessage(error);
		} finally {
			passwordBusy = false;
		}
	}

	async function handleLogout(): Promise<void> {
		loggingOut = true;
		try {
			await logout();
		} catch {
			/* Die Sitzung wird unten in jedem Fall neu gelesen. */
		}
		inbox.reset();
		umkreis.reset();
		await session.refresh();
		loggingOut = false;
		await goto('/');
	}

	async function submitDelete(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (deleteBusy) return;
		deleteError = null;
		if (!deletePassword) {
			deleteError = 'Bitte bestätige mit deinem Passwort.';
			return;
		}
		deleteBusy = true;
		try {
			await deleteAccount(deletePassword);
			deleteOpen = false;
			inbox.reset();
			umkreis.reset();
			await session.refresh();
			toasts.success('Dein Konto ist gelöscht.');
			await goto('/');
		} catch (error) {
			deleteError = isApiError(error) && error.fields.password ? error.fields.password : errorMessage(error);
		} finally {
			deleteBusy = false;
		}
	}

	function decisionLabel(change: PlaceChange): string {
		if (change.decision === 'approved') return 'bestätigt';
		if (change.decision === 'rejected') return 'abgelehnt';
		return 'in Prüfung';
	}
</script>

<svelte:head>
	<title>Einstellungen – {session.siteName}</title>
</svelte:head>

<div class="page" data-testid="settings-page">
	<h1>Einstellungen</h1>

	<section aria-labelledby="profil-titel">
		<h2 id="profil-titel">So sehen dich andere</h2>
		{#if asOthersSee}
			<Card padding="lg" testid="settings-profile">
				<PersonSummary user={asOthersSee} size="lg" showMemberSince />
			</Card>
		{/if}
		<p class="note">
			Mehr ist von dir nicht sichtbar. Der Nickname ist fest. Was niemand sieht, steht in der <a href="/vorschau">Vorschau</a>.
		</p>
	</section>

	<section aria-labelledby="orte-titel">
		<h2 id="orte-titel">Heimatort und Wohnort</h2>
		<p class="note">
			Beide Orte hast du bei der Registrierung festgelegt. Ändern kann sie nur ein Admin auf deinen Antrag. Bis zur Entscheidung gilt der bisherige Ort.
		</p>
		<div class="flex flex-wrap gap-2">
			<Button onclick={() => openChange('residence')} disabled={pending.has('residence')} aria-expanded={changeField === 'residence' ? 'true' : 'false'} testid="change-residence">
				Ich bin umgezogen
			</Button>
			<Button onclick={() => openChange('home')} disabled={pending.has('home')} aria-expanded={changeField === 'home' ? 'true' : 'false'} testid="change-home">
				Mein Heimatort ist falsch
			</Button>
		</div>

		{#if changeField}
			<Card testid="change-form-card">
				<form class="grid gap-4" onsubmit={submitChange} novalidate data-testid="change-form">
					<p>
						{#if changeField === 'residence'}
							Bisheriger Wohnort: <strong>{me?.residence?.name}</strong>. Wähle die Gemeinde, in der du jetzt lebst.
						{:else}
							Bisheriger Heimatort: <strong>{me?.home?.name}</strong>. Wähle die Gemeinde, aus der du tatsächlich stammst.
						{/if}
					</p>
					<PlaceSearch label={changeField === 'residence' ? 'Neuer Wohnort' : 'Richtiger Heimatort'} bind:value={newPlace} error={changeError} testid="change-place" />
					<div class="flex flex-wrap gap-2">
						<Button type="submit" variant="primary" loading={changeBusy} testid="change-submit">Antrag stellen</Button>
						<Button onclick={() => (changeField = null)}>Abbrechen</Button>
					</div>
				</form>
			</Card>
		{/if}

		{#if changes.length > 0}
			<ul class="rows" data-testid="change-list">
				{#each changes as change (change.id)}
					<li data-testid="change-item">
						<div class="min-w-0">
							<p>
								<span class="hs-strong">{change.field === 'residence' ? 'Wohnort' : 'Heimatort'}</span>
								zu {change.new_place.name} ({change.new_place.district_name})
							</p>
							<p class="meta">
								Beantragt am {formatDate(change.created_at)}{#if change.decided_at}, entschieden am {formatDate(change.decided_at)}{/if}
							</p>
						</div>
						<Badge tone={change.decision === 'approved' ? 'success' : change.decision === 'rejected' ? 'danger' : 'accent'}>{decisionLabel(change)}</Badge>
					</li>
				{/each}
			</ul>
		{/if}
	</section>

	<section aria-labelledby="block-titel">
		<h2 id="block-titel">Blockierte Personen</h2>
		<p class="note">Blockierte und Blockierende sehen sich gegenseitig nicht und können sich nicht schreiben. Melden bleibt möglich.</p>
		{#if blocksError}<Notice tone="danger" testid="blocks-error"><p>{blocksError}</p></Notice>{/if}
		{#if blocks.length === 0 && !blocksError}
			<p class="empty" data-testid="blocks-empty">Du hast niemanden blockiert.</p>
		{:else}
			<ul class="rows" data-testid="block-list">
				{#each blocks as entry (entry.user_id)}
					<li data-testid="block-item">
						<div class="min-w-0">
							<p class="hs-strong nick">{entry.nickname ?? 'Konto nicht mehr vorhanden'}</p>
							<p class="meta">Blockiert am {formatDate(entry.created_at)}</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<Button size="sm" loading={unblockingId === entry.user_id} onclick={() => void unblock(entry)} testid="block-remove">Entblocken</Button>
							{#if entry.nickname}
								<Button
									size="sm"
									variant="ghost"
									onclick={() => {
										reportTarget = entry;
										reportOpen = true;
									}}
									testid="block-report">Melden</Button
								>
							{/if}
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</section>

	<section aria-labelledby="darstellung-titel">
		<h2 id="darstellung-titel">Darstellung</h2>
		<ThemeToggle />
		<p class="note">Die Wahl wird nur in diesem Browser gespeichert.</p>
	</section>

	<section aria-labelledby="passwort-titel">
		<h2 id="passwort-titel">Passwort ändern</h2>
		<form class="narrow grid gap-4" onsubmit={submitPassword} novalidate data-testid="password-form">
			<Field label="Aktuelles Passwort" type="password" bind:value={currentPassword} autocomplete="current-password" required error={passwordErrors.current_password} testid="password-current" />
			<Field label="Neues Passwort" type="password" bind:value={newPassword} autocomplete="new-password" required hint="Mindestens 12 Zeichen." error={passwordErrors.new_password} testid="password-new" />
			<Field label="Neues Passwort wiederholen" type="password" bind:value={repeatPassword} autocomplete="new-password" required error={passwordErrors.repeat} testid="password-repeat" />
			{#if passwordFailure}<Notice tone="danger" live><p>{passwordFailure}</p></Notice>{/if}
			<div><Button type="submit" loading={passwordBusy} testid="password-submit">Passwort speichern</Button></div>
		</form>
	</section>

	<section aria-labelledby="abmelden-titel">
		<h2 id="abmelden-titel">Abmelden</h2>
		<div><Button icon={LogOut} loading={loggingOut} onclick={handleLogout} testid="settings-logout">Abmelden</Button></div>
	</section>

	<section aria-labelledby="loeschen-titel">
		<h2 id="loeschen-titel">Konto löschen</h2>
		<div class="grid max-w-prose gap-2">
			<p>Wenn du dein Konto löschst, passiert Folgendes:</p>
			<ul class="bullets">
				<li>Sofort: Du bist für niemanden mehr sichtbar oder erreichbar. E-Mail, Passwort, Nickname, Geburtsjahr und beide Orte werden entfernt, du wirst abgemeldet.</li>
				<li>
					Innerhalb von 24 Stunden: Alle deine Gespräche mit allen Nachrichten, auch auf der Gegenseite, alle Anfragen, Blockierungen und Anträge werden
					gelöscht. Deine Gesprächspartner sehen „Gespräch nicht mehr verfügbar“.
				</li>
				<li>Spätestens nach 31 Tagen sind deine Kontodaten auch aus allen Sicherungen verschwunden.</li>
				<li>
					Länger bleiben nur Belege zu Meldungen (bis 12 Monate nach Abschluss) und Einträge über Admin-Handlungen (bis 24 Monate). Sie enthalten weder
					E-Mail noch Orte.
				</li>
			</ul>
			<p class="note">Das lässt sich nicht rückgängig machen.</p>
		</div>
		<div><Button variant="danger" onclick={() => ((deleteOpen = true), (deletePassword = ''), (deleteError = null))} testid="delete-open">Konto löschen</Button></div>
	</section>
</div>

<Dialog bind:open={deleteOpen} title="Konto endgültig löschen" testid="delete-dialog">
	<form id="konto-loeschen" class="grid gap-4" onsubmit={submitDelete} novalidate>
		<p>Dein Konto wird sofort unsichtbar und danach vollständig gelöscht. Das lässt sich nicht rückgängig machen.</p>
		<Field label="Passwort zur Bestätigung" type="password" bind:value={deletePassword} autocomplete="current-password" required error={deleteError} testid="delete-password" />
	</form>
	{#snippet footer()}
		<Button onclick={() => (deleteOpen = false)} testid="delete-cancel">Abbrechen</Button>
		<Button variant="danger" type="submit" form="konto-loeschen" loading={deleteBusy} testid="delete-confirm">Konto endgültig löschen</Button>
	{/snippet}
</Dialog>

{#if reportTarget}
	<ReportDialog bind:open={reportOpen} targetType="profile" targetId={reportTarget.user_id} subject={reportTarget.nickname ?? 'Blockiertes Konto'} />
{/if}

<style>
	.page {
		display: grid;
		gap: var(--hs-space-7);
		max-width: 44rem;
	}

	section {
		display: grid;
		gap: var(--hs-space-3);
	}

	section + section {
		padding-top: var(--hs-space-6);
		border-top: 1px solid var(--hs-line);
	}

	.note,
	.empty,
	.meta {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.narrow {
		max-width: 26rem;
	}

	.rows {
		display: grid;
		list-style: none;
		margin: 0;
		padding: 0;
		border: 1px solid var(--hs-line);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
	}

	.rows li {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--hs-space-3);
		padding: var(--hs-space-3) var(--hs-space-4);
	}

	.rows li + li {
		border-top: 1px solid var(--hs-line);
	}

	.nick {
		overflow-wrap: anywhere;
	}

	.bullets {
		display: grid;
		gap: var(--hs-space-2);
		padding-left: 1.25rem;
		list-style: disc;
	}
</style>
