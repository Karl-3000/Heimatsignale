<script lang="ts">
	import { errorMessage, isApiError } from '$lib/api/client';
	import { requestPasswordReset } from '$lib/api/endpoints';
	import { session } from '$lib/api/session.svelte';
	import { PowRun } from '$lib/pow/run.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Field from '$lib/ui/Field.svelte';
	import FormPage from '$lib/ui/FormPage.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import PowProgress from '$lib/ui/PowProgress.svelte';

	let email = $state('');
	let busy = $state(false);
	let sent = $state(false);
	let failure = $state<string | null>(null);
	let fieldError = $state<string | null>(null);
	const pow = new PowRun();

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (busy) return;
		failure = null;
		fieldError = null;
		if (!email.includes('@')) {
			fieldError = 'Bitte gib eine gültige E-Mail-Adresse ein.';
			return;
		}
		busy = true;
		try {
			const solved = await pow.solve('password_reset');
			await requestPasswordReset(email.trim(), solved);
			sent = true;
		} catch (error) {
			if (isApiError(error) && error.fields.email) fieldError = error.fields.email;
			else failure = errorMessage(error);
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>Passwort vergessen – {session.siteName}</title>
</svelte:head>

<FormPage title="Passwort vergessen" lead="Gib die E-Mail-Adresse deines Kontos ein. Du bekommst einen Link, mit dem du ein neues Passwort setzen kannst.">
	{#if sent}
		<Notice tone="success" title="E-Mail unterwegs" testid="reset-sent">
			<p>Falls zu {email.trim()} ein Konto gehört, ist der Link auf dem Weg. Sieh auch im Spam-Ordner nach.</p>
		</Notice>
		<p><a href="/anmelden">Zur Anmeldung</a></p>
	{:else}
		<form class="grid gap-4" onsubmit={submit} novalidate data-testid="reset-form">
			<Field label="E-Mail-Adresse" type="email" bind:value={email} autocomplete="email" inputmode="email" required error={fieldError} testid="reset-email" />
			{#if failure}<Notice tone="danger" live testid="reset-error"><p>{failure}</p></Notice>{/if}
			<PowProgress run={pow} />
			<Button type="submit" variant="primary" loading={busy} block testid="reset-submit">Link senden</Button>
		</form>
		<p class="text-sm"><a href="/anmelden">Zurück zur Anmeldung</a></p>
	{/if}
</FormPage>
