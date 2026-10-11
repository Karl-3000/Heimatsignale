<script lang="ts">
	import { session } from '$lib/api/session.svelte';
	import LegalPage from '$lib/ui/LegalPage.svelte';
</script>

<svelte:head>
	<title>Nutzungsbedingungen – {session.siteName}</title>
</svelte:head>

<LegalPage title="Nutzungsbedingungen">
	<p>
		Anbieter des Dienstes ist <span class="todo">TODO: Name des Betreibers</span> (siehe <a href="/impressum">Impressum</a>). Mit der Registrierung
		stimmst du diesen Bedingungen zu.
	</p>

	<h2>1. Zweck des Dienstes</h2>
	<p>
		{session.siteName} hilft Menschen, die in eine neue Stadt gezogen sind, andere Zugezogene aus der eigenen Heimatregion im Umkreis zu
		finden. Der Umkreis beträgt {session.defaultRadius} km um den Wohnort und lässt sich auf {session.maxRadius} km erweitern. Andere Mitglieder können dich aus bis
		zu {session.maxRadius} km Entfernung sehen und dir eine Kontaktanfrage senden. Der Dienst gilt nur für Deutschland: Heimatort und Wohnort sind deutsche Gemeinden.
	</p>
	<p>
		Der Dienst ist <strong>keine Dating-Plattform</strong>. Wer ihn zur Partnersuche oder zur Anmache nutzt, wird gesperrt.
	</p>

	<h2>2. Konto</h2>
	<ul>
		<li>Du musst mindestens 18 Jahre alt sein. Das erklärst du bei der Registrierung selbst.</li>
		<li>Pro Person und E-Mail-Adresse ist ein Konto erlaubt. Wegwerf-Adressen werden abgelehnt.</li>
		<li>Heimatort und Wohnort gibst du wahrheitsgemäß an. Nach der Registrierung ändert sie nur ein Admin auf deinen Antrag.</li>
		<li>Dein Nickname wird automatisch vergeben. Du kannst ihn einmal neu würfeln, danach ist er fest.</li>
		<li>Ohne Bestätigung der E-Mail-Adresse wird das Konto nach 48 Stunden gelöscht.</li>
	</ul>

	<h2>3. Kontakt zu anderen</h2>
	<ul>
		<li>Die erste Nachricht an eine Person ist eine Kontaktanfrage mit höchstens 500 Zeichen und ohne Links. Erst nach der Annahme könnt ihr euch schreiben.</li>
		<li>Du kannst höchstens 5 neue Anfragen pro Tag senden und höchstens 20 offene Anfragen gleichzeitig haben. Pro Person sind insgesamt zwei Anfragen möglich.</li>
		<li>Anfragen laufen nach 30 Tagen ab. Du kannst sie vorher zurückziehen.</li>
		<li>Gespräche bestehen aus reinem Text. Links sind erst nach 10 ausgetauschten Nachrichten möglich.</li>
		<li>Es gibt keine Lesebestätigungen und keinen Online-Status.</li>
	</ul>

	<h2>4. Was nicht erlaubt ist</h2>
	<ul>
		<li>Partnersuche, Anmache und sexuelle Inhalte.</li>
		<li>Belästigung, Drohungen, Beleidigungen und Hassrede.</li>
		<li>Spam, Werbung und das massenhafte Anschreiben von Mitgliedern.</li>
		<li>Falsche Angaben zu Heimatort, Wohnort oder Alter.</li>
		<li>Das automatisierte Auslesen von Daten sowie jeder Versuch, technische Grenzen des Dienstes zu umgehen.</li>
		<li>Rechtswidrige Inhalte jeder Art.</li>
	</ul>

	<h2>5. Blockieren und Melden</h2>
	<p>
		Du kannst jede Person jederzeit blockieren. Das wirkt in beide Richtungen. Profile, Anfragen und Nachrichten kannst du melden. Beim Melden wird
		eine Kopie des betroffenen Inhalts an die Meldung gehängt, bei Nachrichten zusätzlich bis zu 10 vorangehende Nachrichten desselben Gesprächs. Das
		Moderationsteam sieht nie das ganze Postfach.
	</p>

	<h2>6. Moderation, Einschränkung und Sperrung</h2>
	<ul>
		<li>Gehen innerhalb von 24 Stunden Meldungen aus drei verschiedenen Konten zu dir ein, kannst du automatisch 48 Stunden lang keine neuen Anfragen senden. Diese Einschränkung endet von selbst.</li>
		<li>Das Moderationsteam prüft Meldungen in der Regel innerhalb von 72 Stunden.</li>
		<li>Bestätigt sich ein Verstoß, kann das Konto gesperrt werden. Gegen eine Sperrung kannst du einmal Einspruch einlegen. Darüber entscheidet eine andere Person als bei der ersten Entscheidung.</li>
	</ul>

	<h2>7. Löschung und Beendigung</h2>
	<p>
		Du kannst dein Konto jederzeit in den Einstellungen löschen. Was dabei mit deinen Daten geschieht, steht in der
		<a href="/datenschutz">Datenschutzerklärung</a>. Der Anbieter kann Konten bei Verstößen gegen diese Bedingungen sperren oder löschen.
	</p>

	<h2>8. Verfügbarkeit und Haftung</h2>
	<p>
		Der Dienst befindet sich in einer Pilotphase und wird kostenlos angeboten. Eine bestimmte Verfügbarkeit wird nicht zugesagt.
		<span class="todo">TODO: Haftungsregelung durch eine fachkundige Person formulieren lassen.</span>
	</p>

	<h2>9. Änderungen</h2>
	<p>
		<span class="todo">TODO: Regelung für Änderungen dieser Bedingungen (Ankündigung, Frist, Widerspruch) und Datum des Stands eintragen.</span>
	</p>
</LegalPage>
