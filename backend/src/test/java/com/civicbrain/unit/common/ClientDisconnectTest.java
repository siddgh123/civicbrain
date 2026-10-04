package com.civicbrain.unit.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

import com.civicbrain.common.GlobalExceptionHandler;
import com.civicbrain.unit.support.WebSliceTest;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;

/**
 * A client that closes the connection while the response is written (the SPA aborts a photo request when the page
 * changes, docs/05 §2) is not a server error (docs/12 §2 INTERNAL_ERROR = "anything unexpected"): no ERROR/WARN line
 * with a stack trace, and no problem body is written to the closed connection.
 */
@WebSliceTest
class ClientDisconnectTest {

    @Autowired
    MockMvc mvc;

    private final Logger adviceLog = (Logger) LoggerFactory.getLogger(GlobalExceptionHandler.class);
    private final ListAppender<ILoggingEvent> events = new ListAppender<>();

    @BeforeEach
    void captureLog() {
        events.start();
        adviceLog.addAppender(events);
    }

    @AfterEach
    void releaseLog() {
        adviceLog.detachAppender(events);
    }

    @Test
    void aClosedClientConnectionIsNeitherLoggedAsAnErrorNorAnsweredWithAProblem() throws Exception {
        MvcResult result = mvc.perform(get("/api/v1/public/test/client-gone")).andReturn();

        assertThat(events.list).noneMatch(e -> e.getLevel().isGreaterOrEqual(Level.WARN));
        assertThat(result.getResponse().getStatus()).isNotEqualTo(500);
        assertThat(result.getResponse().getContentAsString()).isEmpty();
    }

    @Test
    void anUnexpectedErrorIsStillLoggedAsAnError() throws Exception {
        mvc.perform(get("/api/v1/public/test/boom")).andReturn();

        assertThat(events.list).anyMatch(e -> e.getLevel() == Level.ERROR);
    }
}
