import { describe, expect, it } from 'vitest';
import { fitCamera, panIntoView, screenRectToBox, toScreen, unionBox, viewBounds } from './camera';
import { NetworkCore } from './core';
import { statesFromOverview, totalForScope } from './overview';
import { placeSceneLabels } from './scene';
import { datasetBayern, datasetGross, datasetLangeNamen, datasetWeit } from './synthetic';
import { ownOriginFromAgs } from './types';

const pad = { left: 80, right: 80, top: 40, bottom: 70 };

describe('fitCamera', () => {
	it('passt einen Kasten mittig in die freie Fläche ein', () => {
		const vp = { width: 800, height: 600 };
		const cam = fitCamera({ x0: -400, y0: -300, x1: 400, y1: 300 }, vp, pad, 0.3, 1.2);
		expect(cam.fits).toBe(true);
		expect(cam.k).toBeCloseTo(Math.min(640 / 800, 490 / 600), 6);
		const tl = toScreen(cam, vp, { x: -400, y: -300 });
		const br = toScreen(cam, vp, { x: 400, y: 300 });
		expect(tl.x).toBeGreaterThanOrEqual(pad.left - 0.01);
		expect(tl.y).toBeGreaterThanOrEqual(pad.top - 0.01);
		expect(br.x).toBeLessThanOrEqual(vp.width - pad.right + 0.01);
		expect(br.y).toBeLessThanOrEqual(vp.height - pad.bottom + 0.01);
	});

	it('vergrößert ein kleines Netz nicht über den Höchstmaßstab', () => {
		const cam = fitCamera({ x0: -50, y0: -50, x1: 50, y1: 50 }, { width: 1000, height: 700 }, pad, 0.3, 1.2);
		expect(cam.k).toBe(1.2);
	});

	it('meldet, wenn es beim kleinsten Maßstab nicht passt', () => {
		const cam = fitCamera({ x0: -2000, y0: -2000, x1: 2000, y1: 2000 }, { width: 360, height: 400 }, pad, 0.4, 1.2);
		expect(cam.k).toBe(0.4);
		expect(cam.fits).toBe(false);
	});
});

describe('Ausschnitt', () => {
	it('rechnet zwischen Bildschirm und Netz hin und zurück', () => {
		const cam = { x: 100, y: -50, k: 0.5 };
		const vp = { width: 400, height: 300 };
		const b = viewBounds(cam, vp);
		expect(b).toEqual({ x0: -300, y0: -350, x1: 500, y1: 250 });
		expect(toScreen(cam, vp, { x: 100, y: -50 })).toEqual({ x: 200, y: 150 });
		expect(screenRectToBox(cam, vp, { left: 0, top: 0, right: 400, bottom: 300 })).toEqual(b);
		expect(unionBox([])).toBeNull();
		expect(unionBox([{ x0: 0, y0: 0, x1: 1, y1: 1 }, { x0: -2, y0: 0.5, x1: 0, y1: 3 }])).toEqual({ x0: -2, y0: 0, x1: 1, y1: 3 });
	});

	it('holt einen Punkt mit Rand in den Ausschnitt und lässt sichtbare Punkte in Ruhe', () => {
		const cam = { x: 0, y: 0, k: 1 };
		const vp = { width: 400, height: 300 };
		expect(panIntoView(cam, vp, { x: 50, y: 20 }, 40)).toBe(cam);
		const moved = panIntoView(cam, vp, { x: 400, y: 0 }, 40);
		expect(toScreen(moved, vp, { x: 400, y: 0 }).x).toBeCloseTo(360, 6);
		expect(moved.k).toBe(1);
	});
});

async function expanded(dataset: ReturnType<typeof datasetGross>, depthLimit: number): Promise<NetworkCore> {
	const core = new NetworkCore({
		scope: 'all',
		rootName: 'Alle im Umkreis',
		rootCount: totalForScope(dataset.overview, 'all'),
		states: statesFromOverview(dataset.overview, 'all'),
		own: ownOriginFromAgs(dataset.overview.me.home.ags),
		source: dataset.source
	});
	for (let depth = 1; depth <= depthLimit; depth++) {
		for (const id of core.tree.rows.filter((r) => r.depth === depth).map((r) => r.node.id)) await core.expand(id);
	}
	return core;
}

describe('Beschriftung im Ausschnitt', () => {
	it('schneidet auf Telefon und Desktop keine Beschriftung ab und überlappt nicht', async () => {
		for (const [dataset, depth] of [
			[datasetLangeNamen(), 2],
			[datasetBayern(), 2],
			[datasetWeit(), 1],
			[datasetGross(), 2]
		] as const) {
			const core = await expanded(dataset, depth);
			const box = unionBox(core.scene.nodes.map((n) => ({ x0: n.x - n.hit, y0: n.y - n.hit, x1: n.x + n.hit, y1: n.y + n.hit })))!;
			for (const vp of [
				{ width: 340, height: 460 },
				{ width: 1056, height: 640 }
			]) {
				const cam = fitCamera(box, vp, { left: 56, right: 56, top: 36, bottom: 72 }, 0.2, 1.2);
				const bounds = viewBounds(cam, vp, 6);
				const { labels } = placeSceneLabels(core.scene.labelInputs, 'Alle im Umkreis', { scale: cam.k, bounds });
				const shown = [...labels.values()].filter((l) => l.box !== null);
				for (const l of shown) {
					expect(l.box!.x0).toBeGreaterThanOrEqual(bounds.x0);
					expect(l.box!.x1).toBeLessThanOrEqual(bounds.x1);
					expect(l.box!.y0).toBeGreaterThanOrEqual(bounds.y0);
					expect(l.box!.y1).toBeLessThanOrEqual(bounds.y1);
					expect(l.fontSize * cam.k).toBeCloseTo(12.5, 6);
				}
				for (let i = 0; i < shown.length; i++) {
					for (let j = i + 1; j < shown.length; j++) {
						const a = shown[i].box!;
						const b = shown[j].box!;
						expect(a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0).toBe(false);
					}
				}
				// Die eigene Herkunft bleibt beschriftet, wenn sie im Bild ist.
				const own = core.scene.ownDeepestId ? labels.get(core.scene.ownDeepestId) : null;
				if (own && vp.width > 1000 && dataset.id !== 'gross') expect(`${dataset.id}:${own.variant === 'hidden'}`).toBe(`${dataset.id}:false`);
			}
		}
	});
});
