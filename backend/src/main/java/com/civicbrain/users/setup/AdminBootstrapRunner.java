package com.civicbrain.users.setup;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import com.civicbrain.auth.service.AuthService;
import com.civicbrain.config.AuthProperties;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.model.UserAccount;
import com.civicbrain.users.repo.UserRepository;
import com.civicbrain.users.service.UserAccounts;

/**
 * Profile {@code bootstrap-admin} (non-web, started by the human-only bootstrap script, FR-04): creates the FIRST
 * ADMIN from BOOTSTRAP_ADMIN_EMAIL / NAME / PASSWORD through {@link UserAccounts} (password policy, Argon2id,
 * e-mail verified, no forced password change) and refuses when any ADMIN exists. With
 * {@code app.auth.mfa-required=false} (MVP) nothing about TOTP is set: the admin logs in with e-mail and
 * password; TOTP set-up at first login is the optional P25. The application exits afterwards (CivicbrainApplication).
 */
@Component
@Profile("bootstrap-admin")
public class AdminBootstrapRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(AdminBootstrapRunner.class);

    private final UserRepository users;
    private final UserAccounts accounts;
    private final AuthProperties auth;
    private final Environment env;

    public AdminBootstrapRunner(UserRepository users, UserAccounts accounts, AuthProperties auth, Environment env) {
        this.users = users;
        this.accounts = accounts;
        this.auth = auth;
        this.env = env;
    }

    @Override
    public void run(ApplicationArguments args) {
        bootstrap();
    }

    /** Creates the admin and returns its user id. */
    public long bootstrap() {
        String email = required("BOOTSTRAP_ADMIN_EMAIL");
        String password = required("BOOTSTRAP_ADMIN_PASSWORD");
        String name = env.getProperty("BOOTSTRAP_ADMIN_NAME", "CivicBrain Administrator");
        if (users.countByRole(Role.ADMIN) > 0) {
            throw new IllegalStateException("AdminBootstrapRunner refused: an ADMIN already exists in this database "
                    + "(the bootstrap creates only the first one; further admins are created in the app)");
        }
        UserAccount admin = accounts.create(new UserAccounts.NewAccount(name, AuthService.normalizeEmail(email), null,
                password, Role.ADMIN, true, false, null, null, null));
        log.info("ADMIN created (user id {}); TOTP at first login: {}", admin.id(),
                auth.mfaRequired() ? "required (P25)" : "no (app.auth.mfa-required=false)");
        return admin.id();
    }

    private String required(String key) {
        String value = env.getProperty(key);
        if (value == null || value.isBlank()) {
            throw new IllegalStateException(key + " is missing - run the bootstrap script, which sets it");
        }
        return value;
    }
}
