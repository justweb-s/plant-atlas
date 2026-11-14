import type { Metadata } from "next";
import AtlasView from "../components/AtlasView";

export const metadata: Metadata = {
  title: "Plant Atlas · Ontologia",
  description: "L'ontologia a tutta pagina: le fasce di fatti, le domande, il tabellone, i cambi, le scene.",
};

// The ontology view at full height. The home page shows it in a frame when «Ontologia» is on.
export default function AtlasPage() {
  return <AtlasView />;
}
