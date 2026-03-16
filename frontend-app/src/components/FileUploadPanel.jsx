import { useRef, useState } from "react";

// Reusable upload module for project evidence, deal files, and future ingestion workflows.
export function FileUploadPanel({
  title,
  description,
  accept = ".pdf,.doc,.docx,.xlsx,.csv",
  buttonLabel = "Upload file",
  helperText = "Supported formats can be expanded as the ingestion pipeline grows.",
  onUpload,
}) {
  const inputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage("");
    setErrorMessage("");

    if (!selectedFile) {
      setErrorMessage("Choose a file to continue.");
      return;
    }

    try {
      setIsSubmitting(true);
      if (onUpload) {
        const responseMessage = await onUpload(selectedFile);
        setMessage(responseMessage ?? `${selectedFile.name} was accepted for processing.`);
      } else {
        setMessage(`${selectedFile.name} is ready. Wire this panel to a project document API when the upload backend is added.`);
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Unable to upload the selected file.");
    } finally {
      setIsSubmitting(false);
      setSelectedFile(null);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  }

  return (
    <div className="upload-panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Evidence intake</p>
          <h3 className="projects-heading">{title}</h3>
        </div>
        <span className="panel-note">Reusable component</span>
      </div>
      <p className="hero-text">{description}</p>

      <form className="login-form upload-form" onSubmit={handleSubmit}>
        <label>
          Select file
          <input
            ref={inputRef}
            type="file"
            accept={accept}
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <button type="submit" className="ghost-button login-submit" disabled={isSubmitting}>
          {isSubmitting ? "Uploading..." : buttonLabel}
        </button>
      </form>

      <p className="hint-text">{helperText}</p>
      {selectedFile ? <p className="hint-text">Selected: {selectedFile.name}</p> : null}
      {message ? <p className="hint-text">{message}</p> : null}
      {errorMessage ? <p className="error-message">{errorMessage}</p> : null}
    </div>
  );
}
