/// <reference types="vite/client" />

interface ImportMetaEnv {
  // Base URL of the local backend when the frontend is hosted cross-origin
  // (e.g. Vercel → http://127.0.0.1:8765). Empty/undefined = same-origin.
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
