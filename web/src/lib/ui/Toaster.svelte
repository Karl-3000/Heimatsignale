<script lang="ts">
	import X from '@lucide/svelte/icons/x';
	import Info from '@lucide/svelte/icons/info';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import TriangleAlert from '@lucide/svelte/icons/triangle-alert';
	import Icon from './Icon.svelte';
	import { toasts } from './toast.svelte';
</script>

<!-- Die Region besteht immer, damit Screenreader neue Meldungen ansagen. -->
<div class="toaster" role="status" aria-live="polite" aria-atomic="false" data-testid="toaster">
	{#each toasts.items as toast (toast.id)}
		<div class="toast toast-{toast.kind}" data-testid="toast">
			<span class="glyph">
				<Icon icon={toast.kind === 'success' ? CircleCheck : toast.kind === 'error' ? TriangleAlert : Info} size={18} />
			</span>
			<p>
				{#if toast.kind === 'error'}<span class="hs-sr-only">Fehler: </span>{/if}{toast.message}
			</p>
			<button type="button" onclick={() => toasts.dismiss(toast.id)} aria-label="Meldung schließen">
				<Icon icon={X} size={16} />
			</button>
		</div>
	{/each}
</div>

<style>
	.toaster {
		position: fixed;
		left: 50%;
		bottom: calc(var(--hs-space-4) + env(safe-area-inset-bottom, 0px) + var(--hs-toast-offset, 0px));
		transform: translateX(-50%);
		z-index: 60;
		display: flex;
		flex-direction: column;
		gap: var(--hs-space-2);
		width: min(28rem, calc(100vw - 2rem));
		pointer-events: none;
	}

	.toast {
		display: flex;
		align-items: flex-start;
		gap: var(--hs-space-3);
		padding: var(--hs-space-3) var(--hs-space-3) var(--hs-space-3) var(--hs-space-4);
		border-radius: var(--hs-radius-md);
		border: 1px solid var(--hs-line-strong);
		border-left-width: 4px;
		background: var(--hs-raised);
		color: var(--hs-ink);
		box-shadow: var(--hs-shadow-md);
		font-size: var(--hs-text-sm);
		pointer-events: auto;
		animation: hs-toast-in var(--hs-duration-base) var(--hs-ease-standard);
	}

	@keyframes hs-toast-in {
		from {
			opacity: 0;
			transform: translateY(6px);
		}
	}

	.toast-success {
		border-left-color: var(--hs-success);
	}

	.toast-error {
		border-left-color: var(--hs-danger);
	}

	.toast-info {
		border-left-color: var(--hs-accent);
	}

	.glyph {
		flex: none;
		margin-top: 0.0625rem;
	}

	p {
		flex: 1;
		min-width: 0;
	}

	button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.75rem;
		height: 1.75rem;
		flex: none;
		border: 0;
		border-radius: var(--hs-radius-sm);
		background: transparent;
		color: var(--hs-ink-muted);
		cursor: pointer;
	}

	button:hover {
		background: var(--hs-sunken);
		color: var(--hs-ink);
	}
</style>
