// Reine SPA: Alle Daten liegen hinter dem Login, deshalb kein SSR und kein Prerendering.
// Der statische Adapter liefert index.html als Rückfall für jede Route.
export const ssr = false;
export const prerender = false;
export const trailingSlash = 'never';
