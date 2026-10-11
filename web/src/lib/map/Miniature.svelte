<script lang="ts">
	import { miniatureGeometry, type MiniatureSelection } from './miniature';

	/**
	 * Miniatur des Stufe-1-Netzes eines Wohnorts: bis zu fünf größte Bundesländer plus
	 * immer das eigene, der Rest als "+N". Reine Grafik; die Bedeutung trägt die
	 * Beschriftung des umgebenden Buttons.
	 */
	interface Props {
		selection: MiniatureSelection;
		radius: number;
		/** Ortsname unter der Miniatur, wenn genug Platz ist. */
		caption?: string | null;
	}

	let { selection, radius, caption = null }: Props = $props();

	const inner = $derived(caption ? radius - 10 : radius);
	const geo = $derived(miniatureGeometry(selection, inner));
	const offsetY = $derived(caption ? -5 : 0);
</script>

<svg width={radius * 2} height={radius * 2} viewBox="{-radius} {-radius} {radius * 2} {radius * 2}" aria-hidden="true" focusable="false">
	<circle class="plate" r={radius - 0.75} />
	<g transform="translate(0 {offsetY})">
		{#each geo.nodes as n (n.stateCode)}
			<line x1="0" y1="0" x2={n.x} y2={n.y} stroke-width={n.edgeWidth} class:own={n.own} />
		{/each}
		{#if geo.rest}
			<line x1="0" y1="0" x2={geo.rest.x * 0.72} y2={geo.rest.y * 0.72} stroke-width="1" class="rest-line" />
		{/if}
		{#each geo.nodes as n (n.stateCode)}
			{#if n.own}<circle class="own-ring" cx={n.x} cy={n.y} r={n.r + 2.5} />{/if}
			<circle class="node" class:own={n.own} cx={n.x} cy={n.y} r={n.r} />
			{#if n.label}
				<text class="state" class:own={n.own} x={n.labelX} y={n.labelY} text-anchor="middle" dominant-baseline="central">{n.label}</text>
			{/if}
		{/each}
		{#if geo.rest}
			<text class="rest hs-num" x={geo.rest.x} y={geo.rest.y} text-anchor="middle" dominant-baseline="central">{geo.rest.text}</text>
		{/if}
		<circle class="center" r={geo.centerRadius} />
		<text class="total hs-num" text-anchor="middle" dominant-baseline="central" font-size={geo.centerRadius >= 13 ? 12 : 10}>{selection.total}</text>
	</g>
	{#if caption}
		<text class="caption" y={radius - 9} text-anchor="middle" dominant-baseline="central">{caption}</text>
	{/if}
</svg>

<style>
	svg {
		display: block;
		font-family: var(--hs-font-sans);
		overflow: visible;
	}

	/* Gläserne Scheibe auf der Bühne; die Lichter darin sind dieselben wie im Netz. */
	.plate {
		fill: var(--hs-stage-glass);
		stroke: var(--hs-stage-line);
		stroke-width: 1;
	}

	line {
		stroke: var(--hs-stage-ink);
		stroke-opacity: 0.32;
		stroke-linecap: round;
	}

	line.own {
		stroke: var(--hs-stage-origin);
		stroke-opacity: 0.8;
	}

	.rest-line {
		stroke-dasharray: 1.5 3;
	}

	.node {
		fill: var(--hs-stage-ink);
	}

	.node.own {
		fill: var(--hs-stage-origin);
	}

	.own-ring {
		fill: none;
		stroke: var(--hs-stage-origin);
		stroke-width: 1.25;
	}

	.center {
		fill: var(--hs-stage-ink);
	}

	.total {
		fill: var(--hs-stage-on-light);
		font-weight: var(--hs-weight-strong);
	}

	.state {
		fill: var(--hs-stage-muted);
		font-size: 9px;
		font-weight: var(--hs-weight-strong);
	}

	.state.own {
		fill: var(--hs-stage-origin);
	}

	.rest {
		fill: var(--hs-stage-muted);
		font-size: 10px;
		font-weight: var(--hs-weight-strong);
	}

	.caption {
		fill: var(--hs-stage-ink);
		font-size: 10.5px;
		font-weight: var(--hs-weight-strong);
	}
</style>
