<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { errorMessage, isApiError } from '$lib/api/client';
	import { acceptRequest, blockUser, declineRequest, listRequests, withdrawRequest } from '$lib/api/endpoints';
	import { inbox } from '$lib/api/inbox.svelte';
	import { session } from '$lib/api/session.svelte';
	import type { IncomingRequest, OutgoingRequest, RequestsResponse } from '$lib/api/types';
	import { umkreis } from '$lib/network/umkreis.svelte';
	import Badge from '$lib/ui/Badge.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
	import ConfirmDialog from '$lib/ui/ConfirmDialog.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import PersonSummary from '$lib/ui/PersonSummary.svelte';
	import ReportDialog from '$lib/ui/ReportDialog.svelte';
	import Tabs from '$lib/ui/Tabs.svelte';
	import { toasts } from '$lib/ui/toast.svelte';
	import { formatDate, formatDateTime } from '$lib/util/format';

	let data = $state.raw<RequestsResponse | null>(null);
	let loading = $state(true);
	let loadError = $state<string | null>(null);
	let tab = $state('eingegangen');
	let busyId = $state<string | null>(null);

	let blockTarget = $state<IncomingRequest | null>(null);
	let blockOpen = $state(false);
	let blocking = $state(false);
	let reportTarget = $state<IncomingRequest | null>(null);
	let reportOpen = $state(false);

	const incoming = $derived(data?.incoming ?? []);
	const outgoing = $derived(data?.outgoing ?? []);
	const quota = $derived(data?.quota ?? null);

	async function load(): Promise<void> {
		loadError = null;
		try {
			data = await listRequests();
		} catch (error) {
			loadError = errorMessage(error);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		void load();
	});

	async function act(id: string, action: () => Promise<void>): Promise<void> {
		busyId = id;
		try {
			await action();
		} catch (error) {
			toasts.error(isApiError(error) && error.isNotFound ? 'Diese Anfrage gibt es nicht mehr. Sie wurde zurückgezogen oder ist abgelaufen.' : errorMessage(error));
		} finally {
			busyId = null;
			await load();
			void inbox.refresh();
		}
	}

	function accept(request: IncomingRequest): Promise<void> {
		return act(request.id, async () => {
			const result = await acceptRequest(request.id);
			toasts.success(`Anfrage von ${request.from.nickname} angenommen.`);
			await goto(`/gespraeche/${result.conversation_id}`);
		});
	}

	function decline(request: IncomingRequest): Promise<void> {
		return act(request.id, async () => {
			await declineRequest(request.id);
			toasts.show('Anfrage abgelehnt. Die andere Person erfährt das nicht.');
		});
	}

	function withdraw(request: OutgoingRequest): Promise<void> {
		return act(request.id, async () => {
			await withdrawRequest(request.id);
			toasts.success('Anfrage zurückgezogen.');
		});
	}

	async function block(): Promise<void> {
		const target = blockTarget;
		if (!target) return;
		blocking = true;
		try {
			await blockUser(target.from.id);
			toasts.success(`${target.from.nickname} ist blockiert.`);
			umkreis.reset();
		} catch (error) {
			toasts.error(errorMessage(error));
		} finally {
			blocking = false;
			blockOpen = false;
			await load();
			void inbox.refresh();
		}
	}
</script>

<svelte:head>
	<title>Anfragen – {session.siteName}</title>
</svelte:head>

<div class="page" data-testid="requests-page">
	<header class="grid gap-2">
		<h1>Kontaktanfragen</h1>
		<p class="max-w-prose text-ink-muted">Die erste Nachricht ist immer eine Anfrage. Erst nach der Annahme entsteht ein Gespräch.</p>
	</header>

	{#if loadError}
		<Notice tone="danger" live testid="requests-error"><p>{loadError}</p></Notice>
	{/if}

	<Tabs
		tabs={[
			{ id: 'eingegangen', label: 'Eingegangen', count: incoming.length },
			{ id: 'gesendet', label: 'Gesendet', count: outgoing.length }
		]}
		bind:value={tab}
		label="Anfragen"
		idBase="anfragen"
		testid="requests-tabs"
	/>

	{#if loading}
		<p role="status" class="text-ink-muted">Anfragen werden geladen.</p>
	{:else if tab === 'eingegangen'}
		<div role="tabpanel" id="anfragen-panel-eingegangen" aria-labelledby="anfragen-tab-eingegangen" class="grid gap-4">
			{#if incoming.length === 0}
				<Card tone="sunken" padding="lg" testid="requests-incoming-empty">
					<p class="hs-strong">Keine offenen Anfragen.</p>
					<p class="text-ink-muted">Wenn dich jemand aus deinem Umkreis anschreibt, erscheint die Anfrage hier.</p>
				</Card>
			{:else}
				<ul class="list">
					{#each incoming as request (request.id)}
						<li>
							<Card padding="lg" testid="request-incoming">
								<div class="grid gap-4">
									<PersonSummary user={request.from} link />
									<blockquote class="body" data-testid="request-text">{request.body}</blockquote>
									<p class="text-sm text-ink-subtle">
										Eingegangen {formatDateTime(request.created_at)}. Ohne Antwort läuft die Anfrage am {formatDate(request.expires_at)} ab.
									</p>
									<div class="flex flex-wrap gap-2">
										<Button variant="primary" loading={busyId === request.id} onclick={() => void accept(request)} testid="request-accept">Annehmen</Button>
										<Button disabled={busyId === request.id} onclick={() => void decline(request)} testid="request-decline">Ablehnen</Button>
										<Button
											variant="ghost"
											disabled={busyId === request.id}
											onclick={() => {
												blockTarget = request;
												blockOpen = true;
											}}
											testid="request-block">Blockieren</Button
										>
										<Button
											variant="ghost"
											disabled={busyId === request.id}
											onclick={() => {
												reportTarget = request;
												reportOpen = true;
											}}
											testid="request-report">Melden</Button
										>
									</div>
								</div>
							</Card>
						</li>
					{/each}
				</ul>
				<p class="text-sm text-ink-muted">Eine Ablehnung wird der anderen Person nicht angezeigt. Für sie bleibt die Anfrage offen, bis sie abläuft.</p>
			{/if}
		</div>
	{:else}
		<div role="tabpanel" id="anfragen-panel-gesendet" aria-labelledby="anfragen-tab-gesendet" class="grid gap-4">
			{#if quota}
				<dl class="quota" data-testid="requests-quota">
					<div>
						<dt>Heute gesendet</dt>
						<dd class="hs-num">{quota.today_used} von {quota.today_max}</dd>
					</div>
					<div>
						<dt>Offene Anfragen</dt>
						<dd class="hs-num">{quota.active_used} von {quota.active_max}</dd>
					</div>
				</dl>
			{/if}
			{#if outgoing.length === 0}
				<Card tone="sunken" padding="lg" testid="requests-outgoing-empty">
					<p class="hs-strong">Du hast keine offenen Anfragen.</p>
					<p class="text-ink-muted">Im <a href="/umkreis">Umkreis</a> findest du Menschen aus deiner Heimat und kannst sie über ihr Profil anfragen.</p>
				</Card>
			{:else}
				<ul class="list">
					{#each outgoing as request (request.id)}
						<li>
							<Card padding="lg" testid="request-outgoing">
								<div class="grid gap-4">
									<div class="flex flex-wrap items-start justify-between gap-3">
										<PersonSummary user={request.to} link />
										<Badge tone={request.state === 'open' ? 'accent' : 'neutral'}>{request.state === 'open' ? 'offen' : 'abgelaufen'}</Badge>
									</div>
									<blockquote class="body">{request.body}</blockquote>
									<p class="text-sm text-ink-subtle">
										Gesendet {formatDateTime(request.created_at)}.
										{#if request.state === 'open'}Läuft am {formatDate(request.expires_at)} ab.{/if}
									</p>
									{#if request.state === 'open'}
										<div>
											<Button loading={busyId === request.id} onclick={() => void withdraw(request)} testid="request-withdraw">Zurückziehen</Button>
										</div>
									{/if}
								</div>
							</Card>
						</li>
					{/each}
				</ul>
				<p class="text-sm text-ink-muted">Zurückgezogene Anfragen zählen sofort nicht mehr mit. Pro Person sind insgesamt zwei Anfragen möglich.</p>
			{/if}
		</div>
	{/if}
</div>

<ConfirmDialog bind:open={blockOpen} title="{blockTarget?.from.nickname ?? 'Person'} blockieren" confirmLabel="Blockieren" danger busy={blocking} onconfirm={block} testid="block">
	<p>Ihr seht euch danach gegenseitig nicht mehr und könnt euch nicht mehr schreiben. Die Anfrage verschwindet.</p>
	<p class="mt-3 text-sm text-ink-muted">Wenn du die Anfrage melden möchtest, tu das am besten zuerst. Melden ist später auch aus der Blockliste möglich, dann ohne den Text der Anfrage.</p>
</ConfirmDialog>

{#if reportTarget}
	<ReportDialog bind:open={reportOpen} targetType="request" targetId={reportTarget.id} subject="Anfrage von {reportTarget.from.nickname}" />
{/if}

<style>
	.page {
		display: grid;
		gap: var(--hs-space-5);
		max-width: 44rem;
	}

	.list {
		display: grid;
		gap: var(--hs-space-4);
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.body {
		margin: 0;
		padding: var(--hs-space-3) var(--hs-space-4);
		border-left: 3px solid var(--hs-line-strong);
		background: var(--hs-raised);
		border-radius: 0 var(--hs-radius-md) var(--hs-radius-md) 0;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}

	.quota {
		display: flex;
		flex-wrap: wrap;
		gap: var(--hs-space-3) var(--hs-space-7);
	}

	.quota dt {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-subtle);
	}

	.quota dd {
		font-weight: var(--hs-weight-strong);
	}
</style>
