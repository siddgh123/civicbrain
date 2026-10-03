package com.civicbrain.it.support;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;
import java.util.Random;

import javax.imageio.ImageIO;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.MockMultipartHttpServletRequestBuilder;

import com.civicbrain.users.model.Role;
import com.civicbrain.users.model.UserAccount;
import com.civicbrain.workflow.Actor;
import com.civicbrain.workflow.ActorRole;
import com.civicbrain.workflow.ComplaintStatus;
import com.civicbrain.workflow.WorkflowActor;

import tools.jackson.databind.JsonNode;

/**
 * Helpers for the complaint ITs: a signed-in citizen, capture sessions, multipart submissions (docs/04 §5) and
 * status moves through {@link WorkflowActor}. Each citizen submits at most 5 complaints (5 / 24 h in profile test)
 * and every request comes from its own client IP (20 / h per IP).
 */
public abstract class ComplaintItSupport extends AuthItSupport {

    /** Inside ward number 1 (docs/08_TEST_PLAN.md §2); 18.7700/73.7500 is outside TDMC (smoke E2E_POINT_OUT). */
    public static final double IN_LAT = 18.7440;
    public static final double IN_LON = 73.6760;
    public static final double OUT_LAT = 18.7700;
    public static final double OUT_LON = 73.7500;

    @Autowired
    protected WorkflowActor workflow;

    /** A verified citizen with a fresh access token. */
    public record Citizen(long id, String email, String token) {
    }

    protected Citizen citizen() throws Exception {
        String email = uniqueEmail("cit");
        UserAccount account = user(Role.CITIZEN, email, false);
        return new Citizen(account.id(), email, loginOk(email, PASSWORD).access());
    }

    protected Citizen staff(Role role) throws Exception {
        String email = uniqueEmail(role.name().toLowerCase());
        UserAccount account = user(role, email, false);
        return new Citizen(account.id(), email, loginOk(email, PASSWORD).access());
    }

    protected String captureSession(Citizen c) throws Exception {
        MvcResult r = mvc.perform(post("/api/v1/citizen/capture-sessions").with(bearer(c.token())).with(from(uniqueIp()))).andReturn();
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(201);
        return body(r).path("captureSessionId").asString();
    }

    protected long categoryId(String name) {
        return jdbc.sql("SELECT category_id FROM complaint_categories WHERE category_name = :n").param("n", name)
                .query(Long.class).single();
    }

    /** A valid {@code data} map for the category (depthAnswer FINGER when the category needs one). */
    protected Map<String, Object> data(String category, String sessionId) {
        Map<String, Object> d = new HashMap<>();
        d.put("categoryId", categoryId(category));
        d.put("title", "Deep pothole near the temple");
        d.put("description", "Large pothole on the road near the temple, vehicles are slipping.");
        d.put("landmark", "Near the temple");
        d.put("latitude", IN_LAT);
        d.put("longitude", IN_LON);
        d.put("locationAccuracyM", 12.5);
        d.put("locationCapturedAt", OffsetDateTime.now(ZoneOffset.ofHoursMinutes(5, 30)).minusSeconds(30).toString());
        d.put("devicePitchDeg", 55.5);
        d.put("deviceRollDeg", -1.25);
        d.put("captureSessionId", sessionId);
        d.put("captureMethod", "IN_APP_CAMERA");
        d.put("a4InFrame", false);
        Boolean depth = jdbc.sql("SELECT needs_depth_answer FROM complaint_categories WHERE category_name = :n").param("n", category)
                .query(Boolean.class).single();
        if (depth) {
            d.put("depthAnswer", "FINGER");
        }
        return d;
    }

    protected MvcResult submit(Citizen c, Map<String, Object> data, byte[] photo) throws Exception {
        return submitRaw(c, json.writeValueAsBytes(data), photo, uniqueIp());
    }

    protected MvcResult submitRaw(Citizen c, byte[] data, byte[] photo, String ip) throws Exception {
        MockMultipartHttpServletRequestBuilder request = multipart("/api/v1/citizen/complaints");
        if (data != null) {
            request.file(new MockMultipartFile("data", "data.json", "application/json", data));
        }
        if (photo != null) {
            request.file(new MockMultipartFile("photo", "photo.jpg", "image/jpeg", photo));
        }
        return mvc.perform(request.with(bearer(c.token())).with(from(ip))).andReturn();
    }

    /** A valid complaint of {@code c}: returns the 201 body. */
    protected JsonNode submitOk(Citizen c, String category) throws Exception {
        MvcResult r = submit(c, data(category, captureSession(c)), jpeg(1280, 960, c.id()));
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(201);
        return body(r);
    }

    /** A photo-like JPEG (random ellipses, seeded) of the given size. */
    protected static byte[] jpeg(int width, int height, long seed) throws IOException {
        BufferedImage img = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = img.createGraphics();
        Random r = new Random(seed);
        g.setColor(new Color(60 + r.nextInt(60), 60 + r.nextInt(60), 60 + r.nextInt(60)));
        g.fillRect(0, 0, width, height);
        for (int i = 0; i < 30; i++) {
            g.setColor(new Color(r.nextInt(256), r.nextInt(256), r.nextInt(256)));
            g.fillOval(r.nextInt(width), r.nextInt(height), 20 + r.nextInt(300), 20 + r.nextInt(200));
        }
        g.dispose();
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ImageIO.write(img, "jpg", out);
        return out.toByteArray();
    }

    protected static byte[] resource(String name) throws IOException {
        try (InputStream in = ComplaintItSupport.class.getResourceAsStream(name)) {
            assertThat(in).as(name).isNotNull();
            return in.readAllBytes();
        }
    }

    /** Moves a complaint along the lifecycle with the roles the V2 rules require (test data only). */
    protected void move(long complaintId, long actorUserId, ComplaintStatus... path) {
        for (ComplaintStatus target : path) {
            ActorRole role = switch (target) {
                case VERIFIED, MERGED -> ActorRole.SYSTEM;
                case INSPECTED, IN_PROGRESS, COMPLETED -> ActorRole.CONTRACTOR;
                default -> ActorRole.OFFICER;
            };
            workflow.changeStatus(complaintId, target, role == ActorRole.SYSTEM ? Actor.system() : Actor.user(actorUserId, role),
                    "IT move to " + target);
        }
    }

    protected String status(long complaintId) {
        return jdbc.sql("SELECT status FROM complaints WHERE complaint_id = :id").param("id", complaintId).query(String.class).single();
    }
}
