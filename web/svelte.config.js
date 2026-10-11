import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	compilerOptions: {
		runes: true
	},
	kit: {
		// Reine SPA: alle Daten liegen hinter dem Login, deshalb kein SSR und kein Prerendering.
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'index.html',
			precompress: false,
			strict: true
		}),
		// Die vollständige Content-Security-Policy kommt aus dem Build (Meta-Tag mit Hashes
		// für das Startskript). Keine Inline-Skripte, kein eval, keine fremden Hosts.
		csp: {
			mode: 'hash',
			directives: {
				'default-src': ['self'],
				'script-src': ['self'],
				'style-src': ['self', 'unsafe-inline'],
				'img-src': ['self', 'data:', 'blob:'],
				'font-src': ['self'],
				'connect-src': ['self'],
				'worker-src': ['self', 'blob:'],
				'child-src': ['blob:']
			}
		}
	}
};

export default config;
