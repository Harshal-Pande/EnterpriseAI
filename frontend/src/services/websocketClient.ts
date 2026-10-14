/**
 * Real-Time WebSocket Client for Enterprise AI Mesh Control Room.
 *
 * Connects to FastAPI backend /api/ws endpoint.
 * Features:
 * - Server-side credential authentication (reuses configured API key)
 * - Connection lifecycle states: CONNECTING, CONNECTED, RECONNECTING, DISCONNECTED, UNAUTHORIZED
 * - Bounded exponential backoff with jitter on disconnect
 * - Heartbeat (PING/PONG) keepalive detection
 * - Channel-based subscriptions ('workflows', 'approvals', 'actions', 'scheduler', 'orchestration', 'all')
 * - Duplicate event deduplication via bounded event ID cache
 * - Automatic replay catch-up request on successful reconnect
 */

export type WSConnectionState =
  | 'CONNECTING'
  | 'CONNECTED'
  | 'RECONNECTING'
  | 'DISCONNECTED'
  | 'UNAUTHORIZED';

export interface WSEventMessage {
  event_id: string;
  event_type: string;
  channel: string;
  timestamp: string;
  entity_id?: string;
  entity_type?: string;
  scenario_id?: string;
  workflow_id?: string;
  payload: Record<string, any>;
  is_replay?: boolean;
}

export type WSEventListener = (event: WSEventMessage) => void;
export type WSStateListener = (state: WSConnectionState, details?: string) => void;

class WebSocketClientService {
  private socket: WebSocket | null = null;
  private state: WSConnectionState = 'DISCONNECTED';
  private stateListeners: Set<WSStateListener> = new Set();
  private eventListeners: Map<string, Set<WSEventListener>> = new Map();
  private globalListeners: Set<WSEventListener> = new Set();

  private reconnectAttempts = 0;
  private maxReconnectDelay = 15000;
  private baseReconnectDelay = 1000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingIntervalTimer: ReturnType<typeof setInterval> | null = null;

  private subscribedChannels: Set<string> = new Set(['all']);
  private recentEventIds: Set<string> = new Set();
  private maxRecentEventIds = 250;
  private lastEventTimestamp: string | null = null;
  private lastEventId: string | null = null;

  private isExplicitlyClosed = false;

  public getState(): WSConnectionState {
    return this.state;
  }

  public isConnected(): boolean {
    return this.state === 'CONNECTED';
  }

  public onStateChange(listener: WSStateListener): () => void {
    this.stateListeners.add(listener);
    listener(this.state);
    return () => {
      this.stateListeners.delete(listener);
    };
  }

  public onEvent(eventTypeOrChannel: string, listener: WSEventListener): () => void {
    if (!this.eventListeners.has(eventTypeOrChannel)) {
      this.eventListeners.set(eventTypeOrChannel, new Set());
    }
    this.eventListeners.get(eventTypeOrChannel)!.add(listener);
    return () => {
      const set = this.eventListeners.get(eventTypeOrChannel);
      if (set) {
        set.delete(listener);
        if (set.size === 0) this.eventListeners.delete(eventTypeOrChannel);
      }
    };
  }

  public onAnyEvent(listener: WSEventListener): () => void {
    this.globalListeners.add(listener);
    return () => {
      this.globalListeners.delete(listener);
    };
  }

  private setState(newState: WSConnectionState, details?: string) {
    if (this.state !== newState) {
      this.state = newState;
      this.stateListeners.forEach(listener => {
        try {
          listener(newState, details);
        } catch (err) {
          console.error('[WS] Error in state listener:', err);
        }
      });
    }
  }

  public connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    this.setState(this.reconnectAttempts > 0 ? 'RECONNECTING' : 'CONNECTING');

    const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';
    const wsUrlBase = apiBaseUrl.replace(/^http/, 'ws');
    const apiKey =
      (import.meta.env.VITE_API_KEY as string) ||
      (typeof window !== 'undefined' ? localStorage.getItem('ent_api_key') || '' : '');

    const params = new URLSearchParams();
    if (apiKey) {
      params.append('api_key', apiKey);
    }
    const query = params.toString() ? `?${params.toString()}` : '';
    const fullWsUrl = `${wsUrlBase}/api/ws${query}`;

    try {
      this.socket = new WebSocket(fullWsUrl);
      this.setupSocketHandlers(this.socket);
    } catch (err: any) {
      console.warn('[WS] Connection initialization error:', err);
      this.handleDisconnect('Failed to open socket');
    }
  }

  private setupSocketHandlers(ws: WebSocket): void {
    ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.setState('CONNECTED');
      this.startHeartbeat();

      // Subscribe to configured channels
      this.send({
        action: 'subscribe',
        channels: Array.from(this.subscribedChannels),
      });

      // Catch-up replay on reconnect if previous events exist
      if (this.lastEventTimestamp || this.lastEventId) {
        this.send({
          action: 'replay',
          since_timestamp: this.lastEventTimestamp,
          last_event_id: this.lastEventId,
          limit: 50,
        });
      }
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        this.handleInboundMessage(data);
      } catch (err) {
        console.warn('[WS] Malformed event payload received:', event.data, err);
      }
    };

    ws.onerror = (event: Event) => {
      console.warn('[WS] WebSocket error event:', event);
    };

    ws.onclose = (event: CloseEvent) => {
      this.stopHeartbeat();
      if (event.code === 1008 || event.code === 4401 || event.code === 4403) {
        this.setState('UNAUTHORIZED', event.reason || 'Invalid API credentials');
        return;
      }
      if (!this.isExplicitlyClosed) {
        this.handleDisconnect(event.reason || 'Connection lost');
      } else {
        this.setState('DISCONNECTED');
      }
    };
  }

  private handleInboundMessage(msg: any): void {
    const eventType = msg.event_type;
    const channel = msg.channel;
    const eventId = msg.event_id;

    // Deduplicate identical events (e.g. from retries/replays)
    if (eventId) {
      if (this.recentEventIds.has(eventId)) {
        return;
      }
      this.recentEventIds.add(eventId);
      if (this.recentEventIds.size > this.maxRecentEventIds) {
        const first = this.recentEventIds.values().next().value;
        if (first) this.recentEventIds.delete(first);
      }
    }

    if (msg.timestamp) {
      this.lastEventTimestamp = msg.timestamp;
    }
    if (eventId) {
      this.lastEventId = eventId;
    }

    // Protocol messages
    if (eventType === 'PONG') {
      return;
    }
    if (eventType === 'CONNECTED') {
      return;
    }

    const wsEvent: WSEventMessage = {
      event_id: eventId || `EVT-${Math.random().toString(36).substring(2, 9)}`,
      event_type: eventType,
      channel: channel || 'all',
      timestamp: msg.timestamp || new Date().toISOString(),
      entity_id: msg.entity_id,
      entity_type: msg.entity_type,
      scenario_id: msg.scenario_id,
      workflow_id: msg.workflow_id,
      payload: msg.payload || {},
      is_replay: Boolean(msg.is_replay),
    };

    // Dispatch to global listeners
    this.globalListeners.forEach(fn => {
      try {
        fn(wsEvent);
      } catch (err) {
        console.error('[WS] Error in global event listener:', err);
      }
    });

    // Dispatch by event type
    const byType = this.eventListeners.get(eventType);
    if (byType) {
      byType.forEach(fn => {
        try {
          fn(wsEvent);
        } catch (err) {
          console.error(`[WS] Error in listener for type '${eventType}':`, err);
        }
      });
    }

    // Dispatch by channel
    if (channel && channel !== eventType) {
      const byChannel = this.eventListeners.get(channel);
      if (byChannel) {
        byChannel.forEach(fn => {
          try {
            fn(wsEvent);
          } catch (err) {
            console.error(`[WS] Error in listener for channel '${channel}':`, err);
          }
        });
      }
    }
  }

  private handleDisconnect(reason: string): void {
    this.setState('RECONNECTING', reason);
    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.isExplicitlyClosed) return;

    this.reconnectAttempts += 1;
    // Bounded exponential backoff with 20% jitter
    const delay = Math.min(
      this.baseReconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );
    const jitter = delay * 0.2 * (Math.random() * 2 - 1);
    const actualDelay = Math.max(500, Math.round(delay + jitter));

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, actualDelay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.pingIntervalTimer = setInterval(() => {
      this.send({
        action: 'ping',
        timestamp: new Date().toISOString(),
      });
    }, 25000);
  }

  private stopHeartbeat(): void {
    if (this.pingIntervalTimer) {
      clearInterval(this.pingIntervalTimer);
      this.pingIntervalTimer = null;
    }
  }

  public send(data: Record<string, any>): boolean {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify(data));
        return true;
      } catch (err) {
        console.warn('[WS] Error sending message over socket:', err);
      }
    }
    return false;
  }

  public subscribe(channels: string[], entityId?: string): void {
    channels.forEach(ch => this.subscribedChannels.add(ch));
    this.send({
      action: 'subscribe',
      channels,
      entity_id: entityId,
    });
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      try {
        this.socket.close(1000, 'Client closed normally');
      } catch {
        // Ignore close errors
      }
      this.socket = null;
    }
    this.setState('DISCONNECTED');
  }
}

export const websocketClient = new WebSocketClientService();
