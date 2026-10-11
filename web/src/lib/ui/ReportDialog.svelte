<script lang="ts">
	import Dialog from './Dialog.svelte';
	import Button from './Button.svelte';
	import TextArea from './TextArea.svelte';
	import Notice from './Notice.svelte';
	import { toasts } from './toast.svelte';
	import { sendReport } from '$lib/api/endpoints';
	import { errorMessage } from '$lib/api/client';
	import { REPORT_REASONS, type ReportReason, type ReportTargetType } from '$lib/api/types';

	/**
	 * Meldeformular für ein Profil, eine Kontaktanfrage oder eine Nachricht.
	 * Es nennt die Grenze des Schnappschusses (Projektplan, Abschnitt 8).
	 */
	interface Props {
		open?: boolean;
		targetType: ReportTargetType;
		targetId: string;
		conversationId?: string | null;
		/** Wen oder was die Meldung betrifft, z. B. der Nickname. */
		subject: string;
		onsent?: () => void;
	}

	let { open = $bindable(false), targetType, targetId, conversationId = null, subject, onsent }: Props = $props();

	const uid = $props.id();
	let reason = $state<ReportReason | ''>('');
	let note = $state('');
	let busy = $state(false);
	let failure = $state<string | null>(null);
	let missing = $state(false);

	const heading = $derived(targetType === 'message' ? 'Nachricht melden' : targetType === 'request' ? 'Anfrage melden' : 'Profil melden');

	$effect(() => {
		if (open) {
			reason = '';
			note = '';
			failure = null;
			missing = false;
		}
	});

	async function submit(event: SubmitEvent): Promise<void> {
		event.preventDefault();
		if (!reason) {
			missing = true;
			return;
		}
		busy = true;
		failure = null;
		try {
			await sendReport({ target_type: targetType, target_id: targetId, conversation_id: conversationId, reason, note: note.trim() });
			open = false;
			toasts.success('Meldung gesendet. Das Moderationsteam prüft sie in der Regel innerhalb von 72 Stunden.');
			onsent?.();
		} catch (e) {
			failure = errorMessage(e);
		} finally {
			busy = false;
		}
	}
</script>

<Dialog bind:open title={heading} testid="report-dialog">
	<form id="{uid}-form" onsubmit={submit} class="form" novalidate>
		<p class="subject">Betrifft: <strong>{subject}</strong></p>

		<fieldset aria-describedby={missing ? `${uid}-missing` : undefined}>
			<legend>Grund</legend>
			{#each REPORT_REASONS as option (option.value)}
				<label class="option">
					<input type="radio" name="{uid}-reason" value={option.value} bind:group={reason} data-testid="report-reason-{option.value}" />
					<span>{option.label}</span>
				</label>
			{/each}
			{#if missing && !reason}<p id="{uid}-missing" class="error" role="alert">Bitte wähle einen Grund.</p>{/if}
		</fieldset>

		<TextArea label="Beschreibung (freiwillig)" bind:value={note} max={1000} rows={3} hint="Was ist passiert? Kurz genügt." testid="report-note" />

		<Notice tone="info" title="Was das Moderationsteam sieht">
			{#if targetType === 'message'}
				<p>Die gemeldete Nachricht und bis zu 10 Nachrichten davor aus diesem Gespräch werden als Kopie an die Meldung gehängt. Mehr von deinem Postfach sieht niemand.</p>
			{:else if targetType === 'request'}
				<p>Der Text der Anfrage wird als Kopie an die Meldung gehängt.</p>
			{:else}
				<p>Die sichtbaren Profilangaben werden als Kopie an die Meldung gehängt.</p>
			{/if}
			<p>Die Kopie sichert nur, was jetzt noch vorhanden ist. Hat die andere Person ihren Text vorher gelöscht, enthält die Meldung den Vermerk "Inhalt vom Absender gelöscht" und deine Beschreibung.</p>
		</Notice>

		{#if failure}<Notice tone="danger" live testid="report-error"><p>{failure}</p></Notice>{/if}
	</form>
	{#snippet footer()}
		<Button onclick={() => (open = false)}>Abbrechen</Button>
		<Button variant="primary" type="submit" form="{uid}-form" loading={busy} testid="report-submit">Meldung senden</Button>
	{/snippet}
</Dialog>

<style>
	.form {
		display: flex;
		flex-direction: column;
		gap: var(--hs-space-4);
	}

	.subject {
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	fieldset {
		border: 0;
		padding: 0;
		margin: 0;
		min-width: 0;
	}

	legend {
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
		padding: 0;
		margin-bottom: var(--hs-space-1);
	}

	.option {
		display: flex;
		align-items: center;
		gap: var(--hs-space-3);
		min-height: 2.5rem;
		cursor: pointer;
	}

	.option input {
		width: 1.125rem;
		height: 1.125rem;
		accent-color: var(--hs-accent);
	}

	.error {
		font-size: var(--hs-text-sm);
		color: var(--hs-danger);
		font-weight: var(--hs-weight-strong);
	}
</style>
