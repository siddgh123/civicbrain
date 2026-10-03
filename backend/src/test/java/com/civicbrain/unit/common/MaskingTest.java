package com.civicbrain.unit.common;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import com.civicbrain.auth.service.AuthService;
import com.civicbrain.common.Db;
import com.civicbrain.common.Masking;

/** Masked phones and log-safe text (docs/07_SECURITY.md §6), login identifiers, inet values. */
class MaskingTest {

    @Test
    void phonesAreMaskedToTheLastFourDigits() {
        assertThat(Masking.phone("+919876544321")).isEqualTo("+91******4321");
        assertThat(Masking.phone("9876544321")).isEqualTo("******4321");
        assertThat(Masking.phone(null)).isNull();
        assertThat(Masking.identifier("+919876544321")).isEqualTo("+91******4321");
        assertThat(Masking.identifier("a@b.in")).isEqualTo("a@b.in");
    }

    @Test
    void controlCharactersAreRemovedAndTextIsCut() {
        assertThat(Masking.logSafe("Mozilla\r\nInjected: yes", 100)).isEqualTo("Mozilla  Injected: yes");
        assertThat(Masking.logSafe("x".repeat(500), 300)).hasSize(300);
    }

    @ParameterizedTest
    @CsvSource({
            "' Asha@Example.IN ', asha@example.in",
            "+919876543210, +919876543210",
            "9876543210, +919876543210",
            "'98765 43210', +919876543210",
            "09876543210, +919876543210",
            "919876543210, +919876543210",
            "12345, 12345"})
    void loginIdentifiersAreNormalised(String input, String expected) {
        assertThat(AuthService.normalizeIdentifier(input)).isEqualTo(expected);
    }

    @Test
    void onlyAddressLikeValuesReachTheInetCast() {
        assertThat(Db.inet("127.0.0.1")).isEqualTo("127.0.0.1");
        assertThat(Db.inet("0:0:0:0:0:0:0:1")).isEqualTo("0:0:0:0:0:0:0:1");
        assertThat(Db.inet("fe80::1%eth0")).isEqualTo("fe80::1");
        assertThat(Db.inet("evil'); DROP TABLE users;--")).isNull();
        assertThat(Db.inet(null)).isNull();
    }
}
