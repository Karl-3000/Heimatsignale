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
		top: calc(4.75rem + env(safe-area-inset-top, 0px));
		transform: translateX(-50%);
		z-index: 60;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--hs-space-2);
		width: min(30rem, calc(100vw - 2rem));
		pointer-events: none;
	}

	/* Dunkle Pille, in beiden Themen. */
	.toast {
		display: flex;
		align-items: center;
		gap: var(--hs-space-3);
		max-width: 100%;
		padding: var(--hs-space-2) var(--hs-space-2) var(--hs-space-2) var(--hs-space-4);
		border-radius: 1.75rem;
		border: 1px solid var(--hs-stage-line);
		background: var(--hs-tinte);
		color: var(--hs-stage-ink);
		box-shadow: var(--hs-shadow-lg);
		font-size: var(--hs-text-sm);
		pointer-events: auto;
		animation: hs-toast-in var(--hs-duration-slow) var(--hs-ease-out);
	}

	@keyframes hs-toast-in {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
	}

	.glyph {
		display: inline-flex;
		flex: none;
		color: var(--hs-stage-accent);
	}

	.toast-error .glyph {
		color: var(--hs-stage-danger);
	}

	.toast-success .glyph {
		color: var(--hs-stage-success);
	}

	p {
		flex: 1;
		min-width: 0;
		padding: var(--hs-space-1) 0;
	}

	button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.25rem;
		height: 2.25rem;
		flex: none;
		border: 0;
		border-radius: 50%;
		background: var(--hs-stage-glass);
		color: var(--hs-stage-ink);
		cursor: pointer;
	}

	button:hover {
		background: var(--hs-stage-glass-strong);
	}

	button:focus-visible {
		outline-color: var(--hs-stage-accent);
	}
</style>
