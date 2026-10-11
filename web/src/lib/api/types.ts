/** Typen des API-Vertrags (docs/API.md, Stand v0.1). */

export interface Place {
	ags: string;
	name: string;
	district_ags: string;
	district_name: string;
	state_code: string;
	state_name: string;
}

/** Ort mit Gemeindemittelpunkt. */
export interface PlacePoint extends Place {
	lat: number;
	lon: number;
}

/** So erscheint ein anderer Nutzer überall. Mehr Felder gibt es nicht. */
export interface PublicUser {
	id: string;
	nickname: string;
	/** Eine der Spannen "18–24", "25–34", "35–44", "45–54", "55–64", "65+". */
	age_range: string;
	home: Place;
	residence: { ags: string; name: string };
	/** "2026-10" */
	member_since: string;
}

export type EffectiveState = 'active' | 'muted' | 'awaiting_approval';

export interface Me {
	id: string;
	nickname: string;
	age_range: string;
	home: PlacePoint | null;
	residence: PlacePoint | null;
	member_since: string;
	muted_until: string | null;
	nickname_rerolls_left: number;
	is_staff: boolean;
}

export interface SiteInfo {
	name: string;
	radius_km: number;
	request_body_max: number;
	message_body_max: number;
	poll_seconds: number;
	/** Pfad des Admin-Bereichs, z. B. "/verwaltung/". */
	admin_path?: string;
}

export interface SessionResponse {
	authenticated: boolean;
	csrf_token: string;
	state: EffectiveState | null;
	user: Me | null;
	site: SiteInfo;
}

export type ChallengePurpose = 'register' | 'login' | 'password_reset' | 'resend';

export interface PowChallenge {
	algorithm: string;
	challenge: string;
	salt: string;
	signature: string;
	maxnumber: number;
}

export interface RegisterPayload {
	email: string;
	password: string;
	birth_date: string;
	home_ags: string;
	residence_ags: string;
	invite_code: string | null;
	accept_terms: boolean;
	pow: string;
}

export type PlaceChangeField = 'home' | 'residence';

export interface PlaceChange {
	id: string;
	field: PlaceChangeField;
	new_place: Place;
	created_at: string;
	decided_at: string | null;
	decision: null | 'approved' | 'rejected';
}

export interface StateGroup {
	state_code: string;
	count: number;
	distance_km: number | null;
}

export interface ResidenceOverview {
	ags: string;
	name: string;
	lat: number;
	lon: number;
	total: number;
	states: StateGroup[];
}

export interface NearbyOverview {
	radius_km: number;
	me: { residence: PlacePoint; home: PlacePoint };
	total: number;
	residences: ResidenceOverview[];
}

export type OriginLevel = 'state' | 'district' | 'place';

export interface OriginGroup {
	key: string;
	name: string;
	count: number;
	distance_km: number | null;
}

export interface OriginsResponse {
	level: OriginLevel;
	parent: string | null;
	items: OriginGroup[];
}

export interface PeopleResponse {
	items: PublicUser[];
	page: number;
	has_more: boolean;
}

export type RequestBlockedReason =
	| 'muted'
	| 'attempts_exhausted'
	| 'already_requested'
	| 'connected'
	| 'quota_daily'
	| 'quota_active'
	| 'not_visible';

export interface OutgoingRequestRef {
	id: string;
	state: 'open' | 'expired';
	expires_at: string;
}

export interface Relation {
	can_request: boolean;
	request_blocked_reason: RequestBlockedReason | null;
	outgoing_request: OutgoingRequestRef | null;
	incoming_request_id: string | null;
	conversation_id: string | null;
	blocked_by_me: boolean;
}

export interface UserResponse {
	user: PublicUser;
	relation: Relation;
}

export interface IncomingRequest {
	id: string;
	from: PublicUser;
	body: string;
	created_at: string;
	expires_at: string;
}

export interface OutgoingRequest {
	id: string;
	to: PublicUser;
	body: string;
	created_at: string;
	expires_at: string;
	state: 'open' | 'expired';
}

export interface RequestQuota {
	today_used: number;
	today_max: number;
	active_used: number;
	active_max: number;
}

export interface RequestsResponse {
	incoming: IncomingRequest[];
	outgoing: OutgoingRequest[];
	quota: RequestQuota;
}

export interface SendRequestResponse {
	request_id: string | null;
	conversation_id: string | null;
}

export interface ConversationSummary {
	id: string;
	partner: PublicUser | null;
	available: boolean;
	last_message: { preview: string; created_at: string; mine: boolean } | null;
	created_at: string;
}

export interface Message {
	id: string;
	mine: boolean;
	body: string;
	created_at: string;
}

export interface MessagesResponse {
	partner: PublicUser | null;
	available: boolean;
	links_allowed: boolean;
	messages: Message[];
	has_more: boolean;
}

export interface InboxSummary {
	incoming_requests: number;
	conversations: Array<{ id: string; last_message_at: string | null; last_message_mine: boolean }>;
}

export interface BlockEntry {
	user_id: string;
	nickname: string | null;
	created_at: string;
}

export type ReportTargetType = 'profile' | 'request' | 'message';
export type ReportReason = 'dating' | 'harassment' | 'spam' | 'false_info' | 'other';

export interface ReportPayload {
	target_type: ReportTargetType;
	target_id: string;
	conversation_id: string | null;
	reason: ReportReason;
	note: string;
}

export const REPORT_REASONS: ReadonlyArray<{ value: ReportReason; label: string }> = [
	{ value: 'dating', label: 'Dating oder Anmache' },
	{ value: 'harassment', label: 'Belästigung' },
	{ value: 'spam', label: 'Spam' },
	{ value: 'false_info', label: 'Falsche Angaben' },
	{ value: 'other', label: 'Sonstiges' }
];

export const DEFAULT_SITE: SiteInfo = {
	name: 'Heimatsignale',
	radius_km: 20,
	request_body_max: 500,
	message_body_max: 2000,
	poll_seconds: 30,
	admin_path: '/verwaltung/'
};
