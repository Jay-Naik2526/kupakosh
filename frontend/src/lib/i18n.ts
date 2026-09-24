export type Lang = "en" | "hi";
type S = { en: string; hi: string };
export const TABS: { href: string; no: string; en: string; hi: string; q: string }[] = [
  { href: "/", no: "01", en: "Command", hi: "कमान", q: "What's coming next and what should I do?" },
  { href: "/offsets", no: "02", en: "Offsets", hi: "निकट कूप", q: "What happened in nearby wells, by layer?" },
  { href: "/wiki", no: "03", en: "Wiki", hi: "ज्ञानकोश", q: "What do we know, and who approved it?" },
  { href: "/fixes", no: "04", en: "Fixes", hi: "उपाय", q: "What actually worked?" },
  { href: "/mudwindow", no: "05", en: "Mud Window", hi: "मड सीमा", q: "Which mud weight is safe, by formation?" },
  { href: "/checker", no: "06", en: "Checker", hi: "मिलान", q: "Where do the reports disagree?" },
  { href: "/copilot", no: "07", en: "Copilot", hi: "सहायक", q: "Ask the records." },
  { href: "/brief", no: "08", en: "Brief", hi: "सार", q: "What should the pre-drill brief say?" },
  { href: "/accuracy", no: "09", en: "Accuracy", hi: "सटीकता", q: "How much can you trust this?" },
];
export const T: Record<string, S> = {
  footer: { en: "Decision support only – the engineer decides. Data: public NDR/DGH India basin summaries, and Sodir (Norway) and Utah FORGE (USA) well records used as stand-ins for well-level data; no Oil India well data.",
            hi: "केवल निर्णय सहायता – निर्णय अभियंता का। डेटा: सार्वजनिक NDR/DGH भारत बेसिन सारांश, तथा कूप-स्तर हेतु प्रतिनिधि Sodir (नॉर्वे) व Utah FORGE (अमेरिका) अभिलेख; ऑयल इंडिया का कूप डेटा नहीं।" },
  board: { en: "Prototype for Oil India Limited · SIH 2026", hi: "ऑयल इंडिया लिमिटेड हेतु प्रोटोटाइप · SIH 2026" },
  replay: { en: "REPLAY", hi: "पुनःचलन" },
  insufficient: { en: "Insufficient evidence", hi: "अपर्याप्त साक्ष्य" },
  notEvaluated: { en: "Not evaluated", hi: "मूल्यांकन नहीं हुआ" },
  sources: { en: "View sources", hi: "स्रोत देखें" },
  openWiki: { en: "Open wiki", hi: "ज्ञानकोश खोलें" },
};
export const t = (k: keyof typeof T, lang: Lang) => T[k][lang];
