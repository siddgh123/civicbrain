package com.civicbrain.config;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

import jakarta.validation.Constraint;
import jakarta.validation.Payload;

/**
 * The {@link Secret} is present and is base64 of {@code minBytes}..{@code maxBytes} bytes. The message must name the
 * environment variable (rule 10: fail fast with the variable's name).
 */
@Documented
@Target({ElementType.FIELD, ElementType.METHOD, ElementType.PARAMETER, ElementType.RECORD_COMPONENT})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = Base64KeyValidator.class)
public @interface Base64Key {

    String message();

    int minBytes() default 32;

    int maxBytes() default Integer.MAX_VALUE;

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};
}
