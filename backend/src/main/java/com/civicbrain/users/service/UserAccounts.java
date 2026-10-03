package com.civicbrain.users.service;

import java.time.Clock;
import java.time.Instant;

import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.civicbrain.auth.service.PasswordPolicy;
import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;
import com.civicbrain.privacy.model.ConsentType;
import com.civicbrain.privacy.repo.PrivacyRepository;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.model.UserAccount;
import com.civicbrain.users.repo.UserRepository;

/**
 * Creates accounts - the one way for registration, the E2E seed, the first admin and (P14) officers/contractors:
 * password policy, Argon2id hash, optional consents with the current privacy notice (FR-60). A duplicate e-mail or
 * phone raises the database's unique violation (→ 409 ALREADY_EXISTS in the error advice).
 */
@Service
public class UserAccounts {

    /** Optional consents given at registration (the privacy notice itself is always accepted then). */
    public record Consents(boolean whatsapp, boolean publicPhoto, boolean aiTraining) {
    }

    /**
     * @param consents null for accounts created by staff/scripts without a privacy-notice step
     */
    public record NewAccount(String fullName, String email, String phone, String password, Role role,
                             boolean emailVerified, boolean mustChangePassword, Long createdByUserId,
                             Consents consents, String ip) {
        @Override
        public String toString() {
            return "NewAccount[role=" + role + "]";
        }
    }

    private final UserRepository users;
    private final PrivacyRepository privacy;
    private final PasswordPolicy policy;
    private final PasswordEncoder encoder;
    private final Clock clock;

    public UserAccounts(UserRepository users, PrivacyRepository privacy, PasswordPolicy policy, PasswordEncoder encoder,
                        Clock clock) {
        this.users = users;
        this.privacy = privacy;
        this.policy = policy;
        this.encoder = encoder;
        this.clock = clock;
    }

    @Transactional
    public UserAccount create(NewAccount a) {
        policy.check("password", a.password(), a.email(), a.fullName());
        String hash = encoder.encode(a.password());
        Instant now = clock.instant();
        long id = users.insert(new UserRepository.NewUser(a.fullName().strip(), a.email(), a.phone(), hash, a.role(),
                a.emailVerified() ? now : null, a.consents() != null && a.consents().whatsapp(), a.mustChangePassword(),
                a.createdByUserId(), now));
        if (a.consents() != null) {
            String version = privacy.currentNotice()
                    .orElseThrow(() -> new ApiException(ErrorCode.INTERNAL_ERROR, "No current privacy notice."))
                    .version();
            privacy.insertConsent(id, ConsentType.PRIVACY_NOTICE, true, version, a.ip(), now);
            privacy.insertConsent(id, ConsentType.WHATSAPP_MESSAGES, a.consents().whatsapp(), version, a.ip(), now);
            privacy.insertConsent(id, ConsentType.PUBLIC_PHOTO, a.consents().publicPhoto(), version, a.ip(), now);
            privacy.insertConsent(id, ConsentType.AI_TRAINING, a.consents().aiTraining(), version, a.ip(), now);
        }
        return users.findById(id).orElseThrow();
    }
}
