package com.civicbrain.common;

import java.net.InetAddress;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

import jakarta.servlet.http.HttpServletRequest;

/**
 * The client IP of a request - the "IP" of the per-IP rate limits (docs/04_API_CONTRACT.md §11) and of the audit rows.
 * Only a loopback peer is trusted to name the client: on this laptop that is the Vite proxy or the Cloudflare tunnel,
 * which append the real client to {@code X-Forwarded-For}. The header is then read from the RIGHT: loopback hops are
 * skipped and the first other address is the client. Everything left of it can be written by the client itself and is
 * never used; an entry that is not an IP literal ends the walk (the peer is used). Any other peer is the client and
 * its header is ignored. Tomcat's own header processing is off ({@code server.forward-headers-strategy: none}), so
 * this is the only place that reads the header. Literals only ({@link InetAddress#ofLiteral}) - never a DNS lookup.
 */
public final class ClientIp {

    public static final String HEADER = "X-Forwarded-For";

    private static final Pattern DOTTED_QUAD = Pattern.compile("\\d{1,3}(\\.\\d{1,3}){3}");

    /** A valid IP literal (normalised text) and whether it is a loopback address. */
    private record Literal(String text, boolean loopback) {
    }

    private ClientIp() {
    }

    public static String of(HttpServletRequest request) {
        return resolve(request.getRemoteAddr(), Collections.list(request.getHeaders(HEADER)));
    }

    /**
     * @param peer         the TCP peer ({@code getRemoteAddr()})
     * @param forwardedFor the X-Forwarded-For header lines in arrival order (may be empty)
     */
    public static String resolve(String peer, List<String> forwardedFor) {
        Literal direct = peer == null ? null : literal(peer);
        if (direct == null || !direct.loopback() || forwardedFor == null) {
            return peer;
        }
        List<String> hops = new ArrayList<>();
        for (String line : forwardedFor) {
            for (String hop : line.split(",")) {
                if (!hop.isBlank()) {
                    hops.add(hop.strip());
                }
            }
        }
        for (int i = hops.size() - 1; i >= 0; i--) {
            Literal hop = literal(hops.get(i));
            if (hop == null) {
                return peer;
            }
            if (!hop.loopback()) {
                return hop.text();
            }
        }
        return peer;
    }

    /** IPv4 dotted quad or IPv6 (brackets removed, lower case); null when the text is not an IP literal. */
    private static Literal literal(String text) {
        String s = text.strip().toLowerCase(Locale.ROOT);
        if (s.startsWith("[") && s.endsWith("]")) {
            s = s.substring(1, s.length() - 1);
        }
        if (!DOTTED_QUAD.matcher(s).matches() && s.indexOf(':') < 0) {
            return null;   // no hostnames, no short IPv4 forms
        }
        try {
            return new Literal(s, InetAddress.ofLiteral(s).isLoopbackAddress());
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
