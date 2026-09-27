"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { X } from "lucide-react";
import { useApp } from "@/lib/state";

/**
 * Step-by-step overlay that walks the demo flow of SPEC.md §13 (Accuracy -> Command replay ->
 * notice -> sources -> wiki -> fixes -> mud window/checker -> copilot -> brief -> close).
 * Text only — no numbers are invented here, only real screens are visited.
 *
 * Mounted once in AppShell. Any page can start it with openGuidedTour() (a tiny window event —
 * lib/state.tsx is only allowed to grow a `theme` field for this task, so tour state lives here).
 */
const OPEN_EVENT = "kk:tour:open";
export function openGuidedTour() {
  if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent(OPEN_EVENT));
}

type Step = { href: string; en: { title: string; body: string }; hi: { title: string; body: string } };

const STEPS: Step[] = [
  {
    href: "/accuracy",
    en: { title: "1. Start with the honesty page", body: "Accuracy shows real counts — wells, report entries, events, approved wiki pages — and every measured metric, or \"Not evaluated\" if it isn't measured yet. Nothing here is invented." },
    hi: { title: "1. ईमानदारी वाले पृष्ठ से शुरुआत", body: "सटीकता पृष्ठ वास्तविक गिनतियाँ दिखाता है — कूप, रिपोर्ट प्रविष्टियाँ, घटनाएँ, अनुमोदित ज्ञानकोश पृष्ठ — और हर मापित मापदंड, या यदि मापा नहीं गया तो \"मूल्यांकन नहीं हुआ\"। यहाँ कुछ भी गढ़ा नहीं गया है।" },
  },
  {
    href: "/command",
    en: { title: "2. Pick a well and start REPLAY", body: "Well Room replays real recorded rig-sensor data — never live, always labelled REPLAY. Pick a replayable well and press Start replay." },
    hi: { title: "2. एक कूप चुनें और REPLAY प्रारंभ करें", body: "कूप कक्ष वास्तविक अभिलिखित रिग-सेंसर डेटा का पुनःचलन करता है — कभी लाइव नहीं, हमेशा REPLAY अंकित। पुनःचलन योग्य कूप चुनें और पुनःचलन प्रारंभ करें दबाएँ।" },
  },
  {
    href: "/command",
    en: { title: "3. Watch for the notice", body: "About 150 m before a formation with recorded problems in offset wells, a notice slip appears: hazard, probability with its range, n_eff, and the best fix with its success fraction." },
    hi: { title: "3. सूचना पर्ची देखें", body: "निकट कूपों में अभिलिखित समस्याओं वाली संरचना से लगभग 150 मी पहले एक सूचना पर्ची दिखती है: खतरा, सीमा सहित प्रायिकता, n_eff, और सफलता अंश सहित सर्वोत्तम उपाय।" },
  },
  {
    href: "/command",
    en: { title: "4. View sources", body: "Every number traces back to a document and a line. Click \"View sources\" on the notice to see the exact report text it came from." },
    hi: { title: "4. स्रोत देखें", body: "हर संख्या किसी दस्तावेज़ और पंक्ति तक अनुरेखित होती है। सूचना पर \"स्रोत देखें\" क्लिक कर उस मूल रिपोर्ट पाठ को देखें।" },
  },
  {
    href: "/wiki",
    en: { title: "5. Open the Well Wiki", body: "The compiled, engineer-approved page for that formation: a citation on every sentence, an APPROVED stamp, and a noting sheet with the review history." },
    hi: { title: "5. ज्ञानकोश खोलें", body: "उस संरचना का संकलित, अभियंता-अनुमोदित पृष्ठ: हर वाक्य पर उद्धरण, APPROVED मुहर, और समीक्षा इतिहास सहित टिप्पणी शीट।" },
  },
  {
    href: "/fixes",
    en: { title: "6. See what actually worked", body: "Fixes ranks mitigations by a Wilson lower bound on their success rate — including a fix that made things worse. That is the \"what actually worked\" moment." },
    hi: { title: "6. देखें वास्तव में क्या कारगर रहा", body: "उपाय, सफलता-दर की Wilson निचली सीमा से उपायों को क्रमबद्ध करता है — यहाँ तक कि जिस उपाय से स्थिति बिगड़ी वह भी दिखता है। यही \"वास्तव में क्या कारगर रहा\" वाला क्षण है।" },
  },
  {
    href: "/mudwindow",
    en: { title: "7. Mud window & report checker", body: "The safe mud-weight window per formation, built only from LOT/FIT tests, kicks and losses — plus the Checker, which flags where reports disagree." },
    hi: { title: "7. मड सीमा व रिपोर्ट मिलानकर्ता", body: "प्रति संरचना सुरक्षित मड-भार सीमा, केवल LOT/FIT परीक्षणों, किक और लॉस से बनी — साथ ही मिलानकर्ता, जो रिपोर्टों की असहमति चिह्नित करता है।" },
  },
  {
    href: "/copilot",
    en: { title: "8. Ask the records", body: "Copilot answers only from cited tool output. Ask a question with evidence, then try one it should refuse — it will say \"No evidence found in the records.\"" },
    hi: { title: "8. अभिलेखों से पूछें", body: "सहायक केवल उद्धृत टूल परिणामों से उत्तर देता है। साक्ष्य वाला प्रश्न पूछें, फिर एक ऐसा प्रश्न आज़माएँ जिसे उसे अस्वीकार करना चाहिए — वह कहेगा \"अभिलेखों में कोई साक्ष्य नहीं मिला।\"" },
  },
  {
    href: "/brief",
    en: { title: "9. Prepare the pre-drill brief", body: "Brief compiles hazards, mud window, casing lessons and open conflicts into an official-style PDF, ending with \"Decision support only. The engineer decides.\"" },
    hi: { title: "9. वेधन-पूर्व सार तैयार करें", body: "सार, खतरों, मड सीमा, केसिंग सीख और लंबित विरोधाभासों को एक शासकीय-शैली PDF में संकलित करता है, अंत में \"केवल निर्णय सहायता। निर्णय अभियंता का।\"" },
  },
  {
    href: "/",
    en: { title: "10. Oil India can swap in its own data", body: "Every screen you just saw runs on public stand-in data. The schema does not change when real WCR, DDR and eRTMAC streams replace it." },
    hi: { title: "10. ऑयल इंडिया अपना डेटा जोड़ सकता है", body: "अभी देखे गए सभी स्क्रीन सार्वजनिक प्रतिनिधि डेटा पर चलते हैं। जब वास्तविक WCR, DDR व eRTMAC धाराएँ इसकी जगह लेंगी, तब स्कीमा नहीं बदलेगा।" },
  },
];

export function GuidedTour() {
  const { lang } = useApp();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [i, setI] = useState(0);

  useEffect(() => {
    const onOpen = () => { setI(0); setOpen(true); };
    window.addEventListener(OPEN_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_EVENT, onOpen);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    if (open) router.push(STEPS[i].href);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i, open]);

  if (!open) return null;
  const step = STEPS[i];
  const s = lang === "hi" ? step.hi : step.en;
  const last = i === STEPS.length - 1;

  const finish = () => {
    try { localStorage.setItem("kk.tourDone", "1"); } catch { /* private mode */ }
    setOpen(false);
  };

  return (
    <div className="kk-tour-card" role="dialog" aria-label={lang === "hi" ? "मार्गदर्शित दौरा" : "Guided tour"}>
      <div className="flex items-start gap-2">
        <div className="flex-1">
          <div className="label">
            {lang === "hi" ? "चरण" : "Step"} {i + 1}/{STEPS.length}
          </div>
          <div className="font-semibold mt-0.5">{s.title}</div>
        </div>
        <button className="chip" onClick={() => setOpen(false)} aria-label={lang === "hi" ? "दौरा बंद करें" : "Close tour"}>
          <X size={14} />
        </button>
      </div>
      <p className="small mt-2" style={{ color: "var(--text-2)" }}>{s.body}</p>
      <div className="flex items-center gap-2 mt-3">
        <button className="btn" disabled={i === 0} onClick={() => setI((x) => Math.max(0, x - 1))}>
          {lang === "hi" ? "पीछे" : "Back"}
        </button>
        {!last ? (
          <button className="btn btn-primary" onClick={() => setI((x) => Math.min(STEPS.length - 1, x + 1))}>
            {lang === "hi" ? "आगे" : "Next"}
          </button>
        ) : (
          <button className="btn btn-primary" onClick={finish}>
            {lang === "hi" ? "समाप्त" : "Done"}
          </button>
        )}
        <button className="btn ml-auto" onClick={finish}>
          {lang === "hi" ? "छोड़ें" : "Skip"}
        </button>
      </div>
    </div>
  );
}
