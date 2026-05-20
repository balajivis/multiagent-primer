package com.docvault.controller;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.hamcrest.Matchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void register_newUser_returns200() throws Exception {
        String unique = "testuser_" + System.currentTimeMillis();
        String json = String.format("""
            {
                "username": "%s",
                "email": "%s@example.com",
                "password": "testpass123",
                "fullName": "Test User"
            }
            """, unique, unique);

        mockMvc.perform(post("/api/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.message").value("Registration successful"))
            .andExpect(jsonPath("$.user.username").value(unique))
            .andExpect(jsonPath("$.user.passwordHash").doesNotExist())
            .andExpect(jsonPath("$..passwordHash").isEmpty());
    }

    @Test
    void login_validCredentials_doesNotLeakPasswordHash() throws Exception {
        String unique = "logintest_" + System.currentTimeMillis();
        String registerJson = String.format("""
            {
                "username": "%s",
                "email": "%s@example.com",
                "password": "testpass123",
                "fullName": "Login Test"
            }
            """, unique, unique);

        mockMvc.perform(post("/api/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content(registerJson))
            .andExpect(status().isOk());

        String loginJson = String.format("""
            {"username": "%s", "password": "testpass123"}
            """, unique);

        mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content(loginJson))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.user.username").value(unique))
            .andExpect(jsonPath("$.user.passwordHash").doesNotExist())
            .andExpect(jsonPath("$..passwordHash").isEmpty())
            .andExpect(jsonPath("$..password").isEmpty());
    }

    @Test
    void register_duplicateUsername_returnsBadRequest() throws Exception {
        String json = """
            {
                "username": "johndoe",
                "email": "new@example.com",
                "password": "testpass123",
                "fullName": "Another John"
            }
            """;

        mockMvc.perform(post("/api/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.error").value("Username already exists"));
    }

    @Test
    void getProfile_existingUser_returnsProfile() throws Exception {
        mockMvc.perform(get("/api/auth/profile").param("userId", "2"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.user", notNullValue()))
            .andExpect(jsonPath("$.orderCount", greaterThanOrEqualTo(0)))
            .andExpect(jsonPath("$..passwordHash").isEmpty())
            .andExpect(jsonPath("$..password").isEmpty());
    }

    @Test
    void getProfile_nonExistentUser_returns404() throws Exception {
        mockMvc.perform(get("/api/auth/profile").param("userId", "999"))
            .andExpect(status().isNotFound());
    }

    @Test
    void resetPassword_returnsSuccessRegardless() throws Exception {
        String json = """
            {"email": "nonexistent@example.com"}
            """;

        mockMvc.perform(post("/api/auth/reset-password")
                .contentType(MediaType.APPLICATION_JSON)
                .content(json))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.message", containsString("If that email exists")));
    }

    // DELIBERATELY MISSING:
    // - No test for password strength validation (there is none)
    // - No test for the password reset token storage (it doesn't exist)
    // (SEC-002 password-hash leakage now covered by register/login/profile tests above.)
}
