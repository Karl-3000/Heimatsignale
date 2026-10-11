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
	const index = $derived(value === null ? -1 : options.indexOf(value));
</script>

<fieldset class="radius" data-testid="radius-toggle" {disabled}>
	<legend>Umkreis</legend>
	<div class="hs-seg" style:--seg-count={options.length} style:--seg-index={Math.max(0, index)} data-seg-index={index}>
		{#each options as option (option)}
			<label class="hs-seg-item" data-on={value === option ? 'true' : 'false'}>
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

	label {
		min-width: 4.75rem;
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
		outline-offset: 2px;
	}

	.radius:disabled label {
		cursor: progress;
		opacity: 0.7;
	}
</style>
