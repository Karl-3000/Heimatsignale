<script lang="ts">
	/**
	 * Umschalter für den Umkreis (z. B. 20 km oder 100 km) als Optionsgruppe:
	 * mit Tab erreichbar, mit den Pfeiltasten umschaltbar, die Wahl ist ablesbar.
	 */
	interface Props {
		options: number[];
		value: number | null;
		disabled?: boolean;
		onchange: (radiusKm: number) => void;
	}

	let { options, value, disabled = false, onchange }: Props = $props();

	const uid = $props.id();
</script>

<fieldset class="radius" data-testid="radius-toggle" {disabled}>
	<legend>Umkreis</legend>
	<div class="options">
		{#each options as option (option)}
			<label class:checked={value === option}>
				<input
					type="radio"
					name="{uid}-radius"
					value={option}
					checked={value === option}
					onchange={() => onchange(option)}
					data-testid="radius-{option}"
				/>
				<span class="hs-num">{option} km</span>
			</label>
		{/each}
	</div>
</fieldset>

<style>
	.radius {
		display: flex;
		align-items: center;
		gap: var(--hs-space-3);
		border: 0;
		margin: 0;
		padding: 0;
		min-width: 0;
	}

	legend {
		float: left;
		padding: 0;
		margin-right: var(--hs-space-3);
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.options {
		display: inline-flex;
		gap: 2px;
		padding: 3px;
		border-radius: var(--hs-radius-md);
		background: var(--hs-sunken);
	}

	label {
		position: relative;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-height: 2.375rem;
		min-width: 4.25rem;
		padding: 0 var(--hs-space-3);
		border: 1px solid transparent;
		border-radius: calc(var(--hs-radius-md) - 3px);
		color: var(--hs-ink-muted);
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
		cursor: pointer;
	}

	label:hover {
		color: var(--hs-ink);
	}

	label.checked {
		background: var(--hs-raised);
		border-color: var(--hs-line-strong);
		color: var(--hs-ink);
		box-shadow: var(--hs-shadow-sm);
	}

	input {
		position: absolute;
		inset: 0;
		margin: 0;
		opacity: 0;
		cursor: pointer;
	}

	label:has(input:focus-visible) {
		outline: 2px solid var(--hs-focus);
		outline-offset: 1px;
	}

	.radius:disabled label {
		cursor: progress;
		opacity: 0.7;
	}
</style>
