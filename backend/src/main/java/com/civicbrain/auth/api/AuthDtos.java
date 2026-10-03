package com.civicbrain.auth.api;

import com.civicbrain.users.model.Role;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

/**
 * Request and response bodies of {@code /auth} (docs/04_API_CONTRACT.md §1). Passwords are only checked for presence
 * and a hard upper size here; length and blocklist are the password policy (422 PASSWORD_POLICY). Records holding a
 * password or token hide it in {@code toString()}.
 */
public final class AuthDtos {

    private AuthDtos() {
    }

    static final String NO_CONTROL = "^[^\\p{Cntrl}]+$";

    public record ConsentsRequest(@NotNull Boolean whatsapp, @NotNull Boolean publicPhoto, @NotNull Boolean aiTraining) {
    }

    public record RegisterRequest(
            @NotBlank @Size(max = 150) @Pattern(regexp = NO_CONTROL, message = "must not contain control characters") String fullName,
            @NotBlank @Size(max = 255) @Email @Pattern(regexp = "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", message = "must be an e-mail address") String email,
            @NotBlank @Pattern(regexp = "^\\+91[6-9][0-9]{9}$", message = "must be +91 followed by a 10-digit mobile number") String phone,
            @NotNull @Size(max = 1024) String password,
            @NotBlank @Size(max = 20) String privacyNoticeVersion,
            @NotNull @Valid ConsentsRequest consents) {
        @Override
        public String toString() {
            return "RegisterRequest[]";
        }
    }

    public record OtpResponse(long otpId, long expiresInSec) {
    }

    public record VerifyOtpRequest(@NotNull @Positive Long otpId,
                                   @NotNull @Pattern(regexp = "^[0-9]{6}$", message = "must be 6 digits") String code) {
        @Override
        public String toString() {
            return "VerifyOtpRequest[otpId=" + otpId + "]";
        }
    }

    public record VerifiedResponse(boolean verified) {
    }

    public record ResendOtpRequest(@NotNull @Positive Long otpId) {
    }

    public record LoginRequest(@NotBlank @Size(max = 255) String identifier, @NotNull @Size(max = 1024) String password) {
        @Override
        public String toString() {
            return "LoginRequest[]";
        }
    }

    public record UserSummary(long id, String fullName, Role role, boolean mustChangePassword, String preferredLanguage) {
    }

    public record LoginResponse(String accessToken, long expiresIn, UserSummary user) {
        @Override
        public String toString() {
            return "LoginResponse[user=" + user.id() + "]";
        }
    }

    public record TokenResponse(String accessToken, long expiresIn) {
        @Override
        public String toString() {
            return "TokenResponse[]";
        }
    }

    public record ForgotPasswordRequest(@NotBlank @Size(max = 255) @Email String email) {
        @Override
        public String toString() {
            return "ForgotPasswordRequest[]";
        }
    }

    public record ResetPasswordRequest(@NotNull @Positive Long otpId,
                                       @NotNull @Pattern(regexp = "^[0-9]{6}$", message = "must be 6 digits") String code,
                                       @NotNull @Size(max = 1024) String newPassword) {
        @Override
        public String toString() {
            return "ResetPasswordRequest[otpId=" + otpId + "]";
        }
    }

    public record PasswordChangeRequest(@NotNull @Size(max = 1024) String currentPassword,
                                        @NotNull @Size(max = 1024) String newPassword) {
        @Override
        public String toString() {
            return "PasswordChangeRequest[]";
        }
    }
}
