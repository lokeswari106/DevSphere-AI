import axios from "axios";
export const api = axios.create({ baseURL: "/api", withCredentials: true });
let csrf = "";
export function setCsrf(value) {
  csrf = value || "";
}
api.interceptors.request.use((c) => {
  if (!["get", "head", "options"].includes(c.method))
    c.headers["X-CSRF-Token"] = csrf;
  return c;
});
export function errorText(e) {
  const d = e.response?.data;
  return d?.details?.length
    ? `${d.message}: ${d.details.map((x) => x.message).join("; ")}`
    : d?.message || e.message || "Something went wrong. Try again.";
}
export async function download(url, filename) {
  const { data } = await api.get(url, { responseType: "blob" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(data);
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 5000);
}
export const label = (s) =>
  String(s || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
