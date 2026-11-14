import { redirect } from "next/navigation";

// The ontology view is now the home page; old links to /atlas still work.
export default function AtlasPage() {
  redirect("/");
}
