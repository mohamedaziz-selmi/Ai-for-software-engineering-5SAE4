// The portable launcher supplies the gateway URL before React starts.
export const API_URL=(window as Window & {__CEREBRO_CONFIG__?:{apiUrl?:string}}).__CEREBRO_CONFIG__?.apiUrl
  ||import.meta.env.VITE_API_URL||'http://127.0.0.1:8900';
