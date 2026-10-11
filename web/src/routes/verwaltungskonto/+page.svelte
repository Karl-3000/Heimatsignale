<script lang="ts">
	import { session } from '$lib/api/session.svelte';
	import Button from '$lib/ui/Button.svelte';
	import FormPage from '$lib/ui/FormPage.svelte';
</script>

<svelte:head>
	<title>Admin-Konto – {session.siteName}</title>
</svelte:head>

<FormPage title="Das ist ein Admin-Konto" lead="Mit diesem Konto verwaltest du den Dienst. Es nimmt nicht am Umkreis teil und ist für andere nicht sichtbar.">
	<div data-testid="staff-page">
		<Button href={session.adminPath} variant="primary" rel="external" testid="staff-admin-link">Zum Admin-Bereich</Button>
	</div>
</FormPage>
