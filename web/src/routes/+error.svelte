<script lang="ts">
	import { page } from '$app/state';
	import Button from '$lib/ui/Button.svelte';
	import FormPage from '$lib/ui/FormPage.svelte';
	import { session } from '$lib/api/session.svelte';
</script>

<svelte:head>
	<title>{page.status === 404 ? 'Seite nicht gefunden' : 'Fehler'} – {session.siteName}</title>
</svelte:head>

<FormPage
	title={page.status === 404 ? 'Diese Seite gibt es nicht' : 'Da ist etwas schiefgegangen'}
	lead={page.status === 404 ? 'Die Adresse ist falsch oder die Seite wurde entfernt.' : 'Lade die Seite neu. Wenn der Fehler bleibt, versuche es später noch einmal.'}
>
	<div data-testid="error-page">
		<Button href={session.authenticated ? '/umkreis' : '/'} variant="primary">{session.authenticated ? 'Zum Umkreis' : 'Zur Startseite'}</Button>
	</div>
</FormPage>
