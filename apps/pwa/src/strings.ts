export type Lang = "en" | "hi" | "ta";

export const strings = {
  en: { title: "Cohort Coach", judge: "Judge mode", note: "Demo build. Simulated data is labelled." },
  hi: { title: "कोहॉर्ट कोच", judge: "जज मोड", note: "डेमो संस्करण। नकली डेटा पर लेबल होता है।" },
  ta: { title: "கோஹார்ட் கோச்", judge: "நடுவர் முறை", note: "டெமோ பதிப்பு. உருவகப்படுத்தப்பட்ட தரவு குறிக்கப்படும்." },
} satisfies Record<Lang, Record<string, string>>;

export function t(lang: Lang, key: keyof (typeof strings)["en"]): string {
  return strings[lang][key] ?? strings.en[key];
}
