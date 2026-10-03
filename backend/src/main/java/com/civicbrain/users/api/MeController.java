package com.civicbrain.users.api;

import java.time.OffsetDateTime;
import java.util.List;

import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.civicbrain.auth.api.CurrentUser;
import com.civicbrain.common.Masking;
import com.civicbrain.common.RequestIdFilter;
import com.civicbrain.common.Times;
import com.civicbrain.privacy.model.ConsentType;
import com.civicbrain.users.model.Role;
import com.civicbrain.users.service.MeService;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/** {@code /api/v1/me} - any authenticated user, always their own row (docs/04_API_CONTRACT.md §2). */
@RestController
@RequestMapping("/api/v1/me")
public class MeController {

    public record ConsentView(ConsentType type, boolean granted, String noticeVersion, OffsetDateTime at) {
    }

    public record MeResponse(long id, String fullName, String email, String phoneMasked, Role role, String preferredLanguage,
                             boolean emailOptIn, boolean whatsappOptIn, List<ConsentView> consents) {
    }

    public record UpdateMeRequest(
            @NotBlank @Size(max = 150) @Pattern(regexp = "^[^\\p{Cntrl}]+$", message = "must not contain control characters") String fullName,
            @NotNull @Pattern(regexp = "^(en|mr|hi)$", message = "must be en, mr or hi") String preferredLanguage,
            @NotNull Boolean emailOptIn,
            @NotNull Boolean whatsappOptIn) {
    }

    public record ConsentRequest(@NotNull ConsentType consentType, @NotNull Boolean granted) {
    }

    private final MeService me;

    public MeController(MeService me) {
        this.me = me;
    }

    @GetMapping
    public MeResponse get(Authentication authentication) {
        return view(me.profile(CurrentUser.id(authentication)));
    }

    @PutMapping
    public MeResponse update(@Valid @RequestBody UpdateMeRequest body, Authentication authentication, HttpServletRequest request) {
        return view(me.update(CurrentUser.id(authentication),
                new MeService.ProfileChange(body.fullName(), body.preferredLanguage(), body.emailOptIn(), body.whatsappOptIn()),
                request.getRemoteAddr(), RequestIdFilter.currentId(request)));
    }

    @PostMapping("/consents")
    public MeResponse consent(@Valid @RequestBody ConsentRequest body, Authentication authentication, HttpServletRequest request) {
        return view(me.consent(CurrentUser.id(authentication), body.consentType(), body.granted(),
                request.getRemoteAddr(), RequestIdFilter.currentId(request)));
    }

    private static MeResponse view(MeService.Profile p) {
        var u = p.user();
        return new MeResponse(u.id(), u.fullName(), u.email(), Masking.phone(u.phone()), u.role(), u.preferredLanguage(),
                u.emailOptIn(), u.whatsappOptIn(),
                p.consents().stream().map(c -> new ConsentView(c.type(), c.granted(), c.noticeVersion(), Times.api(c.at()))).toList());
    }
}
