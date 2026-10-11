<script lang="ts">
	import { session } from '$lib/api/session.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Card from '$lib/ui/Card.svelte';
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

<div class="grid gap-8">
	<header class="grid gap-3">
		<h1>Was andere von dir sehen</h1>
		<p class="max-w-prose text-lg text-ink-muted">
			Bevor du dich registrierst, sollst du genau wissen, was sichtbar wird. Diese Seite zeigt es, und sie nennt auch die Grenzen.
		</p>
	</header>

	<div class="grid gap-6 lg:grid-cols-2">
		<section class="grid content-start gap-3" aria-labelledby="sichtbar-titel">
			<h2 id="sichtbar-titel">Das sehen andere Zugezogene im Umkreis von bis zu {session.maxRadius} km</h2>
			<Card padding="lg" testid="preview-card">
				<PersonSummary user={shown} size="lg" showMemberSince />
			</Card>
			<p class="text-sm text-ink-muted">
				{#if me}Das ist dein Profil, so wie es andere sehen.{:else}Ein Beispiel. Dein Nickname wird bei der Registrierung automatisch vergeben und lässt sich
					einmal neu würfeln, danach ist er fest.{/if}
			</p>
			<ul class="list">
				<li>Nickname: automatisch vergeben, nicht frei wählbar.</li>
				<li>Alter: nur als ungefähre Spanne, etwa „etwa 25–34“. Sie wird aus dem Geburtsjahr berechnet und kann an den Grenzen um ein Jahr abweichen.</li>
				<li>Heimatort: die genaue Gemeinde, mit Landkreis und Bundesland.</li>
				<li>Wohnort: die Gemeinde, in der du lebst. Keine Adresse, kein Stadtteil.</li>
				<li>Mitglied seit: Monat und Jahr.</li>
			</ul>
		</section>

		<section class="grid content-start gap-3" aria-labelledby="unsichtbar-titel">
			<h2 id="unsichtbar-titel">Das sieht niemand</h2>
			<ul class="list">
				<li>Deine E-Mail-Adresse.</li>
				<li>Dein Geburtsdatum. Gespeichert wird nur das Geburtsjahr.</li>
				<li>Deine genaue Adresse oder dein Gerätestandort. Der Standort wird nie gespeichert.</li>
				<li>Ob du gerade online bist und ob du eine Nachricht gelesen hast.</li>
				<li>Eine Entfernung zu dir, die genauer ist als die Gemeinde.</li>
			</ul>
			<p class="text-sm text-ink-muted">Fotos, Geschlecht, Hobbys und freie Profiltexte gibt es nicht. Dafür ist kein Feld vorgesehen.</p>
		</section>
	</div>

	<section class="grid max-w-prose gap-3" aria-labelledby="grenzen-titel">
		<h2 id="grenzen-titel">Drei Dinge, die du wissen solltest</h2>
		<Notice tone="info" title="Der Umkreis reicht bis {session.maxRadius} km" testid="preview-radius">
			<p>
				Die Ansicht zeigt zuerst {session.defaultRadius} km um den Wohnort{#if session.maxRadius > session.defaultRadius}
					und lässt sich auf {session.maxRadius} km erweitern{/if}. Gemessen wird zwischen den Mittelpunkten der Gemeinden. Wer bis zu {session.maxRadius} km von
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
		<p class="text-ink-muted">
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
	.list {
		display: grid;
		gap: var(--hs-space-2);
		padding-left: 1.25rem;
		list-style: disc;
	}

	.list li::marker {
		color: var(--hs-ink-subtle);
	}
</style>
