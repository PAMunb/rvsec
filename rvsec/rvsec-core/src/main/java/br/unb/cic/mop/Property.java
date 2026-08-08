package br.unb.cic.mop;

/**
 * The properties that we are interested in.
 *
 */
public enum Property {
	GENERATED_KEY,
    DIGESTED,
    ENCRYPTED,
    /**
     * A monitored {@code Cipher} that completed {@code getInstance} and then an
     * {@code init} whose key requirement held.
     *
     * <p>CrySL states {@code generatedCipher[this] after Inits}, and both stream
     * rules require it of the cipher they are constructed with. The mark is
     * written at the init events rather than on reaching the accepting state,
     * because a cipher handed to a {@code CipherInputStream} has been
     * initialised and has not yet encrypted anything -- the stream performs
     * those calls itself. Marking only at the accepting state would leave every
     * legitimate stream construction unsatisfied.
     */
    GENERATED_CIPHER,
    GENERATED_MAC,
    /**
     * The data a monitored {@code Mac} computed a MAC over.
     *
     * <p>CrySL states {@code macced[M, D]} -- <em>M is the MAC of D</em> -- and
     * {@link #GENERATED_MAC} holds the first place of it. This constant holds the
     * second, which is the place the {@code Cipher} rule's
     * {@code !macced[_, plainText]} quantifies over: with the first place
     * anonymous, the projection onto the data is exactly what that clause asks,
     * so one set of objects reads it faithfully. A clause naming both places
     * would still need a store this one does not have.
     */
    MACED,
    GENERATED_PRIVATE_KEY,
    GENERATED_PUBLIC_KEY,
    GENERATE_SSL_CONTEXT,
    GENERATE_SSL_ENGINE,
    GENERATED_KEY_MANAGERS,
    GENERATED_KEY_PAIR,
    GENERATED_TRUST_MANAGER,
    GENERATED_TRUST_MANAGERS,
    GENERATED_KEY_STORE,
    PREPARED_DH,
    PREPARED_GCM,
    PREPARED_HMAC,
    PREPARED_PBE,
    PREPARED_IV,
    RANDOMIZED,
    SIGNED,
    SPECCED_KEY,
    VERIFIED,
    WRAPPED_KEY
}
