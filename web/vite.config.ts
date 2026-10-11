import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

const backend = 'http://127.0.0.1:8000';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/api': { target: backend, changeOrigin: false },
			'/verwaltung': { target: backend, changeOrigin: false }
		}
	},
	worker: {
		format: 'es'
	},
	test: {
		environment: 'node',
		include: ['src/**/*.test.ts'],
		exclude: ['node_modules/**', 'build/**', '.svelte-kit/**', 'tests/**', 'e2e/**']
	}
});
