<script lang="ts">
	import { session } from '$lib/api/session.svelte';
	import LegalPage from '$lib/ui/LegalPage.svelte';
</script>

<svelte:head>
	<title>Impressum – {session.siteName}</title>
</svelte:head>

<LegalPage title="Impressum">
	<h2>Anbieter</h2>
	<address>
		<span class="todo">TODO: Name des Betreibers (natürliche Person oder Organisation mit Rechtsform)</span><br />
		<span class="todo">TODO: Straße und Hausnummer</span><br />
		<span class="todo">TODO: Postleitzahl und Ort</span>
	</address>

	<h2>Kontakt</h2>
	<p>
		E-Mail: <span class="todo">TODO: E-Mail-Adresse</span><br />
		Telefon: <span class="todo">TODO: Telefonnummer oder ein anderer schneller Kontaktweg</span>
	</p>

	<h2>Vertretungsberechtigt</h2>
	<p><span class="todo">TODO: Vertretungsberechtigte Person, falls der Betreiber eine Organisation ist. Sonst diesen Abschnitt entfernen.</span></p>

	<h2>Registereintrag und Umsatzsteuer</h2>
	<p><span class="todo">TODO: Register, Registernummer und Umsatzsteuer-Identifikationsnummer, soweit vorhanden. Sonst diesen Abschnitt entfernen.</span></p>

	<h2>Verantwortlich für den Inhalt</h2>
	<p><span class="todo">TODO: Name und Anschrift der inhaltlich verantwortlichen Person</span></p>

	<h2>Meldungen zu Inhalten</h2>
	<p>
		Angemeldete Mitglieder melden Profile, Anfragen und Nachrichten direkt im Dienst über „Melden“. Wer kein Konto hat, schreibt an
		<span class="todo">TODO: Kontaktadresse für Hinweise auf rechtswidrige Inhalte</span>.
	</p>

	<h2>Quelltext</h2>
	<p>
		Die Software hinter {session.siteName} ist freie Software unter der Lizenz AGPL-3.0. Quelltext:
		<span class="todo">TODO: Adresse des öffentlichen Repositorys</span>
	</p>
</LegalPage>
