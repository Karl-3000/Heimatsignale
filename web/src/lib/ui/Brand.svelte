<script lang="ts">
	import { session } from '$lib/api/session.svelte';

	/**
	 * Das Zeichen von Heimatsignale mit Wortmarke.
	 *
	 * Das Zeichen ist ein H aus zwei Lichtern: unten links der Ort, an dem du jetzt wohnst,
	 * oben rechts frei schwebend das Heimatlicht, dazwischen eine geschwungene Linie wie die
	 * Kanten des Herkunftsnetzes. Die Wortmarke ist gesetzter Text in Bricolage Grotesque;
	 * der Name kommt aus der Sitzung (site.name).
	 */
	interface Props {
		href?: string | null;
		/** "stage": helles Zeichen auf Nachtblau. */
		tone?: 'page' | 'stage';
		/** Nur das Zeichen, z. B. in engen Kopfzeilen. Der Name bleibt für Screenreader erhalten. */
		markOnly?: boolean;
		size?: 'md' | 'lg';
	}

	let { href = '/', tone = 'page', markOnly = false, size = 'md' }: Props = $props();
</script>

{#snippet content()}
	<svg class="mark" viewBox="0 0 64 64" aria-hidden="true" focusable="false">
		<path class="lines" d="M19 8V44M45 29V56M19 39C32 39 32 30 45 30" />
		<circle class="here" cx="19" cy="46" r="10.5" />
		<circle class="home" cx="45" cy="13" r="7.5" />
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
		stroke-width: 6.5;
		stroke-linecap: round;
	}

	.here {
		fill: var(--mark-ink);
	}

	/* Auf hellem Grund ein sattes Bernstein, damit das Licht als Grafik genug Kontrast hat. */
	.home {
		fill: color-mix(in srgb, var(--hs-heimatlicht) 82%, var(--mark-light));
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
