package com.civicbrain.users.setup;

import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import com.civicbrain.auth.service.AuthService;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.repo.UserRepository;
import com.civicbrain.users.service.UserAccounts;

/**
 * Profile {@code e2e-seed} (non-web, run by seed-e2e.ps1, docs/08_TEST_PLAN.md §2): creates the fixed E2E accounts
 * from the {@code E2E_*} variables (.env.test) through {@link UserAccounts} - real Argon2id hashes, verified e-mail,
 * no forced password change - and exits. Refuses unless the JDBC database name ends with {@code _e2e}. Idempotent: an
 * existing e-mail is skipped. Now: admin + citizen 1/2 (+ ui.admin / ui.citizen when seed-e2e.ps1 set their
 * variables); officers, contractors and staff follow in P14. TOTP stays off while {@code mfa-required=false}.
 */
@Component
@Profile("e2e-seed")
public class E2eSeedRunner implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(E2eSeedRunner.class);

    /** One fixed account: variable prefix, display name, role, and whether the phone variable is required. */
    record Spec(String prefix, String fullName, Role role, boolean phone, boolean optional) {
    }

    static final List<Spec> SPECS = List.of(
            new Spec("E2E_ADMIN", "E2E Admin", Role.ADMIN, false, false),
            new Spec("E2E_CITIZEN1", "E2E Citizen One", Role.CITIZEN, true, false),
            new Spec("E2E_CITIZEN2", "E2E Citizen Two", Role.CITIZEN, true, false),
            new Spec("E2E_UI_ADMIN", "UI Admin", Role.ADMIN, false, true),
            new Spec("E2E_UI_CITIZEN", "UI Citizen", Role.CITIZEN, false, true));

    private final JdbcClient jdbc;
    private final UserRepository users;
    private final UserAccounts accounts;
    private final Environment env;

    public E2eSeedRunner(JdbcClient jdbc, UserRepository users, UserAccounts accounts, Environment env) {
        this.jdbc = jdbc;
        this.users = users;
        this.accounts = accounts;
        this.env = env;
    }

    @Override
    public void run(ApplicationArguments args) {
        seed();
    }

    /** Returns the number of accounts created now. */
    public int seed() {
        String database = jdbc.sql("SELECT current_database()").query(String.class).single();
        if (!database.endsWith("_e2e")) {
            throw new IllegalStateException("E2eSeedRunner refused: database '" + database
                    + "' is not an E2E database (its name must end with _e2e)");
        }
        List<UserAccounts.NewAccount> wanted = new ArrayList<>();
        for (Spec spec : SPECS) {
            String email = env.getProperty(spec.prefix() + "_EMAIL");
            String password = env.getProperty(spec.prefix() + "_PASSWORD");
            if (spec.optional() && (blank(email) || blank(password))) {
                continue;
            }
            String phone = spec.phone() ? required(spec.prefix() + "_PHONE") : null;
            wanted.add(new UserAccounts.NewAccount(spec.fullName(), AuthService.normalizeEmail(required(spec.prefix() + "_EMAIL")),
                    phone, required(spec.prefix() + "_PASSWORD"), spec.role(), true, false, null,
                    spec.role() == Role.CITIZEN ? new UserAccounts.Consents(false, false, false) : null, null));
        }
        int created = 0;
        for (UserAccounts.NewAccount account : wanted) {
            if (users.findByEmail(account.email()).isPresent()) {
                continue;
            }
            accounts.create(account);
            created++;
        }
        log.info("E2E seed on {}: {} accounts created, {} already present", database, created, wanted.size() - created);
        return created;
    }

    private String required(String key) {
        String value = env.getProperty(key);
        if (blank(value)) {
            throw new IllegalStateException(key + " is missing - seed-e2e.ps1 loads it from .env.test");
        }
        return value;
    }

    private static boolean blank(String s) {
        return s == null || s.isBlank();
    }
}
