import { dev } from '$app/environment';
import { env } from '$env/dynamic/public';

/** Entwicklungsrouten (/dev/...) gibt es nur im Entwicklungsmodus oder mit PUBLIC_DEV_ROUTES=1. */
export function devRoutesEnabled(): boolean {
	return dev || env.PUBLIC_DEV_ROUTES === '1';
}
