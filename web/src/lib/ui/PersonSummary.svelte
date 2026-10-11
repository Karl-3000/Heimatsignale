<script lang="ts">
	import type { PublicUser } from '$lib/api/types';
	import { formatAge, formatMemberSince } from '$lib/util/format';

	/**
	 * Alles, was von einer Person sichtbar ist: Nickname, ungefähre Altersspanne,
	 * Heimatort mit Landkreis und Bundesland, Wohnort, Mitglied seit. Mehr gibt es nicht.
	 */
	interface Props {
		user: PublicUser;
		/** Nickname als Link zum Profil. */
		link?: boolean;
		size?: 'md' | 'lg';
		showMemberSince?: boolean;
	}

	let { user, link = false, size = 'md', showMemberSince = false }: Props = $props();
</script>

<div class="person person-{size}">
	<p class="nick">
		{#if link}
			<a href="/profil/{user.id}" data-testid="person-link">{user.nickname}</a>
		{:else}
			{user.nickname}
		{/if}
	</p>
	<dl>
		<div>
			<dt>Alter</dt>
			<dd class="hs-num">{formatAge(user.age_range)}</dd>
		</div>
		<div>
			<dt>Stammt aus</dt>
			<dd>{user.home.name} <span class="more">({user.home.district_name}, {user.home.state_name})</span></dd>
		</div>
		<div>
			<dt>Wohnt in</dt>
			<dd>{user.residence.name}</dd>
		</div>
		{#if showMemberSince && user.member_since}
			<div>
				<dt>Mitglied seit</dt>
				<dd>{formatMemberSince(user.member_since)}</dd>
			</div>
		{/if}
	</dl>
</div>

<style>
	.nick {
		font-weight: var(--hs-weight-strong);
		overflow-wrap: anywhere;
	}

	.person-lg .nick {
		font-size: var(--hs-text-xl);
		letter-spacing: -0.012em;
	}

	dl {
		display: grid;
		gap: 0.125rem;
		margin-top: var(--hs-space-1);
		font-size: var(--hs-text-sm);
	}

	.person-lg dl {
		gap: var(--hs-space-2);
		margin-top: var(--hs-space-3);
		font-size: var(--hs-text-base);
	}

	dl > div {
		display: grid;
		grid-template-columns: 6.5rem 1fr;
		gap: var(--hs-space-2);
	}

	dt {
		color: var(--hs-ink-subtle);
	}

	.more {
		color: var(--hs-ink-muted);
	}
</style>
