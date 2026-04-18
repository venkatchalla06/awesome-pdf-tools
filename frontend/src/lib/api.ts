import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({ baseURL: BASE });

// Attach JWT if present
apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const api = {
  get: async (path: string) => {
    const { data } = await apiClient.get(path);
    return data;
  },
  post: async (path: string, body?: unknown) => {
    const { data } = await apiClient.post(path, body);
    return data;
  },
};
