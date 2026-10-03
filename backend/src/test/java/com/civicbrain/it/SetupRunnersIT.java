package com.civicbrain.it;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mock.env.MockEnvironment;
import org.springframework.transaction.support.TransactionTemplate;

import com.civicbrain.config.AuthProperties;
import com.civicbrain.it.support.AuthItSupport;
import com.civicbrain.it.support.IntegrationTest;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.repo.UserRepository;
import com.civicbrain.users.setup.AdminBootstrapRunner;
import com.civicbrain.users.setup.E2eSeedRunner;

/** E2eSeedRunner's database guard and AdminBootstrapRunner (prompt P06 build 8, rule 10, docs/08 §2). */
@IntegrationTest
class SetupRunnersIT extends AuthItSupport {

    @Autowired
    UserRepository users;
    @Autowired
    AuthProperties auth;
    @Autowired
    TransactionTemplate tx;

    @Test
    void e2eSeedRunnerRefusesADatabaseWhoseNameDoesNotEndWithE2e() {
        MockEnvironment env = new MockEnvironment()
                .withProperty("E2E_ADMIN_EMAIL", uniqueEmail("seed-admin")).withProperty("E2E_ADMIN_PASSWORD", PASSWORD);
        E2eSeedRunner runner = new E2eSeedRunner(jdbc, users, accounts, env);
        String database = jdbc.sql("SELECT current_database()").query(String.class).single();
        assertThat(database).doesNotEndWith("_e2e");

        assertThatThrownBy(runner::seed)
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("refused")
                .hasMessageContaining(database);
        assertThat(jdbc.sql("SELECT count(*) FROM users WHERE email = :e").param("e", env.getProperty("E2E_ADMIN_EMAIL"))
                .query(Long.class).single()).isZero();
    }

    @Test
    void adminBootstrapRefusesWhenAnAdminExists() {
        user(Role.ADMIN, uniqueEmail("existing-admin"), false);
        AdminBootstrapRunner runner = new AdminBootstrapRunner(users, accounts, auth, bootstrapEnv(uniqueEmail("second-admin")));
        assertThatThrownBy(runner::bootstrap).isInstanceOf(IllegalStateException.class).hasMessageContaining("refused");
    }

    @Test
    void adminBootstrapCreatesAVerifiedAdminWithoutTotpOrForcedChange() {
        String email = uniqueEmail("first-admin");
        tx.executeWithoutResult(status -> {
            // pretend this is an empty database: demote existing admins inside this rolled-back transaction
            jdbc.sql("UPDATE users SET role = 'CITIZEN' WHERE role = 'ADMIN'").update();
            long id = new AdminBootstrapRunner(users, accounts, auth, bootstrapEnv(email)).bootstrap();
            Map<String, Object> row = jdbc.sql("""
                    SELECT role, email, email_verified_at IS NOT NULL AS verified, must_change_password, totp_enabled,
                           totp_secret_enc IS NULL AS no_secret, password_hash LIKE '{argon2}$argon2id$%' AS argon2
                      FROM users WHERE user_id = :id""").param("id", id).query().singleRow();
            assertThat(row).containsEntry("role", "ADMIN").containsEntry("email", email)
                    .containsEntry("verified", true).containsEntry("must_change_password", false)
                    .containsEntry("totp_enabled", false).containsEntry("no_secret", true).containsEntry("argon2", true);
            status.setRollbackOnly();
        });
        assertThat(jdbc.sql("SELECT count(*) FROM users WHERE email = :e").param("e", email).query(Long.class).single()).isZero();
    }

    private static MockEnvironment bootstrapEnv(String email) {
        return new MockEnvironment().withProperty("BOOTSTRAP_ADMIN_EMAIL", email)
                .withProperty("BOOTSTRAP_ADMIN_NAME", "Bootstrap Admin").withProperty("BOOTSTRAP_ADMIN_PASSWORD", PASSWORD);
    }
}
