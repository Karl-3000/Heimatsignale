/**
 * Kamera der Netzansicht: Welcher Ausschnitt des festen Netz-Koordinatensystems ist in
 * welchem Maßstab zu sehen. Die Positionen der Knoten ändern sich dadurch nie; die Kamera
 * sorgt nur dafür, dass der sichtbare Baum mit Rand in die Bühne passt.
 */

import type { Box } from './labels';

export interface Camera {
	/** Netzkoordinate in der Mitte des Ausschnitts. */
	x: number;
	y: number;
	/** Bildschirm-Pixel je Netzeinheit. */
	k: number;
}

export interface Viewport {
	width: number;
	height: number;
}

export interface Padding {
	left: number;
	right: number;
	top: number;
	bottom: number;
}

export interface FitResult extends Camera {
	/** false, wenn der Kasten beim kleinsten erlaubten Maßstab nicht ganz hineinpasst. */
	fits: boolean;
}

export function unionBox(boxes: Iterable<Box>): Box | null {
	let out: Box | null = null;
	for (const b of boxes) {
		if (!out) out = { ...b };
		else {
			out.x0 = Math.min(out.x0, b.x0);
			out.y0 = Math.min(out.y0, b.y0);
			out.x1 = Math.max(out.x1, b.x1);
			out.y1 = Math.max(out.y1, b.y1);
		}
	}
	return out;
}

/**
 * Kamera, bei der `box` mit den Rändern `pad` (in Bildschirm-Pixeln) mittig in die Fläche passt.
 * Der Maßstab bleibt zwischen kMin und kMax, damit ein kleines Netz nicht riesig und ein
 * großes nicht unlesbar wird.
 */
export function fitCamera(box: Box, viewport: Viewport, pad: Padding, kMin: number, kMax: number): FitResult {
	const availW = Math.max(40, viewport.width - pad.left - pad.right);
	const availH = Math.max(40, viewport.height - pad.top - pad.bottom);
	const bw = Math.max(1, box.x1 - box.x0);
	const bh = Math.max(1, box.y1 - box.y0);
	const ideal = Math.min(availW / bw, availH / bh);
	const k = Math.max(kMin, Math.min(kMax, ideal));
	// Die Mitte des Kastens liegt in der Mitte der freien Fläche, nicht der ganzen Bühne.
	const cx = (box.x0 + box.x1) / 2;
	const cy = (box.y0 + box.y1) / 2;
	const offsetX = (pad.left - pad.right) / 2;
	const offsetY = (pad.top - pad.bottom) / 2;
	return { x: cx - offsetX / k, y: cy - offsetY / k, k, fits: ideal >= kMin - 1e-9 };
}

/** Sichtbarer Ausschnitt in Netzkoordinaten, um `inset` Bildschirm-Pixel verkleinert. */
export function viewBounds(camera: Camera, viewport: Viewport, inset: number = 0): Box {
	const hw = Math.max(0, viewport.width / 2 - inset) / camera.k;
	const hh = Math.max(0, viewport.height / 2 - inset) / camera.k;
	return { x0: camera.x - hw, y0: camera.y - hh, x1: camera.x + hw, y1: camera.y + hh };
}

export function toScreen(camera: Camera, viewport: Viewport, point: { x: number; y: number }): { x: number; y: number } {
	return { x: (point.x - camera.x) * camera.k + viewport.width / 2, y: (point.y - camera.y) * camera.k + viewport.height / 2 };
}

/** Bildschirm-Rechteck als Kasten in Netzkoordinaten (z. B. die Fläche unter den Bedienelementen). */
export function screenRectToBox(camera: Camera, viewport: Viewport, rect: { left: number; top: number; right: number; bottom: number }): Box {
	return {
		x0: (rect.left - viewport.width / 2) / camera.k + camera.x,
		y0: (rect.top - viewport.height / 2) / camera.k + camera.y,
		x1: (rect.right - viewport.width / 2) / camera.k + camera.x,
		y1: (rect.bottom - viewport.height / 2) / camera.k + camera.y
	};
}

/** Verschiebt die Kamera gerade so weit, dass der Punkt mit Rand im Ausschnitt liegt. */
export function panIntoView(camera: Camera, viewport: Viewport, point: { x: number; y: number }, margin: number): Camera {
	const s = toScreen(camera, viewport, point);
	let dx = 0;
	let dy = 0;
	if (s.x < margin) dx = s.x - margin;
	else if (s.x > viewport.width - margin) dx = s.x - (viewport.width - margin);
	if (s.y < margin) dy = s.y - margin;
	else if (s.y > viewport.height - margin) dy = s.y - (viewport.height - margin);
	if (dx === 0 && dy === 0) return camera;
	return { x: camera.x + dx / camera.k, y: camera.y + dy / camera.k, k: camera.k };
}
