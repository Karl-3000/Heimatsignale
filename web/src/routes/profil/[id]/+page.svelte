<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Ban from '@lucide/svelte/icons/ban';
	import Flag from '@lucide/svelte/icons/flag';
	import Send from '@lucide/svelte/icons/send';
	import { errorMessage, isApiError } from '$lib/api/client';
	import { blockUser, getUser, sendRequest, withdrawRequest } from '$lib/api/endpoints';
	import { session } from '$lib/api/session.svelte';
	import type { RequestBlockedReason, UserResponse } from '$lib/api/types';
	import { umkreis } from '$lib/network/umkreis.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
	import ConfirmDialog from '$lib/ui/ConfirmDialog.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import PersonSummary from '$lib/ui/PersonSummary.svelte';
	import ReportDialog from '$lib/ui/ReportDialog.svelte';
	import TextArea from '$lib/ui/TextArea.svelte';
	import { toasts } from '$lib/ui/toast.svelte';
	import { formatDate } from '$lib/util/format';

	const REASONS: Record<RequestBlockedReason, string> = {
		muted: 'Dein Konto ist gerade eingeschränkt. Du kannst vorübergehend keine neuen Anfragen senden.',
		attempts_exhausted: 'Du hast diese Person bereits zweimal angefragt. Eine weitere Anfrage ist nicht möglich. Sie kann dich weiterhin anfragen.',
		already_requested: 'Deine Anfrage an diese Person ist noch offen.',
		connected: 'Ihr seid bereits im Gespräch.',
		quota_daily: 'Du hast heute bereits die Höchstzahl neuer Anfragen gesendet. Morgen geht es weiter.',
		quota_active: 'Du hast die Höchstzahl offener Anfragen erreicht. Ziehe eine Anfrage zurück oder warte, bis eine abläuft.',
		not_visible: 'Eine Anfrage ist hier nicht möglich.'
	};

	const userId = $derived(page.params.id ?? '');

	let data = $state.raw<UserResponse | null>(null);
	let loading = $state(true);
	let notFound = $state(false);
	let loadError = $state<string | null>(null);

	let body = $state('');
	let sending = $state(false);
	let sendError = $state<string | null>(null);
	let bodyError = $state<string | null>(null);
	let withdrawing = $state(false);

	let blockOpen = $state(false);
	let blocking = $state(false);
	let reportOpen = $state(false);

	const relation = $derived(data?.relation ?? null);
	const user = $derived(data?.user ?? null);

	async function load(id: string): Promise<void> {
		loading = true;
		notFound = false;
		loadError = null;
		try {
			data = await getUser(id);
		} catch (error) {
			data = null;
			if (isApiError(error) && error.isNotFound) notFound = true;
			else loadError = errorMessage(error);
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		const id = userId;
		if (id) void load(id);
	});

	async function submitRequest(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (sending || !user) return;
		sendError = null;
		bodyError = null;
		const text = body.trim();
		if (!text) {
			bodyError = 'Bitte schreibe ein paar Worte.';
			return;
		}
		if (text.length > session.site.request_body_max) {
			bodyError = `Der Text darf höchstens ${session.site.request_body_max} Zeichen haben.`;
			return;
		}
		sending = true;
		try {
			const result = await sendRequest(user.id, text);
			body = '';
			if (result.conversation_id) {
				toasts.success('Ihr hattet euch gegenseitig angefragt. Das Gespräch ist eröffnet.');
				await goto(`/gespraeche/${result.conversation_id}`);
				return;
			}
			toasts.success('Anfrage gesendet.');
			await load(user.id);
		} catch (error) {
			if (isApiError(error) && error.fields.body) bodyError = error.fields.body;
			else if (isApiError(error) && error.isNotFound) notFound = true;
			else sendError = errorMessage(error);
		} finally {
			sending = false;
		}
	}

	async function withdraw(): Promise<void> {
		if (!relation?.outgoing_request || !user) return;
		withdrawing = true;
		try {
			await withdrawRequest(relation.outgoing_request.id);
			toasts.success('Anfrage zurückgezogen.');
		} catch (error) {
			toasts.error(errorMessage(error));
		} finally {
			withdrawing = false;
			await load(user.id);
		}
	}

	async function block(): Promise<void> {
		if (!user) return;
		blocking = true;
		try {
			await blockUser(user.id);
			blockOpen = false;
			toasts.success(`${user.nickname} ist blockiert. Aufheben kannst du das in den Einstellungen.`);
			// Zähler und Listen ändern sich durch die Blockierung; der Umkreis wird neu geladen.
			umkreis.reset();
			await goto('/umkreis');
		} catch (error) {
			blockOpen = false;
			toasts.error(isApiError(error) && error.isNotFound ? 'Dieses Konto ist nicht mehr erreichbar.' : errorMessage(error));
		} finally {
			blocking = false;
		}
	}
</script>

<svelte:head>
	<title>{user ? user.nickname : 'Profil'} – {session.siteName}</title>
</svelte:head>

<div class="page" data-testid="profile-page">
	<p><Button href="/umkreis" variant="ghost" size="sm" icon={ArrowLeft} testid="profile-back">Zurück zum Umkreis</Button></p>

	{#if loading && !data}
		<p role="status" class="text-ink-muted">Profil wird geladen.</p>
	{:else if notFound}
		<Notice tone="info" title="Dieses Profil ist nicht verfügbar" testid="profile-notfound">
			<p>Es existiert nicht oder ist für dich nicht sichtbar, zum Beispiel weil die Person außerhalb deines Umkreises wohnt.</p>
		</Notice>
	{:else if loadError}
		<Notice tone="danger" live testid="profile-error"><p>{loadError}</p></Notice>
		<div><Button onclick={() => void load(userId)}>Erneut versuchen</Button></div>
	{:else if user && relation}
		<h1 class="hs-sr-only">Profil von {user.nickname}</h1>
		<Card padding="lg" testid="profile-card">
			<PersonSummary {user} size="lg" showMemberSince />
		</Card>

		<section class="grid gap-3" aria-labelledby="kontakt-titel">
			<h2 id="kontakt-titel">Kontakt</h2>

			{#if relation.conversation_id}
				<p>Ihr seid im Gespräch.</p>
				<div><Button href="/gespraeche/{relation.conversation_id}" variant="primary" testid="profile-open-conversation">Zum Gespräch</Button></div>
			{:else if relation.incoming_request_id}
				<Notice tone="info" title="{user.nickname} hat dir eine Anfrage gesendet" testid="profile-incoming">
					<p>Du kannst sie annehmen oder ablehnen.</p>
				</Notice>
				<div><Button href="/anfragen" variant="primary">Zu den Anfragen</Button></div>
			{:else if relation.outgoing_request}
				<Notice tone="info" title={relation.outgoing_request.state === 'expired' ? 'Deine Anfrage ist abgelaufen' : 'Deine Anfrage ist offen'} testid="profile-outgoing">
					{#if relation.outgoing_request.state === 'open'}
						<p>Sie läuft am {formatDate(relation.outgoing_request.expires_at)} ab, wenn bis dahin keine Antwort kommt.</p>
					{:else}
						<p>Die Anfrage wurde in 30 Tagen nicht beantwortet.</p>
					{/if}
				</Notice>
				{#if relation.outgoing_request.state === 'open'}
					<div><Button onclick={withdraw} loading={withdrawing} testid="profile-withdraw">Anfrage zurückziehen</Button></div>
				{/if}
			{/if}

			{#if relation.can_request}
				<form class="grid gap-3" onsubmit={submitRequest} novalidate data-testid="request-form">
					<TextArea
						label="Kontaktanfrage an {user.nickname}"
						bind:value={body}
						max={session.site.request_body_max}
						rows={4}
						required
						error={bodyError}
						hint="Stell dich kurz vor, zum Beispiel woher genau du kommst. Links sind in Anfragen nicht erlaubt. Erst wenn die Anfrage angenommen wird, könnt ihr euch schreiben."
						testid="request-body"
					/>
					{#if sendError}<Notice tone="danger" live testid="request-error"><p>{sendError}</p></Notice>{/if}
					<div><Button type="submit" variant="primary" icon={Send} loading={sending} testid="request-submit">Anfrage senden</Button></div>
				</form>
			{:else if !relation.conversation_id && !relation.incoming_request_id && !relation.outgoing_request}
				<Notice tone="info" testid="request-blocked">
					<p>{relation.request_blocked_reason ? REASONS[relation.request_blocked_reason] : 'Eine Anfrage ist hier nicht möglich.'}</p>
					{#if relation.request_blocked_reason === 'muted'}<p><a href="/status">Mehr dazu</a></p>{/if}
				</Notice>
			{:else if relation.request_blocked_reason === 'attempts_exhausted' || relation.request_blocked_reason === 'quota_daily' || relation.request_blocked_reason === 'quota_active' || relation.request_blocked_reason === 'muted'}
				<p class="text-sm text-ink-muted" data-testid="request-blocked">{REASONS[relation.request_blocked_reason]}</p>
			{/if}
		</section>

		<section class="grid gap-3" aria-labelledby="schutz-titel">
			<h2 id="schutz-titel" class="small">Blockieren und melden</h2>
			<p class="text-sm text-ink-muted">
				Blockieren wirkt sofort und in beide Richtungen: Ihr seht euch nicht mehr, werdet füreinander nicht mitgezählt und könnt euch nicht schreiben. Ein
				laufendes Gespräch endet.
			</p>
			<div class="flex flex-wrap gap-2">
				<Button icon={Ban} onclick={() => (blockOpen = true)} testid="profile-block">Blockieren</Button>
				<Button icon={Flag} onclick={() => (reportOpen = true)} testid="profile-report">Melden</Button>
			</div>
		</section>

		<ConfirmDialog bind:open={blockOpen} title="{user.nickname} blockieren" confirmLabel="Blockieren" danger busy={blocking} onconfirm={block} testid="block">
			<p>Ihr seht euch danach gegenseitig nicht mehr und könnt euch nicht mehr schreiben. Offene Anfragen zwischen euch werden zurückgezogen.</p>
			<p class="mt-3 text-sm text-ink-muted">Die Blockierung kannst du in den Einstellungen aufheben. Melden bleibt auch nach dem Blockieren möglich.</p>
		</ConfirmDialog>
		<ReportDialog bind:open={reportOpen} targetType="profile" targetId={user.id} subject={user.nickname} />
	{/if}
</div>

<style>
	.page {
		display: grid;
		gap: var(--hs-space-5);
		max-width: 40rem;
	}

	.small {
		font-size: var(--hs-text-lg);
	}
</style>
