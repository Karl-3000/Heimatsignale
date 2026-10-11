<script lang="ts">
	import { onMount, tick, untrack } from 'svelte';
	import Plus from '@lucide/svelte/icons/plus';
	import Minus from '@lucide/svelte/icons/minus';
	import LocateFixed from '@lucide/svelte/icons/locate-fixed';
	import Icon from '$lib/ui/Icon.svelte';
	import { personen } from '$lib/util/format';
	import { HALF_EXTENT, RING_RADIUS, ROOT_RADIUS } from './geometry';
	import { treeKeyAction } from './keyboard';
	import { LABEL_FONT_SIZE, LABEL_LINE_HEIGHT, LABEL_SUB_FONT_SIZE, estimateTextWidth } from './labels';
	import type { SceneNode } from './scene';
	import { LEVEL_LABEL, ROOT_ID } from './types';
	import type { NetworkView } from './view.svelte';

	/**
	 * Das Herkunftsnetz als SVG. Die Komponente zeichnet nur, was NetworkView
	 * berechnet hat: Positionen sind eingefroren, hier wird nichts simuliert.
	 * Bewegung gibt es ausschließlich beim Aufklappen (300 ms) und nie von selbst.
	 */
	interface Props {
		view: NetworkView;
		/** Höhe des sichtbaren Ausschnitts als CSS-Wert. */
		height?: string;
		testid?: string;
	}

	let { view, height = 'min(70dvh, 40rem)', testid = 'network' }: Props = $props();

	const SIZE = HALF_EXTENT * 2;
	const ZOOM_MIN = 0.6;
	const ZOOM_MAX = 1.6;

	let scroller = $state<HTMLDivElement | null>(null);
	let svg = $state<SVGSVGElement | null>(null);
	let hoverId = $state<string | null>(null);
	let focusInside = $state(false);
	let entering = $state.raw<ReadonlySet<string>>(new Set());
	let dragging = $state(false);

	const scene = $derived(view.scene);
	const nodeById = $derived(new Map(scene.nodes.map((n) => [n.id, n])));
	const activeId = $derived(hoverId ?? (focusInside ? view.focusedNodeId : null));
	const path = $derived(new Set(activeId ? view.pathToRoot(activeId) : []));
	const depths = $derived(new Set(scene.nodes.map((n) => n.depth)));
	const activeNode = $derived(activeId ? (nodeById.get(activeId) ?? null) : null);
	/** Der volle Name erscheint an Fokus, Zeiger und Tipp, wenn die Beschriftung gekürzt oder ausgeblendet ist. */
	const plate = $derived.by(() => {
		if (!activeNode) return null;
		const label = scene.labels.get(activeNode.id);
		if (label && label.variant === 'full') return null;
		const text = `${activeNode.node.name}, ${personen(activeNode.node.count)}`;
		const width = estimateTextWidth(text, LABEL_FONT_SIZE) + 16;
		const x = Math.max(-HALF_EXTENT + width / 2 + 4, Math.min(HALF_EXTENT - width / 2 - 4, activeNode.x));
		const above = activeNode.y - activeNode.hit - 16 > -HALF_EXTENT;
		const y = above ? activeNode.y - activeNode.hit - 16 : activeNode.y + activeNode.hit + 16;
		return { text, width, x, y };
	});

	function reducedMotion(): boolean {
		return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
	}

	function ariaLabel(n: SceneNode): string {
		const parts = [n.node.name, LEVEL_LABEL[n.node.level], personen(n.node.count)];
		if (n.node.own) parts.push('deine Herkunft');
		if (n.node.level === 'place') parts.push(view.isOpen(n.id) ? 'Personen werden angezeigt' : 'Personen anzeigen');
		return parts.join(', ');
	}

	/** Startpunkt der Aufklapp-Animation: die Position des Elternknotens. */
	function origin(n: SceneNode): { x: number; y: number } {
		const parentId = n.node.parentId;
		if (!parentId || parentId === ROOT_ID) return { x: 0, y: 0 };
		const parent = nodeById.get(parentId);
		return parent ? { x: parent.x, y: parent.y } : { x: 0, y: 0 };
	}

	function transformOf(n: SceneNode): string {
		if (entering.has(n.id)) {
			const o = origin(n);
			return `translate(${o.x}px, ${o.y}px) scale(0.2)`;
		}
		return `translate(${n.x}px, ${n.y}px)`;
	}

	/** Verschiebt den Ausschnitt so wenig wie nötig, bis die genannten Knoten sichtbar sind. */
	function reveal(ids: readonly string[], smooth: boolean): void {
		const el = scroller;
		if (!el || ids.length === 0) return;
		let x0 = Infinity;
		let y0 = Infinity;
		let x1 = -Infinity;
		let y1 = -Infinity;
		for (const id of ids) {
			const n = id === ROOT_ID ? { x: 0, y: 0, hit: ROOT_RADIUS } : nodeById.get(id);
			if (!n) continue;
			x0 = Math.min(x0, n.x - n.hit);
			y0 = Math.min(y0, n.y - n.hit);
			x1 = Math.max(x1, n.x + n.hit);
			y1 = Math.max(y1, n.y + n.hit);
		}
		if (!Number.isFinite(x0)) return;
		const pad = 56;
		const z = view.zoom;
		const left = (x0 + HALF_EXTENT) * z - pad;
		const right = (x1 + HALF_EXTENT) * z + pad;
		const top = (y0 + HALF_EXTENT) * z - pad;
		const bottom = (y1 + HALF_EXTENT) * z + pad;
		let targetLeft = el.scrollLeft;
		let targetTop = el.scrollTop;
		if (right - left > el.clientWidth) targetLeft = (left + right) / 2 - el.clientWidth / 2;
		else if (left < el.scrollLeft) targetLeft = left;
		else if (right > el.scrollLeft + el.clientWidth) targetLeft = right - el.clientWidth;
		if (bottom - top > el.clientHeight) targetTop = (top + bottom) / 2 - el.clientHeight / 2;
		else if (top < el.scrollTop) targetTop = top;
		else if (bottom > el.scrollTop + el.clientHeight) targetTop = bottom - el.clientHeight;
		if (targetLeft === el.scrollLeft && targetTop === el.scrollTop) return;
		el.scrollTo({ left: targetLeft, top: targetTop, behavior: smooth && !reducedMotion() ? 'smooth' : 'auto' });
	}

	function center(smooth: boolean): void {
		const el = scroller;
		if (!el) return;
		const mid = HALF_EXTENT * view.zoom;
		el.scrollTo({ left: mid - el.clientWidth / 2, top: mid - el.clientHeight / 2, behavior: smooth && !reducedMotion() ? 'smooth' : 'auto' });
	}

	async function setZoom(next: number): Promise<void> {
		const el = scroller;
		const clamped = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.round(next * 10) / 10));
		if (!el || clamped === view.zoom) return;
		// Der Mittelpunkt des Ausschnitts bleibt beim Zoomen stehen.
		const cx = (el.scrollLeft + el.clientWidth / 2) / view.zoom;
		const cy = (el.scrollTop + el.clientHeight / 2) / view.zoom;
		view.zoom = clamped;
		await tick();
		el.scrollTo({ left: cx * clamped - el.clientWidth / 2, top: cy * clamped - el.clientHeight / 2, behavior: 'auto' });
	}

	function focusNode(id: string): void {
		const el = svg?.querySelector<SVGGElement>(`[data-node-id="${id}"]`);
		el?.focus({ preventScroll: true });
		reveal([id], true);
	}

	async function activate(id: string): Promise<void> {
		view.focus(id);
		focusNode(id);
		await view.toggle(id);
	}

	async function handleKey(event: KeyboardEvent, id: string): Promise<void> {
		const action = treeKeyAction(event.key, view.keyRows, id);
		if (!action) return;
		event.preventDefault();
		if (action.type === 'focus') {
			view.focus(action.id);
			await tick();
			focusNode(action.id);
		} else if (action.type === 'expand') {
			await view.expand(action.id);
		} else if (action.type === 'collapse') {
			view.collapse(action.id);
		} else {
			await view.toggle(action.id);
		}
	}

	function handleFocusOut(event: FocusEvent): void {
		const next = event.relatedTarget;
		if (!(next instanceof Node) || !svg?.contains(next)) focusInside = false;
	}

	// Ziehen mit der Maus verschiebt den Ausschnitt. Berührung nutzt das native Scrollen.
	let dragStart = { x: 0, y: 0, left: 0, top: 0 };

	function handlePointerDown(event: PointerEvent): void {
		if (event.pointerType !== 'mouse' || event.button !== 0 || !scroller) return;
		const target = event.target;
		if (target instanceof Element && target.closest('[data-node-id]')) return;
		dragging = true;
		dragStart = { x: event.clientX, y: event.clientY, left: scroller.scrollLeft, top: scroller.scrollTop };
		scroller.setPointerCapture(event.pointerId);
	}

	function handlePointerMove(event: PointerEvent): void {
		if (!dragging || !scroller) return;
		scroller.scrollLeft = dragStart.left - (event.clientX - dragStart.x);
		scroller.scrollTop = dragStart.top - (event.clientY - dragStart.y);
	}

	function handlePointerUp(event: PointerEvent): void {
		if (!dragging) return;
		dragging = false;
		scroller?.releasePointerCapture(event.pointerId);
	}

	function handleScroll(): void {
		if (scroller) view.scroll = { left: scroller.scrollLeft, top: scroller.scrollTop };
	}

	onMount(() => {
		const el = scroller;
		if (!el) return;
		if (view.scroll) {
			el.scrollTo({ left: view.scroll.left, top: view.scroll.top, behavior: 'auto' });
		} else {
			// Auf schmalen Bildschirmen etwas kleiner beginnen, damit der erste Ring ganz sichtbar ist.
			if (el.clientWidth < 520 && view.zoom === 1) view.zoom = 0.8;
			void tick().then(() => center(false));
		}
	});

	// Neue Knoten wachsen aus ihrem Elternknoten heraus. Nur nach einer Nutzeraktion,
	// nie beim ersten Zeichnen und nie bei reduzierter Bewegung.
	let seenRevision = untrack(() => view.revision);
	$effect(() => {
		const revision = view.revision;
		if (revision === seenRevision) return;
		seenRevision = revision;
		const added = view.added;
		if (added.length === 0) return;
		if (reducedMotion()) {
			void tick().then(() => reveal(added, false));
			return;
		}
		entering = new Set(added);
		let second = 0;
		const first = requestAnimationFrame(() => {
			second = requestAnimationFrame(() => {
				entering = new Set();
				reveal(added, true);
			});
		});
		return () => {
			cancelAnimationFrame(first);
			cancelAnimationFrame(second);
		};
	});
</script>

<div class="frame" style:height data-testid={testid}>
	<div
		class="scroller"
		class:dragging
		bind:this={scroller}
		onscroll={handleScroll}
		onpointerdown={handlePointerDown}
		onpointermove={handlePointerMove}
		onpointerup={handlePointerUp}
		onpointercancel={handlePointerUp}
		role="presentation"
	>
		<svg
			bind:this={svg}
			width={SIZE * view.zoom}
			height={SIZE * view.zoom}
			viewBox="{-HALF_EXTENT} {-HALF_EXTENT} {SIZE} {SIZE}"
			role="group"
			aria-label="Herkunftsnetz von {view.core.root.name}. Mit den Pfeiltasten bewegst du dich durch die Knoten, Enter klappt eine Stufe auf oder zu."
			onfocusin={() => (focusInside = true)}
			onfocusout={handleFocusOut}
		>
			<g class="guides" aria-hidden="true">
				{#if depths.has(1)}<circle r={RING_RADIUS.state} />{/if}
				{#if depths.has(2)}<circle r={RING_RADIUS.district} />{/if}
				{#if depths.has(3)}<circle r={RING_RADIUS.place} />{/if}
			</g>

			<g class="edges" aria-hidden="true">
				{#each scene.edges as edge (edge.id)}
					<path
						d={edge.d}
						stroke-width={edge.width}
						class:highlight={path.has(edge.id)}
						class:dim={path.size > 0 && !path.has(edge.id)}
						class:entering={entering.has(edge.id)}
					/>
				{/each}
			</g>

			<g class="labels" aria-hidden="true">
				{#each scene.nodes as n (n.id)}
					{@const label = scene.labels.get(n.id)}
					{#if label && label.variant !== 'hidden'}
						<text
							x={label.x}
							y={label.y}
							text-anchor={label.anchor}
							dominant-baseline="central"
							class:own={n.node.own}
							class:strong={path.has(n.id)}
							class:entering={entering.has(n.id)}
							font-size={LABEL_FONT_SIZE}
						>
							<tspan>{label.text}</tspan>{#if label.suffix}<tspan class="suffix" dx="4">{label.suffix}</tspan>{/if}
							{#if label.sub}
								<tspan class="sub" x={label.x} dy={LABEL_LINE_HEIGHT} font-size={LABEL_SUB_FONT_SIZE}>{label.sub}</tspan>
							{/if}
						</text>
					{/if}
				{/each}
				<text class="root-label" x={scene.rootLabel.x} y={scene.rootLabel.y} text-anchor="middle" dominant-baseline="central" font-size="13">
					{view.core.root.name}
				</text>
			</g>

			<g class="nodes">
				<g
					class="node root"
					role="button"
					aria-label="{view.core.root.name}, Wohnort in der Mitte, {personen(view.core.root.count)}. Ausschnitt hierher zurückholen."
					tabindex={view.focusedNodeId === ROOT_ID ? 0 : -1}
					data-node-id={ROOT_ID}
					data-testid="network-root"
					onclick={() => center(true)}
					onkeydown={(event) => {
						if (event.key === 'Enter' || event.key === ' ') {
							event.preventDefault();
							center(true);
						} else {
							void handleKey(event, ROOT_ID);
						}
					}}
					onfocus={() => view.focus(ROOT_ID)}
				>
					<circle class="focus-ring" r={ROOT_RADIUS + 5} />
					<circle class="dot" r={ROOT_RADIUS} />
					<text class="count hs-num" text-anchor="middle" dominant-baseline="central" font-size="13">{view.core.root.count}</text>
				</g>

				{#each scene.nodes as n (n.id)}
					<g
						class="node level-{n.node.level}"
						class:own={n.node.own}
						class:open={view.isOpen(n.id)}
						class:selected={view.selectedId === n.id}
						class:loading={view.isLoading(n.id)}
						class:on-path={path.has(n.id)}
						class:entering={entering.has(n.id)}
						style:transform={transformOf(n)}
						role="button"
						aria-label={ariaLabel(n)}
						aria-expanded={view.isOpen(n.id) ? 'true' : 'false'}
						aria-busy={view.isLoading(n.id) ? 'true' : undefined}
						tabindex={view.focusedNodeId === n.id ? 0 : -1}
						data-node-id={n.id}
						data-level={n.node.level}
						data-own={n.node.own ? 'true' : undefined}
						data-testid="network-node"
						onclick={() => void activate(n.id)}
						onkeydown={(event) => void handleKey(event, n.id)}
						onfocus={() => view.focus(n.id)}
						onpointerenter={() => (hoverId = n.id)}
						onpointerleave={() => (hoverId = null)}
					>
						<circle class="hit" r={n.hit} />
						<circle class="focus-ring" r={n.hit} />
						{#if n.node.own}<circle class="own-ring" r={n.r + 3.5} />{/if}
						{#if view.selectedId === n.id}<circle class="selected-ring" r={n.r + (n.node.own ? 7 : 4)} />{/if}
						{#if view.isLoading(n.id)}<circle class="loading-ring" r={n.r + 4} />{/if}
						<circle class="dot" r={n.r} />
						{#if n.countInside}
							<text class="count hs-num" text-anchor="middle" dominant-baseline="central" font-size={n.r >= 16 ? 13 : 11}>{n.node.count}</text>
						{/if}
					</g>
				{/each}
			</g>

			{#if plate}
				<g class="plate" aria-hidden="true" transform="translate({plate.x} {plate.y})">
					<rect x={-plate.width / 2} y="-12" width={plate.width} height="24" rx="6" />
					<text text-anchor="middle" dominant-baseline="central" font-size={LABEL_FONT_SIZE}>{plate.text}</text>
				</g>
			{/if}
		</svg>
	</div>

	<div class="controls">
		<button type="button" onclick={() => void setZoom(view.zoom + 0.2)} disabled={view.zoom >= ZOOM_MAX} aria-label="Netz vergrößern" data-testid="network-zoom-in">
			<Icon icon={Plus} size={18} />
		</button>
		<button type="button" onclick={() => void setZoom(view.zoom - 0.2)} disabled={view.zoom <= ZOOM_MIN} aria-label="Netz verkleinern" data-testid="network-zoom-out">
			<Icon icon={Minus} size={18} />
		</button>
		<button type="button" onclick={() => center(true)} aria-label="Zum Wohnort in der Mitte" data-testid="network-center">
			<Icon icon={LocateFixed} size={18} />
		</button>
	</div>
</div>

<style>
	.frame {
		position: relative;
		min-height: 20rem;
		border: 1px solid var(--hs-line);
		border-radius: var(--hs-radius-lg);
		background: var(--hs-surface);
		overflow: hidden;
	}

	.scroller {
		width: 100%;
		height: 100%;
		overflow: auto;
		cursor: grab;
		overscroll-behavior: contain;
		scrollbar-width: thin;
	}

	.scroller.dragging {
		cursor: grabbing;
		user-select: none;
	}

	svg {
		display: block;
		font-family: var(--hs-font-sans);
	}

	.guides circle {
		fill: none;
		stroke: var(--hs-line);
		stroke-width: 1;
		stroke-dasharray: 2 7;
	}

	.edges path {
		fill: none;
		stroke: var(--hs-edge);
		stroke-opacity: var(--hs-edge-opacity);
		stroke-linecap: round;
		transition:
			stroke-opacity var(--hs-duration-fast) var(--hs-ease-standard),
			opacity var(--hs-duration-slow) var(--hs-ease-standard);
	}

	.edges path.highlight {
		stroke: var(--hs-accent);
		stroke-opacity: 0.95;
	}

	.edges path.dim {
		stroke-opacity: calc(var(--hs-edge-opacity) * 0.55);
	}

	.edges path.entering {
		opacity: 0;
		transition: none;
	}

	.labels text {
		fill: var(--hs-ink);
		font-weight: var(--hs-weight-regular);
		paint-order: stroke;
		stroke: var(--hs-surface);
		stroke-width: 3.5px;
		stroke-linejoin: round;
		pointer-events: none;
		transition: opacity var(--hs-duration-slow) var(--hs-ease-standard);
	}

	.labels text.strong,
	.labels text.own {
		font-weight: var(--hs-weight-strong);
	}

	.labels text.entering {
		opacity: 0;
		transition: none;
	}

	.labels .suffix {
		fill: var(--hs-ink-muted);
		font-variant-numeric: tabular-nums;
	}

	.labels .sub {
		fill: var(--hs-origin);
		font-weight: var(--hs-weight-strong);
	}

	.labels .root-label {
		font-weight: var(--hs-weight-strong);
	}

	.node {
		cursor: pointer;
		outline: none;
		transition:
			transform var(--hs-duration-slow) var(--hs-ease-standard),
			opacity var(--hs-duration-slow) var(--hs-ease-standard);
	}

	.node.entering {
		opacity: 0;
		transition: none;
	}

	.hit {
		fill: transparent;
	}

	.dot {
		fill: var(--hs-node);
		stroke: var(--hs-surface);
		stroke-width: 1.5;
		transition: fill var(--hs-duration-fast) var(--hs-ease-standard);
	}

	.node.root .dot {
		fill: var(--hs-node-root);
	}

	.node.own .dot {
		fill: var(--hs-origin);
	}

	.node.on-path:not(.own):not(.root) .dot {
		fill: var(--hs-accent);
	}

	.own-ring {
		fill: none;
		stroke: var(--hs-origin);
		stroke-width: 1.5;
	}

	.selected-ring {
		fill: none;
		stroke: var(--hs-accent);
		stroke-width: 2.5;
	}

	.loading-ring {
		fill: none;
		stroke: var(--hs-ink-muted);
		stroke-width: 2;
		stroke-dasharray: 3 4;
	}

	.focus-ring {
		fill: none;
		stroke: var(--hs-focus);
		stroke-width: 2.5;
		opacity: 0;
	}

	.node:focus-visible .focus-ring {
		opacity: 1;
	}

	.count {
		fill: var(--hs-on-node);
		font-weight: var(--hs-weight-strong);
		pointer-events: none;
	}

	.node.root .count {
		fill: var(--hs-on-node-root);
	}

	.node.own .count,
	.node.on-path:not(.root) .count {
		fill: var(--hs-on-origin);
	}

	.node.on-path:not(.own):not(.root) .count {
		fill: var(--hs-on-accent);
	}

	.plate {
		pointer-events: none;
	}

	.plate rect {
		fill: var(--hs-ink);
	}

	.plate text {
		fill: var(--hs-bg);
		font-weight: var(--hs-weight-strong);
	}

	.controls {
		position: absolute;
		right: var(--hs-space-3);
		bottom: var(--hs-space-3);
		display: flex;
		flex-direction: column;
		border: 1px solid var(--hs-line-strong);
		border-radius: var(--hs-radius-md);
		background: var(--hs-raised);
		box-shadow: var(--hs-shadow-sm);
		overflow: hidden;
	}

	.controls button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 2.5rem;
		border: 0;
		background: transparent;
		color: var(--hs-ink);
		cursor: pointer;
	}

	.controls button + button {
		border-top: 1px solid var(--hs-line);
	}

	.controls button:hover:not(:disabled) {
		background: var(--hs-sunken);
	}

	.controls button:disabled {
		color: var(--hs-ink-subtle);
		opacity: 0.5;
		cursor: not-allowed;
	}

	.controls button:focus-visible {
		outline: 2px solid var(--hs-focus);
		outline-offset: -2px;
	}
</style>
