package org.telegram.messenger;

import android.app.Activity;
import android.content.SharedPreferences;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import java.net.URI;

/** Persistent, runtime-editable Spotify server address. */
public final class SpotifyServerSettings {
    private static final int DEFAULT_PORT = 8000;
    private static final String PREFERENCES_NAME = "spotify_api_config";
    private static final String SERVER_ADDRESS_KEY = "server_address";

    private SpotifyServerSettings() {}

    @NonNull
    public static String getServerAddress() {
        String address = getPreferences().getString(SERVER_ADDRESS_KEY, SpotifyApiConfig.DEFAULT_SERVER_ADDRESS);
        return address != null ? address : SpotifyApiConfig.DEFAULT_SERVER_ADDRESS;
    }

    public static boolean setServerAddress(@NonNull String address) {
        String normalized = normalizeServerAddress(address);
        if (normalized == null) {
            return false;
        }
        getPreferences().edit().putString(SERVER_ADDRESS_KEY, normalized).apply();
        return true;
    }

    /** Accepts an IP, host with an optional port, or a complete HTTP(S) base URL. */
    @Nullable
    public static String normalizeServerAddress(@Nullable String address) {
        if (address == null) {
            return null;
        }
        String value = address.trim();
        while (value.endsWith("/")) {
            value = value.substring(0, value.length() - 1);
        }
        if (value.isEmpty()) {
            return null;
        }
        if (!value.contains("://")) {
            value = "http://" + value;
        }

        try {
            URI uri = new URI(value);
            String scheme = uri.getScheme();
            if (scheme == null || (!"http".equalsIgnoreCase(scheme) && !"https".equalsIgnoreCase(scheme))) {
                return null;
            }
            if (uri.getHost() == null || uri.getUserInfo() != null || uri.getQuery() != null || uri.getFragment() != null) {
                return null;
            }
            String path = uri.getPath();
            if (path != null && !path.isEmpty() && !"/".equals(path)) {
                return null;
            }
            int port = uri.getPort();
            if (port == -1) {
                port = DEFAULT_PORT;
            } else if (port < 1 || port > 65535) {
                return null;
            }
            return new URI(scheme.toLowerCase(), null, uri.getHost(), port, null, null, null).toString();
        } catch (Exception ignored) {
            return null;
        }
    }

    @NonNull
    public static String getStatusUrl() {
        return endpoint(SpotifyApiConfig.STATUS_PATH);
    }

    @NonNull
    public static String getPlayUrl() {
        return endpoint(SpotifyApiConfig.PLAY_PATH);
    }

    @NonNull
    public static String getPauseUrl() {
        return endpoint(SpotifyApiConfig.PAUSE_PATH);
    }

    @NonNull
    public static String getNextUrl() {
        return endpoint(SpotifyApiConfig.NEXT_PATH);
    }

    @NonNull
    public static String getPreviousUrl() {
        return endpoint(SpotifyApiConfig.PREVIOUS_PATH);
    }

    @NonNull
    private static String endpoint(@NonNull String path) {
        return path.isEmpty() ? "" : getServerAddress() + (path.startsWith("/") ? path : "/" + path);
    }

    @NonNull
    private static SharedPreferences getPreferences() {
        return ApplicationLoader.applicationContext.getSharedPreferences(PREFERENCES_NAME, Activity.MODE_PRIVATE);
    }
}
