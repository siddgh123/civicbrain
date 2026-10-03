package com.civicbrain.it.support;

import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Supplier;

import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Reads the test Mailpit through its HTTP API (search by recipient, message text). */
public class MailpitClient {

    /** One received message: subject and plain-text body. */
    public record Mail(String id, String subject, String text) {
    }

    private final Supplier<String> baseUrl;
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    private final JsonMapper json = JsonMapper.builder().build();

    public MailpitClient(Supplier<String> baseUrl) {
        this.baseUrl = baseUrl;
    }

    /** Every message to {@code address}, newest first. */
    public List<Mail> to(String address) {
        String query = URLEncoder.encode("to:\"" + address + "\"", StandardCharsets.UTF_8);
        JsonNode list = get("/api/v1/search?limit=50&query=" + query);
        List<Mail> mails = new ArrayList<>();
        for (JsonNode m : list.path("messages")) {
            String id = m.path("ID").asString();
            JsonNode full = get("/api/v1/message/" + id);
            mails.add(new Mail(id, full.path("Subject").asString(), full.path("Text").asString()));
        }
        return mails;
    }

    /** Waits (≤ 10 s) until {@code address} has at least {@code count} messages. */
    public List<Mail> await(String address, int count) {
        long deadline = System.currentTimeMillis() + 10_000;
        List<Mail> mails = to(address);
        while (mails.size() < count && System.currentTimeMillis() < deadline) {
            sleep();
            mails = to(address);
        }
        return mails;
    }

    private JsonNode get(String path) {
        try {
            HttpResponse<String> response = http.send(HttpRequest.newBuilder(URI.create(baseUrl.get() + path))
                    .timeout(Duration.ofSeconds(10)).GET().build(), HttpResponse.BodyHandlers.ofString());
            return json.readTree(response.body());
        } catch (IOException e) {
            throw new IllegalStateException("Mailpit not reachable", e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(e);
        }
    }

    private static void sleep() {
        try {
            Thread.sleep(200);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
