package com.civicbrain.complaints.service;

import java.time.Clock;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.AuditLog;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.PageResponse;
import com.civicbrain.complaints.repo.ComplaintRepository;
import com.civicbrain.complaints.repo.FeedbackRepository;
import com.civicbrain.workflow.Actor;
import com.civicbrain.workflow.ActorRole;
import com.civicbrain.workflow.ComplaintStatus;
import com.civicbrain.workflow.WorkflowActor;

/**
 * The citizen's own complaints (docs/04 §5, FR-13, FR-15): list, detail with images and timeline, and the
 * "fixed / not fixed" feedback. Ownership is part of every query; not found and not yours are the same 404.
 * "Not fixed" on a COMPLETED/CLOSED complaint moves it to REOPENED through {@link WorkflowActor} as the citizen, in
 * the same transaction as the feedback row (the V2/V5 triggers write history and outbox and free the plan).
 */
@Service
public class CitizenComplaints {

    /** Statuses in which the citizen may answer "fixed / not fixed". */
    public static final Set<ComplaintStatus> FEEDBACK_STATUSES = EnumSet.of(ComplaintStatus.COMPLETED, ComplaintStatus.CLOSED);
    /** Remarks of the REOPENED status change: the same for every recipient, never the citizen's own comment. */
    static final String REOPEN_REMARKS = "The citizen reported that the issue is not fixed.";

    public record Detail(ComplaintRepository.Detail complaint, List<ComplaintRepository.Image> images,
                         List<ComplaintRepository.TimelineEntry> timeline, boolean canGiveFeedback) {
    }

    public record FeedbackResult(long complaintId, String status, FeedbackRepository.Feedback feedback) {
    }

    private final ComplaintRepository complaints;
    private final FeedbackRepository feedback;
    private final WorkflowActor workflow;
    private final AuditLog audit;
    private final TransactionTemplate tx;
    private final Clock clock;

    public CitizenComplaints(ComplaintRepository complaints, FeedbackRepository feedback, WorkflowActor workflow, AuditLog audit,
                             TransactionTemplate tx, Clock clock) {
        this.complaints = complaints;
        this.feedback = feedback;
        this.workflow = workflow;
        this.audit = audit;
        this.tx = tx;
        this.clock = clock;
    }

    public PageResponse<ComplaintRepository.ListRow> list(long userId, ComplaintStatus status, Integer page, Integer size) {
        var pageable = PageResponse.pageable(page, size, null);
        String s = status == null ? null : status.name();
        long total = complaints.countOwn(userId, s);
        List<ComplaintRepository.ListRow> rows = complaints.listOwn(userId, s, pageable.getPageSize(), pageable.getOffset());
        int totalPages = (int) ((total + pageable.getPageSize() - 1) / pageable.getPageSize());
        return new PageResponse<>(rows, pageable.getPageNumber(), pageable.getPageSize(), total, totalPages);
    }

    public Detail detail(long complaintId, long userId) {
        ComplaintRepository.Detail d = complaints.findOwn(complaintId, userId).orElseThrow(CitizenComplaints::notFound);
        boolean canGiveFeedback = FEEDBACK_STATUSES.contains(ComplaintStatus.valueOf(d.status()));
        return new Detail(d, complaints.images(complaintId), complaints.timeline(complaintId), canGiveFeedback);
    }

    public FeedbackResult giveFeedback(long complaintId, long userId, FeedbackRepository.Feedback answer, String ip, String requestId) {
        return tx.execute(txStatus -> {
            ComplaintStatus current = ComplaintStatus.valueOf(complaints.lockOwnStatus(complaintId, userId)
                    .orElseThrow(CitizenComplaints::notFound));
            if (!FEEDBACK_STATUSES.contains(current)) {
                throw new ApiException(ErrorCode.FEEDBACK_NOT_ALLOWED, "Feedback is possible once the work is completed.");
            }
            Optional<FeedbackRepository.Feedback> previous = feedback.find(complaintId, userId);
            feedback.upsert(complaintId, userId, answer, clock.instant());
            audit.userAction(userId, "complaint", complaintId, previous.isPresent() ? "FEEDBACK_UPDATED" : "FEEDBACK_GIVEN",
                    previous.map(CitizenComplaints::values).orElse(null), values(answer), ip, requestId);
            ComplaintStatus after = current;
            if (!answer.isResolved()) {
                workflow.changeStatus(complaintId, ComplaintStatus.REOPENED, Actor.user(userId, ActorRole.CITIZEN), REOPEN_REMARKS);
                after = ComplaintStatus.REOPENED;
            }
            return new FeedbackResult(complaintId, after.name(), answer);
        });
    }

    private static Map<String, Object> values(FeedbackRepository.Feedback f) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("isResolved", f.isResolved());
        m.put("rating", f.rating());
        m.put("comment", f.comment());
        return m;
    }

    private static ApiException notFound() {
        return new ApiException(ErrorCode.NOT_FOUND, "Not found.");
    }
}
