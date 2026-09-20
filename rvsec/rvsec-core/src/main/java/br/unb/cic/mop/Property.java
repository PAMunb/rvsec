package br.unb.cic.mop;

/**
 * The CrySL predicates a monitored program can satisfy: the name a specification records an
 * {@code ENSURES} clause under, and the name a {@code REQUIRES} clause reads it back by.
 */
public enum Property {
	GENERATED_KEY,
    DIGESTED,
    ENCRYPTED,
    /**
     * CrySL's {@code generatedCipher[this] after Init}: a monitored {@code Cipher} whose
     * {@code init} the instrumentation observed, at the state {@code Init} leads to.
     *
     * <p>{@code CipherSpec} writes it at the acceptance point of {@code init}, and both stream
     * constructors read it: {@code CipherInputStream.crysl} and
     * {@code CipherOutputStream.crysl} each {@code REQUIRES} {@code generatedCipher[cipher]}
     * over the cipher handed to the constructor. Writing at the acceptance point rather than at
     * each {@code init} event is what makes the mark mean "the automaton accepted this
     * initialisation", not merely "an {@code init} call was seen".
     *
     * <p>Not to be confused with {@code cipheredInputStream} and
     * {@code cipheredOutputStream}, which those two rules {@code ENSURE} and no expert rule
     * requires: they have no reader and no site.
     */
    GENERATED_CIPHER,
    /**
     * A MAC a monitored {@code Mac} produced — the first place of CrySL's
     * {@code macced[output1, inputByte]} and of its two siblings in the {@code ENSURES} of
     * {@code Mac.crysl}, which is the byte array {@code doFinal} returned.
     *
     * <p>Kept as a one-place name for the MAC itself. The {@code Mac} chain of the
     * {@code jca_android} set runs on {@link PredicateStore} through {@link #MACED} and
     * {@link #ENCRYPTED} instead, because the two clauses it has to answer —
     * {@code !macced[_, plainText]} of the {@code Cipher} rule and {@code !encrypted[output1, _]}
     * of the {@code Mac} rule — each leave one place anonymous and quantify over the other.
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
    /**
     * A monitored {@code KeyManagerFactory}, and separately the key-manager array it
     * produced.
     *
     * <p>Two {@code ENSURES} clauses of {@code KeyManagerFactory.crysl} share this constant, and
     * object identity is what tells them apart: {@code generatedKeyManager[this] after Init}
     * over the factory and {@code generatedKeyManagers[keyManager] after GetKeyMng} over the
     * array. {@code KeyManagerFactorySpec} writes the first at the acceptance point of
     * {@code init} and the second at the event that sees the array {@code getKeyManagers}
     * returned. {@link PredicateStore} keys on the bound object, so a read against the array can
     * never be answered by a mark left on the factory, and one name for two clauses costs
     * nothing.
     *
     * <p>The reader is {@code SSLContextSpec}'s {@code init}, over the array
     * {@code SSLContext.init} receives -- that is the half {@code SSLContext.crysl} requires,
     * as {@code generatedKeyManagers[km]}. The write over the factory transcribes the rule and
     * has no consumer, exactly like its {@code TrustManagerFactory} twin.
     */
    GENERATED_KEY_MANAGERS,
    GENERATED_KEY_PAIR,
    /**
     * A monitored {@code TrustManagerFactory}, and separately the trust-manager array it
     * produced -- the exact analogue of {@link #GENERATED_KEY_MANAGERS}.
     *
     * <p>The {@code ENSURES} of {@code TrustManagerFactory.crysl} declares
     * {@code generatedTrustManager[this] after Init} and
     * {@code generatedTrustManagers[trustManager] after GetTrustMng}. Both are written
     * under this one constant, told apart by the object bound:
     * {@code TrustManagerFactorySpec} writes the factory at the acceptance point of
     * {@code init} and the array at the event that sees {@code getTrustManagers} return. The
     * reader is {@code SSLContextSpec}'s {@code init}, which asks over the array.
     *
     * <p>Not to be confused with {@link #GENERATED_TRUST_MANAGERS}, the plural, which marks
     * the individual managers inside that array rather than the array itself.
     */
    GENERATED_TRUST_MANAGER,
    /**
     * Each trust manager inside the array a monitored {@code TrustManagerFactory} produced.
     *
     * <p>{@code TrustManagerFactorySpec} writes it once per non-null element, beside the
     * {@link #GENERATED_TRUST_MANAGER} write over the array itself.
     * {@code SSLContextSpec}'s {@code init} reads it to credit an array the store has never
     * seen, when the array is non-empty and every element carries the mark: the rule constrains
     * the managers, and an application that copies an issued manager into a fresh array passes
     * exactly the manager the factory issued. Key-manager arrays have no per-element twin.
     */
    GENERATED_TRUST_MANAGERS,
    GENERATED_KEY_STORE,
    PREPARED_DH,
    PREPARED_GCM,
    PREPARED_HMAC,
    PREPARED_PBE,
    PREPARED_IV,
    RANDOMIZED,
    /**
     * The signature bytes a monitored {@code Signature.sign} returned — the first place of
     * CrySL's {@code signed[output, inputByte] after Sign}.
     */
    SIGNED,
    SPECCED_KEY,
    /**
     * The signature bytes a monitored {@code Signature.verify} was given — the <em>second</em>
     * place of CrySL's {@code verified[verified, sign] after Verify}, not the first.
     *
     * <p>The first place is the {@code boolean} the call returned, and a primitive carries no
     * identity a mark can be keyed on, so {@link PredicateStore} binds the byte array instead.
     */
    VERIFIED,
    /**
     * The bytes a monitored {@code Cipher.wrap(Key)} returned.
     *
     * <p>The {@code ENSURES} of {@code Cipher.crysl} declares
     * {@code wrappedKey[wrappedKeyBytes, wrappedKey]}, over the event
     * {@code wkb1: wrappedKeyBytes = wrap(wrappedKey)}. That {@code ENSURES} is the only place
     * {@code wrappedKey} appears in the expert rules: no rule {@code REQUIRES} it, so a mark
     * would have no reader and the write would be monitoring with no verdict surface. No
     * specification of the set writes it.
     */
    WRAPPED_KEY,
    /**
     * The key material a {@code SecretKeySpec} is constructed from.
     *
     * <p>CrySL states {@code preparedKeyMaterial[keyMaterial]}, ensured by
     * {@code SecretKey.getEncoded()} and required by the {@code SecretKeySpec}
     * constructor.
     *
     * <p>It carries its own name rather than sharing {@link #RANDOMIZED}, because the two are
     * different obligations: key material that came out of a generated key, and a byte array
     * that came out of a {@code SecureRandom}. A conforming program satisfies either without
     * satisfying the other, so one name for both would at once miss misuse and accuse
     * conforming code.
     */
    PREPARED_KEY_MATERIAL,
    /**
     * CrySL's {@code preparedRSA[this]} — an {@code RSAKeyGenParameterSpec} whose key size and
     * public exponent the rule admits.
     *
     * <p>Ensured by {@code RSAKeyGenParameterSpec.crysl} and required by
     * {@code KeyPairGenerator.crysl}: {@code algorithm in {"RSA"} => preparedRSA[params]}.
     * {@code RSAKeyGenParameterSpecSpec} writes it; {@code KeyPairGeneratorSpec} reads it at the
     * two {@code initialize} events that bind a parameter spec, choosing this constant from the
     * algorithm the generator was obtained for.
     */
    PREPARED_RSA,
    /**
     * CrySL's {@code preparedDSA[this]} — a {@code DSAParameterSpec} whose modulus and generator
     * reach the bit length the rule intends.
     *
     * <p>Ensured by {@code DSAParameterSpec.crysl} and required by
     * {@code KeyPairGenerator.crysl}: {@code algorithm in {"DSA"} => preparedDSA[params]}. The
     * rule's sibling producer, {@code DSAGenParameterSpec.crysl}, has no specification here: its
     * class exists only from API 35, above the platform this set targets.
     *
     * <p>{@code DSAParameterSpecSpec} reads the rule's {@code CONSTRAINTS} {@code p >= 1^2048}
     * and {@code g >= 1^2048} as bit lengths, which is not what the clause literally says: CrySL
     * has no exponentiation operator, so {@code 1^2048} evaluates to {@code 1} and the clause as
     * written constrains nothing. The bit-length reading is the one that makes the clause mean
     * something.
     */
    PREPARED_DSA,
    /**
     * CrySL's {@code preparedEC[this]} — an elliptic-curve parameter spec the rule admits.
     *
     * <p>Two rules ensure it, {@code ECParameterSpec.crysl} and {@code ECGenParameterSpec.crysl},
     * the second constraining the curve by standard name; two rules require it,
     * {@code KeyPairGenerator.crysl} with {@code algorithm in {"EC"} => preparedEC[params]} and
     * {@code KeyAgreement.crysl} with {@code algorithm in {"ECDH"} => preparedEC[params]}.
     */
    PREPARED_EC,
    /**
     * CrySL's {@code preparedMGF1[this, mdName]} — a mask-generation-function parameter spec,
     * carrying the digest it was built with.
     *
     * <p>Ensured by {@code MGF1ParameterSpec.crysl} as {@code preparedMGF1[this, mdName]} and
     * required by {@code OAEPParameterSpec.crysl} as {@code preparedMGF1[mgfSpec, mdName]}. The
     * second place is what makes the clause more than an existence check: the OAEP spec's own
     * digest name and the MGF's must agree, and a two-place read is what compares them.
     */
    PREPARED_MGF1,
    /**
     * CrySL's {@code preparedOAEP[this]} — an OAEP parameter spec whose digest and mask function
     * the rule admits.
     *
     * <p>Ensured by {@code OAEPParameterSpec.crysl}. Two rules require it, and only one of the
     * two reads can fire. {@code AlgorithmParameters.crysl} requires it as
     * {@code algorithm in {"OAEP"} => preparedOAEP[paramSpec]}, and
     * {@code AlgorithmParametersSpec} reads it there. {@code Cipher.crysl} guards its own read
     * with {@code mode(transformation) in {"OAEPWithMD5AndMGF1Padding", …}}, over strings the
     * same rule classifies as paddings: the antecedent cannot be satisfied, so that clause
     * constrains no trace. It is transcribed as the rule writes it rather than repaired.
     */
    PREPARED_OAEP,
    /**
     * CrySL's {@code preparedAlg[params, algorithm]} — an {@code AlgorithmParameters} object
     * initialised for a named algorithm.
     *
     * <p>Ensured by {@code AlgorithmParameters.crysl} as {@code preparedAlg[this, algorithm]
     * after Init} and {@code preparedAlg[encParams, algorithm] after GetEncoded}, and by
     * {@code AlgorithmParameterGenerator.crysl} as {@code preparedAlg[algParams, algorithm]
     * after GenParam}; required by {@code AlgorithmParameters.crysl} as
     * {@code preparedAlg[params, algorithm]} and by {@code Cipher.crysl} as
     * {@code preparedAlg[params, alg(transformation)]}.
     *
     * <p>The {@code Cipher} read is not wired, and the obstacle is structural. The rule binds
     * {@code params} through {@code init} overloads that take an {@code AlgorithmParameters}
     * argument, while {@code CipherSpec} fuses the {@code init} overloads into one event whose
     * pointcut binds only the mode and the key. Binding a third argument means another event,
     * and the specification already sits at the monitor generator's ceiling of seventeen events.
     */
    PREPARED_ALG,
    /**
     * CrySL's {@code generatedManagerFactoryParameters[this]} — the parameter object a key or
     * trust manager factory may be initialised from.
     *
     * <p>Two rules ensure it, {@code KeyStoreBuilderParameters.crysl} and
     * {@code CertPathTrustManagerParameters.crysl}; two require it,
     * {@code KeyManagerFactory.crysl} and {@code TrustManagerFactory.crysl}, both as
     * {@code generatedManagerFactoryParameters[params]}. All four sites are wired: the two
     * parameter specifications write the mark over the object they construct, and the two
     * factory specifications read it when the argument {@code init} receives is a
     * {@code ManagerFactoryParameters}.
     */
    GENERATED_MANAGER_FACTORY_PARAMETERS,
    /**
     * CrySL's {@code generatedCertPathParameters[this]} — PKIX parameters built over a key store
     * the instrument observed.
     *
     * <p>Ensured by {@code PKIXParameters.crysl} and {@code PKIXBuilderParameters.crysl}, both of
     * which themselves require {@code generatedKeyStore}; required by
     * {@code CertPathTrustManagerParameters.crysl}. The chain is three specifications deep, and
     * the middle link is what carries its meaning: a store nobody loaded produces parameters
     * nobody may trust.
     */
    GENERATED_CERT_PATH_PARAMETERS,
    /**
     * CrySL's {@code generatedTrustAnchor[this]} — a trust anchor built over a public key the
     * instrument observed.
     *
     * <p>Ensured by {@code TrustAnchor.crysl}, which requires {@code generatedPubkey} in turn. It
     * has no reader: the one clause that would require it is commented out in
     * {@code PKIXBuilderParameters.crysl} ({@code //generatedTrustAnchor[];}), so there is no
     * {@code REQUIRES} to transcribe. That is a property of the rules, not an omission of the
     * set.
     */
    GENERATED_TRUST_ANCHOR,
    /**
     * CrySL's {@code generatedCert[type]} — a certificate produced by a factory obtained for this
     * type and observed by the instrumentation.
     *
     * <p>Ensured by {@code CertificateFactory.crysl} as {@code generatedCert[type]}. No expert
     * rule requires it, so {@code CertificateFactorySpec} writes it and nothing reads it:
     * transcribing the {@code ENSURES} is what the rule asks for, and the predicate is
     * unconsumed rather than missing a site.
     *
     * <p>The write is not gated on the rule's type clause: a factory obtained for a type the
     * clause rejects is accused where it is obtained, and the certificate it produces still
     * carries the mark. The predicate therefore records which type produced the certificate, not
     * that the type was admitted.
     */
    GENERATED_CERT,
    /**
     * CrySL's {@code generatedKeyFactory[this, algorithm]} — a {@code KeyFactory} obtained for an
     * admitted algorithm.
     *
     * <p>Ensured by {@code KeyFactory.crysl} as {@code generatedKeyFactory[this, algorithm] after
     * Get}, and required by no expert rule. Written and unread, like {@link #GENERATED_CERT}.
     */
    GENERATED_KEY_FACTORY,
    /**
     * CrySL's {@code generatedMessageDigest[this]} — a {@code MessageDigest} obtained for an
     * algorithm the rule admits.
     *
     * <p>Ensured by {@code MessageDigest.crysl} as {@code generatedMessageDigest[this] after
     * Get}, and required by {@code DigestInputStream.crysl} and
     * {@code DigestOutputStream.crysl}, both as {@code generatedMessageDigest[digest]}.
     *
     * <p>{@code MessageDigestSpec} writes it in the bodies of the three {@code getInstance}
     * events whose algorithm the rule's value clause admits, and not in the complementary events
     * that accuse the algorithm: ensuring a predicate for a call this specification just refused
     * would hand the stream rules a digest it does not vouch for. The two stream specifications
     * read it at their constructor, and separate {@code VIOLATED} from {@code NOT_OBSERVED} so
     * that a digest obtained where the weaving does not reach is not accused.
     */
    GENERATED_MESSAGE_DIGEST,
    /**
     * CrySL's {@code digestedInputStream[stream, digest]} — a stream read through a digest the
     * instrument observed.
     *
     * <p>Ensured by {@code DigestInputStream.crysl}; required by no expert rule.
     */
    DIGESTED_INPUT_STREAM,
    /**
     * CrySL's {@code digestedOutputStream[stream, digest]} — the output twin of
     * {@link #DIGESTED_INPUT_STREAM}.
     *
     * <p>Ensured by {@code DigestOutputStream.crysl}; required by no expert rule.
     */
    DIGESTED_OUTPUT_STREAM,
    /**
     * CrySL's {@code generatedSSLParameters[this]} — a TLS parameter object whose protocol and
     * cipher-suite lists the rule admits.
     *
     * <p>Ensured by {@code SSLParameters.crysl}; required by no expert rule.
     *
     * <p>Not to be confused with {@link #GENERATE_SSL_ENGINE}, which spells its verb without the
     * {@code D} and names a different predicate. The two names differ by one letter, and the
     * store answers about whichever of them a site passes.
     */
    GENERATED_SSL_PARAMETERS,
    /**
     * An object whose producer already reported it, by value or by origin.
     *
     * <p>Not a CrySL predicate. It lets a consumer that finds no predicate for the object it
     * binds say "refused upstream" instead of "not observed": the store has no entry because
     * the producer refused to write one, not because the object came from where the
     * instrument cannot see. A chain therefore reports its first failure with that site's own
     * code and every later link with its {@code upstream-refused} label code.
     *
     * <p>Producers in {@code jca_android} mark the object they produce whenever the site calls
     * {@code addError} with a value or origin code for it ({@code -ORDER-} reports never mark):
     * {@code SecretKeySpecSpec} ({@code c1}, {@code c2}), {@code GCMParameterSpecSpec} and
     * {@code IvParameterSpec} ({@code c1}, {@code c2}), {@code PBEKeySpecSpec.c1},
     * {@code X509EncodedKeySpecSpec.c1}, {@code KeyFactorySpec} ({@code genPublic},
     * {@code genPrivate}), {@code SecretKeyFactorySpec.gen} and {@code KeyAgreementSpec}
     * ({@code gs1}, {@code gs2}). The {@code getEncoded()} bridges {@code KeySpec.ge1} and
     * {@code SecretKeySpec.e1} carry the mark from a marked key to the array it returns.
     *
     * <p>Consumers read it with {@code validateAny} in their {@code NOT_OBSERVED} branch, before
     * choosing the code: {@code CipherSpec.i2}, {@code MacSpec.i1}, {@code IvChainJunction.use},
     * {@code SecretKeyFactorySpec.gen}, {@code KeyFactorySpec} ({@code genPublic},
     * {@code genPrivate}), {@code KeyAgreementSpec.dophase}, {@code SignatureSpec.i4},
     * {@code SecretKeySpecSpec} ({@code c1}, {@code c2}) and {@code X509EncodedKeySpecSpec.c1}.
     * {@code SecureRandomSpec} and {@code KeyGeneratorSpec} do not mark.
     */
    REPORTED_UPSTREAM
}
