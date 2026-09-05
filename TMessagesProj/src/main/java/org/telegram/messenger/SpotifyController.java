package org.telegram.messenger;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.TimeUnit;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;

/**
 * A single application-wide bridge between the UI and the user's Spotify server.
 *
 * <p>All listeners and state changes live on the main thread. OkHttp callbacks are
 * marshalled back to it before touching UI state.</p>
 */
public final class SpotifyController {
    public interface Listener {
        void onSpotifyStateChanged(@Nullable State state);
    }

    public enum Command {
        PLAY,
        PAUSE,
        NEXT,
        PREVIOUS
    }

    public static final class State {
        public final boolean playing;
        public final String author;
        public final String songName;

        private State(boolean playing, @NonNull String author, @NonNull String songName) {
            this.playing = playing;
            this.author = author;
            this.songName = songName;
        }

        @Override
        public boolean equals(Object other) {
            if (this == other) {
                return true;
            }
            if (!(other instanceof State state)) {
                return false;
            }
            return playing == state.playing
                    && author.equals(state.author)
                    && songName.equals(state.songName);
        }

        @Override
        public int hashCode() {
            return Objects.hash(playing, author, songName);
        }
    }

    private static final long POLL_INTERVAL_MS = 1_000L;
    private static final long ERROR_LOG_INTERVAL_MS = 30_000L;

    private static final OkHttpClient HTTP_CLIENT = new OkHttpClient.Builder()
            .connectTimeout(3, TimeUnit.SECONDS)
            .readTimeout(3, TimeUnit.SECONDS)
            .writeTimeout(3, TimeUnit.SECONDS)
            .callTimeout(5, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build();

    private static final SpotifyController INSTANCE = new SpotifyController();

    private final Set<Listener> listeners = new LinkedHashSet<>();
    private final Runnable pollRunnable = new Runnable() {
        @Override
        public void run() {
            pollScheduled = false;
            if (!polling || listeners.isEmpty()) {
                stopPolling();
                return;
            }
            requestState();
            scheduleNextPoll(POLL_INTERVAL_MS);
        }
    };

    @Nullable
    private State state;
    @Nullable
    private State dismissedState;
    @Nullable
    private Call stateCall;
    private boolean polling;
    private boolean pollScheduled;
    private long lastErrorLogTime;

    private SpotifyController() {}

    public static SpotifyController getInstance() {
        return INSTANCE;
    }

    /** Must be called on the main thread. */
    public void addListener(@NonNull Listener listener) {
        if (!listeners.add(listener)) {
            return;
        }
        listener.onSpotifyStateChanged(getState());
        if (isConfigured(SpotifyServerSettings.getStatusUrl()) && !polling) {
            polling = true;
            requestState();
            scheduleNextPoll(POLL_INTERVAL_MS);
        }
    }

    /** Must be called on the main thread. */
    public void removeListener(@NonNull Listener listener) {
        listeners.remove(listener);
        if (listeners.isEmpty()) {
            stopPolling();
        }
    }

    /** Applies a server-address change immediately. Must be called on the main thread. */
    public void onServerAddressChanged() {
        if (stateCall != null) {
            stateCall.cancel();
            stateCall = null;
        }
        if (pollScheduled) {
            AndroidUtilities.cancelRunOnUIThread(pollRunnable);
            pollScheduled = false;
        }
        state = null;
        dismissedState = null;
        notifyListeners();

        polling = !listeners.isEmpty() && isConfigured(SpotifyServerSettings.getStatusUrl());
        if (polling) {
            requestState();
            scheduleNextPoll(POLL_INTERVAL_MS);
        }
    }

    @Nullable
    public State getState() {
        return Objects.equals(state, dismissedState) ? null : state;
    }

    /** Hides the current snapshot until playback or track metadata changes. */
    public void dismissCurrentState() {
        if (state == null || Objects.equals(state, dismissedState)) {
            return;
        }
        dismissedState = state;
        notifyListeners();
    }

    public boolean canSend(@NonNull Command command) {
        return isConfigured(getCommandUrl(command));
    }

    public void send(@NonNull Command command) {
        String url = getCommandUrl(command);
        if (!isConfigured(url)) {
            return;
        }

        Call commandCall;
        try {
            commandCall = HTTP_CLIENT.newCall(createGetRequest(url));
        } catch (IllegalArgumentException exception) {
            logError("Invalid Spotify " + command.name().toLowerCase() + " URL", exception);
            return;
        }
        commandCall.enqueue(new Callback() {
            @Override
            public void onFailure(@NonNull Call call, @NonNull IOException exception) {
                logError("Spotify " + command.name().toLowerCase() + " request failed", exception);
            }

            @Override
            public void onResponse(@NonNull Call call, @NonNull Response response) {
                try (response) {
                    if (!response.isSuccessful()) {
                        logError("Spotify " + command.name().toLowerCase() + " request returned HTTP " + response.code(), null);
                        return;
                    }
                    // Ask for fresh state immediately instead of waiting for the next tick.
                    AndroidUtilities.runOnUIThread(SpotifyController.this::requestState);
                }
            }
        });
    }

    private void requestState() {
        String url = SpotifyServerSettings.getStatusUrl().trim();
        if (!polling || stateCall != null || url.isEmpty()) {
            return;
        }

        Call call;
        try {
            call = HTTP_CLIENT.newCall(createGetRequest(url));
        } catch (IllegalArgumentException exception) {
            logError("Invalid Spotify status URL", exception);
            return;
        }
        stateCall = call;
        call.enqueue(new Callback() {
            @Override
            public void onFailure(@NonNull Call failedCall, @NonNull IOException exception) {
                finishStateRequest(failedCall, null, exception);
            }

            @Override
            public void onResponse(@NonNull Call completedCall, @NonNull Response response) {
                State result = null;
                Throwable error = null;
                try (response) {
                    if (!response.isSuccessful()) {
                        error = new IOException("HTTP " + response.code());
                    } else {
                        ResponseBody body = response.body();
                        if (body == null) {
                            error = new IOException("empty response body");
                        } else {
                            result = parseState(body.string());
                        }
                    }
                } catch (Throwable throwable) {
                    error = throwable;
                }
                finishStateRequest(completedCall, result, error);
            }
        });
    }

    private void finishStateRequest(@NonNull Call completedCall, @Nullable State result, @Nullable Throwable error) {
        AndroidUtilities.runOnUIThread(() -> {
            if (stateCall != completedCall) {
                return;
            }
            stateCall = null;
            if (error != null) {
                logError("Spotify status request failed", error);
                return;
            }
            if (!Objects.equals(state, result)) {
                state = result;
                if (!Objects.equals(dismissedState, result)) {
                    dismissedState = null;
                }
                notifyListeners();
            }
        });
    }

    @NonNull
    static State parseState(@NonNull String json) throws JSONException {
        JSONObject object = new JSONObject(json);
        boolean playing = object.getBoolean("playing");
        String author = object.getString("author").trim();
        String songName = object.getString("song_name").trim();
        return new State(playing, author, songName);
    }

    private void notifyListeners() {
        for (Listener listener : new ArrayList<>(listeners)) {
            listener.onSpotifyStateChanged(getState());
        }
    }

    private void scheduleNextPoll(long delayMs) {
        if (!polling || pollScheduled) {
            return;
        }
        pollScheduled = true;
        AndroidUtilities.runOnUIThread(pollRunnable, delayMs);
    }

    private void stopPolling() {
        polling = false;
        if (pollScheduled) {
            AndroidUtilities.cancelRunOnUIThread(pollRunnable);
            pollScheduled = false;
        }
        if (stateCall != null) {
            stateCall.cancel();
            stateCall = null;
        }
    }

    @NonNull
    private static Request createGetRequest(@NonNull String url) {
        return new Request.Builder()
                .url(url.trim())
                .get()
                .header("Accept", "application/json")
                .header("Cache-Control", "no-cache")
                .header("User-Agent", "SakuraGram/Spotify")
                .build();
    }

    @NonNull
    private static String getCommandUrl(@NonNull Command command) {
        return switch (command) {
            case PLAY -> SpotifyServerSettings.getPlayUrl();
            case PAUSE -> SpotifyServerSettings.getPauseUrl();
            case NEXT -> SpotifyServerSettings.getNextUrl();
            case PREVIOUS -> SpotifyServerSettings.getPreviousUrl();
        };
    }

    private static boolean isConfigured(@Nullable String url) {
        return url != null && !url.trim().isEmpty();
    }

    private void logError(@NonNull String message, @Nullable Throwable throwable) {
        long now = System.currentTimeMillis();
        if (!BuildVars.LOGS_ENABLED || now - lastErrorLogTime < ERROR_LOG_INTERVAL_MS) {
            return;
        }
        lastErrorLogTime = now;
        if (throwable == null) {
            FileLog.e(message);
        } else {
            FileLog.e(message, throwable);
        }
    }
}
