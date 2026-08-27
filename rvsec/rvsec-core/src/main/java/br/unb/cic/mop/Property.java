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
     * CrySL's {@code generatedCipher[this] after Init}: a monitored {@code Cipher} whose
     * {@code init} the instrumentation observed, at the state {@code Init} leads to.
     *
     * <p>The live {@code jca_android} writes it at {@code CipherSpec}'s {@code @match3}
     * and reads it at both stream constructors, which is the chain
     * {@code Cipher.crysl:144} produces and {@code CipherInputStream.crysl:31} /
     * {@code CipherOutputStream.crysl:32} consume. All three of those clauses arrived
     * with the expert oracle: the generated catalogue the set was first derived against
     * declared none of them, which is why the constant sat unused until gh105 task
     * 11.5(e) wired it. The archived {@code jca_android_bug_predicate} had sites of its
     * own, at the three {@code init} events rather than at an acceptance point, and the
     * frozen {@code jca} never named the constant at all.
     *
     * <p>Not to be confused with {@code cipheredInputStream} and
     * {@code cipheredOutputStream}, which those two rules ENSURE and no rule of the 49
     * requires: those stay dead ends and gain no site.
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
    PREPARED_KEY_MATERIAL,
    /**
     * CrySL's {@code preparedRSA[this]} — an {@code RSAKeyGenParameterSpec} whose key size and
     * public exponent the rule admits.
     *
     * <p>Ensured by {@code RSAKeyGenParameterSpec.crysl:19} and required by
     * {@code KeyPairGenerator.crysl:35}, {@code algorithm in {"RSA"} => preparedRSA[params]}.
     * Before gh109 the required side had no possible producer, so the consuming clause was left
     * unread at {@code KeyPairGeneratorSpec}'s {@code init3}/{@code init4} rather than answering
     * NOT_OBSERVED forever.
     */
    PREPARED_RSA,
    /**
     * CrySL's {@code preparedDSA[this]} — a {@code DSAParameterSpec} whose modulus and generator
     * reach the bit length the rule intends.
     *
     * <p>Ensured by {@code DSAParameterSpec.crysl:20} and required by
     * {@code KeyPairGenerator.crysl:36}. The rule's sibling producer,
     * {@code DSAGenParameterSpec.crysl:25}, is not specified: its class appears only from API 35,
     * so its rule is adjudicated N/A-by-platform in the coverage matrix.
     *
     * <p>The bit-length reading of the rule's {@code p >= 1^2048} is a recorded decision, not a
     * transcription: CrySL has no exponentiation operator and the clause is literally {@code >= 1}
     * (D-20.4, with an {@code oracle-wart} row against the rule).
     */
    PREPARED_DSA,
    /**
     * CrySL's {@code preparedEC[this]} — an elliptic-curve parameter spec the rule admits.
     *
     * <p>Two producers ensure it, {@code ECParameterSpec.crysl:17} and
     * {@code ECGenParameterSpec.crysl:25}, the second constraining the curve by standard name;
     * two rules require it, {@code KeyPairGenerator.crysl:38} and {@code KeyAgreement.crysl:48},
     * both under an {@code algorithm in {"EC"}} / {@code {"ECDH"}} guard.
     */
    PREPARED_EC,
    /**
     * CrySL's {@code preparedMGF1[this, mdName]} — a mask-generation-function parameter spec,
     * carrying the digest it was built with.
     *
     * <p>Ensured by {@code MGF1ParameterSpec.crysl:17} and required by
     * {@code OAEPParameterSpec.crysl:22}, {@code preparedMGF1[mgfSpec, mdName]}. The second place
     * is what makes the clause more than an existence check: the OAEP spec's own digest name and
     * the MGF's must agree, and a two-place read is what compares them.
     */
    PREPARED_MGF1,
    /**
     * CrySL's {@code preparedOAEP[this]} — an OAEP parameter spec whose digest and mask function
     * the rule admits.
     *
     * <p>Ensured by {@code OAEPParameterSpec.crysl:25}. Two rules require it and they are not in
     * the same state. {@code AlgorithmParameters.crysl:40} requires it under
     * {@code algorithm in {"OAEP"}} and is wired. {@code Cipher.crysl:140-141} guards it with
     * {@code mode(transformation)} over strings the same rule classifies as paddings, so the
     * antecedent is unsatisfiable and the clause constrains no trace — a defect recorded as an
     * {@code oracle-wart} row against the rule and transcribed by evident intent, never edited
     * upstream (D-21).
     */
    PREPARED_OAEP,
    /**
     * CrySL's {@code preparedAlg[params, algorithm]} — an {@code AlgorithmParameters} object
     * initialised for a named algorithm.
     *
     * <p>Ensured by {@code AlgorithmParameters.crysl:43-44} (after {@code Init} and after
     * {@code GetEncoded}) and by {@code AlgorithmParameterGenerator.crysl:35} (after
     * {@code GenParam}); required by {@code AlgorithmParameters.crysl:34} and by
     * {@code Cipher.crysl:136}.
     *
     * <p>The {@code Cipher} read stays closed and the reason is structural, not editorial:
     * {@code Cipher.crysl:136} binds {@code params} through the rule's {@code i5}/{@code i7}, and
     * {@code CipherSpec}'s fused {@code i2} carries {@code args(mode, key, ..)} and binds no third
     * argument. Giving it one, or adding an event, collides with the 17-of-17 generator ceiling
     * the specification already sits at. Recorded as a measured impossibility rather than a
     * silence (D-24).
     */
    PREPARED_ALG,
    /**
     * CrySL's {@code generatedManagerFactoryParameters[this]} — the parameter object a key or
     * trust manager factory may be initialised from.
     *
     * <p>Two producers ensure it, {@code KeyStoreBuilderParameters.crysl:14} and
     * {@code CertPathTrustManagerParameters.crysl:17}; two consumers require it,
     * {@code KeyManagerFactory.crysl:32} and {@code TrustManagerFactory.crysl:29}. Both consuming
     * specifications already bind the argument and discriminate on its runtime type, and both
     * recorded, in a comment, that the read was left closed only because no producer existed.
     */
    GENERATED_MANAGER_FACTORY_PARAMETERS,
    /**
     * CrySL's {@code generatedCertPathParameters[this]} — PKIX parameters built over a key store
     * the instrument observed.
     *
     * <p>Ensured by {@code PKIXParameters.crysl:18} and {@code PKIXBuilderParameters.crysl:21},
     * both of which themselves require {@code generatedKeyStore}; required by
     * {@code CertPathTrustManagerParameters.crysl:14}. The chain is three specifications deep and
     * lands whole with gh109's trivial tier, which is why the middle link is worth naming here:
     * a store nobody loaded produces parameters nobody may trust.
     */
    GENERATED_CERT_PATH_PARAMETERS,
    /**
     * CrySL's {@code generatedTrustAnchor[this]} — a trust anchor built over a public key the
     * instrument observed.
     *
     * <p>Ensured by {@code TrustAnchor.crysl:21}, which requires {@code generatedPubkey} in turn.
     * It has no live consumer: the one clause that would require it,
     * {@code PKIXBuilderParameters.crysl:18}, is commented out in the rule
     * ({@code //generatedTrustAnchor[];}) and is deliberately not wired. That is a fact about the
     * oracle, recorded in the predicate ledger, and not a defect of the set.
     */
    GENERATED_TRUST_ANCHOR,
    /**
     * CrySL's {@code generatedCert[type]} — a certificate produced by a factory of an admitted
     * type.
     *
     * <p>Ensured by {@code CertificateFactory.crysl:31}. No rule of the 49 requires it, so it is
     * written and unread: coverage of the rule is the obligation, and the ledger classifies the
     * predicate as unconsumed rather than as an omission.
     */
    GENERATED_CERT,
    /**
     * CrySL's {@code generatedKeyFactory[this, algorithm]} — a {@code KeyFactory} obtained for an
     * admitted algorithm.
     *
     * <p>Ensured by {@code KeyFactory.crysl:30} after {@code Get}, and required by no rule of the
     * 49. Written and unread, like {@link #GENERATED_CERT}.
     */
    GENERATED_KEY_FACTORY,
    /**
     * CrySL's {@code generatedMessageDigest[this]} — a {@code MessageDigest} obtained for an
     * algorithm the rule admits.
     *
     * <p>Ensured by {@code MessageDigest.crysl:46} after {@code Get}, and required by
     * {@code DigestInputStream.crysl:33} and {@code DigestOutputStream.crysl:34}.
     *
     * <p>The set does not write it yet: {@code MessageDigestSpec.mop} ensures {@link #DIGESTED}
     * and nothing else, so the two digest-stream specifications gh109 adds would read a predicate
     * with no producer — the exact shape INV-INS-151 refuses. The constant exists here because the
     * reads need it to compile; the producing site at {@code MessageDigestSpec}'s {@code Get}
     * acceptance point is owed by whichever task wires those reads.
     */
    GENERATED_MESSAGE_DIGEST,
    /**
     * CrySL's {@code digestedInputStream[stream, digest]} — a stream read through a digest the
     * instrument observed.
     *
     * <p>Ensured by {@code DigestInputStream.crysl:36}; required by no rule of the 49.
     */
    DIGESTED_INPUT_STREAM,
    /**
     * CrySL's {@code digestedOutputStream[stream, digest]} — the output twin of
     * {@link #DIGESTED_INPUT_STREAM}.
     *
     * <p>Ensured by {@code DigestOutputStream.crysl:37}; required by no rule of the 49.
     */
    DIGESTED_OUTPUT_STREAM,
    /**
     * CrySL's {@code generatedSSLParameters[this]} — a TLS parameter object whose protocol and
     * cipher-suite lists the rule admits.
     *
     * <p>Ensured by {@code SSLParameters.crysl:48}; required by no rule of the 49.
     *
     * <p>Not to be confused with {@link #GENERATE_SSL_ENGINE}, which spells its verb without the
     * {@code D}: that constant predates this file's naming and is left alone, because renaming it
     * would rewrite sites in three specifications for a letter.
     */
    GENERATED_SSL_PARAMETERS
}
