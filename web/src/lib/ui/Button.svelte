<script lang="ts">
	import type { Component, Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import Icon from './Icon.svelte';

	interface Props extends Omit<HTMLAttributes<HTMLElement>, 'children'> {
		variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'glass';
		size?: 'md' | 'sm';
		/** Mit href wird ein Link im Aussehen eines Buttons gezeichnet. */
		href?: string;
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		loading?: boolean;
		block?: boolean;
		/** Runder Button nur mit Icon. Braucht dann ein aria-label. */
		round?: boolean;
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		icon?: Component<any>;
		testid?: string;
		/** Nur für Links: rel="external" verlässt die App (z. B. zum Admin-Bereich). */
		rel?: string;
		/** Kennung des Formulars, falls der Button außerhalb davon steht. */
		form?: string;
		children?: Snippet;
	}

	let {
		variant = 'secondary',
		size = 'md',
		href,
		type = 'button',
		disabled = false,
		loading = false,
		block = false,
		round = false,
		icon,
		testid,
		children,
		class: className = '',
		...rest
	}: Props = $props();

	const classes = $derived(['btn', `btn-${variant}`, `btn-${size}`, block ? 'btn-block' : '', round ? 'btn-round' : '', className].filter(Boolean).join(' '));
</script>

{#if href && !disabled}
	<a {href} class={classes} data-testid={testid} {...rest}>
		{#if icon}<Icon {icon} size={size === 'sm' ? 16 : 18} />{/if}
		{#if children}<span>{@render children()}</span>{/if}
	</a>
{:else}
	<button {type} class={classes} disabled={disabled || loading} aria-busy={loading ? 'true' : undefined} data-testid={testid} {...rest}>
		{#if loading}
			<span class="spin"><Icon icon={LoaderCircle} size={size === 'sm' ? 16 : 18} /></span>
		{:else if icon}
			<Icon {icon} size={size === 'sm' ? 16 : 18} />
		{/if}
		{#if children}<span>{@render children()}</span>{/if}
	</button>
{/if}

<style>
	.btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--hs-space-2);
		min-height: var(--hs-control-height);
		padding: 0.5rem var(--hs-space-5);
		border: 0;
		border-radius: var(--hs-radius-full);
		font: inherit;
		font-weight: var(--hs-weight-strong);
		font-size: var(--hs-text-base);
		line-height: 1.2;
		text-decoration: none;
		text-align: center;
		max-width: 100%;
		cursor: pointer;
		transition:
			background-color var(--hs-duration-fast) var(--hs-ease-standard),
			color var(--hs-duration-fast) var(--hs-ease-standard),
			transform var(--hs-duration-fast) var(--hs-ease-standard);
	}

	.btn:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: 3px;
		border-radius: var(--hs-radius-full);
	}

	.btn:active:not(:disabled) {
		transform: scale(0.98);
	}

	.btn:disabled {
		cursor: not-allowed;
		opacity: 0.5;
	}

	.btn-sm {
		min-height: 2.5rem;
		padding: 0.375rem var(--hs-space-4);
		font-size: var(--hs-text-sm);
	}

	.btn-block {
		display: flex;
		width: 100%;
	}

	.btn-round {
		width: var(--hs-control-height);
		padding: 0;
		flex: none;
	}

	.btn-primary {
		background: var(--hs-accent);
		color: var(--hs-on-accent);
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--hs-accent-hover);
		color: var(--hs-on-accent);
	}

	.btn-secondary {
		background: var(--hs-accent-soft);
		color: var(--hs-accent-ink);
	}

	.btn-secondary:hover:not(:disabled) {
		background: color-mix(in srgb, var(--hs-accent-soft) 82%, var(--hs-accent));
		color: var(--hs-accent-ink);
	}

	.btn-ghost {
		padding-left: var(--hs-space-3);
		padding-right: var(--hs-space-3);
		background: transparent;
		color: var(--hs-accent-ink);
	}

	.btn-ghost:hover:not(:disabled) {
		background: var(--hs-accent-soft);
	}

	.btn-danger {
		background: var(--hs-danger-soft);
		color: var(--hs-danger);
	}

	.btn-danger:hover:not(:disabled) {
		background: color-mix(in srgb, var(--hs-danger-soft) 82%, var(--hs-danger));
	}

	/* Auf der Bühne: gläserne Pille mit heller Schrift. */
	.btn-glass {
		background: var(--hs-stage-glass);
		color: var(--hs-stage-ink);
		box-shadow: inset 0 0 0 1px var(--hs-stage-line);
	}

	.btn-glass:hover:not(:disabled) {
		background: var(--hs-stage-glass-strong);
		color: var(--hs-stage-ink);
	}

	.btn-glass:focus-visible {
		outline-color: var(--hs-stage-accent);
	}

	.spin {
		display: inline-flex;
		animation: hs-spin 900ms linear infinite;
	}

	@keyframes hs-spin {
		to {
			transform: rotate(360deg);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.spin {
			animation: none;
		}
	}
</style>
