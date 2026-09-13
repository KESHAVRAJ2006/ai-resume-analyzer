import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { AlertCircle, ArrowLeft, Sparkles } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Shell } from "../components/layout/Shell";
import { Dropzone } from "../components/upload/Dropzone";
import { RolePills } from "../components/upload/RolePills";
import { fetchRoles } from "../lib/api";
import { fadeUp, respectMotion, staggerChildren } from "../lib/motion";

/**
 * Screen 2. Pick a file, pick a role, go.
 *
 * Roles are fetched here rather than in App so the request starts exactly when
 * this screen mounts, and so a failure only affects this screen.
 */
export function Upload({ onBack, onAnalyze, submitError }) {
  const [roles, setRoles] = useState([]);
  const [rolesLoading, setRolesLoading] = useState(true);
  const [rolesError, setRolesError] = useState(null);
  const [selectedRole, setSelectedRole] = useState(null);
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    // AbortController cancels the request if the user leaves before it lands,
    // which prevents a setState on an unmounted component.
    const controller = new AbortController();

    fetchRoles(controller.signal)
      .then((data) => {
        setRoles(data);
        // Preselect nothing: making the user choose is the point of the screen,
        // and a default would quietly bias every result toward one role.
        setRolesError(null);
      })
      .catch((error) => {
        if (error.name !== "AbortError") setRolesError(error.message);
      })
      .finally(() => setRolesLoading(false));

    return () => controller.abort();
  }, []);

  const ready = Boolean(file && selectedRole);

  return (
    <main>
      <Shell className="py-12 sm:py-16">
        <motion.div
          variants={staggerChildren(0.06)}
          initial="hidden"
          animate="visible"
          className="mx-auto max-w-3xl"
        >
          <motion.div variants={respectMotion(fadeUp, reduced)}>
            <Button variant="ghost" size="sm" onClick={onBack} className="-ml-3 mb-6">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back
            </Button>
          </motion.div>

          <motion.h1 variants={respectMotion(fadeUp, reduced)} className="text-section">
            Upload your resume
          </motion.h1>
          <motion.p
            variants={respectMotion(fadeUp, reduced)}
            className="mt-2 max-w-prose text-body text-muted"
          >
            Two steps. Your file is analysed in memory and deleted the moment the response is
            sent.
          </motion.p>

          {/* Step 1 -------------------------------------------------------- */}
          <motion.section variants={respectMotion(fadeUp, reduced)} className="mt-10">
            <StepHeading index={1} title="Choose a file" />
            <Dropzone file={file} onFileChange={setFile} onError={setFileError} />
            {fileError && <InlineError message={fileError} />}
          </motion.section>

          {/* Step 2 -------------------------------------------------------- */}
          <motion.section variants={respectMotion(fadeUp, reduced)} className="mt-10">
            <StepHeading index={2} title="Pick a target role" />
            {rolesError ? (
              <Card className="border-band-early/30 bg-band-early/5">
                <p className="text-body text-primary">Could not load roles</p>
                <p className="mt-1.5 text-small text-muted">{rolesError}</p>
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-4"
                  onClick={() => window.location.reload()}
                >
                  Retry
                </Button>
              </Card>
            ) : (
              <RolePills
                roles={roles}
                value={selectedRole}
                onChange={setSelectedRole}
                loading={rolesLoading}
              />
            )}
          </motion.section>

          {/* A failed analysis sends the user back here, because the fix is
              always on this screen: a different file or a different role. */}
          {submitError && (
            <motion.div variants={respectMotion(fadeUp, reduced)} className="mt-10">
              <Card className="border-band-early/30 bg-band-early/5">
                <p className="flex items-start gap-2 text-body text-primary">
                  <AlertCircle
                    className="mt-0.5 h-4 w-4 shrink-0 text-band-early"
                    aria-hidden="true"
                  />
                  That analysis did not go through
                </p>
                <p className="mt-1.5 pl-6 text-small text-muted">{submitError}</p>
              </Card>
            </motion.div>
          )}

          {/* Action -------------------------------------------------------- */}
          <motion.div
            variants={respectMotion(fadeUp, reduced)}
            className="mt-12 flex flex-col gap-4 sm:flex-row sm:items-center"
          >
            <Button
              size="lg"
              disabled={!ready}
              onClick={() =>
                onAnalyze(
                  file,
                  selectedRole,
                  // Pass the display name too: the Analyzing screen shows it,
                  // and it would otherwise have to refetch the role list to
                  // turn "data_scientist" back into "Data Scientist".
                  roles.find((role) => role.role_id === selectedRole)?.role_name ?? "",
                )
              }
              className="w-full sm:w-auto"
            >
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              Analyze resume
            </Button>

            {/* Says which step is outstanding instead of leaving a dead button
                with no explanation. */}
            {!ready && (
              <p className="text-small text-subtle">
                {!file && !selectedRole
                  ? "Add a file and pick a role to continue."
                  : !file
                    ? "Add a file to continue."
                    : "Pick a role to continue."}
              </p>
            )}
          </motion.div>
        </motion.div>
      </Shell>
    </main>
  );
}

/** Numbered step label, so the two sections read as a sequence. */
function StepHeading({ index, title }) {
  return (
    <div className="mb-4 flex items-center gap-2.5">
      <span className="flex h-6 w-6 items-center justify-center rounded-pill border border-line bg-elevated text-label tabular-nums text-muted">
        {index}
      </span>
      <h2 className="text-title">{title}</h2>
    </div>
  );
}

/** Inline validation message, tied to the control above it. */
function InlineError({ message }) {
  return (
    <p role="alert" className="mt-3 flex items-start gap-2 text-small text-band-early">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      {message}
    </p>
  );
}
