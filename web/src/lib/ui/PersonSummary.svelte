<script lang="ts">
	import type { PublicUser } from '$lib/api/types';
	import { formatAge, formatMemberSince } from '$lib/util/format';

	/**
	 * Alles, was von einer Person sichtbar ist: Nickname, ungefähre Altersspanne,
	 * Heimatort mit Landkreis und Bundesland, Wohnort, Mitglied seit. Mehr gibt es nicht.
	 * Gesetzt wie eine Visitenkarte: der Name groß, darunter drei ruhige Zeilen.
	 */
	interface Props {
		user: PublicUser;
		/** Nickname als Link zum Profil. */
		link?: boolean;
		size?: 'md' | 'lg';
		showMemberSince?: boolean;
		/** Auf der Bühne: Schrift in den Farben des Himmels. */
		onStage?: boolean;
	}

	let { user, link = false, size = 'md', showMemberSince = false, onStage = false }: Props = $props();
</script>

<div class="person person-{size}" class:on-stage={onStage}>
	<p class="nick">
		{#if link}
			<a href="/profil/{user.id}" data-testid="person-link">{user.nickname}</a>
		{:else}
			{user.nickname}
		{/if}
	</p>
	<dl>
		<div>
			<dt class="hs-sr-only">Alter</dt>
			<dd class="hs-num">{formatAge(user.age_range)}</dd>
		</div>
		<div>
			<dt class="hs-sr-only">Stammt</dt>
			<dd>aus {user.home.name}, <span class="more">{user.home.district_name}, {user.home.state_name}</span></dd>
		</div>
		<div>
			<dt class="hs-sr-only">Wohnort</dt>
			<dd>wohnt in {user.residence.name}</dd>
		</div>
		{#if showMemberSince && user.member_since}
			<div class="since">
				<dt class="hs-sr-only">Mitglied</dt>
				<dd>dabei seit {formatMemberSince(user.member_since)}</dd>
			</div>
		{/if}
	</dl>
</div>

<style>
	.nick {
		font-family: var(--hs-font-display);
		font-weight: var(--hs-weight-display);
		font-size: var(--hs-text-lg);
		letter-spacing: -0.02em;
		line-height: 1.15;
		overflow-wrap: anywhere;
	}

	.nick a {
		color: inherit;
		text-decoration-color: color-mix(in srgb, currentColor 30%, transparent);
	}

	.nick a:hover {
		color: var(--hs-accent-ink);
		text-decoration-color: currentColor;
	}

	.person-lg .nick {
		font-size: clamp(1.875rem, 5vw, 2.75rem);
		letter-spacing: var(--hs-tracking-display);
		line-height: var(--hs-leading-display);
	}

	dl {
		display: grid;
		gap: 0.125rem;
		margin-top: var(--hs-space-2);
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.person-lg dl {
		gap: var(--hs-space-1);
		margin-top: var(--hs-space-4);
		font-size: var(--hs-text-lg);
		line-height: 1.4;
		color: var(--hs-ink);
	}

	.more,
	.since {
		color: var(--hs-ink-muted);
	}

	.person-lg .since {
		margin-top: var(--hs-space-3);
		font-size: var(--hs-text-sm);
	}

	.on-stage,
	.on-stage dl,
	.person-lg.on-stage dl {
		color: var(--hs-stage-ink);
	}

	.on-stage .more,
	.on-stage .since {
		color: var(--hs-stage-muted);
	}

	.on-stage .nick a:hover {
		color: var(--hs-stage-accent);
	}
</style>
