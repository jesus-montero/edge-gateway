/**
 * Servicio auxiliar de autenticación para el frontend.
 *
 * Este módulo expone pequeñas utilidades para gestionar una sesión ligera almacenada
 * en `localStorage`, realizar solicitudes de inicio de sesión y actualización de credenciales
 * contra la API del backend, y consultar el estado de autenticación para componentes de UI.
 *
 * Deliberadamente mantiene la sesión mínima (solo `username`) porque el backend
 * gestiona los tokens de autenticación reales y cookies.
 *
 * Autor: Jesus Montero
 * Fecha: 2026
 */

import { API_BASE_URL } from '../config';

const SESSION_KEY = 'edge_gateway_dashboard_session';

export type AuthSession = {
  username: string;
};

type LoginResponse = {
  status: string;
  username: string;
};

/**
 * Lee la sesión persistida desde localStorage.
 *
 * Devuelve la `AuthSession` analizada cuando está presente y es válida, en caso contrario `null`.
 */
function readSession(): AuthSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthSession;
  } catch {
    return null;
  }
}
/**
 * Devuelve la sesión actual, o `null` si no hay ninguna disponible.
 */
export function getSession(): AuthSession | null {
  return readSession();
}
/**
 * Devuelve el nombre de usuario de la sesión actual, o `null` cuando no está
 * autenticado.
 */
export function getSessionUsername(): string | null {
  return readSession()?.username ?? null;
}
/**
 * Devuelve si existe una sesión válida.
 */
export function isAuthenticated(): boolean {
  return readSession() !== null;
}


/**
 * Realiza una solicitud de inicio de sesión contra el backend y persiste una sesión mínima.
 *
 * Lanza un Error cuando la solicitud falla. En caso de éxito, la sesión se almacena
 * en `localStorage` y el valor resuelto contiene la `AuthSession` guardada.
 */
export async function login(username: string, password: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `La solicitud de inicio de sesión falló con estado ${response.status}`);
  }

  const payload = (await response.json()) as LoginResponse;
  const session: AuthSession = { username: payload.username };
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}


/**
 * Actualiza las credenciales del usuario actual llamando al endpoint del backend.
 *
 * En caso de éxito, el nombre de usuario de la sesión local se actualiza para reflejar los cambios.
 */
export async function updateCredentials(newUsername: string, newPassword: string): Promise<AuthSession> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/credentials`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_username: newUsername, new_password: newPassword }),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `La solicitud de actualización de credenciales falló con estado ${response.status}`);
  }

  const payload = (await response.json()) as LoginResponse;
  const session: AuthSession = { username: payload.username };
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

/**
 * Limpia la sesión persistida (cierre de sesión local).
 */
export function logout(): void {
  localStorage.removeItem(SESSION_KEY);
}


export default { getSession, getSessionUsername, isAuthenticated, login, logout, updateCredentials };
