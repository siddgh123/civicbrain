package com.civicbrain.auth.service;

import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Component;

import com.civicbrain.config.AppProperties;

/**
 * The auth e-mails, sent synchronously with JavaMailSender (docs/07_SECURITY.md §1) - never through
 * {@code notification_outbox}/{@code notifications}, so the plain code is never stored. The code appears exactly
 * once in the text and nowhere in the subject. Nothing of the message is logged. Throws
 * {@link org.springframework.mail.MailException} on SMTP problems (10 s timeouts, application.yml).
 */
@Component
public class AuthMailer {

    private final JavaMailSender mail;
    private final AppProperties app;

    public AuthMailer(JavaMailSender mail, AppProperties app) {
        this.mail = mail;
        this.app = app;
    }

    public void sendCode(String to, String code) {
        send(to, "Your CivicBrain verification code", """
                Your CivicBrain verification code is %s.

                It is valid for 10 minutes and works once. Never share it - TDMC staff will never ask for it.
                If you did not ask for this code, you can ignore this e-mail.

                CivicBrain - Talegaon Dabhade Municipal Council (prototype)
                """.formatted(code));
    }

    /** FR-03: the code for POST /auth/password/reset. */
    public void sendResetCode(String to, String code) {
        send(to, "Your CivicBrain password reset code", """
                Your CivicBrain password reset code is %s.

                It is valid for 10 minutes and works once. Never share it - TDMC staff will never ask for it.
                If you did not ask to reset your password, ignore this e-mail; your password stays the same.

                CivicBrain - Talegaon Dabhade Municipal Council (prototype)
                """.formatted(code));
    }

    /** To the owner of an existing account when someone registers with their e-mail or phone (04 §1). */
    public void sendRegistrationAttempt(String to) {
        send(to, "Someone tried to register with your details", """
                Someone tried to create a new CivicBrain account with your e-mail address or phone number.
                You already have an account, so nothing was created or changed.

                If this was you, log in instead: %s/login
                If it was not you, you can ignore this e-mail. Your password was not shared.

                CivicBrain - Talegaon Dabhade Municipal Council (prototype)
                """.formatted(app.baseUrl()));
    }

    private void send(String to, String subject, String text) {
        SimpleMailMessage message = new SimpleMailMessage();
        message.setFrom(app.mailFrom());
        message.setTo(to);
        message.setSubject(subject);
        message.setText(text);
        mail.send(message);
    }
}
