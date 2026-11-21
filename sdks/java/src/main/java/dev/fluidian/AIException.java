package dev.fluidian;

/** Thrown by {@link Ctx#ai} when a capability cannot be fulfilled. */
public final class AIException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    public AIException(String message) {
        super(message);
    }
}
