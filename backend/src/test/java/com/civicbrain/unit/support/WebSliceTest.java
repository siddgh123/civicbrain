package com.civicbrain.unit.support;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.security.oauth2.jwt.BadJwtException;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.test.context.ActiveProfiles;

import com.civicbrain.common.ProblemWriter;
import com.civicbrain.common.RateLimiter;
import com.civicbrain.config.RateLimitProperties;
import com.civicbrain.config.SecurityConfig;
import com.civicbrain.config.SecurityProblemHandler;

/**
 * MVC slice without a database: the real security chain, request-id filter and error advice in front of
 * {@link TestController}. Runs in surefire (no Docker). Bearer tokens are not decodable here (no user table): the
 * slice's JwtDecoder rejects every token; signed-in cases use {@code @WithMockUser}.
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@WebMvcTest(controllers = TestController.class)
@ActiveProfiles("test")
@Import({SecurityConfig.class, SecurityProblemHandler.class, ProblemWriter.class, TestController.class,
        WebSliceTest.SliceBeans.class})
public @interface WebSliceTest {

    @TestConfiguration(proxyBeanMethods = false)
    @EnableConfigurationProperties(RateLimitProperties.class)
    @Import(RateLimiter.class)
    class SliceBeans {
        @Bean
        JwtDecoder rejectingJwtDecoder() {
            return token -> {
                throw new BadJwtException("no JWT decoding in the MVC slice");
            };
        }
    }
}
