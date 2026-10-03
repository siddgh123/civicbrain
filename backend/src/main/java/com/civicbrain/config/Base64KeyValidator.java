package com.civicbrain.config;

import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;

/** Checks {@link Base64Key}: present, valid base64, decoded length in range. Never reads the value into a message. */
public class Base64KeyValidator implements ConstraintValidator<Base64Key, Secret> {

    private int minBytes;
    private int maxBytes;

    @Override
    public void initialize(Base64Key annotation) {
        this.minBytes = annotation.minBytes();
        this.maxBytes = annotation.maxBytes();
    }

    @Override
    public boolean isValid(Secret secret, ConstraintValidatorContext context) {
        if (secret == null || secret.isBlank()) {
            return false;
        }
        try {
            int length = secret.bytes().length;
            return length >= minBytes && length <= maxBytes;
        } catch (IllegalArgumentException notBase64) {
            return false;
        }
    }
}
