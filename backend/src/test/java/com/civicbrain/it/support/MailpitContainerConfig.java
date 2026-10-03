package com.civicbrain.it.support;

import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.test.context.DynamicPropertyRegistrar;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.utility.DockerImageName;

/**
 * One Mailpit container (docs/08_TEST_PLAN.md §1, same image as scripts/dev/start-mailpit.ps1) shared by every
 * integration test: Spring Mail sends to its SMTP port, {@link MailpitClient} reads its HTTP API.
 */
@TestConfiguration(proxyBeanMethods = false)
public class MailpitContainerConfig {

    public static final DockerImageName MAILPIT = DockerImageName.parse("axllent/mailpit:v1.31.3");
    static final int SMTP = 1025;
    static final int HTTP = 8025;

    /** Own type, so it never competes with the PostGIS container for injection. */
    public static class MailpitContainer extends GenericContainer<MailpitContainer> {
        MailpitContainer() {
            super(MAILPIT);
            withExposedPorts(SMTP, HTTP);
            waitingFor(Wait.forHttp("/api/v1/info").forPort(HTTP));
        }

        public String apiUrl() {
            return "http://" + getHost() + ":" + getMappedPort(HTTP);
        }
    }

    @Bean
    MailpitContainer mailpit() {
        return new MailpitContainer();
    }

    @Bean
    DynamicPropertyRegistrar mailpitProperties(MailpitContainer mailpit) {
        return registry -> {
            registry.add("spring.mail.host", mailpit::getHost);
            registry.add("spring.mail.port", () -> mailpit.getMappedPort(SMTP));
        };
    }

    @Bean
    MailpitClient mailpitClient(MailpitContainer mailpit) {
        return new MailpitClient(mailpit::apiUrl);
    }
}
