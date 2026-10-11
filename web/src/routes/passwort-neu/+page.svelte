<script lang="ts">
	import { page } from '$app/state';
	import { errorMessage, isApiError } from '$lib/api/client';
	import { confirmPasswordReset } from '$lib/api/endpoints';
	import { session } from '$lib/api/session.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Field from '$lib/ui/Field.svelte';
	import FormPage from '$lib/ui/FormPage.svelte';
	import Notice from '$lib/ui/Notice.svelte';

	const uid = $derived(page.url.searchParams.get('uid') ?? '');
	const token = $derived(page.url.searchParams.get('token') ?? '');

	let password = $state('');
	let repeat = $state('');
	let busy = $state(false);
	let done = $state(false);
	let failure = $state<{ code: string; message: string } | null>(null);
	let fields = $state<Record<string, string>>({});

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (busy) return;
		failure = null;
		fields = {};
		if (password.length < 12) {
			fields = { password: 'Das Passwort braucht mindestens 12 Zeichen.' };
			return;
		}
		if (password !== repeat) {
			fields = { repeat: 'Die beiden Eingaben stimmen nicht überein.' };
			return;
		}
		busy = true;
		try {
			await confirmPasswordReset(uid, token, password);
			done = true;
		} catch (error) {
			if (isApiError(error)) {
				fields = error.fields;
				if (!error.fields.password) failure = { code: error.code, message: error.message };
			} else {
				failure = { code: 'error', message: errorMessage(error) };
			}
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>Neues Passwort – {session.siteName}</title>
</svelte:head>

<FormPage title="Neues Passwort setzen">
	{#if !uid || !token}
		<Notice tone="danger" title="Der Link ist unvollständig" testid="newpw-invalid">
			<p>Öffne den Link aus der E-Mail noch einmal oder fordere einen neuen an.</p>
		</Notice>
		<p><a href="/passwort-vergessen">Neuen Link anfordern</a></p>
	{:else if done}
		<Notice tone="success" title="Passwort geändert" testid="newpw-done">
			<p>Du kannst dich jetzt mit dem neuen Passwort anmelden.</p>
		</Notice>
		<div><Button href="/anmelden" variant="primary">Zur Anmeldung</Button></div>
	{:else}
		<form class="grid gap-4" onsubmit={submit} novalidate data-testid="newpw-form">
			<Field
				label="Neues Passwort"
				type="password"
				bind:value={password}
				autocomplete="new-password"
				required
				hint="Mindestens 12 Zeichen. Ein Satz aus mehreren Wörtern ist gut zu merken."
				error={fields.password}
				testid="newpw-password"
			/>
			<Field label="Neues Passwort wiederholen" type="password" bind:value={repeat} autocomplete="new-password" required error={fields.repeat} testid="newpw-repeat" />
			{#if failure}
				<Notice tone="danger" live testid="newpw-error">
					<p>{failure.message}</p>
					{#if failure.code === 'token_invalid'}<p><a href="/passwort-vergessen">Neuen Link anfordern</a></p>{/if}
				</Notice>
			{/if}
			<Button type="submit" variant="primary" loading={busy} block testid="newpw-submit">Passwort speichern</Button>
		</form>
	{/if}
</FormPage>
