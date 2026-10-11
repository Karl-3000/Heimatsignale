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
		gap: var(--hs-space-1);
	}

	label {
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
	}

	.hint {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	textarea {
		width: 100%;
		padding: var(--hs-space-3);
		border: 1px solid var(--hs-line-strong);
		border-radius: var(--hs-radius-md);
		background: var(--hs-raised);
		color: var(--hs-ink);
		font: inherit;
		line-height: var(--hs-leading-normal);
		resize: vertical;
	}

	textarea:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: 1px;
		border-color: var(--hs-focus);
	}

	textarea[aria-invalid='true'] {
		border-color: var(--hs-danger);
		border-width: 2px;
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
