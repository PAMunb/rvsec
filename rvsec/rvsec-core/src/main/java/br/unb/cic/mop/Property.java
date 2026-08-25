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
     * <p>No specification of any live set writes or reads this constant. The only
     * sites are in the archived {@code jca_android_bug_predicate}: its
     * {@code CipherSpec} writes the mark at the three {@code init} events, and its
     * {@code CipherInputStreamSpec} and {@code CipherOutputStreamSpec} validate it of
     * the cipher they are constructed with. The successor set {@code jca_android}
     * carries the two stream rules with no such read -- {@code cipheredInputStream}
     * and {@code cipheredOutputStream} are dead-end predicates -- and the frozen
     * {@code jca} never named the constant at all.
     *
     * <p>Kept because {@link Property} is append-only (INV-INS-132): the ordinals are
     * a freeze item and {@code test_property_append_only} fails any removal.
     */
    GENERATED_CIPHER,
    /**
     * A MAC a monitored {@code Mac} produced, the first place of CrySL's
     * {@code macced[M, D]}.
     *
     * <p>Written and read only by frozen and archived sets: {@code jca/MacSpec.mop}
     * writes it at its two {@code doFinal} events and removes it on failure, and the
     * archived {@code jca_android_bug_predicate/MacSpec.mop} does the same. The live
     * {@code jca_android} does not name it -- its {@code Mac} chain runs on
     * {@link PredicateStore} through {@link #MACED} and {@link #ENCRYPTED}. The
     * conformance component of {@code rvsec-crysl-mop} reads the {@code jca} sites as
     * its arity-1 substrate fixture, so the name is load-bearing outside this enum too.
     */
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
    /**
     * The trust-manager array a monitored {@code TrustManagerFactory} produced.
     *
     * <p>No set writes it. The frozen {@code jca/TrustManagerFactorySpec.mop:88} only
     * {@code remove}s it in the failure handler -- a clearing of a mark nothing ever
     * set -- and the archived {@code jca_android_bug_predicate} is where the matching
     * write and the {@code SSLContextSpec} read live. The live {@code jca_android}
     * wires that edge through {@link PredicateStore} instead, so the constant has no
     * live producer and no live consumer; {@code PredicateStoreTest} uses it as a
     * neutral key for the three-valued verdict cases.
     */
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
    /**
     * The bytes a monitored {@code Cipher.wrap(Key)} returned.
     *
     * <p>Write-only wherever it appears, and nowhere in a live set:
     * {@code jca/CipherSpec.mop:118} sets it at the {@code wrap} event and no
     * specification of any of the five sets validates it. {@code jca_android} deleted
     * the write rather than relocating it (gh105 task 4.1): the {@code Cipher} rule
     * names {@code w: wrap(wrappedKey)} in no {@code ENSURES} clause, so the mark
     * translates no clause and has no acceptance point to move to.
     */
    WRAPPED_KEY,
    /**
     * The key material a {@code SecretKeySpec} is constructed from.
     *
     * <p>CrySL states {@code preparedKeyMaterial[keyMaterial]}, ensured by
     * {@code SecretKey.getEncoded()} and required by the {@code SecretKeySpec}
     * constructor. The set wrote and read that clause under {@link #RANDOMIZED}
     * until this constant existed, which conflated two different obligations:
     * key material that came out of a generated key, and a byte array that came
     * out of a {@code SecureRandom}. A conforming program satisfies one without
     * satisfying the other, so the conflation both missed misuse and accused
     * conforming code.
     */
    PREPARED_KEY_MATERIAL
}
