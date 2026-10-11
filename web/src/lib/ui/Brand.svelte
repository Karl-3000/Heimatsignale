<script lang="ts">
	import { session } from '$lib/api/session.svelte';

	/**
	 * Das Zeichen von Heimatsignale mit Wortmarke.
	 *
	 * Das Zeichen ist ein kleines h, das zugleich ein Torbogen ist: Im Bogen steht das
	 * Heimatlicht wie eine aufgehende Sonne in einer Tür. Der Stamm und der Bogen sind ein
	 * einziger runder Strich. Die Wortmarke ist gesetzter Text in Bricolage Grotesque;
	 * der Name kommt aus der Sitzung (site.name).
	 */
	interface Props {
		href?: string | null;
		/** "stage": Zeichen in der Schriftfarbe der Bühne, auf dem Himmel. */
		tone?: 'page' | 'stage';
		/** Nur das Zeichen, z. B. in engen Kopfzeilen. Der Name bleibt für Screenreader erhalten. */
		markOnly?: boolean;
		size?: 'md' | 'lg';
	}

	let { href = '/', tone = 'page', markOnly = false, size = 'md' }: Props = $props();
</script>

{#snippet content()}
	<svg class="mark" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
		<path class="lines" d="M17 8V55M17 40C17 24 47 24 47 40V55" />
		<circle class="home" cx="32" cy="47" r="7.5" />
	</svg>
	<span class="word" class:hs-sr-only={markOnly}>{session.siteName}</span>
{/snippet}

{#if href}
	<a class="brand brand-{tone} brand-{size}" {href} data-testid="brand">{@render content()}</a>
{:else}
	<span class="brand brand-{tone} brand-{size}" data-testid="brand">{@render content()}</span>
{/if}

<style>
	.brand {
		--mark-ink: var(--hs-ink);
		--mark-light: var(--hs-origin);
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		min-height: 2.75rem;
		color: var(--hs-ink);
		text-decoration: none;
	}

	.brand-stage {
		--mark-ink: var(--hs-stage-ink);
		--mark-light: var(--hs-stage-origin);
		color: var(--hs-stage-ink);
	}

	.mark {
		width: 2rem;
		height: 2rem;
		flex: none;
	}

	.lines {
		fill: none;
		stroke: var(--mark-ink);
		stroke-width: 9;
		stroke-linecap: round;
		stroke-linejoin: round;
	}

	/* Der Lichtpunkt ist immer Heimatlicht, auf jedem Grund. */
	.home {
		fill: var(--hs-heimatlicht);
	}

	.brand-stage .home {
		fill: var(--hs-stage-origin);
	}

	.word {
		font-family: var(--hs-font-display);
		font-weight: 650;
		font-size: 1.3125rem;
		letter-spacing: -0.035em;
		line-height: 1;
	}

	.brand-lg .mark {
		width: 3rem;
		height: 3rem;
	}

	.brand-lg .word {
		font-size: 1.875rem;
	}

	a.brand:focus-visible {
		outline-offset: 4px;
		border-radius: var(--hs-radius-md);
	}

	.brand-stage:focus-visible {
		outline-color: var(--hs-stage-accent);
	}
</style>
