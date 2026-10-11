<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Dices from '@lucide/svelte/icons/dices';
	import { errorMessage, isApiError } from '$lib/api/client';
	import { confirmNickname, rerollNickname, verifyEmail } from '$lib/api/endpoints';
	import { session } from '$lib/api/session.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
	import FormPage from '$lib/ui/FormPage.svelte';
	import Notice from '$lib/ui/Notice.svelte';

	type Phase = 'verifying' | 'nickname' | 'invalid' | 'missing';

	let phase = $state<Phase>('verifying');
	let failure = $state<string | null>(null);
	let rolling = $state(false);
	let confirming = $state(false);

	const user = $derived(session.user);
	const rerollsLeft = $derived(user?.nickname_rerolls_left ?? 0);

	onMount(() => {
		void start();
	});

	async function start(): Promise<void> {
		const token = page.url.searchParams.get('token');
		if (!token) {
			// Ohne Token: Wer schon angemeldet ist, kann hier noch den Nickname festlegen.
			if (session.authenticated && rerollsLeft > 0) phase = 'nickname';
			else if (session.authenticated) await goto('/umkreis', { replaceState: true });
			else phase = 'missing';
			return;
		}
		try {
			await verifyEmail(token);
			// Nach der Bestätigung ist man angemeldet; die Sitzung samt CSRF-Token wird neu gelesen.
			const data = await session.refresh();
			if (data?.state === 'awaiting_approval') {
				await goto('/status', { replaceState: true });
				return;
			}
			// Den Token aus der Adresszeile nehmen, damit er nicht im Verlauf stehen bleibt.
			await goto('/bestaetigen', { replaceState: true, noScroll: true, keepFocus: true });
			phase = 'nickname';
		} catch (error) {
			if (isApiError(error) && error.code === 'token_invalid') phase = 'invalid';
			else {
				phase = 'invalid';
				failure = errorMessage(error);
			}
		}
	}

	async function reroll(): Promise<void> {
		rolling = true;
		failure = null;
		try {
			const result = await rerollNickname();
			session.patchUser({ nickname: result.nickname, nickname_rerolls_left: result.nickname_rerolls_left });
		} catch (error) {
			if (isApiError(error) && error.code === 'reroll_used') session.patchUser({ nickname_rerolls_left: 0 });
			failure = errorMessage(error);
		} finally {
			rolling = false;
		}
	}

	async function confirm(): Promise<void> {
		confirming = true;
		failure = null;
		try {
			await confirmNickname();
			session.patchUser({ nickname_rerolls_left: 0 });
			await goto('/umkreis');
		} catch (error) {
			failure = errorMessage(error);
		} finally {
			confirming = false;
		}
	}
</script>

<svelte:head>
	<title>E-Mail bestätigen – {session.siteName}</title>
</svelte:head>

{#if phase === 'verifying'}
	<FormPage title="E-Mail wird bestätigt">
		<p role="status" data-testid="verify-pending">Einen Moment.</p>
	</FormPage>
{:else if phase === 'nickname' && user}
	<FormPage title="Dein Nickname" lead="Deine E-Mail-Adresse ist bestätigt. Unter diesem Namen sehen dich andere. Er wird automatisch vergeben, damit niemand sich inszenieren muss.">
		<Card padding="lg" testid="nickname-card">
			<p class="nick" data-testid="nickname" aria-live="polite">{user.nickname}</p>
		</Card>
		{#if failure}<Notice tone="danger" live testid="nickname-error"><p>{failure}</p></Notice>{/if}
		<p class="text-sm text-ink-muted">
			{#if rerollsLeft > 0}
				Gefällt er dir nicht, kannst du genau einmal neu würfeln. Danach ist der Nickname fest und lässt sich nicht mehr ändern.
			{:else}
				Der Nickname ist jetzt fest und lässt sich nicht mehr ändern.
			{/if}
		</p>
		<div class="flex flex-wrap gap-3">
			<Button variant="primary" onclick={confirm} loading={confirming} testid="nickname-confirm">
				{rerollsLeft > 0 ? 'Diesen Nickname behalten' : 'Weiter zum Umkreis'}
			</Button>
			{#if rerollsLeft > 0}
				<Button icon={Dices} onclick={reroll} loading={rolling} testid="nickname-reroll">Einmal neu würfeln</Button>
			{/if}
		</div>
	</FormPage>
{:else if phase === 'missing'}
	<FormPage title="Bestätigungslink fehlt">
		<Notice tone="info" testid="verify-missing">
			<p>Öffne den Link aus der Bestätigungs-E-Mail. Er ist 48 Stunden gültig.</p>
		</Notice>
		<p><a href="/anmelden">Zur Anmeldung</a></p>
	</FormPage>
{:else}
	<FormPage title="Der Link ist nicht mehr gültig">
		<Notice tone="danger" testid="verify-invalid">
			<p>{failure ?? 'Der Bestätigungslink ist abgelaufen oder wurde schon benutzt.'}</p>
			<p>Ist dein Konto schon bestätigt, kannst du dich einfach anmelden. Sonst lässt sich die E-Mail auf der Anmeldeseite erneut senden.</p>
		</Notice>
		<div class="flex flex-wrap gap-3">
			<Button href="/anmelden" variant="primary">Zur Anmeldung</Button>
			<Button href="/registrieren">Neu registrieren</Button>
		</div>
	</FormPage>
{/if}

<style>
	.nick {
		font-size: var(--hs-text-2xl);
		font-weight: var(--hs-weight-strong);
		letter-spacing: -0.015em;
		overflow-wrap: anywhere;
	}
</style>
