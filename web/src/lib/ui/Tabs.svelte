<script lang="ts" module>
	export interface TabItem {
		id: string;
		label: string;
		count?: number;
	}
</script>

<script lang="ts">
	/**
	 * Reiterleiste nach dem ARIA-Muster "Tabs" mit automatischer Aktivierung:
	 * Pfeiltasten wechseln den Reiter, Pos1 und Ende springen an die Ränder.
	 * Die zugehörigen Flächen zeichnet die aufrufende Seite mit
	 * role="tabpanel", id="{idBase}-panel-{id}" und aria-labelledby="{idBase}-tab-{id}".
	 */
	interface Props {
		tabs: TabItem[];
		value: string;
		label: string;
		idBase: string;
		testid?: string;
		onchange?: (id: string) => void;
	}

	let { tabs, value = $bindable(), label, idBase, testid, onchange }: Props = $props();

	let list = $state<HTMLDivElement | null>(null);

	function select(id: string, focus: boolean): void {
		if (id !== value) {
			value = id;
			onchange?.(id);
		}
		if (focus) {
			const el = list?.querySelector<HTMLButtonElement>(`[data-tab="${id}"]`);
			el?.focus();
		}
	}

	function handleKey(event: KeyboardEvent): void {
		const index = tabs.findIndex((t) => t.id === value);
		let next = -1;
		if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
		else if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
		else if (event.key === 'Home') next = 0;
		else if (event.key === 'End') next = tabs.length - 1;
		if (next < 0) return;
		event.preventDefault();
		select(tabs[next].id, true);
	}
</script>

<div class="tabs" role="tablist" aria-label={label} bind:this={list} data-testid={testid}>
	{#each tabs as tab (tab.id)}
		<button
			type="button"
			role="tab"
			id="{idBase}-tab-{tab.id}"
			aria-selected={tab.id === value ? 'true' : 'false'}
			aria-controls="{idBase}-panel-{tab.id}"
			tabindex={tab.id === value ? 0 : -1}
			data-tab={tab.id}
			data-testid={testid ? `${testid}-${tab.id}` : undefined}
			class:selected={tab.id === value}
			onclick={() => select(tab.id, false)}
			onkeydown={handleKey}
		>
			<span>{tab.label}</span>
			{#if tab.count !== undefined}<span class="count hs-num">{tab.count}</span>{/if}
		</button>
	{/each}
</div>

<style>
	.tabs {
		display: inline-flex;
		gap: 2px;
		padding: 3px;
		border-radius: var(--hs-radius-md);
		background: var(--hs-sunken);
		max-width: 100%;
		overflow-x: auto;
	}

	button {
		display: inline-flex;
		align-items: center;
		gap: var(--hs-space-2);
		min-height: 2.375rem;
		padding: 0 var(--hs-space-4);
		border: 1px solid transparent;
		border-radius: calc(var(--hs-radius-md) - 3px);
		background: transparent;
		color: var(--hs-ink-muted);
		font: inherit;
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
		white-space: nowrap;
		cursor: pointer;
		transition: background-color var(--hs-duration-fast) var(--hs-ease-standard);
	}

	button:hover {
		color: var(--hs-ink);
	}

	button.selected {
		background: var(--hs-raised);
		border-color: var(--hs-line-strong);
		color: var(--hs-ink);
		box-shadow: var(--hs-shadow-sm);
	}

	button:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: 1px;
	}

	.count {
		min-width: 1.375rem;
		padding: 0 0.375rem;
		border-radius: var(--hs-radius-full);
		background: var(--hs-accent-soft);
		color: var(--hs-ink);
		font-size: var(--hs-text-xs);
		line-height: 1.375rem;
		text-align: center;
	}
</style>
