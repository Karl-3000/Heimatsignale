<script lang="ts">
	import type { HTMLTextareaAttributes } from 'svelte/elements';

	/** Mehrzeiliges Textfeld mit Zeichenzähler. */
	interface Props extends Omit<HTMLTextareaAttributes, 'value' | 'class'> {
		label: string;
		value?: string;
		hint?: string;
		error?: string | null;
		max?: number;
		testid?: string;
		hideLabel?: boolean;
	}

	let { label, value = $bindable(''), hint, error = null, max, testid, hideLabel = false, rows = 4, ...rest }: Props = $props();

	const uid = $props.id();
	const length = $derived(value.length);
	const over = $derived(max !== undefined && length > max);
	const describedBy = $derived(
		[hint ? `${uid}-hint` : '', max !== undefined ? `${uid}-count` : '', error ? `${uid}-error` : ''].filter(Boolean).join(' ') || undefined
	);
</script>

<div class="field">
	<label for={uid} class={hideLabel ? 'hs-sr-only' : ''}>{label}</label>
	{#if hint}<p id="{uid}-hint" class="hint">{hint}</p>{/if}
	<textarea
		id={uid}
		{rows}
		bind:value
		aria-invalid={error || over ? 'true' : undefined}
		aria-describedby={describedBy}
		data-testid={testid}
		{...rest}
	></textarea>
	<div class="below">
		{#if error}<p id="{uid}-error" class="error" role="alert">{error}</p>{:else}<span></span>{/if}
		{#if max !== undefined}
			<p id="{uid}-count" class="count hs-num" class:over>
				{length} von {max} Zeichen{#if over}, zu lang{/if}
			</p>
		{/if}
	</div>
</div>

<style>
	.field {
		display: flex;
		flex-direction: column;
		gap: var(--hs-space-2);
	}

	label {
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
	}

	.hint {
		margin-top: calc(var(--hs-space-1) * -1);
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	textarea {
		width: 100%;
		padding: var(--hs-space-3) var(--hs-space-4);
		border: 0;
		border-radius: var(--hs-radius-md);
		background: var(--hs-sunken);
		box-shadow: inset 0 0 0 1px transparent;
		color: var(--hs-ink);
		font: inherit;
		line-height: var(--hs-leading-normal);
		resize: vertical;
		transition:
			box-shadow var(--hs-duration-fast) var(--hs-ease-standard),
			background-color var(--hs-duration-fast) var(--hs-ease-standard);
	}

	textarea::placeholder {
		color: var(--hs-ink-subtle);
	}

	textarea:hover {
		box-shadow: inset 0 0 0 1px var(--hs-line-strong);
	}

	textarea:focus-visible {
		outline: none;
		background: var(--hs-raised);
		box-shadow: inset 0 0 0 2px var(--hs-focus);
	}

	textarea[aria-invalid='true'] {
		box-shadow: inset 0 0 0 2px var(--hs-danger);
	}

	.below {
		display: flex;
		justify-content: space-between;
		gap: var(--hs-space-3);
	}

	.error {
		font-size: var(--hs-text-sm);
		color: var(--hs-danger);
		font-weight: var(--hs-weight-strong);
	}

	.count {
		font-size: var(--hs-text-xs);
		color: var(--hs-ink-subtle);
		white-space: nowrap;
	}

	.count.over {
		color: var(--hs-danger);
		font-weight: var(--hs-weight-strong);
	}
</style>
