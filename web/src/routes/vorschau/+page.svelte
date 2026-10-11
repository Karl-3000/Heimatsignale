<script lang="ts">
	import { session } from '$lib/api/session.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import PersonSummary from '$lib/ui/PersonSummary.svelte';
	import type { PublicUser } from '$lib/api/types';

	// Beispielprofil aus dem Projektplan. Ist jemand angemeldet, zeigt die Seite das eigene Profil.
	const example: PublicUser = {
		id: 'beispiel',
		nickname: 'Stiller-Leuchtturm-412',
		age_range: '25–34',
		home: { ags: '09780139', name: 'Sonthofen', district_ags: '09780', district_name: 'Oberallgäu', state_code: '09', state_name: 'Bayern' },
		residence: { ags: '00000000', name: 'Musterstadt' },
		member_since: '2026-10'
	};

	const me = $derived(session.user);
	const shown = $derived<PublicUser>(
		me && me.home && me.residence
			? { id: me.id, nickname: me.nickname, age_range: me.age_range, home: me.home, residence: { ags: me.residence.ags, name: me.residence.name }, member_since: me.member_since }
			: example
	);
</script>

<svelte:head>
	<title>Was andere von dir sehen – {session.siteName}</title>
</svelte:head>

<div class="page">
	<header class="head">
		<h1>Was andere von dir sehen</h1>
		<p class="hs-lead">Bevor du dich registrierst, sollst du genau wissen, was sichtbar wird. Diese Seite zeigt es, und sie nennt auch die Grenzen.</p>
	</header>

	<section class="shown" aria-labelledby="sichtbar-titel">
		<!-- Die Karte steht so auf der Bühne, wie sie im Produkt erscheint. -->
		<div class="hs-stage panel">
			<div class="card" data-testid="preview-card">
				<PersonSummary user={shown} size="lg" showMemberSince />
			</div>
		</div>
		<div class="explain">
			<h2 id="sichtbar-titel">Das sehen andere Zugezogene im Umkreis von bis zu {session.maxRadius} km</h2>
			<p class="quiet">
				{#if me}Das ist dein Profil, so wie es andere sehen.{:else}Ein Beispiel. Dein Nickname wird bei der Registrierung automatisch vergeben und lässt sich
					einmal neu würfeln, danach ist er fest.{/if}
			</p>
			<dl class="facts">
				<div>
					<dt>Nickname</dt>
					<dd>Automatisch vergeben, nicht frei wählbar.</dd>
				</div>
				<div>
					<dt>Alter</dt>
					<dd>Nur als ungefähre Spanne, etwa „etwa 25–34“. Sie wird aus dem Geburtsjahr berechnet und kann an den Grenzen um ein Jahr abweichen.</dd>
				</div>
				<div>
					<dt>Heimatort</dt>
					<dd>Die genaue Gemeinde, mit Landkreis und Bundesland.</dd>
				</div>
				<div>
					<dt>Wohnort</dt>
					<dd>Die Gemeinde, in der du lebst. Keine Adresse, kein Stadtteil.</dd>
				</div>
				<div>
					<dt>Dabei seit</dt>
					<dd>Monat und Jahr.</dd>
				</div>
			</dl>
		</div>
	</section>

	<section class="hidden" aria-labelledby="unsichtbar-titel">
		<h2 id="unsichtbar-titel" class="big">Das sieht niemand.</h2>
		<div>
			<ul class="calm">
				<li>Deine E-Mail-Adresse.</li>
				<li>Dein Geburtsdatum. Gespeichert wird nur das Geburtsjahr.</li>
				<li>Deine genaue Adresse oder dein Gerätestandort. Der Standort wird nie gespeichert.</li>
				<li>Ob du gerade online bist und ob du eine Nachricht gelesen hast.</li>
				<li>Eine Entfernung zu dir, die genauer ist als die Gemeinde.</li>
			</ul>
			<p class="quiet">Fotos, Geschlecht, Hobbys und freie Profiltexte gibt es nicht. Dafür ist kein Feld vorgesehen.</p>
		</div>
	</section>

	<section class="limits" aria-labelledby="grenzen-titel">
		<h2 id="grenzen-titel">Drei Dinge, die du wissen solltest</h2>
		<div class="notes">
			<Notice tone="info" title="Der Umkreis reicht bis {session.maxRadius} km" testid="preview-radius">
				<p>
					Die Ansicht zeigt zuerst {session.defaultRadius} km um den Wohnort{session.maxRadius > session.defaultRadius
						? ` und lässt sich auf ${session.maxRadius} km erweitern`
						: ''}. Gemessen wird zwischen den Mittelpunkten der Gemeinden. Wer bis zu {session.maxRadius} km von
					dir entfernt wohnt, kann dich also sehen und anfragen, auch wenn du selbst nur den kleineren Umkreis ansiehst.
				</p>
			</Notice>
			<Notice tone="info" title="Die Stufen sind Navigation, kein Schutz" testid="preview-levels">
				<p>
					Die Herkunft erscheint stufenweise: Bundesland, dann Landkreis, dann Ort. Das dient der Übersicht. Jedes angemeldete Mitglied im Umkreis von
					bis zu {session.maxRadius} km kann bis zu deinem Heimatort und deinem Profil durchklicken und dir eine Kontaktanfrage senden.
				</p>
			</Notice>
			<Notice tone="warning" title="Restrisiko in kleinen Orten" testid="preview-risk">
				<p>
					Genauer Heimatort, ungefähre Altersspanne und Wohnort-Gemeinde zusammen können in kleinen Orten auf eine bestimmte Person hinweisen. Wenn du das
					nicht möchtest, ist dieser Dienst nicht das Richtige für dich.
				</p>
			</Notice>
		</div>
		<p class="quiet measure">
			Du kannst jede Person blockieren und melden. Blockierte und Blockierende sehen sich gegenseitig nicht mehr und werden füreinander nicht mitgezählt.
			In kleinen Gruppen kann ein verschwundenes Profil trotzdem auffallen.
		</p>
	</section>

	{#if !session.authenticated}
		<div class="flex flex-wrap gap-3">
			<Button href="/registrieren" variant="primary" testid="preview-register">Registrieren</Button>
			<Button href="/datenschutz">Datenschutz lesen</Button>
		</div>
	{/if}
</div>

<style>
	.page {
		display: grid;
		gap: var(--hs-space-8);
	}

	.head {
		display: grid;
		gap: var(--hs-space-4);
	}

	.shown {
		display: grid;
		gap: var(--hs-space-6);
		align-items: center;
	}

	.panel {
		display: grid;
		place-items: center;
		padding: var(--hs-space-6) var(--hs-space-4);
		min-height: 22rem;
	}

	/* Die Personenkarte: weiß und erhaben, genau wie im Produkt. */
	.card {
		width: min(100%, 26rem);
		padding: var(--hs-space-6);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
		color: var(--hs-ink);
		box-shadow: var(--hs-shadow-lg);
	}

	.explain {
		display: grid;
		gap: var(--hs-space-4);
		align-content: start;
	}

	.quiet {
		color: var(--hs-ink-muted);
	}

	.measure {
		max-width: var(--hs-prose);
	}

	.facts {
		display: grid;
	}

	.facts > div {
		display: grid;
		gap: 0.125rem;
		padding: var(--hs-space-3) 0;
		border-top: 1px solid var(--hs-line);
	}

	.facts dt {
		font-weight: var(--hs-weight-strong);
	}

	.facts dd {
		color: var(--hs-ink-muted);
	}

	.hidden {
		display: grid;
		gap: var(--hs-space-5);
	}

	.big {
		font-size: clamp(2.25rem, 5vw, 3.5rem);
		line-height: 1.05;
		letter-spacing: var(--hs-tracking-display);
	}

	.calm {
		display: grid;
		list-style: none;
		margin: 0 0 var(--hs-space-4);
		padding: 0;
		font-size: var(--hs-text-lg);
		line-height: 1.45;
	}

	.calm li {
		padding: var(--hs-space-3) 0;
		border-top: 1px solid var(--hs-line);
	}

	.limits {
		display: grid;
		gap: var(--hs-space-5);
	}

	.notes {
		display: grid;
		gap: var(--hs-space-3);
	}

	@media (min-width: 900px) {
		.shown,
		.hidden {
			grid-template-columns: repeat(12, minmax(0, 1fr));
			column-gap: var(--hs-space-6);
		}

		.panel {
			grid-column: 1 / span 6;
			min-height: 26rem;
		}

		.explain {
			grid-column: 7 / span 6;
		}

		.hidden .big {
			grid-column: 1 / span 5;
		}

		.hidden > div {
			grid-column: 7 / span 6;
		}

		.notes {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}
</style>
