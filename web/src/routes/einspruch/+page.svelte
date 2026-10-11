<script lang="ts">
	import { page } from '$app/state';
	import { errorMessage, isApiError } from '$lib/api/client';
	import { createAppealByToken } from '$lib/api/endpoints';
	import { session } from '$lib/api/session.svelte';
	import Button from '$lib/ui/Button.svelte';
	import FormPage from '$lib/ui/FormPage.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import TextArea from '$lib/ui/TextArea.svelte';

	const token = $derived(page.url.searchParams.get('token') ?? '');

	let text = $state('');
	let busy = $state(false);
	let done = $state(false);
	let exists = $state(false);
	let failure = $state<string | null>(null);
	let fieldError = $state<string | null>(null);

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (busy) return;
		failure = null;
		fieldError = null;
		if (text.trim().length < 10) {
			fieldError = 'Bitte beschreibe kurz, warum du die Sperrung für falsch hältst.';
			return;
		}
		busy = true;
		try {
			await createAppealByToken(token, text.trim());
			done = true;
		} catch (error) {
			if (isApiError(error) && error.code === 'appeal_exists') exists = true;
			else if (isApiError(error) && error.fields.text) fieldError = error.fields.text;
			else failure = errorMessage(error);
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>Einspruch – {session.siteName}</title>
</svelte:head>

<FormPage
	title="Einspruch gegen die Sperrung"
	lead="Dein Konto wurde nach einer Prüfung gesperrt. Du kannst einmal Einspruch einlegen. Darüber entscheidet eine andere Person aus dem Moderationsteam als bei der ersten Entscheidung."
	wide
>
	{#if !token}
		<Notice tone="danger" title="Der Link ist unvollständig" testid="appeal-invalid">
			<p>Öffne den Link aus der E-Mail zur Sperrung noch einmal.</p>
		</Notice>
	{:else if done}
		<Notice tone="success" title="Einspruch eingegangen" testid="appeal-done">
			<p>Wir prüfen ihn und melden uns per E-Mail bei dir.</p>
		</Notice>
	{:else if exists}
		<Notice tone="info" title="Es liegt bereits ein Einspruch vor" testid="appeal-exists">
			<p>Zu dieser Sperrung hast du schon Einspruch eingelegt. Du bekommst die Entscheidung per E-Mail.</p>
		</Notice>
	{:else}
		<form class="grid gap-4" onsubmit={submit} novalidate data-testid="appeal-form">
			<TextArea label="Deine Sicht" bind:value={text} max={2000} rows={7} required error={fieldError} hint="Was ist aus deiner Sicht passiert, und warum ist die Sperrung falsch?" testid="appeal-text" />
			{#if failure}<Notice tone="danger" live testid="appeal-error"><p>{failure}</p></Notice>{/if}
			<div><Button type="submit" variant="primary" loading={busy} testid="appeal-submit">Einspruch senden</Button></div>
		</form>
	{/if}
</FormPage>
