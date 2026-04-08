/**
 * Axios API client with snake_case <-> camelCase transformers.
 */

import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL } from "../config";

/** Convert camelCase keys to snake_case for API requests. */
function toSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

/** Convert snake_case keys to camelCase for API responses. */
function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
}

/** Recursively transform object keys. */
function transformKeys(
  data: unknown,
  transformer: (key: string) => string,
): unknown {
  if (Array.isArray(data)) {
    return data.map((item) => transformKeys(item, transformer));
  }
  if (data !== null && typeof data === "object" && !(data instanceof FormData)) {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      result[transformer(key)] = transformKeys(value, transformer);
    }
    return result;
  }
  return data;
}

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
    "X-User-Id": "default-user",
  },
});

// Request interceptor: camelCase -> snake_case
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (config.data && !(config.data instanceof FormData)) {
    config.data = transformKeys(config.data, toSnakeCase);
  }
  return config;
});

// Response interceptor: snake_case -> camelCase
apiClient.interceptors.response.use(
  (response) => {
    if (response.data) {
      response.data = transformKeys(response.data, toCamelCase);
    }
    return response;
  },
  (error) => {
    if (error.response?.data) {
      error.response.data = transformKeys(error.response.data, toCamelCase);
    }
    return Promise.reject(error);
  },
);

export default apiClient;
