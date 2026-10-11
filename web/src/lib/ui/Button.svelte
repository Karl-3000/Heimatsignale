<script lang="ts">
	import type { Component, Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import Icon from './Icon.svelte';

	interface Props extends Omit<HTMLAttributes<HTMLElement>, 'children'> {
		variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
		size?: 'md' | 'sm';
		/** Mit href wird ein Link im Aussehen eines Buttons gezeichnet. */
		href?: string;
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		loading?: boolean;
		block?: boolean;
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		icon?: Component<any>;
		testid?: string;
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
		icon,
		testid,
		children,
		class: className = '',
		...rest
	}: Props = $props();

	const classes = $derived(['btn', `btn-${variant}`, `btn-${size}`, block ? 'btn-block' : '', className].filter(Boolean).join(' '));
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
		padding: 0 var(--hs-space-4);
		border: 1px solid transparent;
		border-radius: var(--hs-radius-md);
		font: inherit;
		font-weight: var(--hs-weight-strong);
		font-size: var(--hs-text-sm);
		line-height: 1.2;
		text-decoration: none;
		cursor: pointer;
		transition:
			background-color var(--hs-duration-fast) var(--hs-ease-standard),
			border-color var(--hs-duration-fast) var(--hs-ease-standard),
			color var(--hs-duration-fast) var(--hs-ease-standard);
	}

	.btn:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: 2px;
	}

	.btn:disabled {
		cursor: not-allowed;
		opacity: 0.55;
	}

	.btn-sm {
		min-height: 2.25rem;
		padding: 0 var(--hs-space-3);
	}

	.btn-block {
		display: flex;
		width: 100%;
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
		background: var(--hs-raised);
		border-color: var(--hs-line-strong);
		color: var(--hs-ink);
	}

	.btn-secondary:hover:not(:disabled) {
		background: var(--hs-sunken);
		color: var(--hs-ink);
	}

	.btn-ghost {
		background: transparent;
		color: var(--hs-accent);
	}

	.btn-ghost:hover:not(:disabled) {
		background: var(--hs-accent-soft);
		color: var(--hs-ink);
	}

	.btn-danger {
		background: var(--hs-raised);
		border-color: var(--hs-danger);
		color: var(--hs-danger);
	}

	.btn-danger:hover:not(:disabled) {
		background: var(--hs-danger-soft);
		color: var(--hs-ink);
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
