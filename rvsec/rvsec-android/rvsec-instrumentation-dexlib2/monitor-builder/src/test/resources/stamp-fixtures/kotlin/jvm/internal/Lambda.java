package kotlin.jvm.internal;

/** Superclass of kotlinc lambda classes; its only field is the arity. */
public abstract class Lambda {
    private final int arity;

    protected Lambda(int arity) {
        this.arity = arity;
    }
}
