package com.civicbrain.users.repo;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import com.civicbrain.common.Db;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.model.UserAccount;

/**
 * {@code users} through {@link JdbcClient} (explicit SQL, parameters only). Every timestamp comes from the
 * application {@code Clock}, so token checks never compare the database clock with the JVM clock.
 */
@Repository
public class UserRepository {

    private static final String COLUMNS = """
            user_id, full_name, email, phone, password_hash, role, is_active, email_verified_at, whatsapp_opt_in,
            email_opt_in, preferred_language, failed_login_count, locked_until, must_change_password, totp_enabled,
            token_valid_after""";

    /** Values of a new account; {@code tokenValidAfter} is a whole second (see AccessTokens). */
    public record NewUser(String fullName, String email, String phone, String passwordHash, Role role,
                          Instant emailVerifiedAt, boolean whatsappOptIn, boolean mustChangePassword,
                          Long createdByUserId, Instant now) {
    }

    /** Active flag and revocation time of one user, read for every bearer token. */
    public record TokenState(boolean active, Instant tokenValidAfter) {
    }

    private final JdbcClient jdbc;

    public UserRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<UserAccount> findById(long id) {
        return jdbc.sql("SELECT " + COLUMNS + " FROM users WHERE user_id = :id").param("id", id)
                .query(UserRepository::map).optional();
    }

    public Optional<UserAccount> findByEmail(String email) {
        return jdbc.sql("SELECT " + COLUMNS + " FROM users WHERE lower(email) = lower(:email)").param("email", email)
                .query(UserRepository::map).optional();
    }

    public Optional<UserAccount> findByPhone(String phone) {
        return jdbc.sql("SELECT " + COLUMNS + " FROM users WHERE phone = :phone").param("phone", phone)
                .query(UserRepository::map).optional();
    }

    /** Accounts that already use this e-mail or phone (0, 1 or 2 rows). */
    public List<UserAccount> findByEmailOrPhone(String email, String phone) {
        return jdbc.sql("SELECT " + COLUMNS + " FROM users WHERE lower(email) = lower(:email) OR phone = :phone ORDER BY user_id")
                .param("email", email).param("phone", phone)
                .query(UserRepository::map).list();
    }

    public Optional<TokenState> tokenState(long id) {
        return jdbc.sql("SELECT is_active, token_valid_after FROM users WHERE user_id = :id").param("id", id)
                .query((rs, n) -> new TokenState(rs.getBoolean("is_active"), Db.instant(rs, "token_valid_after")))
                .optional();
    }

    public long countByRole(Role role) {
        return jdbc.sql("SELECT count(*) FROM users WHERE role = :role").param("role", role.name())
                .query(Long.class).single();
    }

    public long insert(NewUser u) {
        return jdbc.sql("""
                INSERT INTO users (full_name, email, phone, password_hash, role, email_verified_at, whatsapp_opt_in,
                                   must_change_password, created_by_user_id, password_changed_at, token_valid_after,
                                   created_at, updated_at)
                VALUES (:fullName, :email, :phone, :hash, :role, :verified, :whatsapp, :mustChange, :createdBy, :now,
                        :tokenValidAfter, :now, :now)
                RETURNING user_id""")
                .param("fullName", u.fullName()).param("email", u.email()).param("phone", u.phone())
                .param("hash", u.passwordHash()).param("role", u.role().name())
                .param("verified", Db.ts(u.emailVerifiedAt())).param("whatsapp", u.whatsappOptIn())
                .param("mustChange", u.mustChangePassword()).param("createdBy", u.createdByUserId())
                .param("now", Db.ts(u.now())).param("tokenValidAfter", Db.ts(u.now().truncatedTo(ChronoUnit.SECONDS)))
                .query(Long.class).single();
    }

    /**
     * One more failed login; the {@code maxFailures}-th sets {@code locked_until} and starts the count again.
     * Returns true when this failure locked the account.
     */
    public boolean recordFailedLogin(long id, int maxFailures, Instant lockUntil) {
        return jdbc.sql("""
                WITH old AS (SELECT failed_login_count FROM users WHERE user_id = :id FOR UPDATE)
                UPDATE users u
                   SET locked_until = CASE WHEN old.failed_login_count + 1 >= :max THEN :lockUntil ELSE u.locked_until END,
                       failed_login_count = CASE WHEN old.failed_login_count + 1 >= :max THEN 0 ELSE old.failed_login_count + 1 END
                  FROM old
                 WHERE u.user_id = :id
                RETURNING old.failed_login_count + 1 >= :max AS locked""")
                .param("max", maxFailures).param("lockUntil", Db.ts(lockUntil)).param("id", id)
                .query(Boolean.class).optional().orElse(false);
    }

    public void recordLoginSuccess(long id, Instant now) {
        jdbc.sql("UPDATE users SET failed_login_count = 0, locked_until = NULL, last_login_at = :now WHERE user_id = :id")
                .param("now", Db.ts(now)).param("id", id).update();
    }

    public void markEmailVerified(long id, Instant now) {
        jdbc.sql("UPDATE users SET email_verified_at = COALESCE(email_verified_at, :now) WHERE user_id = :id")
                .param("now", Db.ts(now)).param("id", id).update();
    }

    public void updatePassword(long id, String hash, Instant now) {
        jdbc.sql("""
                UPDATE users SET password_hash = :hash, password_changed_at = :now, must_change_password = false,
                                 failed_login_count = 0, locked_until = NULL
                 WHERE user_id = :id""")
                .param("hash", hash).param("now", Db.ts(now)).param("id", id).update();
    }

    /**
     * Revokes every access token issued so far (logout-all, password change, role change, disable): the new
     * {@code token_valid_after} is a whole second later than both "now" and the previous value, so it is after
     * every {@code iat} AccessTokens has issued (iat = max(now, ceil(old value)), whole seconds).
     */
    public void revokeAccessTokens(long id, Instant now) {
        jdbc.sql("""
                UPDATE users
                   SET token_valid_after = greatest(:now, date_trunc('second', token_valid_after) + interval '1 second')
                                           + interval '1 second'
                 WHERE user_id = :id""")
                .param("now", Db.ts(now.truncatedTo(ChronoUnit.SECONDS))).param("id", id).update();
    }

    public void updateProfile(long id, String fullName, String preferredLanguage, boolean emailOptIn, boolean whatsappOptIn) {
        jdbc.sql("""
                UPDATE users SET full_name = :fullName, preferred_language = :language, email_opt_in = :emailOptIn,
                                 whatsapp_opt_in = :whatsappOptIn
                 WHERE user_id = :id""")
                .param("fullName", fullName).param("language", preferredLanguage).param("emailOptIn", emailOptIn)
                .param("whatsappOptIn", whatsappOptIn).param("id", id).update();
    }

    public void updateWhatsappOptIn(long id, boolean optIn) {
        jdbc.sql("UPDATE users SET whatsapp_opt_in = :optIn WHERE user_id = :id").param("optIn", optIn).param("id", id).update();
    }

    private static UserAccount map(ResultSet rs, int row) throws SQLException {
        return new UserAccount(
                rs.getLong("user_id"),
                rs.getString("full_name"),
                rs.getString("email"),
                rs.getString("phone"),
                rs.getString("password_hash"),
                Role.valueOf(rs.getString("role")),
                rs.getBoolean("is_active"),
                Db.instant(rs, "email_verified_at"),
                rs.getBoolean("whatsapp_opt_in"),
                rs.getBoolean("email_opt_in"),
                rs.getString("preferred_language"),
                rs.getInt("failed_login_count"),
                Db.instant(rs, "locked_until"),
                rs.getBoolean("must_change_password"),
                rs.getBoolean("totp_enabled"),
                Db.instant(rs, "token_valid_after"));
    }
}
