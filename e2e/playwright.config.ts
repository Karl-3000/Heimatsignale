import { defineConfig } from '@playwright/test';

// Senkrechter Durchstich gegen das echte Backend (PROJEKT.md, Abschnitt 5 und 19).
export default defineConfig({
	testDir: './tests',
	timeout: 120_000,
	expect: { timeout: 15_000 },
	workers: 1,
	retries: 0,
	reporter: [['list']],
	outputDir: process.env.E2E_OUT ? `${process.env.E2E_OUT}/fehler` : './test-results',
	use: {
		baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:4173',
		locale: 'de-DE',
		viewport: { width: 1280, height: 900 },
		screenshot: 'only-on-failure',
		trace: 'off'
	}
});
