<script lang="ts">
	import type { Snippet } from 'svelte';
	import X from '@lucide/svelte/icons/x';
	import Icon from './Icon.svelte';

	/**
	 * Modaler Dialog auf Basis des nativen <dialog>-Elements: showModal() liefert
	 * Fokusfalle, Escape zum Schließen und die Rückgabe des Fokus an den Auslöser.
	 */
	interface Props {
		open?: boolean;
		title: string;
		testid?: string;
		onclose?: () => void;
		children: Snippet;
		footer?: Snippet;
	}

	let { open = $bindable(false), title, testid, onclose, children, footer }: Props = $props();

	const uid = $props.id();
	let element = $state<HTMLDialogElement | null>(null);

	$effect(() => {
		const el = element;
		if (!el) return;
		if (open && !el.open) el.showModal();
		else if (!open && el.open) el.close();
	});

	function handleClose(): void {
		if (open) open = false;
		onclose?.();
	}

	function handleBackdrop(event: MouseEvent): void {
		// Ein Klick auf den abgedunkelten Rand trifft das dialog-Element selbst.
		if (event.target === element) open = false;
	}
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
<dialog bind:this={element} aria-labelledby="{uid}-title" data-testid={testid} onclose={handleClose} onclick={handleBackdrop}>
	<div class="panel">
		<header>
			<h2 id="{uid}-title">{title}</h2>
			<button type="button" class="close" onclick={() => (open = false)} aria-label="Schließen">
				<Icon icon={X} size={20} />
			</button>
		</header>
		<div class="content">
			{@render children()}
		</div>
		{#if footer}
			<footer>{@render footer()}</footer>
		{/if}
	</div>
</dialog>

<style>
	dialog {
		width: min(34rem, calc(100vw - 2rem));
		max-height: calc(100dvh - 2rem);
		margin: auto;
		padding: 0;
		border: 0;
		border-radius: var(--hs-radius-stage);
		background: var(--hs-surface);
		color: var(--hs-ink);
		box-shadow: var(--hs-shadow-lg);
		overflow: hidden;
	}

	dialog::backdrop {
		background: var(--hs-backdrop);
		backdrop-filter: blur(10px);
		-webkit-backdrop-filter: blur(10px);
	}

	dialog[open] {
		animation: hs-dialog-in var(--hs-duration-slow) var(--hs-ease-out);
	}

	@keyframes hs-dialog-in {
		from {
			opacity: 0;
			transform: translateY(12px) scale(0.98);
		}
	}

	.panel {
		display: flex;
		flex-direction: column;
		max-height: calc(100dvh - 2rem);
	}

	header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--hs-space-3);
		padding: var(--hs-space-5) var(--hs-space-4) 0 var(--hs-space-6);
	}

	h2 {
		font-size: var(--hs-text-xl);
		padding-top: var(--hs-space-2);
	}

	.close {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.75rem;
		height: 2.75rem;
		flex: none;
		border: 0;
		border-radius: 50%;
		background: var(--hs-sunken);
		color: var(--hs-ink-muted);
		cursor: pointer;
	}

	.close:hover {
		color: var(--hs-ink);
	}

	.content {
		padding: var(--hs-space-4) var(--hs-space-6) var(--hs-space-6);
		overflow-y: auto;
	}

	footer {
		display: flex;
		flex-wrap: wrap;
		justify-content: flex-end;
		gap: var(--hs-space-2);
		padding: var(--hs-space-4) var(--hs-space-6) var(--hs-space-5);
		border-top: 1px solid var(--hs-line);
	}

	@media (max-width: 480px) {
		header {
			padding-left: var(--hs-space-5);
		}

		.content {
			padding-left: var(--hs-space-5);
			padding-right: var(--hs-space-5);
		}

		footer {
			padding-left: var(--hs-space-5);
			padding-right: var(--hs-space-5);
		}
	}
</style>
