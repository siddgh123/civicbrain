package com.civicbrain.privacy.repo;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import com.civicbrain.common.Db;
import com.civicbrain.privacy.model.ConsentType;

/** {@code privacy_notices}, {@code user_consents} (append-only history) and the view {@code v_current_consents}. */
@Repository
public class PrivacyRepository {

    public record Notice(String version, Instant publishedAt, String summary) {
    }

    public record Consent(ConsentType type, boolean granted, String noticeVersion, Instant at) {
    }

    private final JdbcClient jdbc;

    public PrivacyRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<Notice> currentNotice() {
        return jdbc.sql("SELECT version, published_at, summary FROM privacy_notices WHERE is_current")
                .query((rs, n) -> new Notice(rs.getString("version"), Db.instant(rs, "published_at"), rs.getString("summary")))
                .optional();
    }

    public void insertConsent(long userId, ConsentType type, boolean granted, String noticeVersion, String ip, Instant now) {
        jdbc.sql("""
                INSERT INTO user_consents (user_id, consent_type, granted, notice_version, created_at, ip_address)
                VALUES (:userId, :type, :granted, :version, :now, CAST(:ip AS inet))""")
                .param("userId", userId).param("type", type.name()).param("granted", granted)
                .param("version", noticeVersion).param("now", Db.ts(now)).param("ip", Db.inet(ip))
                .update();
    }

    /** The latest decision per consent type. */
    public List<Consent> currentConsents(long userId) {
        return jdbc.sql("""
                SELECT consent_type, granted, notice_version, created_at FROM v_current_consents
                 WHERE user_id = :userId ORDER BY consent_type""")
                .param("userId", userId)
                .query((rs, n) -> new Consent(ConsentType.valueOf(rs.getString("consent_type")), rs.getBoolean("granted"),
                        rs.getString("notice_version"), Db.instant(rs, "created_at")))
                .list();
    }
}
