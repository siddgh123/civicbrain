package com.civicbrain.notifications.service;

import java.time.Instant;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

import com.civicbrain.common.Times;

/** Dates in messages as the UI shows them (docs/05_UI_SPEC.md §2): Asia/Kolkata, "5 Oct 2026, 8:20 am", "7 Oct 2026". */
public final class MessageFormats {

    private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("d MMM yyyy", Locale.ENGLISH);
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("h:mm", Locale.ENGLISH);

    private MessageFormats() {
    }

    public static String dateTime(Instant instant) {
        var local = instant.atZone(Times.KOLKATA);
        return DATE.format(local) + ", " + TIME.format(local) + (local.getHour() < 12 ? " am" : " pm");
    }

    public static String date(LocalDate date) {
        return DATE.format(date);
    }
}
