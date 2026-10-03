package com.civicbrain.unit.support;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.ActiveProfiles;

import com.civicbrain.common.ProblemWriter;
import com.civicbrain.config.SecurityConfig;
import com.civicbrain.config.SecurityProblemHandler;

/**
 * MVC slice without a database: the real security chain, request-id filter and error advice in front of
 * {@link TestController}. Runs in surefire (no Docker).
 */
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@WebMvcTest(controllers = TestController.class)
@ActiveProfiles("test")
@Import({SecurityConfig.class, SecurityProblemHandler.class, ProblemWriter.class, TestController.class})
public @interface WebSliceTest {
}
