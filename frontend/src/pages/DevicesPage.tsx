/**
 * Página de gestión de dispositivos para el frontend del edge gateway.
 *
 * Esta página carga los dispositivos configurados desde el backend, consulta el
 * estado en tiempo real de cada dispositivo y permite al usuario crear, editar y eliminar
 * entradas de dispositivo a través de un panel de editor deslizante.
 *
 * Responsabilidades:
 * - Obtener y actualizar el catálogo de dispositivos.
 * - Resolver el estado en tiempo real de cada dispositivo.
 * - Proporcionar flujos de creación, edición y eliminación.
 * - Mantener el estado del editor sincronizado con el dispositivo seleccionado.
 *
 * Autor:
 *   Jesus Montero
 *
 * Fecha:
 *   2026
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPlus, faTrashCan } from '@fortawesome/free-solid-svg-icons';
import { PageCard } from '../components/PageCard';
import { createDevice, deleteDevice, getDeviceStatus, getDevices, updateDevice, type BackendDevice, type DeviceRuntimeStatus } from '../services/api';
import { DEFAULT_REFRESH_SECONDS } from '../config';

type DeviceEditorMode = 'create' | 'edit';

/**
 * Devuelve el identificador de dispositivo disponible más bajo.
 *
 * @param devices Lista actual de dispositivos del backend.
 * @returns El primer entero positivo no utilizado por ningún dispositivo.
 */
function getNextAvailableDeviceId(devices: BackendDevice[]): number {
  const occupiedIds = new Set(devices.map((device) => device.device_id));
  let candidate = 1;

  while (occupiedIds.has(candidate)) {
    candidate += 1;
  }

  return candidate;
}

/**
 * Renderiza y gestiona la página de dispositivos.
 *
 * @returns El componente de página de dispositivos.
 */
export function DevicesPage() {
  const [devices, setDevices] = useState<BackendDevice[]>([]);
  const [statuses, setStatuses] = useState<Record<number, DeviceRuntimeStatus | null>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDevice, setSelectedDevice] = useState<BackendDevice | null>(null);
  const [editorMode, setEditorMode] = useState<DeviceEditorMode>('edit');
  const [editorValues, setEditorValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [deletingDeviceId, setDeletingDeviceId] = useState<number | null>(null);

  const editableFields = ['name', 'type', 'ip', 'idpista', 'heartbeat_seconds'];
  const availableTypes = useMemo(
    () => Array.from(new Set(devices.map((device) => device.type).filter((type) => type.trim().length > 0))).sort(),
    [devices],
  );
  const typeOptions = useMemo(() => {
    const currentType = selectedDevice?.type?.trim();

    if (!currentType) {
      return availableTypes;
    }

    return availableTypes.includes(currentType) ? availableTypes : [currentType, ...availableTypes];
  }, [availableTypes, selectedDevice?.type]);

  const loadDevices = useCallback(async (showLoading: boolean) => {
    try {
      if (showLoading) {
        setLoading(true);
      }

      const result = await getDevices();

      const statusResults = await Promise.all(
        result.devices.map(async (device) => {
          try {
            const status = await getDeviceStatus(device.device_id);
            return [device.device_id, status] as const;
          } catch {
            return [device.device_id, null] as const;
          }
        }),
      );

      setDevices(result.devices);
      setStatuses(Object.fromEntries(statusResults));
      setError(null);
    } catch (fetchError) {
      setError(fetchError instanceof Error ? fetchError.message : 'No se puede cargar la lista de dispositivos');
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void loadDevices(true);
  }, [loadDevices]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      void loadDevices(false);
    }, DEFAULT_REFRESH_SECONDS * 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [loadDevices]);

  useEffect(() => {
    if (!selectedDevice) return;

    const nextValues: Record<string, string> = {};
    for (const field of editableFields) {
      const v = (selectedDevice as any)[field] as unknown;
      nextValues[field] = v === null || v === undefined ? '' : String(v);
    }

    setEditorValues(nextValues);
    setSaveError(null);
  }, [selectedDevice]);

  const openNewDeviceDrawer = useCallback(() => {
    const nextDeviceId = getNextAvailableDeviceId(devices);

    setEditorMode('create');
    setSaveError(null);
    setSelectedDevice({
      device_id: nextDeviceId,
      name: '',
      type: '',
      heartbeat_seconds: undefined,
      idpista: '',
      ip: '',
      username: '',
      password: '',
    });
  }, [devices]);

  function openExistingDeviceDrawer(device: BackendDevice) {
    setEditorMode('edit');
    setSelectedDevice(device);
  }

  async function handleSaveDevice() {
    if (!selectedDevice) return;

    setSaving(true);
    setSaveError(null);

    try {
      const payload: Record<string, unknown> = {};
      for (const field of editableFields) {
        const nextValue = editorValues[field] ?? '';
        if (nextValue === '') {
          payload[field] = null;
          continue;
        }

        if (field === 'heartbeat_seconds') {
          payload[field] = Number(nextValue);
        } else {
          payload[field] = nextValue;
        }
      }

      payload.device_id = selectedDevice.device_id;

      if (editorMode === 'create') {
        await createDevice(payload);
      } else {
        await updateDevice(selectedDevice.device_id, payload);
      }

      setSelectedDevice(null);
      await loadDevices(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'No se pudo guardar');
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteDevice(device: BackendDevice) {
    const confirmed = window.confirm(
      `¿Eliminar el dispositivo "${device.name}" (ID ${device.device_id})? Esta acción no se puede deshacer.`,
    );

    if (!confirmed) {
      return;
    }

    setDeletingDeviceId(device.device_id);
    setSaveError(null);

    try {
      await deleteDevice(device.device_id);

      if (selectedDevice?.device_id === device.device_id) {
        setSelectedDevice(null);
      }

      await loadDevices(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'No se pudo eliminar el dispositivo');
    } finally {
      setDeletingDeviceId(null);
    }
  }

  return (
    <PageCard
      title="Dispositivos"
      description=""
      headerActions={
        <button
          type="button"
          className="device-add-button"
          aria-label="Añadir dispositivo"
          title="Añadir dispositivo"
          onClick={openNewDeviceDrawer}
        >
          <FontAwesomeIcon icon={faPlus} />
        </button>
      }
    >
      {loading ? (
        <div className="muted-block">Cargando dispositivos...</div>
      ) : error ? (
        <div className="alert error">{error}</div>
      ) : devices.length === 0 ? (
        <div className="empty-state">
          <strong>No hay dispositivos configurados.</strong>
          <p>El backend ha devuelto una lista vacía.</p>
        </div>
      ) : (
        <>
          {saveError ? <div className="alert error">{saveError}</div> : null}

          <div className="metrics-grid devices-grid">
            {devices.map((device) => (
              <div
                key={device.device_id}
                role="button"
                tabIndex={0}
                className="metric device-card device-card-button"
                onClick={() => openExistingDeviceDrawer(device)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    openExistingDeviceDrawer(device);
                  }
                }}
              >
                <span>{device.device_id}</span>
                <span
                  aria-label={statuses[device.device_id]?.online ? 'Dispositivo online' : 'Dispositivo offline'}
                  className={`device-status-dot ${statuses[device.device_id]?.online ? 'online' : 'offline'}`}
                />
                <strong>{device.name}</strong>
                <div className="device-details">
                  <small>Tipo: {device.type}</small>
                  {device.ip ? <small>IP: {device.ip}</small> : null}
                  {device.idpista ? <small>Pista: {device.idpista}</small> : null}
                  <small>Estado: {statuses[device.device_id]?.status ?? 'desconocido'}</small>
                </div>
                <button
                  type="button"
                  className="device-delete-button"
                  aria-label={`Eliminar dispositivo ${device.name}`}
                  title="Eliminar dispositivo"
                  disabled={deletingDeviceId === device.device_id}
                  onClick={(event) => {
                    event.stopPropagation();
                    void handleDeleteDevice(device);
                  }}
                >
                  <FontAwesomeIcon icon={faTrashCan} />
                </button>
              </div>
            ))}
          </div>

          <aside className={`device-drawer${selectedDevice ? ' open' : ''}`} role="dialog" aria-modal="true" aria-hidden={!selectedDevice}>
            <div className="device-drawer-header">
              <div>
                <p className="device-drawer-eyebrow">
                  {editorMode === 'create' ? 'Alta de dispositivo' : 'Edición del dispositivo'}
                </p>
                <h3>{selectedDevice?.name?.trim() ? selectedDevice.name : editorMode === 'create' ? 'Nuevo dispositivo' : 'Sin seleccionar'}</h3>
              </div>
              <button type="button" className="btn btn-secondary" onClick={() => setSelectedDevice(null)}>
                Cerrar
              </button>
            </div>

            {selectedDevice ? (
              <div className="device-drawer-body">
                <div className="device-id-readonly">
                  <span>ID {selectedDevice.device_id}</span>
                  <div></div>
                </div>

                <div className="device-form-grid">
                  <label className="device-field">
                    <span>Nombre</span>
                    <input
                      type="text"
                      value={editorValues['name'] ?? ''}
                      onChange={(event) =>
                        setEditorValues((current) => ({ ...current, name: event.target.value }))
                      }
                    />
                  </label>

                  <label className="device-field">
                    <span>Tipo</span>
                    {editorMode === 'edit' ? (
                      <select
                        value={editorValues['type'] ?? ''}
                        onChange={(event) =>
                          setEditorValues((current) => ({ ...current, type: event.target.value }))
                        }
                      >
                        <option value="">Selecciona un tipo</option>
                        {typeOptions.map((type) => (
                          <option key={type} value={type}>
                            {type}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        list="device-types"
                        type="text"
                        value={editorValues['type'] ?? ''}
                        onChange={(event) =>
                          setEditorValues((current) => ({ ...current, type: event.target.value }))
                        }
                      />
                    )}
                  </label>

                  <label className="device-field">
                    <span>IP</span>
                    <input
                      type="text"
                      value={editorValues['ip'] ?? ''}
                      onChange={(event) =>
                        setEditorValues((current) => ({ ...current, ip: event.target.value }))
                      }
                    />
                  </label>

                  <label className="device-field">
                    <span>Pista</span>
                    <input
                      type="text"
                      value={editorValues['idpista'] ?? ''}
                      onChange={(event) =>
                        setEditorValues((current) => ({ ...current, idpista: event.target.value }))
                      }
                    />
                  </label>

                  <label className="device-field">
                    <span>Heartbeat</span>
                    <input
                      type="number"
                      value={editorValues['heartbeat_seconds'] ?? ''}
                      onChange={(event) =>
                        setEditorValues((current) => ({ ...current, heartbeat_seconds: event.target.value }))
                      }
                    />
                  </label>
                </div>

                <datalist id="device-types">
                  {availableTypes.map((type) => (
                    <option key={type} value={type} />
                  ))}
                </datalist>

                <div className="device-drawer-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => setSelectedDevice(null)}>
                    Cancelar
                  </button>
                  <button type="button" className="btn btn-primary" onClick={handleSaveDevice} disabled={saving}>
                    {saving ? 'Guardando...' : editorMode === 'create' ? 'Crear dispositivo' : 'Guardar cambios'}
                  </button>
                </div>
              </div>
            ) : null}
          </aside>

          <div className={`device-drawer-overlay${selectedDevice ? ' open' : ''}`} onClick={() => setSelectedDevice(null)} />
        </>
      )}
    </PageCard>
  );
}