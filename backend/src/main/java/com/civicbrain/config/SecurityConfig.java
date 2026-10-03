package com.civicbrain.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter;
import org.springframework.security.oauth2.server.resource.web.authentication.BearerTokenAuthenticationFilter;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter.ReferrerPolicy;
import org.springframework.security.web.header.writers.StaticHeadersWriter;
import org.springframework.security.web.header.writers.CrossOriginOpenerPolicyHeaderWriter.CrossOriginOpenerPolicy;

import com.civicbrain.auth.service.AccessTokens;
import com.civicbrain.common.ProblemWriter;
import com.civicbrain.common.RateLimiter;

import jakarta.servlet.DispatcherType;

/**
 * Deny by default (docs/07_SECURITY.md §2) with the headers of §4. Bearer JWTs (JwtConfig) give the role from the
 * {@code roles} claim; role areas follow 07 §2, everything else is denied. CSRF protection is off because the API
 * uses bearer tokens; the two cookie endpoints (/auth/refresh, /auth/logout) check {@code X-CB-CSRF} and the Origin
 * themselves (RefreshCookie). After the bearer token: PASSWORD_CHANGE_REQUIRED and the per-user rate limit.
 * Only in the web application (the one-shot profiles e2e-seed and bootstrap-admin run without a web server).
 */
@Configuration(proxyBeanMethods = false)
@ConditionalOnWebApplication(type = ConditionalOnWebApplication.Type.SERVLET)
@EnableMethodSecurity
public class SecurityConfig {

    static final String CONTENT_SECURITY_POLICY = "default-src 'self'; img-src 'self' blob: data: https://tile.openstreetmap.org; "
            + "connect-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; "
            + "base-uri 'none'; frame-ancestors 'none'; form-action 'self'";
    static final String PERMISSIONS_POLICY = "camera=(self), geolocation=(self), microphone=(), payment=()";

    @Bean
    SecurityFilterChain apiSecurity(HttpSecurity http, SecurityProblemHandler problems, ProblemWriter writer,
                                    RateLimiter limits, Environment environment) throws Exception {
        boolean apiDocs = environment.matchesProfiles("dev | test");
        http.csrf(AbstractHttpConfigurer::disable)
                .httpBasic(AbstractHttpConfigurer::disable)
                .formLogin(AbstractHttpConfigurer::disable)
                .logout(AbstractHttpConfigurer::disable)
                .requestCache(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .exceptionHandling(e -> e.authenticationEntryPoint(problems).accessDeniedHandler(problems))
                .oauth2ResourceServer(o -> o
                        .jwt(j -> j.jwtAuthenticationConverter(jwtAuthenticationConverter()))
                        .authenticationEntryPoint(problems)
                        .accessDeniedHandler(problems))
                .addFilterAfter(new PasswordChangeRequiredFilter(writer), BearerTokenAuthenticationFilter.class)
                .addFilterAfter(new UserRateLimitFilter(limits, writer), PasswordChangeRequiredFilter.class)
                .headers(h -> h
                        .contentSecurityPolicy(csp -> csp.policyDirectives(CONTENT_SECURITY_POLICY))
                        .referrerPolicy(r -> r.policy(ReferrerPolicy.STRICT_ORIGIN_WHEN_CROSS_ORIGIN))
                        .crossOriginOpenerPolicy(c -> c.policy(CrossOriginOpenerPolicy.SAME_ORIGIN))
                        .addHeaderWriter(new StaticHeadersWriter("Permissions-Policy", PERMISSIONS_POLICY))
                        .frameOptions(f -> f.deny())
                        .httpStrictTransportSecurity(hsts -> hsts.maxAgeInSeconds(31_536_000).includeSubDomains(false)))
                .authorizeHttpRequests(a -> {
                    a.dispatcherTypeMatchers(DispatcherType.ERROR).permitAll();
                    a.requestMatchers("/actuator/health").permitAll();
                    // bearer-authenticated despite the /auth prefix (04 §1, 07 §2) - before the /auth/** permit
                    a.requestMatchers(HttpMethod.POST, "/api/v1/auth/logout-all", "/api/v1/auth/password/change").authenticated();
                    a.requestMatchers("/api/v1/auth/**", "/api/v1/public/**", "/api/v1/webhooks/**").permitAll();
                    a.requestMatchers(HttpMethod.POST, "/api/v1/client-errors").permitAll();
                    if (apiDocs) {
                        a.requestMatchers("/v3/api-docs", "/v3/api-docs/**").permitAll();
                    }
                    a.requestMatchers("/api/v1/citizen/**").hasRole("CITIZEN");
                    a.requestMatchers("/api/v1/officer/**").hasAnyRole("OFFICER", "ADMIN");
                    a.requestMatchers("/api/v1/contractor/**").hasAnyRole("CONTRACTOR", "CONTRACTOR_STAFF");
                    a.requestMatchers("/api/v1/admin/**").hasRole("ADMIN");
                    a.requestMatchers("/api/v1/me", "/api/v1/me/**", "/api/v1/files/**").authenticated();
                    a.anyRequest().denyAll();
                });
        return http.build();
    }

    /** {@code roles: ["CITIZEN"]} → authority ROLE_CITIZEN; the principal name is the user id ({@code sub}). */
    static JwtAuthenticationConverter jwtAuthenticationConverter() {
        JwtGrantedAuthoritiesConverter authorities = new JwtGrantedAuthoritiesConverter();
        authorities.setAuthoritiesClaimName(AccessTokens.ROLES);
        authorities.setAuthorityPrefix("ROLE_");
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(authorities);
        return converter;
    }
}
