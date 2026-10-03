package com.civicbrain.config;

import java.time.Clock;
import java.time.Duration;
import java.util.List;
import java.util.Objects;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.jose.jws.MacAlgorithm;
import org.springframework.security.oauth2.jwt.JwtClaimNames;
import org.springframework.security.oauth2.jwt.JwtClaimValidator;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtIssuerValidator;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

import com.civicbrain.auth.service.AccessTokens;
import com.civicbrain.auth.service.TokenRevocationValidator;
import com.nimbusds.jose.JOSEObjectType;
import com.nimbusds.jose.jwk.source.ImmutableSecret;
import com.nimbusds.jose.proc.DefaultJOSEObjectTypeVerifier;

/**
 * HS256 access tokens with {@code JWT_SECRET} (docs/07_SECURITY.md §1). The decoder accepts only alg HS256 and
 * {@code typ=at+jwt}, and validates {@code exp}/{@code nbf} (60 s skew, application clock), {@code iss}, {@code aud},
 * a present {@code iat} and {@code iat >= users.token_valid_after} ({@link TokenRevocationValidator}).
 */
@Configuration(proxyBeanMethods = false)
public class JwtConfig {

    @Bean
    public JwtEncoder jwtEncoder(AuthProperties auth) {
        return new NimbusJwtEncoder(new ImmutableSecret<>(key(auth)));
    }

    @Bean
    public JwtDecoder jwtDecoder(AuthProperties auth, Clock clock, TokenRevocationValidator revocation) {
        NimbusJwtDecoder decoder = NimbusJwtDecoder.withSecretKey(key(auth))
                .macAlgorithm(MacAlgorithm.HS256)
                .jwtProcessorCustomizer(p -> p.setJWSTypeVerifier(
                        new DefaultJOSEObjectTypeVerifier<>(new JOSEObjectType(AccessTokens.TYPE))))
                .build();
        JwtTimestampValidator timestamps = new JwtTimestampValidator(Duration.ofSeconds(60));
        timestamps.setClock(clock);
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(List.of(
                timestamps,
                new JwtIssuerValidator(auth.jwtIssuer()),
                new JwtClaimValidator<List<String>>(JwtClaimNames.AUD, aud -> aud != null && aud.contains(auth.jwtAudience())),
                new JwtClaimValidator<Object>(JwtClaimNames.IAT, Objects::nonNull),
                revocation)));
        return decoder;
    }

    static SecretKey key(AuthProperties auth) {
        return new SecretKeySpec(auth.jwtSecret().bytes(), "HmacSHA256");
    }
}
