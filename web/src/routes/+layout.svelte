<script lang="ts">
	import '@fontsource-variable/inter';
	import '../app.css';
	import { onMount, type Snippet } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import Waypoints from '@lucide/svelte/icons/waypoints';
	import Inbox from '@lucide/svelte/icons/inbox';
	import MessageSquare from '@lucide/svelte/icons/message-square';
	import Settings from '@lucide/svelte/icons/settings';
	import LogOut from '@lucide/svelte/icons/log-out';
	import { onUnauthorized } from '$lib/api/client';
	import { logout } from '$lib/api/endpoints';
	import { LOGIN_PATH, guardRedirect, normalizePath } from '$lib/api/guard';
	import { inbox } from '$lib/api/inbox.svelte';
	import { session } from '$lib/api/session.svelte';
	import { umkreis } from '$lib/network/umkreis.svelte';
	import Brand from '$lib/ui/Brand.svelte';
	import Button from '$lib/ui/Button.svelte';
	import Icon from '$lib/ui/Icon.svelte';
	import Notice from '$lib/ui/Notice.svelte';
	import ThemeToggle from '$lib/ui/ThemeToggle.svelte';
	import Toaster from '$lib/ui/Toaster.svelte';
	import { devRoutesEnabled } from '$lib/util/dev';
	import { formatRemaining } from '$lib/util/format';

	let { children }: { children: Snippet } = $props();

	const devRoutes = devRoutesEnabled();
	const path = $derived(normalizePath(page.url.pathname));
	const guardSession = $derived({
		authenticated: session.authenticated,
		state: session.state,
		isStaff: session.user?.is_staff === true
	});
	const redirect = $derived(session.loaded && !session.failed ? guardRedirect(path, guardSession, devRoutes) : null);
	const allowed = $derived(session.loaded && !session.failed && redirect === null);

	/** Vollwertige App-Navigation nur für aktive und stummgeschaltete Konten. */
	const inApp = $derived(session.authenticated && !guardSession.isStaff && (session.state === 'active' || session.state === 'muted'));
	let loggingOut = $state(false);

	const nav = $derived([
		{ href: '/umkreis', label: 'Umkreis', icon: Waypoints, count: 0, testid: 'nav-umkreis' },
		{ href: '/anfragen', label: 'Anfragen', icon: Inbox, count: inbox.incomingRequests, testid: 'nav-anfragen' },
		{ href: '/gespraeche', label: 'Gespräche', icon: MessageSquare, count: inbox.unreadCount, testid: 'nav-gespraeche' },
		{ href: '/einstellungen', label: 'Einstellungen', icon: Settings, count: 0, testid: 'nav-einstellungen' }
	]);

	function isCurrent(href: string): boolean {
		return path === href || path.startsWith(`${href}/`) || (href === '/umkreis' && path.startsWith('/profil/'));
	}

	function countLabel(item: { href: string; count: number }): string {
		if (item.count === 0) return '';
		if (item.href === '/anfragen') return item.count === 1 ? ', 1 offene Anfrage' : `, ${item.count} offene Anfragen`;
		return item.count === 1 ? ', 1 Gespräch mit neuen Nachrichten' : `, ${item.count} Gespräche mit neuen Nachrichten`;
	}

	async function handleLogout(): Promise<void> {
		loggingOut = true;
		try {
			await logout();
		} catch {
			/* Auch wenn der Aufruf scheitert, wird die Sitzung unten neu gelesen. */
		}
		inbox.reset();
		umkreis.reset();
		await session.refresh();
		loggingOut = false;
		await goto('/');
	}

	onMount(() => {
		onUnauthorized(() => {
			// Sitzung abgelaufen oder beendet: lokalen Zustand verwerfen und zur Anmeldung.
			session.clear();
			inbox.reset();
			umkreis.reset();
			void goto(LOGIN_PATH);
		});
		void session.refresh();
		return () => onUnauthorized(null);
	});

	// Routenschutz: unangemeldet zur Anmeldung, wartend zur Statusseite, Admin-Konto zum Hinweis.
	$effect(() => {
		if (redirect && redirect !== path) void goto(redirect, { replaceState: true });
	});

	// Posteingang alle site.poll_seconds abfragen, solange jemand angemeldet und aktiv ist.
	$effect(() => {
		if (!inApp) return;
		inbox.start(session.site.poll_seconds);
		return () => inbox.stop();
	});
</script>

<a class="hs-skip" href="#inhalt">Zum Inhalt springen</a>

<div class="shell" class:in-app={inApp}>
	<header class="top">
		<div class="bar">
			<Brand href={inApp ? '/umkreis' : '/'} />
			{#if inApp}
				<nav class="main-nav" aria-label="Hauptnavigation">
					<ul>
						{#each nav as item (item.href)}
							<li>
								<a href={item.href} aria-current={isCurrent(item.href) ? 'page' : undefined} data-testid={item.testid}>
									<Icon icon={item.icon} size={18} />
									<span>{item.label}</span>
									{#if item.count > 0}
										<span class="count hs-num" aria-hidden="true">{item.count}</span>
										<span class="hs-sr-only">{countLabel(item)}</span>
									{/if}
								</a>
							</li>
						{/each}
					</ul>
				</nav>
				<div class="end">
					<Button variant="ghost" size="sm" icon={LogOut} loading={loggingOut} onclick={handleLogout} testid="logout">Abmelden</Button>
				</div>
			{:else if session.authenticated}
				<div class="end">
					<Button variant="ghost" size="sm" icon={LogOut} loading={loggingOut} onclick={handleLogout} testid="logout">Abmelden</Button>
				</div>
			{:else if session.loaded}
				<nav class="guest-nav" aria-label="Hauptnavigation">
					<a href="/vorschau" class="plain" aria-current={path === '/vorschau' ? 'page' : undefined}>Vorschau</a>
					<a href="/anmelden" class="plain" aria-current={path === '/anmelden' ? 'page' : undefined} data-testid="nav-anmelden">Anmelden</a>
					<Button href="/registrieren" variant="primary" size="sm" testid="nav-registrieren">Registrieren</Button>
				</nav>
			{/if}
		</div>
	</header>

	{#if inApp && session.state === 'muted'}
		<div class="banner">
			<Notice tone="warning" title="Dein Konto ist vorübergehend eingeschränkt" testid="muted-banner">
				<p>
					Du kannst gerade keine neuen Anfragen senden ({formatRemaining(session.user?.muted_until)}). Bestehende Gespräche laufen weiter.
					<a href="/status">Mehr dazu und Einspruch</a>
				</p>
			</Notice>
		</div>
	{/if}

	<main id="inhalt" tabindex="-1">
		{#if !session.loaded}
			<p class="state" role="status">Lädt.</p>
		{:else if session.failed}
			<div class="state">
				<Notice tone="danger" title="Der Dienst ist gerade nicht erreichbar" live testid="session-error">
					<p>Die Verbindung zum Server ist fehlgeschlagen. Prüfe deine Internetverbindung und versuche es noch einmal.</p>
				</Notice>
				<div class="retry"><Button variant="primary" onclick={() => void session.refresh()}>Erneut versuchen</Button></div>
			</div>
		{:else if allowed}
			{@render children()}
		{:else}
			<p class="state" role="status">Lädt.</p>
		{/if}
	</main>

	<footer class="bottom">
		<div class="foot">
			<nav aria-label="Rechtliches">
				<a href="/datenschutz">Datenschutz</a>
				<a href="/impressum">Impressum</a>
				<a href="/nutzungsbedingungen">Nutzungsbedingungen</a>
				{#if !session.authenticated}<a href="/vorschau">Was andere von dir sehen</a>{/if}
			</nav>
			<ThemeToggle compact />
		</div>
		<p class="note">Nur für Deutschland. Kein Tracking, keine Werbung, keine Dating-Plattform.</p>
	</footer>

	{#if inApp}
		<nav class="tabbar" aria-label="Hauptnavigation unten">
			<ul>
				{#each nav as item (item.href)}
					<li>
						<a href={item.href} aria-current={isCurrent(item.href) ? 'page' : undefined} data-testid="{item.testid}-mobil">
							<span class="tab-icon">
								<Icon icon={item.icon} size={22} />
								{#if item.count > 0}<span class="dot hs-num" aria-hidden="true">{item.count}</span>{/if}
							</span>
							<span class="tab-label">{item.label}</span>
							{#if item.count > 0}<span class="hs-sr-only">{countLabel(item)}</span>{/if}
						</a>
					</li>
				{/each}
			</ul>
		</nav>
	{/if}
</div>

<Toaster />

<style>
	.shell {
		display: flex;
		flex-direction: column;
		min-height: 100dvh;
	}

	.top {
		position: sticky;
		top: 0;
		z-index: 40;
		background: var(--hs-bg);
		border-bottom: 1px solid var(--hs-line);
	}

	.bar {
		display: flex;
		align-items: center;
		gap: var(--hs-space-5);
		max-width: var(--hs-content);
		min-height: 3.75rem;
		margin: 0 auto;
		padding: 0 var(--hs-space-4);
	}

	.end {
		margin-left: auto;
	}

	.main-nav {
		display: none;
		flex: 1;
	}

	.main-nav ul {
		display: flex;
		gap: var(--hs-space-1);
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.main-nav a {
		display: inline-flex;
		align-items: center;
		gap: var(--hs-space-2);
		min-height: 2.5rem;
		padding: 0 var(--hs-space-3);
		border-radius: var(--hs-radius-md);
		color: var(--hs-ink-muted);
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
		text-decoration: none;
	}

	.main-nav a:hover {
		background: var(--hs-sunken);
		color: var(--hs-ink);
	}

	.main-nav a[aria-current='page'] {
		color: var(--hs-ink);
		box-shadow: inset 0 -2px 0 var(--hs-accent);
		border-bottom-left-radius: 0;
		border-bottom-right-radius: 0;
	}

	.count {
		min-width: 1.25rem;
		padding: 0 0.3rem;
		border-radius: var(--hs-radius-full);
		background: var(--hs-accent);
		color: var(--hs-on-accent);
		font-size: var(--hs-text-xs);
		line-height: 1.25rem;
		text-align: center;
	}

	.guest-nav {
		display: flex;
		align-items: center;
		gap: var(--hs-space-2);
		margin-left: auto;
	}

	.guest-nav .plain {
		display: none;
		align-items: center;
		min-height: 2.5rem;
		padding: 0 var(--hs-space-3);
		color: var(--hs-ink);
		font-size: var(--hs-text-sm);
		font-weight: var(--hs-weight-strong);
		text-decoration: none;
		border-radius: var(--hs-radius-md);
	}

	.guest-nav .plain:hover {
		background: var(--hs-sunken);
	}

	.guest-nav .plain[aria-current='page'] {
		box-shadow: inset 0 -2px 0 var(--hs-accent);
	}

	.guest-nav .plain[data-testid='nav-anmelden'] {
		display: inline-flex;
	}

	.banner {
		max-width: var(--hs-content);
		width: 100%;
		margin: var(--hs-space-4) auto 0;
		padding: 0 var(--hs-space-4);
	}

	main {
		flex: 1;
		width: 100%;
		max-width: var(--hs-content);
		margin: 0 auto;
		padding: var(--hs-space-5) var(--hs-space-4) var(--hs-space-7);
		outline: none;
	}

	.state {
		padding: var(--hs-space-7) 0;
		color: var(--hs-ink-muted);
	}

	.retry {
		margin-top: var(--hs-space-4);
	}

	.bottom {
		border-top: 1px solid var(--hs-line);
		padding: var(--hs-space-5) var(--hs-space-4);
		font-size: var(--hs-text-sm);
		color: var(--hs-ink-muted);
	}

	.in-app .bottom {
		padding-bottom: calc(var(--hs-space-5) + 4.25rem + env(safe-area-inset-bottom, 0px));
	}

	.foot {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--hs-space-3) var(--hs-space-5);
		max-width: var(--hs-content);
		margin: 0 auto;
	}

	.foot nav {
		display: flex;
		flex-wrap: wrap;
		gap: var(--hs-space-1) var(--hs-space-5);
	}

	.foot a {
		display: inline-flex;
		align-items: center;
		min-height: 2rem;
		color: var(--hs-ink-muted);
	}

	.note {
		max-width: var(--hs-content);
		margin: var(--hs-space-3) auto 0;
	}

	.tabbar {
		position: fixed;
		left: 0;
		right: 0;
		bottom: 0;
		z-index: 40;
		background: var(--hs-raised);
		border-top: 1px solid var(--hs-line);
		padding-bottom: env(safe-area-inset-bottom, 0px);
	}

	.tabbar ul {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.tabbar a {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.125rem;
		min-height: 3.75rem;
		padding: var(--hs-space-1);
		color: var(--hs-ink-muted);
		font-size: 0.6875rem;
		font-weight: var(--hs-weight-strong);
		text-decoration: none;
	}

	.tabbar a[aria-current='page'] {
		color: var(--hs-ink);
		box-shadow: inset 0 2px 0 var(--hs-accent);
	}

	.tabbar a:focus-visible {
		outline-offset: -3px;
	}

	.tab-icon {
		position: relative;
		display: inline-flex;
	}

	.tab-label {
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.dot {
		position: absolute;
		top: -0.375rem;
		left: 0.875rem;
		min-width: 1.125rem;
		padding: 0 0.25rem;
		border-radius: var(--hs-radius-full);
		background: var(--hs-accent);
		color: var(--hs-on-accent);
		font-size: 0.6875rem;
		line-height: 1.125rem;
		text-align: center;
	}

	.in-app .end {
		display: none;
	}

	@media (min-width: 480px) {
		.guest-nav .plain {
			display: inline-flex;
		}
	}

	@media (min-width: 800px) {
		.main-nav {
			display: block;
		}

		.in-app .end {
			display: block;
		}

		.tabbar {
			display: none;
		}

		.in-app .bottom {
			padding-bottom: var(--hs-space-5);
		}

		main {
			padding-top: var(--hs-space-6);
		}
	}

	/* Auf schmalen Bildschirmen liegen Meldungen über der unteren Navigation. */
	@media (max-width: 799px) {
		:global(body:has(.shell.in-app)) {
			--hs-toast-offset: 4.25rem;
		}
	}
</style>
