package com.civicbrain.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.Environment;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.header.writers.ReferrerPolicyHeaderWriter.ReferrerPolicy;
import org.springframework.security.web.header.writers.StaticHeadersWriter;
import org.springframework.security.web.header.writers.CrossOriginOpenerPolicyHeaderWriter.CrossOriginOpenerPolicy;

import jakarta.servlet.DispatcherType;

/**
 * Deny by default (docs/07_SECURITY.md §2) with the headers of §4. Skeleton: only health, auth and public paths are
 * open; the role areas (/citizen, /officer, /contractor, /admin, /me, /files) and the JWT resource server come with
 * P06. CSRF protection is off because the API uses bearer tokens; the two cookie endpoints (/auth/refresh,
 * /auth/logout) check the X-CB-CSRF header and the Origin themselves (P06).
 */
@Configuration(proxyBeanMethods = false)
@EnableMethodSecurity
public class SecurityConfig {

    static final String CONTENT_SECURITY_POLICY = "default-src 'self'; img-src 'self' blob: data: https://tile.openstreetmap.org; "
            + "connect-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; "
            + "base-uri 'none'; frame-ancestors 'none'; form-action 'self'";
    static final String PERMISSIONS_POLICY = "camera=(self), geolocation=(self), microphone=(), payment=()";

    @Bean
    SecurityFilterChain apiSecurity(HttpSecurity http, SecurityProblemHandler problems, Environment environment) throws Exception {
        boolean apiDocs = environment.matchesProfiles("dev | test");
        http.csrf(AbstractHttpConfigurer::disable)
                .httpBasic(AbstractHttpConfigurer::disable)
                .formLogin(AbstractHttpConfigurer::disable)
                .logout(AbstractHttpConfigurer::disable)
                .requestCache(AbstractHttpConfigurer::disable)
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .exceptionHandling(e -> e.authenticationEntryPoint(problems).accessDeniedHandler(problems))
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
                    a.requestMatchers("/api/v1/auth/**", "/api/v1/public/**").permitAll();
                    if (apiDocs) {
                        a.requestMatchers("/v3/api-docs", "/v3/api-docs/**").permitAll();
                    }
                    a.anyRequest().denyAll();
                });
        return http.build();
    }
}
