package com.civicbrain.unit.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import com.civicbrain.auth.service.PasswordPolicy;
import com.civicbrain.common.ApiException;
import com.civicbrain.common.ErrorCode;

/** docs/07_SECURITY.md §1 / FR-01: 12-128 characters, blocklist, not the user's e-mail or name. */
class PasswordPolicyTest {

    private final PasswordPolicy policy = new PasswordPolicy();

    @ParameterizedTest
    @ValueSource(strings = {"Correct-Horse-Battery-42", "abcdefghijkx", "मेरा पासवर्ड बहुत लंबा है", "Smoke-AbCdEf123456"})
    void acceptsLongUncommonPasswords(String password) {
        policy.check("password", password, "smoke-1a2b3c4d@smoke.local", "Smoke Test 1a2b3c4d");
    }

    @Test
    void lengthIsCountedInCodePointsFrom12To128() {
        assertThat(refused("x1y2z3w4v5u")).isTrue();                 // 11
        assertThat(refused("x1y2z3w4v5u6")).isFalse();               // 12
        assertThat(refused("😀😀😀😀😀😀😀😀😀😀😀a")).isFalse();          // 12 code points (23 chars)
        assertThat(refused("a".repeat(5) + "b".repeat(123))).isFalse(); // 128
        assertThat(refused("a".repeat(5) + "b".repeat(124))).isTrue();  // 129
    }

    @ParameterizedTest
    @ValueSource(strings = {"password1234", "Password2026!!", "QWERTYUIOP12", "123456789012", "Talegaon@2026", "aaaaaaaaaaaaaaa"})
    void refusesCommonPasswords(String password) {
        assertThat(refused(password)).isTrue();
    }

    @Test
    void refusesTheEmailOrTheName() {
        assertThatThrownBy(() -> policy.check("newPassword", "ravi.patil@example.in!", "ravi.patil@example.in", "R P"))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.code()).isEqualTo(ErrorCode.PASSWORD_POLICY);
                    assertThat(e.status()).isEqualTo(422);
                    assertThat(e.fieldErrors().getFirst().field()).isEqualTo("newPassword");
                });
        assertThat(refused("my-RaviPatil-pw-2026", "rp@example.in", "Ravi Patil")).isTrue();
    }

    private boolean refused(String password) {
        return refused(password, "someone@example.in", "Some One");
    }

    private boolean refused(String password, String email, String name) {
        try {
            policy.check("password", password, email, name);
            return false;
        } catch (ApiException e) {
            return true;
        }
    }
}
