/**
 * Configuración global para la aplicación frontend.
 *
 * Este módulo centraliza configuraciones compartidas que se aplican a múltiples páginas
 * y servicios.
 */

/**
 * Intervalo de actualización predeterminado en segundos para sondear puntos finales de datos.
 * Utilizado por páginas que necesitan sincronizarse periódicamente con el backend.
 */
export const DEFAULT_REFRESH_SECONDS = 60;

/**
 * URL base para solicitudes de API del backend.
 * Resuelto desde la variable de entorno VITE_API_BASE_URL o por defecto a la
 * ruta de API del mismo origen.
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';
