package com.civicbrain.notifications.channel;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.MailParseException;
import org.springframework.mail.MailPreparationException;
import org.springframework.mail.MailSendException;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Component;
import org.springframework.web.util.HtmlUtils;
import org.thymeleaf.ITemplateEngine;
import org.thymeleaf.context.Context;

import com.civicbrain.config.AppProperties;

import jakarta.mail.MessagingException;
import jakarta.mail.SendFailedException;
import jakarta.mail.internet.MimeMessage;

/**
 * E-mail through Spring Mail (Mailpit in dev/E2E, Gmail SMTP or Brevo for the demo; 10 s timeouts, application.yml).
 * The stored body is the HTML-escaped text of the template (TemplateRenderer HTML mode); it goes into the
 * Thymeleaf layout {@code templates/mail/layout.html} (links made clickable) and, unescaped, into the plain-text
 * part. Provider name by SMTP host (02 §5 rule 7): smtp.gmail.com → GMAIL_SMTP, Brevo → BREVO, anything else
 * (Mailpit) → INTERNAL. Nothing of the message is logged.
 */
@Component
public class EmailChannel implements NotificationChannel {

    static final String FOOTER = "CivicBrain - Talegaon Dabhade Municipal Council (prototype). This is an automatic message; please do not reply.";
    /** Our own links (APP_BASE_URL + path) never contain '&' - which also keeps escaped entities out of a link. */
    private static final Pattern URL = Pattern.compile("https?://[^\\s<>\"'&]+");

    private final JavaMailSender mail;
    private final ITemplateEngine templates;
    private final AppProperties app;
    private final String provider;

    public EmailChannel(JavaMailSender mail, ITemplateEngine templates, AppProperties app, @Value("${spring.mail.host}") String smtpHost) {
        this.mail = mail;
        this.templates = templates;
        this.app = app;
        this.provider = providerFor(smtpHost);
    }

    /** 02 §5 rule 7 for e-mail. */
    public static String providerFor(String smtpHost) {
        String host = smtpHost == null ? "" : smtpHost.strip().toLowerCase(Locale.ROOT);
        if (host.equals("smtp.gmail.com") || host.endsWith(".gmail.com")) {
            return "GMAIL_SMTP";
        }
        if (host.contains("brevo") || host.contains("sendinblue")) {
            return "BREVO";
        }
        return "INTERNAL";
    }

    @Override
    public String channel() {
        return "EMAIL";
    }

    @Override
    public String provider() {
        return provider;
    }

    @Override
    public String send(Message message) {
        try {
            MimeMessage mime = mail.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(mime, true, "UTF-8");
            helper.setFrom(app.mailFrom());
            helper.setTo(message.destination());
            helper.setSubject(message.subject().replaceAll("[\\r\\n]+", " "));
            helper.setText(plainText(message.body()), html(message.subject(), message.body()));
            mail.send(mime);
            return mime.getMessageID();
        } catch (MessagingException | MailParseException | MailPreparationException e) {
            throw new PermanentFailure("message could not be built: " + e.getClass().getSimpleName(), e);
        } catch (MailSendException e) {
            if (e.getFailedMessages().values().stream().anyMatch(SendFailedException.class::isInstance)) {
                throw new PermanentFailure("address refused by the SMTP server", e);
            }
            throw e;
        }
    }

    String html(String subject, String escapedBody) {
        Context context = new Context(Locale.ENGLISH);
        context.setVariable("subject", subject);
        context.setVariable("bodyHtml", linkify(escapedBody));
        context.setVariable("baseUrl", app.baseUrl());
        context.setVariable("footer", FOOTER);
        return templates.process("mail/layout", context);
    }

    static String plainText(String escapedBody) {
        return HtmlUtils.htmlUnescape(escapedBody) + "\n\n-- \n" + FOOTER + "\n";
    }

    /** Escaped text → the same text with every http(s) URL as a link (trailing punctuation stays text). */
    static String linkify(String escaped) {
        Matcher m = URL.matcher(escaped);
        StringBuilder out = new StringBuilder();
        while (m.find()) {
            String url = m.group();
            String tail = "";
            while (!url.isEmpty() && ".,;:!?)".indexOf(url.charAt(url.length() - 1)) >= 0) {
                tail = url.charAt(url.length() - 1) + tail;
                url = url.substring(0, url.length() - 1);
            }
            m.appendReplacement(out, Matcher.quoteReplacement("<a href=\"" + url + "\">" + url + "</a>" + tail));
        }
        m.appendTail(out);
        return out.toString();
    }
}
