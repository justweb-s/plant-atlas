import type { Metadata } from "next";
import AtlasView from "./components/AtlasView";

export const metadata: Metadata = {
  title: "Plant Atlas",
  description: "L'ontologia sempre visibile: le cinque fasce di fatti, le domande, il tabellone, i cambi, le scene.",
};

export default function Home() {
  return <AtlasView />;
}
