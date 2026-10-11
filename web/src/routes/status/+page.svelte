<script lang="ts">
	import { errorMessage, isApiError } from '$lib/api/client';
	import { createAppeal } from '$lib/api/endpoints';
	import { session } from '$lib/api/session.svelte';
	import Button from '$lib/ui/Button.svelte';
	import FormPage from '$lib/ui/FormPage.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import TextArea from '$lib/ui/TextArea.svelte';
	import { formatDateTime, formatRemaining } from '$lib/util/format';

	let text = $state('');
	let busy = $state(false);
	let done = $state(false);
	let exists = $state(false);
	let failure = $state<string | null>(null);
	let fieldError = $state<string | null>(null);
	let checking = $state(false);

	const mutedUntil = $derived(session.user?.muted_until ?? null);

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (busy) return;
		failure = null;
		fieldError = null;
		if (text.trim().length < 10) {
			fieldError = 'Bitte beschreibe kurz, warum du die Einschränkung für falsch hältst.';
			return;
		}
		busy = true;
		try {
			await createAppeal(text.trim());
			done = true;
		} catch (error) {
			if (isApiError(error) && error.code === 'appeal_exists') exists = true;
			else if (isApiError(error) && error.fields.text) fieldError = error.fields.text;
			else failure = errorMessage(error);
		} finally {
			busy = false;
		}
	}

	async function recheck(): Promise<void> {
		checking = true;
		await session.refresh();
		checking = false;
	}
</script>

<svelte:head>
	<title>Kontostatus – {session.siteName}</title>
</svelte:head>

{#if session.state === 'awaiting_approval'}
	<FormPage title="Dein Konto wartet auf Freigabe" wide>
		<div class="grid gap-4" data-testid="status-awaiting">
			<p>
				Deine E-Mail-Adresse ist bestätigt. Von deinem Internetanschluss kamen in kurzer Zeit mehrere Registrierungen, deshalb schaltet eine Person aus dem
				Team dein Konto von Hand frei. Das schützt vor massenhaft angelegten Konten.
			</p>
			<Notice tone="info" title="So geht es weiter">
				<p>Die Freigabe dauert in der Regel höchstens 7 Tage. Du bekommst eine E-Mail, sobald dein Konto aktiv ist.</p>
				<p>Dein Konto wird in dieser Zeit nicht gelöscht. Dauert es länger als 14 Tage, melden wir uns mit dem Stand.</p>
			</Notice>
			<p class="text-sm text-ink-muted">Solange bist du für andere nicht sichtbar und kannst den Umkreis noch nicht öffnen.</p>
			<div><Button onclick={recheck} loading={checking} testid="status-recheck">Status erneut prüfen</Button></div>
		</div>
	</FormPage>
{:else if session.state === 'muted'}
	<FormPage title="Dein Konto ist vorübergehend eingeschränkt" wide>
		<div class="grid gap-4" data-testid="status-muted">
			<p>
				Mehrere Mitglieder haben dich innerhalb kurzer Zeit gemeldet. Deshalb kannst du für 48 Stunden keine neuen Kontaktanfragen senden. Die Einschränkung
				endet von selbst.
			</p>
			<dl class="facts">
				<div>
					<dt>Endet</dt>
					<dd data-testid="status-muted-until">
						<span class="hs-num">{formatDateTime(mutedUntil)}</span>
						<span class="text-ink-muted">({formatRemaining(mutedUntil)})</span>
					</dd>
				</div>
				<div>
					<dt>Weiter möglich</dt>
					<dd>Bestehende Gespräche, Anfragen empfangen und beantworten, den Umkreis ansehen.</dd>
				</div>
				<div>
					<dt>Gerade nicht möglich</dt>
					<dd>Neue Kontaktanfragen senden.</dd>
				</div>
			</dl>
			<p class="text-sm text-ink-muted">
				Das Moderationsteam prüft die Meldungen, in der Regel innerhalb von 72 Stunden. Die Prüfung kann die Sache ohne Folgen schließen oder zu einer
				Sperrung führen.
			</p>

			<h2>Einspruch</h2>
			{#if done}
				<Notice tone="success" title="Einspruch eingegangen" testid="status-appeal-done"><p>Wir prüfen ihn zusammen mit den Meldungen.</p></Notice>
			{:else if exists}
				<Notice tone="info" title="Es liegt bereits ein Einspruch vor" testid="status-appeal-exists"><p>Du musst nichts weiter tun.</p></Notice>
			{:else}
				<form class="grid gap-4" onsubmit={submit} novalidate data-testid="status-appeal-form">
					<TextArea label="Deine Sicht" bind:value={text} max={2000} rows={6} required error={fieldError} hint="Was ist aus deiner Sicht passiert?" testid="status-appeal-text" />
					{#if failure}<Notice tone="danger" live><p>{failure}</p></Notice>{/if}
					<div><Button type="submit" variant="primary" loading={busy} testid="status-appeal-submit">Einspruch senden</Button></div>
				</form>
			{/if}
			<p><a href="/umkreis">Zurück zum Umkreis</a></p>
		</div>
	</FormPage>
{:else}
	<FormPage title="Kontostatus">
		<p>Dein Konto ist aktiv.</p>
		<p><a href="/umkreis">Zum Umkreis</a></p>
	</FormPage>
{/if}

<style>
	.facts {
		display: grid;
		gap: var(--hs-space-3);
		padding: var(--hs-space-4);
		border: 1px solid var(--hs-line);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
	}

	.facts dt {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-subtle);
	}
</style>
