<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Send from '@lucide/svelte/icons/send';
	import { errorMessage, isApiError } from '$lib/api/client';
	import { blockUser, deleteMessage, getMessages, sendMessage } from '$lib/api/endpoints';
	import { inbox } from '$lib/api/inbox.svelte';
	import { session } from '$lib/api/session.svelte';
	import type { Message, PublicUser } from '$lib/api/types';
	import { umkreis } from '$lib/network/umkreis.svelte';
	import Button from '$lib/ui/Button.svelte';
	import ConfirmDialog from '$lib/ui/ConfirmDialog.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import ReportDialog from '$lib/ui/ReportDialog.svelte';
	import TextArea from '$lib/ui/TextArea.svelte';
	import { toasts } from '$lib/ui/toast.svelte';
	import { formatDateTime, formatRetryAfter } from '$lib/util/format';

	const conversationId = $derived(page.params.id ?? '');

	/** Ältere, nachgeladene Seiten und das jüngste Fenster, das beim Polling ersetzt wird. */
	let older = $state.raw<Message[]>([]);
	let latest = $state.raw<Message[]>([]);
	let hasMore = $state(false);
	let partner = $state.raw<PublicUser | null>(null);
	let available = $state(true);
	let linksAllowed = $state(false);
	let loading = $state(true);
	let notFound = $state(false);
	let loadError = $state<string | null>(null);
	let loadingOlder = $state(false);

	let draft = $state('');
	let sending = $state(false);
	let sendError = $state<string | null>(null);
	let draftError = $state<string | null>(null);

	let deleteTarget = $state<Message | null>(null);
	let deleteOpen = $state(false);
	let deleting = $state(false);
	let reportTarget = $state<Message | null>(null);
	let reportOpen = $state(false);
	let blockOpen = $state(false);
	let blocking = $state(false);

	let scroller = $state<HTMLDivElement | null>(null);

	const messages = $derived.by(() => {
		const ids = new Set(latest.map((m) => m.id));
		return [...older.filter((m) => !ids.has(m.id)), ...latest];
	});
	const partnerName = $derived(partner?.nickname ?? 'Gespräch');

	function nearBottom(): boolean {
		const el = scroller;
		if (!el) return true;
		return el.scrollHeight - el.scrollTop - el.clientHeight < 80;
	}

	async function scrollToEnd(): Promise<void> {
		await tick();
		if (scroller) scroller.scrollTop = scroller.scrollHeight;
	}

	function markSeen(): void {
		if (document.visibilityState === 'hidden') return;
		const last = latest[latest.length - 1];
		inbox.markSeen(conversationId, last ? last.created_at : new Date().toISOString());
	}

	async function refresh(initial: boolean): Promise<void> {
		const stick = initial || nearBottom();
		try {
			const data = await getMessages(conversationId);
			const lastBefore = latest[latest.length - 1]?.id;
			latest = data.messages;
			partner = data.partner;
			available = data.available;
			linksAllowed = data.links_allowed;
			if (initial) hasMore = data.has_more;
			loadError = null;
			markSeen();
			const lastAfter = latest[latest.length - 1]?.id;
			if (stick && (initial || lastAfter !== lastBefore)) await scrollToEnd();
		} catch (error) {
			if (isApiError(error) && error.isNotFound) notFound = true;
			else if (initial) loadError = errorMessage(error);
		} finally {
			loading = false;
		}
	}

	async function loadOlder(): Promise<void> {
		const first = messages[0];
		if (!first || loadingOlder) return;
		loadingOlder = true;
		const el = scroller;
		const previousHeight = el?.scrollHeight ?? 0;
		try {
			const data = await getMessages(conversationId, first.id);
			older = [...data.messages, ...older];
			hasMore = data.has_more;
			await tick();
			// Die Leseposition bleibt stehen, obwohl oben Nachrichten dazukommen.
			if (el) el.scrollTop += el.scrollHeight - previousHeight;
		} catch (error) {
			toasts.error(errorMessage(error));
		} finally {
			loadingOlder = false;
		}
	}

	onMount(() => {
		void refresh(true);
		const timer = setInterval(
			() => {
				if (document.visibilityState !== 'hidden' && !notFound) void refresh(false);
			},
			Math.max(10, session.site.poll_seconds) * 1000
		);
		const onVisible = () => {
			if (document.visibilityState === 'visible') markSeen();
		};
		document.addEventListener('visibilitychange', onVisible);
		return () => {
			clearInterval(timer);
			document.removeEventListener('visibilitychange', onVisible);
		};
	});

	async function submit(event?: SubmitEvent): Promise<void> {
		event?.preventDefault();
		if (sending) return;
		sendError = null;
		draftError = null;
		const text = draft.trim();
		if (!text) return;
		if (text.length > session.site.message_body_max) {
			draftError = `Eine Nachricht darf höchstens ${session.site.message_body_max} Zeichen haben.`;
			return;
		}
		sending = true;
		try {
			const message = await sendMessage(conversationId, text);
			latest = [...latest, message];
			draft = '';
			markSeen();
			await scrollToEnd();
		} catch (error) {
			if (isApiError(error) && error.fields.body) draftError = error.fields.body;
			else if (isApiError(error) && error.code === 'unavailable') {
				available = false;
				sendError = 'Dieses Gespräch ist nicht mehr verfügbar.';
			} else if (isApiError(error) && error.isRateLimited) {
				sendError = `In diesem Gespräch wurden in der letzten Stunde sehr viele Nachrichten gesendet. Bitte versuche es ${formatRetryAfter(error.retryAfter)} noch einmal.`;
			} else sendError = errorMessage(error);
		} finally {
			sending = false;
		}
	}

	function handleDraftKey(event: KeyboardEvent): void {
		if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
			event.preventDefault();
			void submit();
		}
	}

	async function confirmDelete(): Promise<void> {
		const target = deleteTarget;
		if (!target) return;
		deleting = true;
		try {
			await deleteMessage(target.id);
			latest = latest.filter((m) => m.id !== target.id);
			older = older.filter((m) => m.id !== target.id);
			toasts.success('Nachricht gelöscht. Sie ist für euch beide verschwunden.');
		} catch (error) {
			toasts.error(errorMessage(error));
		} finally {
			deleting = false;
			deleteOpen = false;
		}
	}

	async function block(): Promise<void> {
		if (!partner) return;
		blocking = true;
		try {
			await blockUser(partner.id);
			toasts.success(`${partner.nickname} ist blockiert. Das Gespräch ist beendet.`);
			umkreis.reset();
			void inbox.refresh();
			await goto('/gespraeche');
		} catch (error) {
			toasts.error(errorMessage(error));
		} finally {
			blocking = false;
			blockOpen = false;
		}
	}
</script>

<svelte:head>
	<title>{partnerName} – {session.siteName}</title>
</svelte:head>

<div class="page" data-testid="conversation-page">
	<p><Button href="/gespraeche" variant="ghost" size="sm" icon={ArrowLeft} testid="conversation-back">Alle Gespräche</Button></p>

	{#if loading}
		<p role="status" class="text-ink-muted">Gespräch wird geladen.</p>
	{:else if notFound}
		<Notice tone="info" title="Gespräch nicht mehr verfügbar" testid="conversation-notfound">
			<p>Dieses Gespräch gibt es nicht oder nicht mehr.</p>
		</Notice>
	{:else if loadError}
		<Notice tone="danger" live testid="conversation-error"><p>{loadError}</p></Notice>
		<div><Button onclick={() => void refresh(true)}>Erneut versuchen</Button></div>
	{:else}
		<header class="head">
			<div class="min-w-0">
				<h1 class="title">
					{#if partner}<a href="/profil/{partner.id}" data-testid="conversation-partner">{partner.nickname}</a>{:else}Gespräch{/if}
				</h1>
				{#if partner}
					<p class="text-sm text-ink-muted">aus {partner.home.name} ({partner.home.district_name}), wohnt in {partner.residence.name}</p>
				{/if}
			</div>
			{#if partner && available}
				<Button size="sm" onclick={() => (blockOpen = true)} testid="conversation-block">Blockieren</Button>
			{/if}
		</header>

		{#if !available}
			<Notice tone="info" title="Gespräch nicht mehr verfügbar" testid="conversation-unavailable">
				<p>Die andere Person ist nicht mehr erreichbar. Du kannst hier nichts mehr schreiben.</p>
			</Notice>
		{/if}

		<div class="messages" bind:this={scroller} data-testid="message-list">
			{#if hasMore}
				<div class="older"><Button size="sm" loading={loadingOlder} onclick={loadOlder} testid="messages-older">Ältere Nachrichten laden</Button></div>
			{/if}
			{#if messages.length === 0}
				<p class="none">Noch keine Nachrichten. Ihr kommt aus derselben Gegend, das ist ein guter Anfang.</p>
			{/if}
			<div role="log" aria-live="polite" aria-label="Nachrichten">
			<ol>
				{#each messages as message (message.id)}
					<li class:mine={message.mine} data-testid="message" data-mine={message.mine ? 'true' : 'false'}>
						<div class="bubble">
							<p class="who">{message.mine ? 'Du' : partnerName}<span class="hs-sr-only">, </span><span class="when hs-num">{formatDateTime(message.created_at)}</span></p>
							<p class="text">{message.body}</p>
						</div>
						{#if message.mine}
							<button
								type="button"
								class="action"
								onclick={() => {
									deleteTarget = message;
									deleteOpen = true;
								}}
								data-testid="message-delete">Löschen</button
							>
						{:else if available}
							<button
								type="button"
								class="action"
								onclick={() => {
									reportTarget = message;
									reportOpen = true;
								}}
								data-testid="message-report">Melden</button
							>
						{/if}
					</li>
				{/each}
			</ol>
			</div>
		</div>

		{#if available}
			<form class="composer" onsubmit={submit} novalidate data-testid="message-form">
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div onkeydown={handleDraftKey}>
					<TextArea
						label="Nachricht an {partnerName}"
						hideLabel
						bind:value={draft}
						max={session.site.message_body_max}
						rows={3}
						placeholder="Nachricht schreiben"
						error={draftError}
						testid="message-input"
					/>
				</div>
				{#if sendError}<Notice tone="danger" live testid="message-error"><p>{sendError}</p></Notice>{/if}
				<div class="send-row">
					<p class="text-sm text-ink-muted" data-testid="links-hint">
						{#if linksAllowed}
							Reiner Text. Links sind in diesem Gespräch erlaubt.
						{:else}
							Reiner Text. Links sind erst möglich, wenn ihr zusammen 10 Nachrichten ausgetauscht habt und beide geschrieben haben.
						{/if}
					</p>
					<Button type="submit" variant="primary" icon={Send} loading={sending} disabled={draft.trim().length === 0} testid="message-send">Senden</Button>
				</div>
			</form>
		{/if}
	{/if}
</div>

<ConfirmDialog bind:open={deleteOpen} title="Nachricht löschen" confirmLabel="Löschen" danger busy={deleting} onconfirm={confirmDelete} testid="delete-message">
	<p>Die Nachricht verschwindet für euch beide und lässt sich nicht wiederherstellen.</p>
	{#if deleteTarget}<blockquote class="quote">{deleteTarget.body}</blockquote>{/if}
</ConfirmDialog>

<ConfirmDialog bind:open={blockOpen} title="{partnerName} blockieren" confirmLabel="Blockieren" danger busy={blocking} onconfirm={block} testid="block">
	<p>Das Gespräch endet sofort für euch beide. Ihr seht euch gegenseitig nicht mehr und könnt euch nicht mehr schreiben.</p>
	<p class="mt-3 text-sm text-ink-muted">Wenn du eine Nachricht melden möchtest, tu das zuerst. Nach dem Blockieren kannst du nur noch das Profil melden.</p>
</ConfirmDialog>

{#if reportTarget}
	<ReportDialog bind:open={reportOpen} targetType="message" targetId={reportTarget.id} {conversationId} subject="Nachricht von {partnerName}" />
{/if}

<style>
	.page {
		display: grid;
		gap: var(--hs-space-4);
		max-width: 44rem;
	}

	.head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--hs-space-3);
	}

	.title {
		font-size: var(--hs-text-xl);
		overflow-wrap: anywhere;
	}

	.title a {
		color: var(--hs-ink);
	}

	.messages {
		height: min(58dvh, 34rem);
		min-height: 14rem;
		overflow-y: auto;
		padding: var(--hs-space-4);
		border: 1px solid var(--hs-line);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
		overscroll-behavior: contain;
	}

	.older {
		display: flex;
		justify-content: center;
		margin-bottom: var(--hs-space-4);
	}

	.none {
		color: var(--hs-ink-muted);
	}

	ol {
		display: grid;
		gap: var(--hs-space-3);
		list-style: none;
		margin: 0;
		padding: 0;
	}

	li {
		display: grid;
		justify-items: start;
		gap: 0.125rem;
	}

	li.mine {
		justify-items: end;
	}

	.bubble {
		max-width: min(34rem, 88%);
		padding: var(--hs-space-2) var(--hs-space-3);
		border: 1px solid var(--hs-line);
		border-radius: var(--hs-radius-md);
		background: var(--hs-raised);
	}

	.mine .bubble {
		background: var(--hs-accent-soft);
		border-color: transparent;
	}

	.who {
		font-size: var(--hs-text-xs);
		font-weight: var(--hs-weight-strong);
		color: var(--hs-ink-muted);
	}

	.when {
		margin-left: var(--hs-space-2);
		font-weight: var(--hs-weight-regular);
	}

	.text {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}

	.action {
		min-height: 1.75rem;
		padding: 0 var(--hs-space-2);
		border: 0;
		border-radius: var(--hs-radius-sm);
		background: transparent;
		color: var(--hs-ink-muted);
		font: inherit;
		font-size: var(--hs-text-xs);
		text-decoration: underline;
		text-underline-offset: 0.18em;
		cursor: pointer;
	}

	.action:hover {
		color: var(--hs-ink);
		background: var(--hs-sunken);
	}

	.composer {
		display: grid;
		gap: var(--hs-space-2);
	}

	.send-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--hs-space-3);
	}

	.send-row p {
		flex: 1 1 16rem;
	}

	.quote {
		margin: var(--hs-space-3) 0 0;
		padding: var(--hs-space-2) var(--hs-space-3);
		border-left: 3px solid var(--hs-line-strong);
		background: var(--hs-raised);
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		max-height: 8rem;
		overflow: auto;
	}
</style>
