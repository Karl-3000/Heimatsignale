<script lang="ts">
	import { goto } from '$app/navigation';
	import { ApiError, errorMessage } from '$lib/api/client';
	import { login, resendVerification } from '$lib/api/endpoints';
	import { session } from '$lib/api/session.svelte';
	import { PowRun } from '$lib/pow/run.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Field from '$lib/ui/Field.svelte';
	import FormPage from '$lib/ui/FormPage.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import PowProgress from '$lib/ui/PowProgress.svelte';
	import { formatRetryAfter } from '$lib/util/format';

	let email = $state('');
	let password = $state('');
	let busy = $state(false);
	let failure = $state<{ code: string; message: string } | null>(null);
	let fields = $state<Record<string, string>>({});
	let resent = $state(false);
	let resending = $state(false);
	const pow = new PowRun();

	async function attempt(solution: string | null): Promise<void> {
		try {
			await login(email.trim(), password, solution);
		} catch (error) {
			// Nach vielen Fehlversuchen verlangt der Server zusätzlich eine Rechenaufgabe.
			if (error instanceof ApiError && error.code === 'pow_required' && solution === null) {
				const solved = await pow.solve('login');
				await attempt(solved);
				return;
			}
			throw error;
		}
	}

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (busy) return;
		failure = null;
		fields = {};
		resent = false;
		if (!email.trim() || !password) {
			fields = {
				...(email.trim() ? {} : { email: 'Bitte gib deine E-Mail-Adresse ein.' }),
				...(password ? {} : { password: 'Bitte gib dein Passwort ein.' })
			};
			return;
		}
		busy = true;
		try {
			await attempt(null);
			// Nach dem Login gilt ein neuer CSRF-Token; die Sitzung wird neu gelesen.
			const data = await session.refresh();
			await goto(data?.state === 'awaiting_approval' ? '/status' : '/umkreis');
		} catch (error) {
			if (error instanceof ApiError) {
				fields = error.fields;
				let message = error.message;
				if (error.code === 'login_locked') message = `${error.message} Du kannst es ${formatRetryAfter(error.retryAfter)} wieder versuchen.`;
				failure = { code: error.code, message };
			} else {
				failure = { code: 'error', message: errorMessage(error) };
			}
		} finally {
			busy = false;
		}
	}

	async function resend(): Promise<void> {
		resending = true;
		try {
			const solved = await pow.solve('resend');
			await resendVerification(email.trim(), solved);
			resent = true;
			failure = null;
		} catch (error) {
			failure = { code: 'error', message: errorMessage(error) };
		} finally {
			resending = false;
		}
	}
</script>

<svelte:head>
	<title>Anmelden – {session.siteName}</title>
</svelte:head>

<FormPage title="Anmelden">
	<form class="grid gap-4" onsubmit={submit} novalidate data-testid="login-form">
		<Field label="E-Mail-Adresse" type="email" bind:value={email} autocomplete="email" inputmode="email" required error={fields.email} testid="login-email" />
		<Field label="Passwort" type="password" bind:value={password} autocomplete="current-password" required error={fields.password} testid="login-password" />

		{#if failure}
			<Notice tone="danger" live testid="login-error">
				<p>{failure.message}</p>
				{#if failure.code === 'unverified'}
					<p>Der Bestätigungslink ist 48 Stunden gültig. Du kannst dir die E-Mail noch einmal senden lassen.</p>
				{:else if failure.code === 'suspended'}
					<p>Den Link für einen Einspruch findest du in der E-Mail zur Sperrung.</p>
				{:else if failure.code === 'staff_only_admin'}
					<p><a href={session.adminPath} rel="external">Zur Anmeldung im Admin-Bereich</a></p>
				{/if}
			</Notice>
			{#if failure.code === 'unverified'}
				<Button onclick={resend} loading={resending} testid="login-resend">Bestätigungs-E-Mail erneut senden</Button>
			{/if}
		{/if}

		{#if resent}
			<Notice tone="success" title="E-Mail unterwegs" testid="login-resent">
				<p>Falls zu dieser Adresse ein unbestätigtes Konto gehört, ist ein neuer Bestätigungslink auf dem Weg.</p>
			</Notice>
		{/if}

		<PowProgress run={pow} />

		<Button type="submit" variant="primary" loading={busy} block testid="login-submit">Anmelden</Button>
	</form>

	<p class="text-sm text-ink-muted">
		<a href="/passwort-vergessen" data-testid="login-forgot">Passwort vergessen</a>
		<span aria-hidden="true" class="mx-2">|</span>
		Noch kein Konto? <a href="/registrieren">Registrieren</a>
	</p>
</FormPage>
