export type BackendHealth = {
  status: string;
  app_name: string;
  environment: string;
};

import { API_BASE_URL } from '../config';

export type BackendDevice = {
  device_id: number;
  name: string;
  type: string;
  heartbeat_seconds?: number;
  idpista?: string;
  ip?: string;
  username?: string;
  password?: string;
  [key: string]: unknown;
};

export type DevicesResponse = {
  status: string;
  count: number;
  devices: BackendDevice[];
};

export type DeviceRuntimeStatus = {
  device_id: number | string;
  name?: string;
  status: string;
  online: boolean;
};

export type DeviceStatusResponse = {
  status: string;
  devices: DeviceRuntimeStatus[];
};

export async function getHealth(): Promise<BackendHealth> {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`);

  if (!response.ok) {
    throw new Error(`La petición de salud falló con estado ${response.status}`);
  }

  return response.json() as Promise<BackendHealth>;
}

export async function getDevices(): Promise<DevicesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/devices`);

  if (!response.ok) {
    throw new Error(`La petición de dispositivos falló con estado ${response.status}`);
  }

  return response.json() as Promise<DevicesResponse>;
}

export async function getDeviceStatus(deviceId: number): Promise<DeviceRuntimeStatus | null> {
  const response = await fetch(`${API_BASE_URL}/api/v1/devices/${deviceId}/status`);

  if (!response.ok) {
    throw new Error(`La petición de estado del dispositivo falló con estado ${response.status}`);
  }

  const payload = (await response.json()) as DeviceStatusResponse;
  return payload.devices?.[0] ?? null;
}

export async function updateDevice(deviceId: number, payload: Record<string, unknown>): Promise<BackendDevice> {
  const response = await fetch(`${API_BASE_URL}/api/v1/devices/${deviceId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`La petición de actualización del dispositivo falló con estado ${response.status}`);
  }

  return response.json() as Promise<BackendDevice>;
}

export async function createDevice(payload: Record<string, unknown>): Promise<BackendDevice> {
  const response = await fetch(`${API_BASE_URL}/api/v1/devices`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`La petición de creación del dispositivo falló con estado ${response.status}`);
  }

  const result = (await response.json()) as { device?: BackendDevice };
  if (!result.device) {
    throw new Error('La petición de creación del dispositivo no devolvió ningún payload de dispositivo');
  }

  return result.device;
}

export async function deleteDevice(deviceId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/devices/${deviceId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    throw new Error(`La petición de eliminación del dispositivo falló con estado ${response.status}`);
  }
}

// --- SaaS providers (config/saas.yaml) ---
export type SaasProvider = {
  provider_name: string;
  provider: Record<string, unknown>;
};

export type SaasListResponse = {
  status: string;
  count: number;
  providers: Record<string, Record<string, unknown>>;
};

export async function getSaasProviders(): Promise<SaasListResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/saas`);
  if (!response.ok) {
    throw new Error(`La petición de listado de SaaS falló con estado ${response.status}`);
  }

  return response.json() as Promise<SaasListResponse>;
}

export async function getSaasProvider(providerName: string): Promise<SaasProvider> {
  const response = await fetch(`${API_BASE_URL}/api/v1/saas/${encodeURIComponent(providerName)}`);
  if (!response.ok) {
    throw new Error(`La petición del proveedor SaaS falló con estado ${response.status}`);
  }

  return response.json() as Promise<SaasProvider>;
}

export async function createSaasProvider(providerName: string, config: Record<string, unknown>): Promise<SaasProvider> {
  const response = await fetch(`${API_BASE_URL}/api/v1/saas/${encodeURIComponent(providerName)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `La petición de creación del proveedor SaaS falló con estado ${response.status}`);
  }

  return response.json() as Promise<SaasProvider>;
}

export async function updateSaasProvider(providerName: string, config: Record<string, unknown>): Promise<SaasProvider> {
  const response = await fetch(`${API_BASE_URL}/api/v1/saas/${encodeURIComponent(providerName)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `La petición de actualización del proveedor SaaS falló con estado ${response.status}`);
  }

  return response.json() as Promise<SaasProvider>;
}

export async function deleteSaasProvider(providerName: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/saas/${encodeURIComponent(providerName)}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `La petición de eliminación del proveedor SaaS falló con estado ${response.status}`);
  }
}

export type BackendRule = {
  name: string;
  when: Record<string, unknown>;
  actions: Record<string, unknown>[];
  [key: string]: unknown;
};

export type RulesResponse = {
  status: string;
  count: number;
  rules: BackendRule[];
};

export type RuleResponse = {
  status: string;
  rule: BackendRule;
};

export async function getRules(): Promise<RulesResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/rules`);

  if (!response.ok) {
    throw new Error(`La petición de reglas falló con estado ${response.status}`);
  }

  return response.json() as Promise<RulesResponse>;
}

export async function getRule(ruleName: string): Promise<RuleResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/rules/${encodeURIComponent(ruleName)}`);

  if (!response.ok) {
    throw new Error(`La petición de la regla falló con estado ${response.status}`);
  }

  return response.json() as Promise<RuleResponse>;
}

export async function createRule(payload: BackendRule): Promise<RuleResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `La petición de creación de la regla falló con estado ${response.status}`);
  }

  return response.json() as Promise<RuleResponse>;
}

export async function updateRule(ruleName: string, payload: Omit<BackendRule, 'name'>): Promise<RuleResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/rules/${encodeURIComponent(ruleName)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `La petición de actualización de la regla falló con estado ${response.status}`);
  }

  return response.json() as Promise<RuleResponse>;
}

export async function deleteRule(ruleName: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/rules/${encodeURIComponent(ruleName)}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `La petición de eliminación de la regla falló con estado ${response.status}`);
  }
}