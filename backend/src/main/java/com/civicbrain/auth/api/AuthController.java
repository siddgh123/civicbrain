package com.civicbrain.auth.api;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.CookieValue;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.civicbrain.auth.api.AuthDtos.ForgotPasswordRequest;
import com.civicbrain.auth.api.AuthDtos.LoginRequest;
import com.civicbrain.auth.api.AuthDtos.LoginResponse;
import com.civicbrain.auth.api.AuthDtos.OtpResponse;
import com.civicbrain.auth.api.AuthDtos.PasswordChangeRequest;
import com.civicbrain.auth.api.AuthDtos.RegisterRequest;
import com.civicbrain.auth.api.AuthDtos.ResendOtpRequest;
import com.civicbrain.auth.api.AuthDtos.ResetPasswordRequest;
import com.civicbrain.auth.api.AuthDtos.TokenResponse;
import com.civicbrain.auth.api.AuthDtos.UserSummary;
import com.civicbrain.auth.api.AuthDtos.VerifiedResponse;
import com.civicbrain.auth.api.AuthDtos.VerifyOtpRequest;
import com.civicbrain.auth.service.AuthService;
import com.civicbrain.users.model.UserAccount;
import com.civicbrain.users.service.UserAccounts;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;

/** {@code /api/v1/auth} (docs/04_API_CONTRACT.md §1). Public, except logout-all and password change (bearer). */
@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService auth;
    private final RefreshCookie cookie;

    public AuthController(AuthService auth, RefreshCookie cookie) {
        this.auth = auth;
        this.cookie = cookie;
    }

    @PostMapping("/register")
    public ResponseEntity<OtpResponse> register(@Valid @RequestBody RegisterRequest body, HttpServletRequest request) {
        var consents = new UserAccounts.Consents(body.consents().whatsapp(), body.consents().publicPhoto(),
                body.consents().aiTraining());
        var registered = auth.register(new AuthService.RegisterCommand(body.fullName(), body.email(), body.phone(),
                body.password(), body.privacyNoticeVersion(), consents), CurrentUser.client(request));
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(new OtpResponse(registered.otpId(), registered.expiresInSeconds()));
    }

    @PostMapping("/verify-otp")
    public VerifiedResponse verifyOtp(@Valid @RequestBody VerifyOtpRequest body, HttpServletRequest request) {
        auth.verifyOtp(body.otpId(), body.code(), CurrentUser.client(request));
        return new VerifiedResponse(true);
    }

    @PostMapping("/resend-otp")
    public ResponseEntity<Void> resendOtp(@Valid @RequestBody ResendOtpRequest body, HttpServletRequest request) {
        auth.resendOtp(body.otpId(), CurrentUser.client(request));
        return ResponseEntity.status(HttpStatus.ACCEPTED).build();
    }

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@Valid @RequestBody LoginRequest body, HttpServletRequest request) {
        AuthService.Session session = auth.login(body.identifier(), body.password(), CurrentUser.client(request));
        UserAccount user = session.user();
        return ResponseEntity.ok()
                .header(HttpHeaders.SET_COOKIE, cookie.issue(session.refresh().value(), session.refresh().maxAge()).toString())
                .body(new LoginResponse(session.access().value(), session.access().expiresInSeconds(),
                        new UserSummary(user.id(), user.fullName(), user.role(), user.mustChangePassword(),
                                user.preferredLanguage())));
    }

    @PostMapping("/refresh")
    public ResponseEntity<TokenResponse> refresh(@CookieValue(name = RefreshCookie.NAME, required = false) String refreshToken,
                                                 HttpServletRequest request) {
        cookie.checkCsrf(request);
        AuthService.Session session = auth.refresh(refreshToken, CurrentUser.client(request));
        return ResponseEntity.ok()
                .header(HttpHeaders.SET_COOKIE, cookie.issue(session.refresh().value(), session.refresh().maxAge()).toString())
                .body(new TokenResponse(session.access().value(), session.access().expiresInSeconds()));
    }

    @PostMapping("/logout")
    public ResponseEntity<Void> logout(@CookieValue(name = RefreshCookie.NAME, required = false) String refreshToken,
                                       HttpServletRequest request) {
        cookie.checkCsrf(request);
        auth.logout(refreshToken, CurrentUser.client(request));
        return ResponseEntity.noContent().header(HttpHeaders.SET_COOKIE, cookie.clear().toString()).build();
    }

    @PostMapping("/logout-all")
    public ResponseEntity<Void> logoutAll(Authentication authentication, HttpServletRequest request) {
        auth.logoutAll(CurrentUser.id(authentication), CurrentUser.client(request));
        return ResponseEntity.noContent().header(HttpHeaders.SET_COOKIE, cookie.clear().toString()).build();
    }

    @PostMapping("/password/forgot")
    public ResponseEntity<OtpResponse> forgotPassword(@Valid @RequestBody ForgotPasswordRequest body, HttpServletRequest request) {
        var otp = auth.forgotPassword(body.email(), CurrentUser.client(request));
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(new OtpResponse(otp.otpId(), otp.expiresInSeconds()));
    }

    @PostMapping("/password/reset")
    public ResponseEntity<Void> resetPassword(@Valid @RequestBody ResetPasswordRequest body, HttpServletRequest request) {
        auth.resetPassword(body.otpId(), body.code(), body.newPassword(), CurrentUser.client(request));
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/password/change")
    public ResponseEntity<Void> changePassword(@Valid @RequestBody PasswordChangeRequest body,
                                               @CookieValue(name = RefreshCookie.NAME, required = false) String refreshToken,
                                               Authentication authentication, HttpServletRequest request) {
        auth.changePassword(CurrentUser.id(authentication), body.currentPassword(), body.newPassword(), refreshToken,
                CurrentUser.client(request));
        return ResponseEntity.noContent().build();
    }
}
