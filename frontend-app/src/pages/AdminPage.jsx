import { useEffect, useState } from "react";
import { getSession } from "../auth";
import { fetchAccessRequests, reviewAccessRequest } from "../api/adminClient";
import { SectionTitle } from "../components/SectionTitle";

export function AdminPage() {
  const session = getSession();
  const isAdmin = session?.user?.role === "admin";
  const [accessRequests, setAccessRequests] = useState([]);
  const [reviewError, setReviewError] = useState("");
  const [reviewMessage, setReviewMessage] = useState("");
  const [isLoadingRequests, setIsLoadingRequests] = useState(isAdmin);
  const [activeRequestId, setActiveRequestId] = useState("");

  const pendingRequests = accessRequests.filter((request) => request.status === "pending");
  const approvedRequests = accessRequests.filter((request) => request.status === "approved");
  const rejectedRequests = accessRequests.filter((request) => request.status === "rejected");

  useEffect(() => {
    let isMounted = true;

    async function loadAccessRequests() {
      if (!isAdmin) {
        return;
      }
      setIsLoadingRequests(true);
      setReviewError("");
      try {
        const data = await fetchAccessRequests();
        if (isMounted) {
          setAccessRequests(data);
        }
      } catch (error) {
        if (isMounted) {
          setReviewError(error instanceof Error ? error.message : "Unable to load access requests.");
        }
      } finally {
        if (isMounted) {
          setIsLoadingRequests(false);
        }
      }
    }

    loadAccessRequests();
    return () => {
      isMounted = false;
    };
  }, [isAdmin]);

  async function handleReview(requestId, status) {
    try {
      setActiveRequestId(requestId);
      setReviewError("");
      const payload = await reviewAccessRequest(requestId, status);
      setAccessRequests((current) =>
        current.map((item) => (item.request_id === requestId ? { ...item, status: payload.status } : item)),
      );
      setReviewMessage(payload.message);
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Unable to review the access request.");
    } finally {
      setActiveRequestId("");
    }
  }

  return (
    <main className="content about-content">
      <section className="glass-card architecture-hero">
        <SectionTitle
          eyebrow="Admin"
          title="Access governance"
          description="Review elevated-access requests, keep promotions visible, and manage the first internal approval workflow directly inside the platform."
        />
      </section>

      <section className="section-block">
        <div className="overview-grid admin-overview-grid">
          <article className="metric-card">
            <span>Pending review</span>
            <strong>{pendingRequests.length}</strong>
            <p>Requests currently waiting on an admin decision</p>
          </article>
          <article className="metric-card">
            <span>Approved</span>
            <strong>{approvedRequests.length}</strong>
            <p>Requests accepted through the current workflow</p>
          </article>
          <article className="metric-card">
            <span>Rejected</span>
            <strong>{rejectedRequests.length}</strong>
            <p>Requests declined after review</p>
          </article>
        </div>
      </section>

      <section className="section-block">
        <div className="glass-card">
          <SectionTitle
            eyebrow="Queue"
            title="Access request review"
            description="Requests submitted from the sign-in experience land here for an admin decision."
          />
          {!isAdmin ? <p className="callout-message">Admin access is required to review access requests.</p> : null}
          {reviewError ? <p className="callout-message">{reviewError}</p> : null}
          {reviewMessage ? <p className="hint-text">{reviewMessage}</p> : null}
          {isAdmin ? (
            <div className="admin-request-list">
              {pendingRequests.map((request) => (
                <article key={request.request_id} className="admin-request-card">
                  <div>
                    <strong>{request.full_name}</strong>
                    <p>{request.email}</p>
                    <p>{request.company_name}</p>
                    <small>
                      {request.requested_role} | {request.status}
                    </small>
                  </div>
                  <div className="admin-request-side">
                    <p>{request.reason}</p>
                    <div className="admin-request-actions">
                      <button
                        type="button"
                        className="ghost-button"
                        disabled={activeRequestId === request.request_id || request.status !== "pending"}
                        onClick={() => handleReview(request.request_id, "rejected")}
                      >
                        Reject
                      </button>
                      <button
                        type="button"
                        className="primary-button"
                        disabled={activeRequestId === request.request_id || request.status !== "pending"}
                        onClick={() => handleReview(request.request_id, "approved")}
                      >
                        {activeRequestId === request.request_id ? "Saving..." : "Approve"}
                      </button>
                    </div>
                  </div>
                </article>
              ))}
              {!pendingRequests.length && !isLoadingRequests ? <p className="hint-text">No access requests are waiting for review.</p> : null}
              {isLoadingRequests ? <p className="hint-text">Loading access requests...</p> : null}
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
