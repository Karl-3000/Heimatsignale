<script lang="ts">
	import { session } from '$lib/api/session.svelte';
	import DemoNetwork from '$lib/network/DemoNetwork.svelte';
	import Brand from '$lib/ui/Brand.svelte';
	import Button from '$lib/ui/Button.svelte';

	const wider = $derived(session.maxRadius > session.defaultRadius);
</script>

<svelte:head>
	<title>{session.siteName}: Zugezogene aus deiner Heimat im Umkreis finden</title>
	<meta name="description" content="Wer neu in eine Stadt zieht, findet hier andere Zugezogene aus der eigenen Heimatregion im Umkreis von 20 km, auf Wunsch bis 100 km. Nur für Deutschland, keine Dating-Plattform." />
</svelte:head>

<!-- Der Hero ist die Bühne: Nachtblau vom oberen Rand an, die Kopfzeile liegt durchsichtig darüber. -->
<section class="hero" aria-labelledby="hero-titel">
	<div class="hero-inner">
		<div class="hero-text">
			<h1 id="hero-titel">Finde Menschen aus deiner Heimat, dort wo du jetzt wohnst.</h1>
			<p class="hero-lead">
				{session.siteName} zeigt dir andere Zugezogene im Umkreis von {session.defaultRadius} km um deinen Wohnort{#if wider}, auf Wunsch bis {session.maxRadius} km{/if}.
				Schritt für Schritt siehst du, woher sie stammen: erst das Bundesland, dann der Landkreis, dann der genaue Ort.
			</p>
			<div class="hero-actions">
				<Button href="/registrieren" variant="primary" testid="landing-register">Registrieren</Button>
				<Button href="/vorschau" variant="glass" testid="landing-preview">Ansehen, was andere von dir sehen</Button>
			</div>
		</div>
		<div class="hero-stage">
			<DemoNetwork hero height="clamp(24rem, 68dvh, 42rem)" />
			<p class="hero-caption">Ein Beispiel mit erfundenen Daten. Wähle ein Licht, um die nächste Stufe zu öffnen.</p>
		</div>
	</div>
</section>

<div class="page">
	<section class="statement" aria-labelledby="nicht-titel">
		<h2 id="nicht-titel" class="big">Kein Foto. Kein Geschlecht. Kein Profiltext.</h2>
		<div class="copy">
			<p>
				{session.siteName} ist keine Dating-Plattform und so gebaut, dass es sich dafür schlecht eignet. Es gibt keine Hobbys, keine Likes, keinen
				Online-Status und keine Lesebestätigungen.
			</p>
			<p>
				Dein Nickname wird automatisch vergeben. Dein Alter erscheint nur als ungefähre Spanne. Wer den Dienst zur Partnersuche nutzt, wird gesperrt.
			</p>
		</div>
	</section>

	<section class="steps-section" aria-labelledby="ablauf-titel">
		<h2 id="ablauf-titel" class="section-title">In drei Schritten</h2>
		<ol class="steps">
			<li>
				<h3>Heimatort und Wohnort angeben</h3>
				<p>Beides sind deutsche Gemeinden aus dem amtlichen Verzeichnis. Dazu E-Mail, Passwort und Geburtsdatum. Mehr fragen wir nicht.</p>
			</li>
			<li>
				<h3>Umkreis ansehen</h3>
				<p>Du siehst, aus welchen Bundesländern, Landkreisen und Orten die Zugezogenen in deiner Nähe stammen. Deine eigene Herkunft leuchtet.</p>
			</li>
			<li>
				<h3>Kontaktanfrage senden</h3>
				<p>Die erste Nachricht ist eine Anfrage. Erst wenn die andere Person sie annimmt, könnt ihr euch schreiben.</p>
			</li>
		</ol>
	</section>

	<section class="pair" aria-label="Was du vorher wissen solltest">
		<div>
			<h2 class="section-title">Nur Deutschland</h2>
			<p>
				Heimatort und Wohnort sind deutsche Gemeinden. Wenn dein Heimatort außerhalb Deutschlands liegt, kannst du dich im Pilot noch nicht
				registrieren.
			</p>
		</div>
		<div>
			<h2 class="section-title">Sparsam mit Daten</h2>
			<p>
				Kein Tracking, keine Werbung. Dein Gerätestandort wird nie gespeichert. Andere Mitglieder können dich aus bis zu {session.maxRadius} km
				Entfernung sehen und anfragen. Was sie von dir sehen und was niemand sieht, zeigt die <a href="/vorschau">Vorschau</a> vor der Registrierung.
			</p>
		</div>
	</section>

	<section class="hs-stage closing" aria-labelledby="schluss-titel">
		<Brand href={null} tone="stage" markOnly size="lg" />
		<h2 id="schluss-titel" class="big">Schau nach, wer aus deiner Gegend hier lebt.</h2>
		<div class="hero-actions">
			<Button href="/registrieren" variant="primary">Registrieren</Button>
			<Button href="/anmelden" variant="glass">Anmelden</Button>
		</div>
	</section>
</div>

<style>
	.hero {
		position: relative;
		background:
			radial-gradient(70% 80% at 72% 58%, color-mix(in srgb, var(--hs-stage-lift) 70%, transparent) 0%, transparent 68%),
			var(--hs-stage-bg);
		color: var(--hs-stage-ink);
		border-bottom: 1px solid var(--hs-stage-border);
		overflow: hidden;
	}

	.hero-inner {
		display: grid;
		gap: var(--hs-space-6);
		max-width: var(--hs-content);
		margin: 0 auto;
		padding: calc(4rem + var(--hs-space-7)) var(--hs-gutter) var(--hs-space-6);
	}

	.hero-text {
		display: grid;
		gap: var(--hs-space-5);
		align-content: start;
		position: relative;
		z-index: 1;
	}

	.hero h1 {
		max-width: 13ch;
		font-size: var(--hs-text-hero);
		font-weight: 620;
		line-height: 1.03;
		letter-spacing: -0.02em;
	}

	.hero-lead {
		max-width: 34rem;
		font-size: var(--hs-text-base);
		line-height: 1.5;
		color: var(--hs-stage-muted);
	}

	.hero-actions {
		display: flex;
		flex-wrap: wrap;
		gap: var(--hs-space-3);
	}

	.hero-stage {
		min-width: 0;
	}

	.hero-caption {
		margin-top: var(--hs-space-2);
		font-size: var(--hs-text-sm);
		color: var(--hs-stage-muted);
		text-align: right;
	}

	.hero :global(:focus-visible) {
		outline-color: var(--hs-stage-accent);
	}

	.page {
		display: grid;
		gap: var(--hs-space-9);
		max-width: var(--hs-content);
		margin: 0 auto;
		padding: var(--hs-space-9) var(--hs-gutter) var(--hs-space-8);
	}

	.big {
		font-size: var(--hs-text-statement);
		line-height: 1.08;
		letter-spacing: var(--hs-tracking-display);
	}

	.section-title {
		font-size: var(--hs-text-2xl);
	}

	.statement {
		display: grid;
		gap: var(--hs-space-5);
	}

	.statement .big {
		font-size: clamp(2.25rem, 5.4vw, 4rem);
		max-width: 11ch;
	}

	.copy {
		display: grid;
		gap: var(--hs-space-4);
		align-content: start;
		max-width: 34rem;
		font-size: var(--hs-text-lg);
		line-height: 1.5;
		color: var(--hs-ink-muted);
	}

	.steps-section {
		display: grid;
		gap: var(--hs-space-6);
	}

	.steps {
		display: grid;
		gap: var(--hs-space-6);
		list-style: none;
		margin: 0;
		padding: 0;
		counter-reset: schritt;
	}

	.steps li {
		counter-increment: schritt;
		display: grid;
		gap: var(--hs-space-2);
		align-content: start;
		padding-top: var(--hs-space-4);
		border-top: 1px solid var(--hs-line);
	}

	/* Die Ziffer ist Teil einer echten Reihenfolge, deshalb darf sie groß sein. */
	.steps li::before {
		content: counter(schritt);
		font-family: var(--hs-font-display);
		font-weight: var(--hs-weight-display);
		font-size: var(--hs-text-3xl);
		line-height: 1;
		letter-spacing: var(--hs-tracking-display);
		color: var(--hs-accent-ink);
		font-variant-numeric: tabular-nums;
	}

	.steps h3 {
		margin-top: var(--hs-space-2);
		font-size: var(--hs-text-xl);
	}

	.steps p,
	.pair p {
		max-width: 30rem;
		color: var(--hs-ink-muted);
	}

	.pair {
		display: grid;
		gap: var(--hs-space-7);
	}

	.pair > div {
		display: grid;
		gap: var(--hs-space-3);
		align-content: start;
	}

	.closing {
		display: grid;
		gap: var(--hs-space-5);
		justify-items: start;
		padding: var(--hs-space-7) var(--hs-space-5);
	}

	.closing .big {
		max-width: 16ch;
		color: var(--hs-stage-ink);
	}

	.closing :global(:focus-visible) {
		outline-color: var(--hs-stage-accent);
	}

	@media (min-width: 720px) {
		.closing {
			grid-template-columns: minmax(0, 1fr) auto;
			align-items: end;
			column-gap: var(--hs-space-6);
			padding: var(--hs-space-8);
		}

		.closing :global(.brand) {
			grid-column: 1 / -1;
		}

		.steps,
		.pair {
			grid-template-columns: repeat(3, minmax(0, 1fr));
			gap: var(--hs-space-6);
		}

		.pair {
			grid-template-columns: repeat(2, minmax(0, 1fr));
			gap: var(--hs-space-8);
		}

		.statement {
			grid-template-columns: repeat(12, minmax(0, 1fr));
			column-gap: var(--hs-space-5);
			align-items: end;
		}

		.statement .big {
			grid-column: 1 / span 7;
		}

		.statement .copy {
			grid-column: 8 / span 5;
		}
	}

	@media (min-width: 1000px) {
		.hero-inner {
			grid-template-columns: repeat(12, minmax(0, 1fr));
			column-gap: var(--hs-space-5);
			align-items: center;
			padding-top: calc(4rem + var(--hs-space-6));
			padding-bottom: var(--hs-space-7);
		}

		.hero-text {
			grid-column: 1 / span 7;
			grid-row: 1;
		}

		/* Das Netz ragt nach links unter die Überschrift; die Schrift liegt darüber. */
		.hero-stage {
			grid-column: 7 / span 6;
			grid-row: 1;
			margin-left: -3.5rem;
		}

		.hero-lead {
			max-width: 29rem;
			font-size: var(--hs-text-lg);
		}
	}
</style>
