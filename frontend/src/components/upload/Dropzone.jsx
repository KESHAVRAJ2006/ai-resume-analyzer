import { useCallback, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { FileText, UploadCloud, X } from "lucide-react";
import { Button } from "../ui/Button";
import { cn, formatBytes } from "../../lib/utils";
import { DURATION, EASE } from "../../lib/motion";

const ACCEPTED_EXTENSIONS = [".pdf", ".docx"];
const MAX_BYTES = 5 * 1024 * 1024; // mirrors MAX_UPLOAD_MB on the backend

/**
 * Validate a dropped or chosen file before it ever reaches the network.
 *
 * The backend re-checks both of these - a browser check is a courtesy, not a
 * security boundary - but failing here turns a 3-second round trip into
 * instant feedback.
 *
 * @param {File} file
 * @returns {string|null} an error message, or null when the file is fine
 */
function validateFile(file) {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((extension) => name.endsWith(extension))) {
    return "That file type is not supported. Upload a PDF or DOCX.";
  }
  if (file.size > MAX_BYTES) {
    return `That file is ${formatBytes(file.size)}. The limit is 5 MB.`;
  }
  if (file.size === 0) {
    return "That file is empty.";
  }
  return null;
}

/**
 * Full-width drag-and-drop zone that glows on dragover and shows the chosen
 * file with its size and a remove button.
 *
 * @param {object} props
 * @param {File|null} props.file currently selected file
 * @param {(file: File|null) => void} props.onFileChange
 * @param {(message: string|null) => void} props.onError
 */
export function Dropzone({ file, onFileChange, onError }) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);
  const reduced = useReducedMotion();

  const accept = useCallback(
    (candidate) => {
      if (!candidate) return;
      const problem = validateFile(candidate);
      if (problem) {
        onError(problem);
        onFileChange(null);
        return;
      }
      onError(null);
      onFileChange(candidate);
    },
    [onError, onFileChange],
  );

  // dragenter/dragover fire continuously and on child elements too. Tracking a
  // boolean and always calling preventDefault is what stops the browser from
  // navigating away to open the file.
  const handleDragOver = (event) => {
    event.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (event) => {
    event.preventDefault();
    // relatedTarget is null when the pointer leaves the window entirely.
    if (!event.currentTarget.contains(event.relatedTarget)) setIsDragging(false);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    accept(event.dataTransfer.files?.[0]);
  };

  if (file) {
    return (
      <motion.div
        initial={reduced ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: DURATION.base, ease: EASE }}
        className="flex items-center gap-4 rounded-card border border-line bg-surface p-5"
      >
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-control border border-line bg-elevated">
          <FileText className="h-5 w-5 text-accent" strokeWidth={1.75} aria-hidden="true" />
        </span>

        <div className="min-w-0 flex-1">
          {/* truncate matters: resume filenames are often very long. */}
          <p className="truncate text-body font-medium text-primary">{file.name}</p>
          <p className="text-small tabular-nums text-subtle">{formatBytes(file.size)}</p>
        </div>

        <Button
          variant="subtle"
          size="icon"
          onClick={() => {
            onFileChange(null);
            onError(null);
            // Clearing the input's value lets the user re-pick the same file;
            // without this, choosing the identical file fires no change event.
            if (inputRef.current) inputRef.current.value = "";
          }}
          aria-label={`Remove ${file.name}`}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </Button>

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(",")}
          className="hidden"
          onChange={(event) => accept(event.target.files?.[0])}
        />
      </motion.div>
    );
  }

  return (
    <div
      onDragEnter={handleDragOver}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "relative rounded-card border border-dashed transition-all duration-200 ease-brand",
        isDragging
          ? "border-accent bg-accent-soft shadow-accent-glow"
          : "border-line bg-surface hover:border-line-strong",
      )}
    >
      {/* The whole zone is one <label>, so a click anywhere opens the picker and
          keyboard users reach it through the input rather than a fake button. */}
      <label
        htmlFor="resume-input"
        className="flex cursor-pointer flex-col items-center gap-4 px-6 py-14 text-center"
      >
        <motion.span
          animate={isDragging && !reduced ? { y: -4, scale: 1.04 } : { y: 0, scale: 1 }}
          transition={{ duration: DURATION.fast, ease: EASE }}
          className={cn(
            "flex h-14 w-14 items-center justify-center rounded-card border transition-colors duration-200 ease-brand",
            isDragging ? "border-accent/40 bg-accent/15" : "border-line bg-elevated",
          )}
        >
          <UploadCloud
            className={cn(
              "h-6 w-6 transition-colors duration-200 ease-brand",
              isDragging ? "text-accent-hover" : "text-muted",
            )}
            strokeWidth={1.75}
            aria-hidden="true"
          />
        </motion.span>

        <span>
          <span className="block text-title">
            {isDragging ? "Drop it here" : "Drop your resume, or browse"}
          </span>
          <span className="mt-1.5 block text-small text-subtle">
            PDF or DOCX, up to 5 MB
          </span>
        </span>
      </label>

      <input
        ref={inputRef}
        id="resume-input"
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(",")}
        // sr-only rather than hidden: a display:none input cannot receive focus,
        // which would make the zone unreachable by keyboard.
        className="sr-only"
        onChange={(event) => accept(event.target.files?.[0])}
      />
    </div>
  );
}
