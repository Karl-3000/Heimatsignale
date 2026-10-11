/**
 * Typisierte Funktionen je Endpunkt, genau nach docs/API.md.
 * Suchmitte und Radius werden nie übergeben; der Server kennt den Wohnort.
 */

import { api } from './client';
import type {
	BlockEntry,
	ChallengePurpose,
	ConversationSummary,
	InboxSummary,
	Message,
	MessagesResponse,
	NearbyOverview,
	OriginLevel,
	OriginsResponse,
	PeopleResponse,
	Place,
	PlaceChange,
	PlaceChangeField,
	PowChallenge,
	RegisterPayload,
	ReportPayload,
	RequestsResponse,
	SendRequestResponse,
	SessionResponse,
	UserResponse
} from './types';

const id = (value: string): string => encodeURIComponent(value);

/* Sitzung und Konto */

export function getChallenge(purpose: ChallengePurpose): Promise<PowChallenge> {
	return api.get<PowChallenge>('/api/auth/challenge', { purpose });
}

export function register(payload: RegisterPayload): Promise<{ ok: boolean }> {
	return api.post('/api/auth/register', payload, { quiet401: true });
}

export function verifyEmail(token: string): Promise<SessionResponse> {
	return api.post('/api/auth/verify-email', { token }, { quiet401: true });
}

export function resendVerification(email: string, pow: string): Promise<{ ok: boolean }> {
	return api.post('/api/auth/resend-verification', { email, pow }, { quiet401: true });
}

export function login(email: string, password: string, pow: string | null): Promise<SessionResponse> {
	return api.post('/api/auth/login', { email, password, pow }, { quiet401: true });
}

export function logout(): Promise<void> {
	return api.post('/api/auth/logout', undefined, { quiet401: true });
}

export function requestPasswordReset(email: string, pow: string): Promise<{ ok: boolean }> {
	return api.post('/api/auth/password-reset', { email, pow }, { quiet401: true });
}

export function confirmPasswordReset(uid: string, token: string, password: string): Promise<void> {
	return api.post('/api/auth/password-reset/confirm', { uid, token, password }, { quiet401: true });
}

export function rerollNickname(): Promise<{ nickname: string; nickname_rerolls_left: number }> {
	return api.post('/api/me/nickname/reroll');
}

export function confirmNickname(): Promise<void> {
	return api.post('/api/me/nickname/confirm');
}

export function changePassword(currentPassword: string, newPassword: string): Promise<void> {
	return api.post('/api/me/password', { current_password: currentPassword, new_password: newPassword });
}

export function deleteAccount(password: string): Promise<void> {
	return api.post('/api/me/delete', { password }, { quiet401: true });
}

export function listPlaceChanges(): Promise<{ items: PlaceChange[] }> {
	return api.get('/api/me/place-changes');
}

export function createPlaceChange(field: PlaceChangeField, newAgs: string): Promise<PlaceChange> {
	return api.post('/api/me/place-changes', { field, new_ags: newAgs });
}

export function createAppeal(text: string): Promise<unknown> {
	return api.post('/api/appeals', { text });
}

export function createAppealByToken(token: string, text: string): Promise<unknown> {
	return api.post('/api/appeals/by-token', { token, text }, { quiet401: true });
}

/* Orte */

export function searchPlaces(q: string, signal?: AbortSignal): Promise<{ items: Place[] }> {
	return api.get('/api/places/search', { q }, { quiet401: true, signal });
}

/** Nur zum Vorbelegen des Wohnort-Suchfelds. Koordinaten vorher auf zwei Nachkommastellen runden. */
export function nearestPlace(lat: number, lon: number): Promise<{ place: Place }> {
	return api.post('/api/places/nearest', { lat, lon }, { quiet401: true });
}

/* Umkreis und Herkunft */

/* `radiusKm` ist einer der Werte aus site.radius_options; ohne Angabe gilt der Standard des Servers. */

export function getOverview(radiusKm?: number): Promise<NearbyOverview> {
	return api.get('/api/nearby/overview', { radius_km: radiusKm });
}

export function getOrigins(residence: string, level: OriginLevel, parent?: string, radiusKm?: number): Promise<OriginsResponse> {
	return api.get('/api/nearby/origins', { residence, level, parent: level === 'state' ? undefined : parent, radius_km: radiusKm });
}

export function getPeople(residence: string, home: string, page: number, radiusKm?: number): Promise<PeopleResponse> {
	return api.get('/api/nearby/people', { residence, home, page, radius_km: radiusKm });
}

export function getUser(userId: string): Promise<UserResponse> {
	return api.get(`/api/users/${id(userId)}`);
}

/* Kontaktanfragen */

export function listRequests(): Promise<RequestsResponse> {
	return api.get('/api/requests');
}

export function sendRequest(toUserId: string, body: string): Promise<SendRequestResponse> {
	return api.post('/api/requests', { to_user_id: toUserId, body });
}

export function acceptRequest(requestId: string): Promise<{ conversation_id: string }> {
	return api.post(`/api/requests/${id(requestId)}/accept`);
}

export function declineRequest(requestId: string): Promise<void> {
	return api.post(`/api/requests/${id(requestId)}/decline`);
}

export function withdrawRequest(requestId: string): Promise<void> {
	return api.post(`/api/requests/${id(requestId)}/withdraw`);
}

/* Konversationen */

export function listConversations(): Promise<{ items: ConversationSummary[] }> {
	return api.get('/api/conversations');
}

export function getMessages(conversationId: string, before?: string): Promise<MessagesResponse> {
	return api.get(`/api/conversations/${id(conversationId)}/messages`, { before });
}

export function sendMessage(conversationId: string, body: string): Promise<Message> {
	return api.post(`/api/conversations/${id(conversationId)}/messages`, { body });
}

export function deleteMessage(messageId: string): Promise<void> {
	return api.delete(`/api/messages/${id(messageId)}`);
}

export function getInboxSummary(): Promise<InboxSummary> {
	return api.get('/api/inbox/summary');
}

/* Blockieren und Melden */

export function listBlocks(): Promise<{ items: BlockEntry[] }> {
	return api.get('/api/blocks');
}

export function blockUser(userId: string): Promise<void> {
	return api.post('/api/blocks', { user_id: userId });
}

export function unblockUser(userId: string): Promise<void> {
	return api.delete(`/api/blocks/${id(userId)}`);
}

export function sendReport(payload: ReportPayload): Promise<{ ok: boolean }> {
	return api.post('/api/reports', payload);
}
