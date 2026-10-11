<script lang="ts">
	import { session } from '$lib/api/session.svelte';
	import LegalPage from '$lib/ui/LegalPage.svelte';
</script>

<svelte:head>
	<title>Datenschutz – {session.siteName}</title>
</svelte:head>

<LegalPage title="Datenschutzerklärung">
	<h2>Verantwortlicher</h2>
	<address>
		<span class="todo">TODO: Name des Verantwortlichen</span><br />
		<span class="todo">TODO: Anschrift</span><br />
		<span class="todo">TODO: E-Mail-Adresse für Datenschutzanfragen</span>
	</address>
	<p><span class="todo">TODO: Datenschutzbeauftragte Person benennen, falls eine bestellt ist. Sonst diesen Satz entfernen.</span></p>

	<h2>Das Wichtigste in Kürze</h2>
	<ul>
		<li>Wir fragen nur, was der Dienst braucht: E-Mail, Passwort, Geburtsdatum, Heimatort, Wohnort.</li>
		<li>Vom Geburtsdatum speichern wir nur das Jahr und den Vermerk, dass du deine Volljährigkeit selbst erklärt hast.</li>
		<li>Es gibt kein Foto, keine Geschlechtsangabe, keine Hobbys und kein freies Profil. Diese Daten erheben wir nicht.</li>
		<li>Dein Gerätestandort wird nie gespeichert, auch nicht in technischen Protokollen.</li>
		<li>Kein Tracking, keine Werbung, keine eingebundenen Dienste Dritter.</li>
	</ul>

	<h2>Welche Daten wir verarbeiten</h2>
	<!-- Die Tabelle scrollt auf schmalen Bildschirmen seitlich; der Bereich muss dafür per Tastatur erreichbar sein. -->
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<div class="table-wrap" tabindex="0" role="region" aria-label="Tabelle: Daten, Zweck, Rechtsgrundlage und Aufbewahrung">
		<table>
			<thead>
				<tr>
					<th scope="col">Datum</th>
					<th scope="col">Zweck</th>
					<th scope="col">Rechtsgrundlage</th>
					<th scope="col">Aufbewahrung</th>
				</tr>
			</thead>
			<tbody>
				<tr>
					<td>E-Mail-Adresse, Passwort (nur als Hash)</td>
					<td>Anmeldung, Bestätigung, Benachrichtigung</td>
					<td>Vertrag (Art. 6 Abs. 1 b DSGVO)</td>
					<td>bis zur Löschung des Kontos</td>
				</tr>
				<tr>
					<td>Geburtsjahr und Erklärung der Volljährigkeit</td>
					<td>Mindestalter 18, Anzeige einer ungefähren Altersspanne</td>
					<td>Vertrag</td>
					<td>bis zur Löschung des Kontos</td>
				</tr>
				<tr>
					<td>Heimatort und Wohnort (Gemeinde)</td>
					<td>Kernfunktion: Umkreis und Herkunft</td>
					<td>Vertrag</td>
					<td>bis zur Löschung des Kontos</td>
				</tr>
				<tr>
					<td>Kontaktanfragen und Nachrichten</td>
					<td>Kommunikation zwischen Mitgliedern</td>
					<td>Vertrag</td>
					<td>bis zur Löschung durch dich oder mit dem Konto</td>
				</tr>
				<tr>
					<td>Zeitpunkt der letzten Aktivität</td>
					<td>Kennzahl „aktives Konto“ im Pilot</td>
					<td>Berechtigtes Interesse (Art. 6 Abs. 1 f DSGVO)</td>
					<td>bis zur Löschung des Kontos. Nur ein Zeitstempel, kein Verlauf</td>
				</tr>
				<tr>
					<td>Kopien gemeldeter Inhalte</td>
					<td>Moderation und Einspruch</td>
					<td>Berechtigtes Interesse</td>
					<td>12 Monate nach Abschluss der Meldung</td>
				</tr>
				<tr>
					<td>IP-Adresse bei der Registrierung (nur als Hash)</td>
					<td>Begrenzung von Massenregistrierungen</td>
					<td>Berechtigtes Interesse</td>
					<td>7 Tage, ohne Zuordnung zu einem Konto</td>
				</tr>
				<tr>
					<td>Protokoll der Admin-Handlungen</td>
					<td>Nachvollziehbarkeit und Kontrolle der Admins</td>
					<td>Berechtigtes Interesse</td>
					<td>24 Monate. Enthält keine Orte, keine E-Mails, keine Texte</td>
				</tr>
				<tr>
					<td>Löschjournal (Objektkennung und Zeitpunkt)</td>
					<td>Durchsetzung von Löschungen nach einer Wiederherstellung</td>
					<td>Rechtliche Pflicht (Art. 17 DSGVO)</td>
					<td>60 Tage</td>
				</tr>
				<tr>
					<td>Zusammengefasste Tageszahlen</td>
					<td>Auswertung des Pilots</td>
					<td>Berechtigtes Interesse</td>
					<td>unbegrenzt. Reine Zahlen ohne Personenbezug</td>
				</tr>
			</tbody>
		</table>
	</div>

	<h2>Was andere Mitglieder von dir sehen</h2>
	<p>
		Angemeldete Mitglieder, deren Wohnort höchstens 20 km von deinem entfernt liegt (gemessen zwischen den Mittelpunkten der Gemeinden), sehen:
		Nickname, ungefähre Altersspanne, Heimatort mit Landkreis und Bundesland, Wohnort-Gemeinde und den Monat deiner Registrierung. Nicht sichtbar sind
		E-Mail, Geburtsdatum, Adresse, Online-Status und Lesestatus. Ob ein Gespräch ungelesen ist, merkt sich nur dein eigener Browser.
	</p>
	<p>
		<strong>Restrisiko:</strong> Genauer Heimatort, Altersspanne und Wohnort-Gemeinde zusammen können in kleinen Orten auf eine bestimmte Person hinweisen.
		Die stufenweise Anzeige der Herkunft (Bundesland, Landkreis, Ort) ist Navigation und kein Schutz. Das zeigt die <a href="/vorschau">Vorschau</a> vor
		der Registrierung.
	</p>

	<h2>Standort</h2>
	<p>
		Deinen Wohnort wählst du selbst aus der Liste der Gemeinden. Wenn du bei der Registrierung die Standortfreigabe nutzt, sendet dein Browser den
		Standort einmal auf zwei Nachkommastellen gerundet (etwa ein Kilometer), um die nächste Gemeinde vorzuschlagen. Diese Koordinaten werden weder
		gespeichert noch protokolliert. Du bestätigst die Gemeinde selbst.
	</p>
	<p>Es gibt keine dauerhafte Ortshistorie. Bei einem Änderungsantrag halten wir den alten und den neuen Ort bis 30 Tage nach der Entscheidung vor.</p>

	<h2>Löschung</h2>
	<p>Du kannst dein Konto jederzeit in den Einstellungen löschen. Dann geschieht Folgendes:</p>
	<ol>
		<li>
			<strong>Sofort:</strong> E-Mail, Passwort, Nickname, Geburtsjahr und beide Orte werden aus dem laufenden System entfernt, alle Sitzungen enden. Ab
			diesem Moment bist du für niemanden mehr sichtbar oder erreichbar.
		</li>
		<li>
			<strong>Innerhalb von 24 Stunden:</strong> Alle deine Gespräche mit allen Nachrichten (auch auf der Gegenseite), alle Anfragen von dir und an dich,
			Blockierungen, Anträge und Einsprüche werden gelöscht. Deine Gesprächspartner sehen „Gespräch nicht mehr verfügbar“.
		</li>
		<li>
			<strong>Spätestens 31 Tage nach der Löschung</strong> sind deine Kontodaten auch aus allen Sicherungen verschwunden. Sicherungen werden 30 Tage
			aufbewahrt.
		</li>
	</ol>
	<p>
		Bewusst länger bleiben Belege zu Meldungen (bis 12 Monate nach Abschluss) und das Protokoll der Admin-Handlungen (bis 24 Monate). Sie sind deshalb
		auch in neueren Sicherungen enthalten. Sie enthalten keine E-Mail und keine Orte. Gemeldete Texte können aber Namen oder Orte enthalten, die jemand
		selbst geschrieben hat. Die darin verbleibenden Kennungen sind pseudonym, nicht anonym, und werden als personenbezogene Daten behandelt.
	</p>
	<p>
		Jeder Löschauftrag wird zusätzlich in einem Löschjournal außerhalb der Datenbank vermerkt (nur Kennung und Zeitpunkt, 60 Tage). Muss eine Sicherung
		eingespielt werden, werden damit alle seither erfolgten Löschungen erneut ausgeführt, bevor der Dienst wieder erreichbar ist.
	</p>
	<p>Weitere Fristen: Eigene Nachrichten kannst du einzeln löschen, sie verschwinden sofort für beide Seiten. Abgelaufene Anfragen werden nach 7 Tagen gelöscht.</p>

	<h2>Technische Protokolle</h2>
	<p>
		Der Webserver protokolliert Zugriffe mit gekürzter IP-Adresse (letzter Teil entfernt) und löscht diese Protokolle nach 7 Tagen. Der Dienst setzt nur
		technisch notwendige Cookies: eines für die Anmeldung und eines zum Schutz von Formularen. Dein Browser speichert außerdem lokal das gewählte
		Farbschema und bis wann du ein Gespräch gelesen hast.
	</p>

	<h2>Empfänger und Auftragsverarbeiter</h2>
	<ul>
		<li>Hosting: <span class="todo">TODO: Hoster mit Sitz und Hinweis auf den Vertrag zur Auftragsverarbeitung</span></li>
		<li>E-Mail-Versand: <span class="todo">TODO: Anbieter für den Versand von Bestätigungs- und Benachrichtigungs-E-Mails mit Vertrag zur Auftragsverarbeitung</span></li>
		<li>
			Kartenkacheln: Die Karte wird vom eigenen Server ausgeliefert. <span class="todo">TODO: Falls stattdessen ein Anbieter genutzt wird, hier mit Vertrag zur Auftragsverarbeitung nennen.</span>
		</li>
	</ul>
	<p>Es gibt keine Tracking-Dienste, keine Werbe-SDKs und keine Übermittlung an Dritte zu Werbezwecken.</p>

	<h2>Deine Rechte</h2>
	<ul>
		<li>Auskunft über die zu dir gespeicherten Daten (Art. 15 DSGVO).</li>
		<li>Berichtigung (Art. 16): Heimatort und Wohnort über den Antrag in den Einstellungen, alles andere über die Kontaktadresse oben.</li>
		<li>Löschung (Art. 17): über „Konto löschen“ in den Einstellungen.</li>
		<li>Einschränkung der Verarbeitung (Art. 18), Datenübertragbarkeit (Art. 20) und Widerspruch gegen Verarbeitungen auf Grundlage berechtigter Interessen (Art. 21).</li>
		<li>
			Beschwerde bei einer Aufsichtsbehörde: <span class="todo">TODO: zuständige Datenschutzaufsichtsbehörde nennen</span>
		</li>
	</ul>

	<p><span class="todo">TODO: Datum des Stands dieser Erklärung eintragen.</span></p>
</LegalPage>
