import { Shell } from "./Shell";

/**
 * Footer. Its real job is the disclaimer - the product makes a judgement about
 * someone's resume, so the limits of that judgement are stated on every screen
 * rather than buried in an about page.
 */
export function Footer() {
  return (
    <footer className="mt-24 border-t border-line py-8">
      <Shell className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="max-w-prose text-small text-subtle">
          Scores estimate skill overlap with a role&apos;s requirements. They are not hiring
          decisions, and nothing here reads name, gender, age, photo, religion, nationality,
          marital status or disability.
        </p>
        <p className="text-small text-subtle">Your file is deleted after analysis.</p>
      </Shell>
    </footer>
  );
}
