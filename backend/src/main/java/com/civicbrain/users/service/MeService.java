package com.civicbrain.users.service;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.civicbrain.common.ApiException;
import com.civicbrain.common.AuditLog;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.privacy.model.ConsentType;
import com.civicbrain.privacy.repo.PrivacyRepository;
import com.civicbrain.users.model.UserAccount;
import com.civicbrain.users.repo.UserRepository;

/**
 * Own profile and consents (docs/04_API_CONTRACT.md §2, FR-60). The WhatsApp opt-in and the WHATSAPP_MESSAGES consent
 * always change together, in one transaction (02 §5 rule 5). Every change writes {@code audit_logs}.
 */
@Service
public class MeService {

    public record Profile(UserAccount user, List<PrivacyRepository.Consent> consents) {
    }

    public record ProfileChange(String fullName, String preferredLanguage, boolean emailOptIn, boolean whatsappOptIn) {
    }

    private final UserRepository users;
    private final PrivacyRepository privacy;
    private final AuditLog audit;
    private final Clock clock;

    public MeService(UserRepository users, PrivacyRepository privacy, AuditLog audit, Clock clock) {
        this.users = users;
        this.privacy = privacy;
        this.audit = audit;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public Profile profile(long userId) {
        UserAccount user = users.findById(userId).orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND, "Not found."));
        return new Profile(user, privacy.currentConsents(userId));
    }

    @Transactional
    public Profile update(long userId, ProfileChange change, String ip, String requestId) {
        UserAccount before = users.findById(userId).orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND, "Not found."));
        users.updateProfile(userId, change.fullName().strip(), change.preferredLanguage(), change.emailOptIn(),
                change.whatsappOptIn());
        if (before.whatsappOptIn() != change.whatsappOptIn()) {
            privacy.insertConsent(userId, ConsentType.WHATSAPP_MESSAGES, change.whatsappOptIn(), currentNotice(), ip, clock.instant());
        }
        audit.userAction(userId, "users", userId, "PROFILE_UPDATED",
                Map.of("fullName", before.fullName(), "preferredLanguage", before.preferredLanguage(),
                        "emailOptIn", before.emailOptIn(), "whatsappOptIn", before.whatsappOptIn()),
                Map.of("fullName", change.fullName().strip(), "preferredLanguage", change.preferredLanguage(),
                        "emailOptIn", change.emailOptIn(), "whatsappOptIn", change.whatsappOptIn()),
                ip, requestId);
        return profile(userId);
    }

    /** A new consent decision; PRIVACY_NOTICE cannot be withdrawn here (it is the basis of the account). */
    @Transactional
    public Profile consent(long userId, ConsentType type, boolean granted, String ip, String requestId) {
        if (type == ConsentType.PRIVACY_NOTICE) {
            throw ApiException.validation("consentType", "NOT_ALLOWED",
                    "the privacy notice is accepted at registration; use a privacy request to close the account");
        }
        UserAccount user = users.findById(userId).orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND, "Not found."));
        Instant now = clock.instant();
        privacy.insertConsent(userId, type, granted, currentNotice(), ip, now);
        if (type == ConsentType.WHATSAPP_MESSAGES && user.whatsappOptIn() != granted) {
            users.updateWhatsappOptIn(userId, granted);
        }
        audit.userAction(userId, "users", userId, "CONSENT_CHANGED", null,
                Map.of("consentType", type.name(), "granted", granted), ip, requestId);
        return profile(userId);
    }

    private String currentNotice() {
        return privacy.currentNotice()
                .orElseThrow(() -> new ApiException(ErrorCode.INTERNAL_ERROR, "No current privacy notice."))
                .version();
    }
}
