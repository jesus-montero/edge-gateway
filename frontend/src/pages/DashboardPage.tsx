import { useCallback, useEffect, useState } from 'react';
import { PageCard } from '../components/PageCard';
import { getHealth, getDevices, getDeviceStatus, type BackendHealth, type BackendDevice, type DeviceRuntimeStatus } from '../services/api';
import { DEFAULT_REFRESH_SECONDS } from '../config';

export function DashboardPage() {
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [devices, setDevices] = useState<BackendDevice[]>([]);
  const [statuses, setStatuses] = useState<Record<number, DeviceRuntimeStatus | null>>({});
  const [devicesLoading, setDevicesLoading] = useState(true);
  const [devicesError, setDevicesError] = useState<string | null>(null);

  const loadData = useCallback(async (showLoading: boolean) => {
    try {
      if (showLoading) {
        setLoading(true);
        setDevicesLoading(true);
      }

      const healthResult = await getHealth();
      setHealth(healthResult);
      setError(null);

      const devicesResult = await getDevices();
      const statusResults = await Promise.all(
        devicesResult.devices.map(async (device) => {
          try {
            const status = await getDeviceStatus(device.device_id);
            return [device.device_id, status] as const;
          } catch {
            return [device.device_id, null] as const;
          }
        }),
      );

      setDevices(devicesResult.devices);
      setStatuses(Object.fromEntries(statusResults));
      setDevicesError(null);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'No se puede conectar con el backend');
      setDevicesError(fetchError instanceof Error ? fetchError.message : 'No se pueden cargar los dispositivos');
    } finally {
      if (showLoading) {
        setLoading(false);
        setDevicesLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadData(true);
  }, [loadData]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      void loadData(false);
    }, DEFAULT_REFRESH_SECONDS * 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [loadData]);

  const offlineDevices = devices.filter((device) => !statuses[device.device_id]?.online);

  return (
    <div className="page-stack">
      <PageCard title="Estado del servicio" description="">
        {loading ? (
          <div className="muted-block">Cargando estado del backend...</div>
        ) : error ? (
          <div className="alert error">{error}</div>
        ) : health ? (
          <div className="metrics-grid">
            <div className="metric">
              <span>Estado</span>
              <strong>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                  {health.status === 'ok' ? (
                    <>
                      <svg width="24" height="24" viewBox="0 0 24 24" role="img" aria-label="Servicio OK">
                        <circle cx="12" cy="12" r="10" fill="#2ecc71" />
                      </svg>
                      <span style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>OK</span>
                    </>
                  ) : (
                    <>
                      <svg width="24" height="24" viewBox="0 0 24 24" role="img" aria-label="Servicio NO">
                        <circle cx="12" cy="12" r="10" fill="#e74c3c" />
                      </svg>
                      <span style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>NO</span>
                    </>
                  )}
                </span>
              </strong>
            </div>
            <div className="metric">
              <span>Aplicación</span>
              <strong>{health.app_name}</strong>
            </div>
            <div className="metric">
              <span>Entorno</span>
              <strong>{health.environment}</strong>
            </div>
          </div>
        ) : null}
      </PageCard>

      <PageCard title="Fallo de dispositivos" description="">
        {devicesLoading ? (
          <div className="muted-block">Cargando dispositivos...</div>
        ) : devicesError ? (
          <div className="alert error">{devicesError}</div>
        ) : offlineDevices.length === 0 ? (
          <div className="muted-block">Todos los dispositivos están online</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {offlineDevices.map((device) => (
              <div
                key={device.device_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '8px 12px',
                  borderRadius: 4,
                  borderLeft: '3px solid #e74c3c',
                }}
              >
                <span
                  aria-label="Dispositivo offline"
                  style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    backgroundColor: '#e74c3c',
                    flexShrink: 0,
                  }}
                />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <strong style={{ display: 'block', fontSize: '0.95rem' }}>{device.name}</strong>
                  {device.ip && <small style={{ color: '#888' }}>{device.ip}</small>}
                </div>
              </div>
            ))}
          </div>
        )}
      </PageCard>
    </div>
  );
}