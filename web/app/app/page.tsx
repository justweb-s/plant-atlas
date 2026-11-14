import { redirect } from "next/navigation";

// The RSPP app is the home page again; old links to /app still work.
export default function AppPage() {
  redirect("/");
}
