/// <reference types="vite/client" />

// Variaveis do arquivo .env lidas pelo front (so as que comecam com VITE_)
interface ImportMetaEnv {
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
