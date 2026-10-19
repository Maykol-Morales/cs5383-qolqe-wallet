// Allure 3 (sin Java): npx allure@3 generate reportes/allure-results  →  reportes/allure/
// historyPath acumula una línea por corrida: da las tendencias del dashboard entre corridas.
const nombre = "Qolqe Wallet · Núcleo + G3";

export default {
  name: nombre,
  output: "reportes/allure",
  historyPath: "reportes/allure-historial.jsonl",
  plugins: {
    awesome: {
      options: { reportName: nombre, reportLanguage: "es", singleFile: true, groupBy: ["epic", "story"], appendTitlePath: true },
    },
    dashboard: { options: { reportName: nombre, reportLanguage: "es", singleFile: true } },
  },
};
