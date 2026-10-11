<script lang="ts">
	import type { Snippet } from 'svelte';
	import Dialog from './Dialog.svelte';
	import Button from './Button.svelte';

	/** Rückfrage vor einer Aktion mit Folgen. Der Abbruch steht immer zuerst. */
	interface Props {
		open?: boolean;
		title: string;
		confirmLabel: string;
		danger?: boolean;
		busy?: boolean;
		testid?: string;
		onconfirm: () => void | Promise<void>;
		children: Snippet;
	}

	let { open = $bindable(false), title, confirmLabel, danger = false, busy = false, testid = 'confirm', onconfirm, children }: Props = $props();
</script>

<Dialog bind:open {title} testid="{testid}-dialog">
	{@render children()}
	{#snippet footer()}
		<Button onclick={() => (open = false)} testid="{testid}-cancel">Abbrechen</Button>
		<Button variant={danger ? 'danger' : 'primary'} loading={busy} onclick={() => void onconfirm()} testid="{testid}-ok">{confirmLabel}</Button>
	{/snippet}
</Dialog>
