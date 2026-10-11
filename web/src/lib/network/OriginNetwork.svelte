<script lang="ts">
	import { onMount, tick, untrack } from 'svelte';
	import Plus from '@lucide/svelte/icons/plus';
	import Minus from '@lucide/svelte/icons/minus';
	import Scan from '@lucide/svelte/icons/scan';
	import Icon from '$lib/ui/Icon.svelte';
	import { personen } from '$lib/util/format';
	import { fitCamera, panIntoView, screenRectToBox, unionBox, viewBounds, type Camera } from './camera';
	import { HALF_EXTENT, RING_RADIUS, ROOT_RADIUS } from './geometry';
	import { treeKeyAction } from './keyboard';
	import { LABEL_FONT_SIZE, estimateTextWidth, type Box } from './labels';
	import { placeSceneLabels, type SceneNode } from './scene';
	import { LEVEL_LABEL, ROOT_ID } from './types';
	import type { NetworkView } from './view.svelte';

	/**
	 * Das Herkunftsnetz auf der Bühne: Lichter auf Nachtblau.
	 *
	 * Die Komponente zeichnet nur, was NetworkView berechnet hat. Positionen sind eingefroren,
	 * hier wird nichts simuliert. Beweglich ist allein die Kamera: Nach jeder Änderung passt sie
	 * den sichtbaren Baum mit Rand in die Bühne ein. Bewegung gibt es nur als Antwort auf eine
	 * Aktion (Aufklappen, 300 ms) und nie von selbst.
	 */
	interface Props {
		view: NetworkView;
		/** Höhe der Bühne als CSS-Wert. */
		height?: string;
		/** Einmaliges Aufleuchten von der Mitte nach außen beim ersten Zeichnen (Startseite). */
		intro?: boolean;
		/** Ohne eigenen Bühnengrund, wenn die umgebende Fläche schon die Bühne ist (Hero der Startseite). */
		plain?: boolean;
		testid?: string;
	}

	let { view, height = 'clamp(26rem, 72dvh, 46rem)', intro = false, plain = false, testid = 'network' }: Props = $props();

	const uid = $props.id();
	const K_MIN = 0.22;
	const K_MAX = 2.2;
	/** Kleinster und größter Maßstab, den das automatische Einpassen wählt. */
	const K_FIT_MIN = 0.4;
	const K_FIT_MAX = 1.25;
	/** Platz für die Bedienelemente unten rechts: Dort liegen nie Knoten oder Beschriftungen. */
	const CONTROLS = { width: 156, height: 64 };

	let frame = $state<HTMLDivElement | null>(null);
	let svg = $state<SVGSVGElement | null>(null);
	let size = $state.raw({ width: 0, height: 0 });
	let camera = $state.raw<Camera>(untrack(() => view.camera) ?? { x: 0, y: 0, k: 1 });
	/** Kamera, für die die Beschriftungen platziert wurden. Folgt dem Einpassen und Zoomen, nicht dem Ziehen. */
	let labelCamera = $state.raw<Camera>(untrack(() => view.camera) ?? { x: 0, y: 0, k: 1 });
	let hoverId = $state<string | null>(null);
	let focusInside = $state(false);
	let entering = $state.raw<ReadonlySet<string>>(new Set());
	let pulsing = $state.raw<ReadonlySet<string>>(new Set());
	let dragging = $state(false);
	let introRunning = $state(untrack(() => intro));

	const scene = $derived(view.scene);
	const nodeById = $derived(new Map(scene.nodes.map((n) => [n.id, n])));
	const activeId = $derived(hoverId ?? (focusInside ? view.focusedNodeId : null));
	const path = $derived(new Set(activeId ? view.pathToRoot(activeId) : []));
	const depths = $derived(new Set(scene.nodes.map((n) => n.depth)));
	const activeNode = $derived(activeId ? (nodeById.get(activeId) ?? null) : null);

	/** Auf dem Bildschirm bleiben auch die kleinsten Lichter sichtbar und treffbar. */
	const minDot = $derived(3.2 / camera.k);
	const minHit = $derived(11 / camera.k);

	const placed = $derived.by(() => {
		if (size.width === 0) return { labels: scene.labels, rootLabel: { ...scene.rootLabel, fontSize: 13 } };
		const vp = size;
		const obstacle = screenRectToBox(labelCamera, vp, {
			left: vp.width - CONTROLS.width,
			top: vp.height - CONTROLS.height,
			right: vp.width,
			bottom: vp.height
		});
		return placeSceneLabels(scene.labelInputs, view.core.root.name, {
			scale: labelCamera.k,
			bounds: viewBounds(labelCamera, vp, 8),
			obstacles: [obstacle]
		});
	});

	/** Der volle Name erscheint an Fokus, Zeiger und Tipp, wenn die Beschriftung gekürzt oder ausgeblendet ist. */
	const plate = $derived.by(() => {
		if (!activeNode || size.width === 0) return null;
		const label = placed.labels.get(activeNode.id);
		if (label && label.variant === 'full') return null;
		const k = 1 / camera.k;
		const text = `${activeNode.node.name}, ${personen(activeNode.node.count)}`;
		const width = (estimateTextWidth(text, LABEL_FONT_SIZE) + 20) * k;
		const b = viewBounds(camera, size, 8);
		const x = Math.max(b.x0 + width / 2, Math.min(b.x1 - width / 2, activeNode.x));
		const offset = Math.max(activeNode.hit, minHit) + 18 * k;
		const above = activeNode.y - offset - 14 * k > b.y0;
		return { text, width, x, y: above ? activeNode.y - offset : activeNode.y + offset, k };
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

	function boxOf(ids: readonly string[]): Box | null {
		const boxes: Box[] = [];
		for (const id of ids) {
			if (id === ROOT_ID) {
				boxes.push({ x0: -ROOT_RADIUS, y0: -ROOT_RADIUS, x1: ROOT_RADIUS, y1: ROOT_RADIUS + 26 });
				continue;
			}
			const n = nodeById.get(id);
			if (n) boxes.push({ x0: n.x - n.hit, y0: n.y - n.hit, x1: n.x + n.hit, y1: n.y + n.hit });
		}
		return unionBox(boxes);
	}

	function setCamera(next: Camera, relabel: boolean): void {
		camera = next;
		view.camera = next;
		if (relabel) labelCamera = next;
	}

	/**
	 * Passt den sichtbaren Baum in die Bühne ein, mit Rand für Beschriftungen und ohne die
	 * Fläche der Bedienelemente. Passt nicht alles hinein, bleibt der Maßstab lesbar und der
	 * Ausschnitt zeigt die Knoten in `focus` (z. B. die gerade aufgeklappten samt Elternknoten).
	 */
	function fit(focus: readonly string[] | null = null, whole: boolean = false): void {
		if (size.width === 0) return;
		const side = Math.min(110, Math.max(36, size.width * 0.14));
		const pad = { left: side, right: side, top: 34, bottom: CONTROLS.height + 8 };
		const all = boxOf([ROOT_ID, ...scene.nodes.map((n) => n.id)]);
		if (!all) return;
		// "Ganzes Netz zeigen" darf kleiner werden als das automatische Einpassen, bis wirklich alles im Bild ist.
		let result = fitCamera(all, size, pad, whole ? K_MIN : K_FIT_MIN, K_FIT_MAX);
		if (!result.fits && focus && focus.length > 0) {
			const part = boxOf(focus);
			if (part) result = fitCamera(part, size, pad, K_FIT_MIN, Math.min(1, K_FIT_MAX));
		}
		setCamera({ x: result.x, y: result.y, k: result.k }, true);
	}

	function zoomBy(factor: number): void {
		const k = Math.max(K_MIN, Math.min(K_MAX, camera.k * factor));
		if (k === camera.k) return;
		setCamera({ x: camera.x, y: camera.y, k }, true);
	}

	function focusNode(id: string): void {
		const el = svg?.querySelector<SVGGElement>(`[data-node-id="${id}"]`);
		el?.focus({ preventScroll: true });
		const n = id === ROOT_ID ? { x: 0, y: 0 } : nodeById.get(id);
		if (n && size.width > 0) {
			const next = panIntoView(camera, { width: size.width, height: size.height - CONTROLS.height }, n, 48);
			if (next !== camera) setCamera(next, true);
		}
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

	// Ziehen verschiebt den Ausschnitt. Senkrechtes Wischen auf dem Telefon scrollt weiter die Seite.
	let dragStart = { px: 0, py: 0, x: 0, y: 0 };
	let dragMoved = false;

	function handlePointerDown(event: PointerEvent): void {
		if (event.button !== 0 || !svg) return;
		const target = event.target;
		if (target instanceof Element && target.closest('[data-node-id]')) return;
		// Kein Textmarkieren beim Ziehen mit der Maus. Berührung behält ihr natives Verhalten (senkrechtes Scrollen).
		if (event.pointerType === 'mouse') event.preventDefault();
		dragging = true;
		dragMoved = false;
		dragStart = { px: event.clientX, py: event.clientY, x: camera.x, y: camera.y };
		svg.setPointerCapture(event.pointerId);
	}

	function handlePointerMove(event: PointerEvent): void {
		if (!dragging) return;
		const dx = event.clientX - dragStart.px;
		const dy = event.clientY - dragStart.py;
		if (Math.abs(dx) + Math.abs(dy) > 3) dragMoved = true;
		setCamera({ x: dragStart.x - dx / camera.k, y: dragStart.y - dy / camera.k, k: camera.k }, false);
	}

	function handlePointerUp(event: PointerEvent): void {
		if (!dragging) return;
		dragging = false;
		svg?.releasePointerCapture(event.pointerId);
		if (dragMoved) labelCamera = camera;
	}

	onMount(() => {
		const el = frame;
		if (!el) return;
		let first = true;
		const observer = new ResizeObserver(() => {
			const next = { width: el.clientWidth, height: el.clientHeight };
			if (next.width === size.width && next.height === size.height) return;
			size = next;
			// Beim ersten Messen: gemerkten Ausschnitt behalten (Rückkehr vom Profil), sonst einpassen.
			if (first && view.camera) labelCamera = camera;
			else fit(null);
			first = false;
		});
		observer.observe(el);

		let timer = 0;
		if (intro && !reducedMotion()) {
			// Das Netz leuchtet einmal von der Mitte nach außen auf.
			entering = new Set(scene.nodes.map((n) => n.id));
			timer = window.setTimeout(() => {
				entering = new Set();
				pulsing = new Set(scene.nodes.filter((n) => n.node.own).map((n) => n.id));
				window.setTimeout(() => (introRunning = false), 900);
			}, 260);
		} else {
			introRunning = false;
		}
		return () => {
			observer.disconnect();
			window.clearTimeout(timer);
		};
	});

	// Neue Knoten wachsen aus ihrem Elternknoten heraus, ihre Kanten zeichnen sich nach außen.
	// Nur nach einer Nutzeraktion und nie bei reduzierter Bewegung.
	let seenRevision = untrack(() => view.revision);
	$effect(() => {
		const revision = view.revision;
		if (revision === seenRevision) return;
		seenRevision = revision;
		const added = view.added;
		const parents = [...new Set(added.map((id) => nodeById.get(id)?.node.parentId ?? ROOT_ID))];
		const focus = added.length > 0 ? [...added, ...parents] : null;
		if (added.length === 0 || reducedMotion()) {
			void tick().then(() => fit(focus));
			return;
		}
		entering = new Set(added);
		let second = 0;
		const first = requestAnimationFrame(() => {
			second = requestAnimationFrame(() => {
				entering = new Set();
				// Erscheint die eigene Herkunft, geht einmal ein Ring von ihr aus.
				pulsing = new Set(added.filter((id) => nodeById.get(id)?.node.own));
				fit(focus);
			});
		});
		return () => {
			cancelAnimationFrame(first);
			cancelAnimationFrame(second);
		};
	});
</script>

<div class="frame" class:hs-stage={!plain} class:plain style:height bind:this={frame} data-testid={testid}>
	<svg
		bind:this={svg}
		class:dragging
		width="100%"
		height="100%"
		role="group"
		aria-label="Herkunftsnetz von {view.core.root.name}. Mit den Pfeiltasten bewegst du dich durch die Knoten, Enter klappt eine Stufe auf oder zu."
		onfocusin={() => (focusInside = true)}
		onfocusout={handleFocusOut}
		onpointerdown={handlePointerDown}
		onpointermove={handlePointerMove}
		onpointerup={handlePointerUp}
		onpointercancel={handlePointerUp}
	>
		<defs>
			<radialGradient id="{uid}-hof">
				<stop offset="0.42" class="hof-a" />
				<stop offset="1" class="hof-b" />
			</radialGradient>
			<radialGradient id="{uid}-licht">
				<stop offset="0.3" class="licht-a" />
				<stop offset="1" class="licht-b" />
			</radialGradient>
		</defs>

		<g
			class="world"
			class:still={dragging}
			class:intro={introRunning}
			style:transform="translate({size.width / 2 - camera.x * camera.k}px, {size.height / 2 - camera.y * camera.k}px) scale({camera.k})"
		>
			<g class="guides" aria-hidden="true">
				{#if depths.has(1)}<circle r={RING_RADIUS.state} />{/if}
				{#if depths.has(2)}<circle r={RING_RADIUS.district} />{/if}
				{#if depths.has(3)}<circle r={RING_RADIUS.place} />{/if}
			</g>

			<g class="edges" aria-hidden="true">
				{#each scene.edges as edge (edge.id)}
					{@const own = nodeById.get(edge.id)?.node.own === true}
					<path
						d={edge.d}
						pathLength="1"
						stroke-width={Math.max(edge.width, 1.1 / camera.k)}
						class:own
						class:highlight={path.has(edge.id)}
						class:dim={path.size > 0 && !path.has(edge.id)}
						class:entering={entering.has(edge.id)}
						style:--depth={nodeById.get(edge.id)?.depth ?? 1}
					/>
				{/each}
			</g>

			<g class="nodes">
				<g
					class="node root"
					role="button"
					aria-label="{view.core.root.name}, Wohnort in der Mitte, {personen(view.core.root.count)}. Ganzes Netz zeigen."
					tabindex={view.focusedNodeId === ROOT_ID ? 0 : -1}
					data-node-id={ROOT_ID}
					data-testid="network-root"
					onclick={() => fit(null, true)}
					onkeydown={(event) => {
						if (event.key === 'Enter' || event.key === ' ') {
							event.preventDefault();
							fit(null, true);
						} else {
							void handleKey(event, ROOT_ID);
						}
					}}
					onfocus={() => view.focus(ROOT_ID)}
				>
					<circle class="halo" r={ROOT_RADIUS * 2.1} fill="url(#{uid}-hof)" />
					<circle class="focus-ring" r={ROOT_RADIUS + 6} stroke-width={2.5 / camera.k} />
					<circle class="dot" r={ROOT_RADIUS} />
					<text class="count hs-num" text-anchor="middle" dominant-baseline="central" font-size="13">{view.core.root.count}</text>
				</g>

				{#each scene.nodes as n (n.id)}
					{@const r = Math.max(n.r, minDot)}
					{@const hit = Math.max(n.hit, minHit)}
					<g
						class="node level-{n.node.level}"
						class:own={n.node.own}
						class:open={view.isOpen(n.id)}
						class:selected={view.selectedId === n.id}
						class:loading={view.isLoading(n.id)}
						class:on-path={path.has(n.id)}
						class:entering={entering.has(n.id)}
						style:transform={transformOf(n)}
						style:--depth={n.depth}
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
						<circle class="hit" r={hit} />
						<circle class="halo" r={n.node.own ? r * 2.6 + 10 / camera.k : r * 1.9 + 3 / camera.k} fill="url(#{uid}-{n.node.own ? 'licht' : 'hof'})" />
						{#if pulsing.has(n.id)}<circle class="pulse" r={r + 4 / camera.k} stroke-width={1.5 / camera.k} />{/if}
						<circle class="focus-ring" r={hit} stroke-width={2.5 / camera.k} />
						{#if n.node.own}<circle class="own-ring" r={r + 4 / camera.k} stroke-width={1.5 / camera.k} />{/if}
						{#if view.selectedId === n.id}<circle class="selected-ring" r={r + (n.node.own ? 8 : 5) / camera.k} stroke-width={2 / camera.k} />{/if}
						{#if view.isLoading(n.id)}<circle class="loading-ring" r={r + 5 / camera.k} stroke-width={1.5 / camera.k} />{/if}
						<circle class="dot" {r} />
						{#if n.countInside && n.r * camera.k >= 8.5}
							<text class="count hs-num" text-anchor="middle" dominant-baseline="central" font-size={Math.min(n.r * 0.95, 13 / Math.min(1, camera.k))}>{n.node.count}</text>
						{/if}
					</g>
				{/each}
			</g>

			<g class="labels" aria-hidden="true">
				{#each scene.nodes as n (n.id)}
					{@const label = placed.labels.get(n.id)}
					{#if label && label.variant !== 'hidden'}
						<text
							x={label.x}
							y={label.y}
							text-anchor={label.anchor}
							dominant-baseline="central"
							class:own={n.node.own}
							class:strong={path.has(n.id)}
							class:entering={entering.has(n.id)}
							font-size={label.fontSize}
							stroke-width={4 / labelCamera.k}
							style:--depth={n.depth}
						>
							<tspan>{label.text}</tspan>{#if label.suffix}<tspan class="suffix" dx={4 / labelCamera.k}>{label.suffix}</tspan>{/if}
							{#if label.sub}
								<tspan class="sub" x={label.x} dy={label.lineHeight} font-size={label.subFontSize}>{label.sub}</tspan>
							{/if}
						</text>
					{/if}
				{/each}
				<text
					class="root-label"
					x={placed.rootLabel.x}
					y={placed.rootLabel.y}
					text-anchor="middle"
					dominant-baseline="central"
					font-size={placed.rootLabel.fontSize}
					stroke-width={4 / labelCamera.k}
				>
					{view.core.root.name}
				</text>
			</g>

			{#if plate}
				<g class="plate" aria-hidden="true" transform="translate({plate.x} {plate.y})">
					<rect x={-plate.width / 2} y={-13 * plate.k} width={plate.width} height={26 * plate.k} rx={13 * plate.k} />
					<text text-anchor="middle" dominant-baseline="central" font-size={LABEL_FONT_SIZE * plate.k}>{plate.text}</text>
				</g>
			{/if}
		</g>
	</svg>

	<div class="controls">
		<button type="button" onclick={() => zoomBy(1 / 1.3)} disabled={camera.k <= K_MIN} aria-label="Netz verkleinern" data-testid="network-zoom-out">
			<Icon icon={Minus} size={18} />
		</button>
		<button type="button" onclick={() => zoomBy(1.3)} disabled={camera.k >= K_MAX} aria-label="Netz vergrößern" data-testid="network-zoom-in">
			<Icon icon={Plus} size={18} />
		</button>
		<button type="button" onclick={() => fit(null, true)} aria-label="Ganzes Netz zeigen" data-testid="network-center">
			<Icon icon={Scan} size={18} />
		</button>
	</div>
</div>

<style>
	.frame {
		position: relative;
		min-height: 22rem;
	}

	.frame.plain {
		color: var(--hs-stage-ink);
	}

	svg {
		display: block;
		font-family: var(--hs-font-sans);
		cursor: grab;
		touch-action: pan-y;
		user-select: none;
	}

	svg.dragging {
		cursor: grabbing;
	}

	/* Die Kamera gleitet beim Einpassen; beim Ziehen folgt sie dem Zeiger ohne Verzögerung. */
	.world {
		transition: transform var(--hs-duration-slow) var(--hs-ease-out);
		will-change: transform;
	}

	.world.still {
		transition: none;
	}

	.hof-a {
		stop-color: var(--hs-stage-ink);
		stop-opacity: 0.2;
	}

	.hof-b {
		stop-color: var(--hs-stage-ink);
		stop-opacity: 0;
	}

	.licht-a {
		stop-color: var(--hs-stage-origin);
		stop-opacity: 0.55;
	}

	.licht-b {
		stop-color: var(--hs-stage-origin);
		stop-opacity: 0;
	}

	.guides circle {
		fill: none;
		stroke: var(--hs-stage-line);
		stroke-width: 1;
		vector-effect: non-scaling-stroke;
	}

	/* Kanten: Mondweiß mit wenig Deckkraft. pathLength="1" erlaubt das Zeichnen von innen nach außen. */
	.edges path {
		fill: none;
		stroke: var(--hs-stage-ink);
		stroke-opacity: 0.2;
		stroke-linecap: round;
		stroke-dasharray: 1;
		stroke-dashoffset: 0;
		transition:
			stroke-dashoffset var(--hs-duration-slow) var(--hs-ease-standard),
			stroke-opacity var(--hs-duration-fast) var(--hs-ease-standard),
			stroke var(--hs-duration-fast) var(--hs-ease-standard);
	}

	.edges path.own {
		stroke: var(--hs-stage-origin);
		stroke-opacity: 0.62;
	}

	.edges path.highlight {
		stroke: var(--hs-stage-accent);
		stroke-opacity: 0.95;
	}

	.edges path.own.highlight {
		stroke: var(--hs-stage-origin);
		stroke-opacity: 1;
	}

	.edges path.dim:not(.own) {
		stroke-opacity: 0.1;
	}

	.edges path.entering {
		stroke-dashoffset: 1;
		transition: none;
	}

	.labels text {
		fill: var(--hs-stage-ink);
		font-weight: var(--hs-weight-regular);
		paint-order: stroke;
		stroke: var(--hs-stage-bg);
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
		fill: var(--hs-stage-muted);
		font-variant-numeric: tabular-nums;
	}

	.labels .sub {
		fill: var(--hs-stage-origin);
		font-weight: var(--hs-weight-strong);
	}

	.labels .root-label {
		font-weight: var(--hs-weight-strong);
	}

	.node {
		cursor: pointer;
		outline: none;
		transition:
			transform var(--hs-duration-slow) var(--hs-ease-out),
			opacity var(--hs-duration-slow) var(--hs-ease-standard);
	}

	.node.entering {
		opacity: 0;
		transition: none;
	}

	/* Einmaliges Aufleuchten auf der Startseite: Ring für Ring von der Mitte nach außen. */
	.world.intro .node,
	.world.intro .edges path,
	.world.intro .labels text {
		transition-duration: 420ms;
		transition-delay: calc((var(--depth, 1) - 1) * 160ms);
	}

	.hit {
		fill: transparent;
	}

	.halo {
		pointer-events: none;
	}

	.dot {
		fill: var(--hs-stage-ink);
		transition: fill var(--hs-duration-fast) var(--hs-ease-standard);
	}

	.node.own .dot {
		fill: var(--hs-stage-origin);
	}

	.node.on-path:not(.own):not(.root) .dot {
		fill: var(--hs-stage-accent);
	}

	.own-ring {
		fill: none;
		stroke: var(--hs-stage-origin);
	}

	.selected-ring {
		fill: none;
		stroke: var(--hs-stage-ink);
	}

	.loading-ring {
		fill: none;
		stroke: var(--hs-stage-muted);
		stroke-dasharray: 3 4;
		vector-effect: non-scaling-stroke;
	}

	.focus-ring {
		fill: none;
		stroke: var(--hs-stage-accent);
		opacity: 0;
	}

	.node:focus-visible .focus-ring {
		opacity: 1;
	}

	/* Ein einziger Ring, der sich einmal ausbreitet, wenn die eigene Herkunft erscheint. */
	.pulse {
		fill: none;
		stroke: var(--hs-stage-origin);
		transform-box: fill-box;
		transform-origin: center;
		animation: hs-pulse 900ms var(--hs-ease-out) 180ms 1 both;
		pointer-events: none;
	}

	@keyframes hs-pulse {
		from {
			opacity: 0.9;
			transform: scale(1);
		}
		to {
			opacity: 0;
			transform: scale(3.4);
		}
	}

	.count {
		fill: var(--hs-stage-on-light);
		font-weight: var(--hs-weight-strong);
		pointer-events: none;
	}

	.plate {
		pointer-events: none;
	}

	.plate rect {
		fill: var(--hs-stage-ink);
	}

	.plate text {
		fill: var(--hs-stage-on-light);
		font-weight: var(--hs-weight-strong);
	}

	/* Gläserne Pille unten rechts. Die Kamera hält diese Ecke frei. */
	.controls {
		position: absolute;
		right: var(--hs-space-4);
		bottom: var(--hs-space-4);
		display: flex;
		padding: 3px;
		border-radius: var(--hs-radius-full);
		background: var(--hs-stage-glass);
		box-shadow: inset 0 0 0 1px var(--hs-stage-line);
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
	}

	.controls button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.5rem;
		height: 2.5rem;
		border: 0;
		border-radius: 50%;
		background: transparent;
		color: var(--hs-stage-ink);
		cursor: pointer;
	}

	.controls button:hover:not(:disabled) {
		background: var(--hs-stage-glass-strong);
	}

	.controls button:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.controls button:focus-visible {
		outline: 2px solid var(--hs-stage-accent);
		outline-offset: 1px;
		border-radius: 50%;
	}

	@media (prefers-reduced-motion: reduce) {
		.pulse {
			display: none;
		}
	}
</style>
