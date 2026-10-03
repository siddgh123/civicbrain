package com.civicbrain.config;

import java.util.Map;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.argon2.Argon2PasswordEncoder;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.DelegatingPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

/**
 * docs/07_SECURITY.md §1: Argon2id (salt 16, hash 32, parallelism 1, 19 MiB, 2 iterations) for new hashes, bcrypt(12)
 * still accepted. A stored value without a known {@code {id}} prefix (old seed data) never matches - it cannot log in.
 */
@Configuration(proxyBeanMethods = false)
public class PasswordConfig {

    static final String ARGON2 = "argon2";

    @Bean
    PasswordEncoder passwordEncoder() {
        DelegatingPasswordEncoder encoder = new DelegatingPasswordEncoder(ARGON2, Map.of(
                ARGON2, new Argon2PasswordEncoder(16, 32, 1, 19456, 2),
                "bcrypt", new BCryptPasswordEncoder(12)));
        encoder.setDefaultPasswordEncoderForMatches(new NeverMatches());
        return encoder;
    }

    private static final class NeverMatches implements PasswordEncoder {
        @Override
        public String encode(CharSequence rawPassword) {
            throw new UnsupportedOperationException("never used for new hashes");
        }

        @Override
        public boolean matches(CharSequence rawPassword, String encodedPassword) {
            return false;
        }
    }
}
