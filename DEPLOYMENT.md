# Despliegue en Raspberry Pi

## Configuración inicial en Raspberry Pi
Si ya tienes configurados el servicio del backend y Nginx, puedes saltarte esta sección e ir directamente al comando de despliegue.

1. Instala los paquetes base:

```bash
sudo apt install -y python3 python3-venv python3-pip nginx git
```

2. Crea la cuenta de servicio:

```bash
sudo adduser --system --group --home /opt/edge-gateway edgegw
```

3. Copia este repositorio en `/opt/edge-gateway` y haz que pertenezca a `edgegw`.
4. Crea el entorno virtual en `backend/.venv` e instala `backend/requirements.txt`.
5. Crea `/etc/edge-gateway/edge-gateway.env` con `SECRET_KEY`, `ADMIN_USERNAME` y `ADMIN_PASSWORD`.
6. Crea la unidad de systemd `edge-gateway-backend.service` usando este `ExecStart`, que es más seguro que invocar directamente `uvicorn`:

```ini
[Unit]
Description=Edge Gateway Backend API
After=network-online.target
Wants=network-online.target

[Service]
User=edgegw
Group=edgegw
WorkingDirectory=/opt/edge-gateway/backend
EnvironmentFile=/etc/edge-gateway/edge-gateway.env
ExecStart=/opt/edge-gateway/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 5000
Restart=always
RestartSec=5
StandardOutput=append:/var/log/edge-gateway/backend.log
StandardError=append:/var/log/edge-gateway/backend.log

[Install]
WantedBy=multi-user.target
```

7. Crea `/var/log/edge-gateway/backend.log` y la regla de logrotate.
8. Configura Nginx para servir el frontend desde `/opt/edge-gateway/frontend/dist` y hacer proxy de `/api/` a `http://127.0.0.1:5000`.

## Copia manual desde Windows

Copia las siguientes carpetas y archivos a la Raspberry Pi dentro de `/opt/edge-gateway`:

- `backend/app/`
- `backend/requirements.txt`
- `frontend/dist/` después de compilarlo en local
- `config/`
- `nginx/`

También conserva este archivo local en la Pi si necesitas que el backend lea las mismas credenciales:

- `backend/.env` -> `/etc/edge-gateway/edge-gateway.env`

Una vez copiado, asegúrate de que el árbol de destino pertenece a `edgegw`:

```bash
sudo chown -R edgegw:edgegw /opt/edge-gateway
```

Si cambia el frontend, recompílalo primero en local con:

```powershell
cd frontend
npm ci
npm run build
```

Después copia el nuevo contenido de `frontend/dist/` a la Pi.

## Cómo compilar el frontend

Si no has compilado el frontend antes, estos son los pasos exactos desde la raíz del repositorio:

1. Abre PowerShell en la raíz del proyecto.
2. Instala una vez las dependencias del frontend:

```powershell
cd frontend
npm ci
```

3. Compila los archivos de producción:

```powershell
npm run build
```

4. Cuando termine la compilación, el sitio generado estará en `frontend/dist/`.

Si solo cambias el backend, no necesitas volver a compilar el frontend.

## Distribución en ejecución

- El backend escucha en `127.0.0.1:5000`.
- Nginx sirve el frontend desde `/opt/edge-gateway/frontend/dist`.
- Nginx hace proxy de `/api/` hacia `127.0.0.1:5000`.

## Redirección de Nginx
ln -s /opt/edge-gateway/nginx/sites-available/edge-gateway.conf /etc/nginx/sites-enabled/edge-gateway.conf
cd /etc/nginx/sites-enabled/
rm default
sudo nginx -t
sudo systemctl reload nginx
