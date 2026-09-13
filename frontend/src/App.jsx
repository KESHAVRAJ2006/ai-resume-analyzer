import { Suspense, lazy, useCallback, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Nav } from "./components/layout/Nav";
import { Footer } from "./components/layout/Footer";
import { Landing } from "./screens/Landing";
import { Upload } from "./screens/Upload";
import { Analyzing } from "./screens/Analyzing";
import { analyzeResume } from "./lib/api";
import { screenTransition } from "./lib/motion";

/**
 * Results is code-split. It is the only screen that uses Recharts, which is
 * ~400KB on its own - loading it up front would more than double the landing
 * page's bundle for a screen the visitor reaches several seconds later, if at
 * all.
 */
const loadResults = () => import("./screens/Results");
const Results = lazy(loadResults);

/**
 * The whole app is a four-step linear flow, so it uses a state machine rather
 * than a router. There are no deep links to support - a results URL would be
 * meaningless without the file that produced it - and this keeps the bundle
 * free of a routing dependency.
 */
const VIEW = {
  LANDING: "landing",
  UPLOAD: "upload",
  ANALYZING: "analyzing",
  RESULTS: "results",
};

export default function App() {
  const [view, setView] = useState(VIEW.LANDING);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [pending, setPending] = useState({ fileName: "", roleName: "" });

  // Held in a ref, not state: aborting is a side effect and must not re-render.
  const abortRef = useRef(null);

  const handleAnalyze = useCallback(async (file, roleId, roleName) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setPending({ fileName: file.name, roleName });
    setError(null);
    setView(VIEW.ANALYZING);

    // Fetch the results chunk in parallel with the analysis. The request takes
    // a few seconds, so by the time the data lands the code is already there
    // and the Suspense fallback never actually appears.
    loadResults();

    try {
      const data = await analyzeResume(file, roleId, controller.signal);
      setAnalysis(data);
      setView(VIEW.RESULTS);
    } catch (caught) {
      if (caught.name === "AbortError") return;
      // Back to Upload with the message: the user's next action is to fix the
      // file or pick another role, and both live on that screen.
      setError(caught.message);
      setView(VIEW.UPLOAD);
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setAnalysis(null);
    setError(null);
    setView(VIEW.LANDING);
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <Nav onStart={() => setView(VIEW.UPLOAD)} showCta={view === VIEW.LANDING} />

      <div className="flex-1">
        {/* mode="wait" lets the outgoing screen finish before the next enters,
            so the two never overlap mid-fade. */}
        <AnimatePresence mode="wait">
          <motion.div key={view} {...screenTransition}>
            {view === VIEW.LANDING && <Landing onStart={() => setView(VIEW.UPLOAD)} />}

            {view === VIEW.UPLOAD && (
              <Upload
                onBack={reset}
                submitError={error}
                onAnalyze={handleAnalyze}
              />
            )}

            {view === VIEW.ANALYZING && (
              <Analyzing fileName={pending.fileName} roleName={pending.roleName} />
            )}

            {view === VIEW.RESULTS && analysis && (
              // The fallback reuses the Analyzing screen, so on the rare slow
              // connection where the chunk is not ready the user keeps seeing
              // the skeletons rather than a blank page.
              <Suspense
                fallback={
                  <Analyzing fileName={pending.fileName} roleName={pending.roleName} />
                }
              >
                <Results data={analysis} onRestart={() => setView(VIEW.UPLOAD)} />
              </Suspense>
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      <Footer />
    </div>
  );
}
