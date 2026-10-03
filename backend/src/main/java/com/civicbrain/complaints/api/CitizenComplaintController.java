package com.civicbrain.complaints.api;

import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.civicbrain.auth.api.CurrentUser;
import com.civicbrain.common.ApiException;
import com.civicbrain.common.ClientIp;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.common.PageResponse;
import com.civicbrain.common.RequestIdFilter;
import com.civicbrain.common.Times;
import com.civicbrain.complaints.repo.ComplaintRepository;
import com.civicbrain.complaints.repo.FeedbackRepository;
import com.civicbrain.complaints.service.CitizenComplaints;
import com.civicbrain.complaints.service.ComplaintIntake;
import com.civicbrain.workflow.ComplaintStatus;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * {@code /api/v1/citizen} (CITIZEN, e-mail verified; docs/04 §5): capture sessions, complaint submission, own
 * complaints and feedback. Responses are citizen DTOs only (no authenticity, AI or other users' data, 07 §2).
 */
@RestController
@RequestMapping("/api/v1/citizen")
public class CitizenComplaintController {

    public record CaptureSessionResponse(UUID captureSessionId, OffsetDateTime expiresAt) {
    }

    public record SubmitResponse(long complaintId, String publicRef, String status, Integer wardNumber) {
    }

    public record ListItem(long complaintId, String publicRef, String title, String categoryName, String status, Integer wardNumber,
                           OffsetDateTime submittedAt, Long thumbnailImageId) {
    }

    public record ImageView(long imageId, String role) {
    }

    public record TimelineView(String status, OffsetDateTime at, String remarks) {
    }

    public record DetailResponse(long complaintId, String publicRef, String title, String categoryName, String status,
                                 Integer wardNumber, OffsetDateTime submittedAt, Long thumbnailImageId, Long categoryId,
                                 String description, String landmark, double latitude, double longitude, List<ImageView> images,
                                 List<TimelineView> timeline, String contractorName, LocalDate plannedDate,
                                 String mergedIntoPublicRef, boolean canGiveFeedback) {
    }

    public record FeedbackRequest(
            @NotNull Boolean isResolved,
            @Min(1) @Max(5) Integer rating,
            @Size(max = 1000) @Pattern(regexp = ComplaintData.TEXT, message = "must not contain control characters") String comment) {
    }

    public record FeedbackResponse(long complaintId, String status, boolean isResolved, Integer rating, String comment) {
    }

    private final ComplaintIntake intake;
    private final CitizenComplaints complaints;

    public CitizenComplaintController(ComplaintIntake intake, CitizenComplaints complaints) {
        this.intake = intake;
        this.complaints = complaints;
    }

    @PostMapping("/capture-sessions")
    @ResponseStatus(HttpStatus.CREATED)
    public CaptureSessionResponse captureSession(Authentication authentication, HttpServletRequest request) {
        ComplaintIntake.IssuedSession s = intake.issueCaptureSession(CurrentUser.id(authentication), client(request));
        return new CaptureSessionResponse(s.id(), Times.api(s.expiresAt()));
    }

    /**
     * Multipart {@code data} (JSON; a file part, or a plain text field) + {@code photo}. Both parts are optional for
     * Spring so that the service reports a missing one in the documented validation order.
     */
    @PostMapping(value = "/complaints", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<SubmitResponse> submit(@RequestPart(name = "data", required = false) MultipartFile dataFile,
                                                 @RequestPart(name = "photo", required = false) MultipartFile photo,
                                                 Authentication authentication, HttpServletRequest request) {
        String dataField = dataFile == null ? request.getParameter("data") : null;
        byte[] data = dataFile != null ? bytes(dataFile) : dataField == null ? null : dataField.getBytes(StandardCharsets.UTF_8);
        ComplaintIntake.Submitted s = intake.submit(CurrentUser.id(authentication), data, photo == null ? null : bytes(photo), client(request));
        return ResponseEntity.created(URI.create("/api/v1/citizen/complaints/" + s.complaintId()))
                .body(new SubmitResponse(s.complaintId(), s.publicRef(), s.status(), s.wardNumber()));
    }

    @GetMapping("/complaints")
    public PageResponse<ListItem> list(@RequestParam(required = false) Integer page, @RequestParam(required = false) Integer size,
                                       @RequestParam(required = false) ComplaintStatus status, Authentication authentication) {
        PageResponse<ComplaintRepository.ListRow> rows = complaints.list(CurrentUser.id(authentication), status, page, size);
        return new PageResponse<>(rows.items().stream().map(r -> new ListItem(r.complaintId(), r.publicRef(), r.title(), r.categoryName(),
                r.status(), r.wardNumber(), Times.api(r.submittedAt()), r.thumbnailImageId())).toList(),
                rows.page(), rows.size(), rows.totalItems(), rows.totalPages());
    }

    @GetMapping("/complaints/{id}")
    public DetailResponse detail(@PathVariable long id, Authentication authentication) {
        CitizenComplaints.Detail d = complaints.detail(id, CurrentUser.id(authentication));
        ComplaintRepository.Detail c = d.complaint();
        Long thumbnail = d.images().stream().filter(i -> "CITIZEN_EVIDENCE".equals(i.role())).map(ComplaintRepository.Image::imageId)
                .findFirst().orElse(null);
        return new DetailResponse(c.complaintId(), c.publicRef(), c.title(), c.categoryName(), c.status(), c.wardNumber(),
                Times.api(c.submittedAt()), thumbnail, c.categoryId(), c.description(), c.landmark(), c.latitude(), c.longitude(),
                d.images().stream().map(i -> new ImageView(i.imageId(), i.role())).toList(),
                d.timeline().stream().map(t -> new TimelineView(t.status(), Times.api(t.at()), t.remarks())).toList(),
                c.contractorName(), c.plannedDate(), c.mergedIntoPublicRef(), d.canGiveFeedback());
    }

    @PostMapping("/complaints/{id}/feedback")
    @ResponseStatus(HttpStatus.CREATED)
    public FeedbackResponse feedback(@PathVariable long id, @Valid @RequestBody FeedbackRequest body, Authentication authentication,
                                     HttpServletRequest request) {
        String comment = body.comment() == null || body.comment().isBlank() ? null : body.comment().strip();
        CitizenComplaints.FeedbackResult r = complaints.giveFeedback(id, CurrentUser.id(authentication),
                new FeedbackRepository.Feedback(body.isResolved(), body.rating(), comment), ClientIp.of(request),
                RequestIdFilter.currentId(request));
        return new FeedbackResponse(r.complaintId(), r.status(), r.feedback().isResolved(), r.feedback().rating(), r.feedback().comment());
    }

    private static ComplaintIntake.Client client(HttpServletRequest request) {
        return new ComplaintIntake.Client(ClientIp.of(request), request.getHeader("User-Agent"), RequestIdFilter.currentId(request));
    }

    private static byte[] bytes(MultipartFile file) {
        try {
            return file.getBytes();
        } catch (IOException e) {
            throw new ApiException(ErrorCode.MALFORMED_REQUEST, "The upload could not be read.");
        }
    }
}
