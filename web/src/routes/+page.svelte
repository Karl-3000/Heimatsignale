<script lang="ts">
	import { session } from '$lib/api/session.svelte';
	import DemoNetwork from '$lib/network/DemoNetwork.svelte';
	import Button from '$lib/ui/Button.svelte';
</script>

<svelte:head>
	<title>{session.siteName}: Zugezogene aus deiner Heimat im Umkreis finden</title>
	<meta name="description" content="Wer neu in eine Stadt zieht, findet hier andere Zugezogene aus der eigenen Heimatregion im Umkreis von 20 km. Nur für Deutschland, keine Dating-Plattform." />
</svelte:head>

<div class="grid gap-12 pb-8">
	<section class="grid gap-5 pt-4 sm:pt-10">
		<h1 class="hero-title max-w-[22ch]">Finde Menschen aus deiner Heimat, dort wo du jetzt wohnst.</h1>
		<p class="max-w-prose text-lg text-ink-muted">
			{session.siteName} zeigt dir andere Zugezogene im Umkreis von 20 km um deinen Wohnort und lässt dich Schritt für Schritt erkennen, woher sie stammen:
			erst das Bundesland, dann der Landkreis, dann der genaue Ort.
		</p>
		<div class="flex flex-wrap gap-3">
			<Button href="/registrieren" variant="primary" testid="landing-register">Registrieren</Button>
			<Button href="/vorschau" testid="landing-preview">Ansehen, was andere von dir sehen</Button>
		</div>
	</section>

	<section class="grid gap-4" aria-labelledby="beispiel-titel">
		<div class="grid gap-1">
			<h2 id="beispiel-titel">So sieht ein Herkunftsnetz aus</h2>
			<p class="max-w-prose text-ink-muted">
				Ein Beispiel mit erfundenen Daten: In der Mitte steht ein Wohnort, darum die Herkunft der Menschen, die dort leben. Wähle einen Knoten, um die
				nächste Stufe zu öffnen.
			</p>
		</div>
		<DemoNetwork />
	</section>

	<section class="grid gap-5" aria-labelledby="ablauf-titel">
		<h2 id="ablauf-titel">In drei Schritten</h2>
		<ol class="steps">
			<li>
				<h3>Heimatort und Wohnort angeben</h3>
				<p>Beides sind deutsche Gemeinden aus dem amtlichen Verzeichnis. Dazu E-Mail, Passwort und Geburtsdatum. Mehr fragen wir nicht.</p>
			</li>
			<li>
				<h3>Umkreis ansehen</h3>
				<p>Du siehst, aus welchen Bundesländern, Landkreisen und Orten die Zugezogenen in deiner Nähe stammen. Deine eigene Herkunft ist hervorgehoben.</p>
			</li>
			<li>
				<h3>Kontaktanfrage senden</h3>
				<p>Die erste Nachricht ist eine Anfrage. Erst wenn die andere Person sie annimmt, könnt ihr euch schreiben.</p>
			</li>
		</ol>
	</section>

	<section class="facts" aria-labelledby="grenzen-titel">
		<h2 id="grenzen-titel" class="hs-sr-only">Was du vorher wissen solltest</h2>
		<div>
			<h3>Keine Dating-Plattform</h3>
			<p>
				Es gibt kein Foto, keine Geschlechtsangabe, keine Hobbys, keine Likes und keinen Online-Status. Dein Nickname wird automatisch vergeben. Das Alter
				erscheint nur als ungefähre Spanne. Wer den Dienst zur Partnersuche nutzt, wird gesperrt.
			</p>
		</div>
		<div>
			<h3>Nur Deutschland</h3>
			<p>
				Heimatort und Wohnort sind deutsche Gemeinden. Wenn dein Heimatort außerhalb Deutschlands liegt, kannst du dich im Pilot noch nicht registrieren.
			</p>
		</div>
		<div>
			<h3>Sparsam mit Daten</h3>
			<p>
				Kein Tracking, keine Werbung. Dein Gerätestandort wird nie gespeichert. Was andere von dir sehen und was niemand sieht, zeigt die
				<a href="/vorschau">Vorschau</a> vor der Registrierung.
			</p>
		</div>
	</section>
</div>

<style>
	.hero-title {
		font-size: clamp(var(--hs-text-3xl), 6vw, var(--hs-text-4xl));
		letter-spacing: -0.025em;
		line-height: 1.08;
	}

	.steps {
		display: grid;
		gap: var(--hs-space-5);
		list-style: none;
		margin: 0;
		padding: 0;
		counter-reset: schritt;
	}

	.steps li {
		counter-increment: schritt;
		display: grid;
		grid-template-columns: 2.25rem minmax(0, 1fr);
		column-gap: var(--hs-space-3);
		row-gap: var(--hs-space-1);
	}

	.steps li::before {
		content: counter(schritt);
		grid-row: span 2;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.25rem;
		height: 2.25rem;
		border: 1.5px solid var(--hs-ink);
		border-radius: 50%;
		font-weight: var(--hs-weight-strong);
		font-variant-numeric: tabular-nums;
	}

	.steps h3,
	.steps p {
		grid-column: 2;
	}

	.steps p,
	.facts p {
		color: var(--hs-ink-muted);
	}

	.facts {
		display: grid;
		gap: var(--hs-space-5);
		padding-top: var(--hs-space-6);
		border-top: 1px solid var(--hs-line);
	}

	.facts h3 {
		margin-bottom: var(--hs-space-1);
	}

	@media (min-width: 800px) {
		.steps,
		.facts {
			grid-template-columns: repeat(3, minmax(0, 1fr));
			gap: var(--hs-space-6);
		}
	}
</style>
