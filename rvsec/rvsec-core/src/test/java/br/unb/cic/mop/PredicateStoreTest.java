package br.unb.cic.mop;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

import javax.crypto.spec.SecretKeySpec;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

/**
 * The contract of the {@code jca_android} predicate substrate, stated as tests.
 *
 * <p>
 * Every case here corresponds to a defect measured on the old store: keying by {@code equals}
 * under monitors that key by identity, an arity of one under binary clauses, a boolean answer
 * under a three-valued truth, a varargs head that spread reference arrays, and state that outlived
 * both the objects it described and the trace it was recorded in. The tests are the reason those
 * defects cannot come back silently.
 */
public class PredicateStoreTest {

	private PredicateStore store;

	@Before
	public void freshStore() {
		store = PredicateStore.instance();
		store.reset();
	}

	@After
	public void leaveNothingBehind() {
		store.reset();
	}

	@Test
	public void twoKeysThatAreEqualButNotTheSameObjectAreDifferentSubjects() {
		byte[] material = new byte[] { 1, 2, 3, 4, 5, 6, 7, 8 };
		SecretKeySpec generated = new SecretKeySpec(material, "AES");
		SecretKeySpec handWritten = new SecretKeySpec(material, "AES");

		// The premise of the whole test: the JCA defines these as equal.
		assertEquals(generated, handWritten);
		assertNotSame(generated, handWritten);

		store.ensure(Property.GENERATED_KEY, generated);

		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.GENERATED_KEY, generated));
		assertEquals(PredicateVerdict.NOT_OBSERVED, store.validate(Property.GENERATED_KEY, handWritten));
	}

	@Test
	public void aTrackedStringPositionMatchesRegardlessOfCase() {
		Object key = new Object();
		store.ensure(Property.GENERATED_KEY, key, "AES");

		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.GENERATED_KEY, key, "aes"));
		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.GENERATED_KEY, key, "AES"));
	}

	@Test
	public void aTrackedStringPositionThatDiffersIsPositiveEvidenceOfAViolation() {
		Object key = new Object();
		store.ensure(Property.GENERATED_KEY, key, "AES");

		assertEquals(PredicateVerdict.VIOLATED, store.validate(Property.GENERATED_KEY, key, "DES"));
	}

	@Test
	public void integerPositionsAreTrackedByValueSoAutoboxingCannotSplitThem() {
		Object spec = new Object();
		store.ensure(Property.PREPARED_PBE, spec, Integer.valueOf(100000));

		// Two boxes over the same int are different objects outside the cache range.
		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.PREPARED_PBE, spec, Integer.valueOf(100000)));
		assertEquals(PredicateVerdict.VIOLATED, store.validate(Property.PREPARED_PBE, spec, Integer.valueOf(999)));
	}

	@Test
	public void anUntrackedValuePositionIsComparedByIdentityLikeTheBoundObject() {
		Object cipher = new Object();
		byte[] plainText = new byte[] { 9, 9, 9 };
		byte[] sameBytes = new byte[] { 9, 9, 9 };

		store.ensure(Property.MACED, cipher, plainText);

		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.MACED, cipher, plainText));
		assertEquals(PredicateVerdict.VIOLATED, store.validate(Property.MACED, cipher, sameBytes));
	}

	@Test
	public void aBinaryClauseDistinguishesItsSecondPlace() {
		Object key = new Object();
		store.ensure(Property.GENERATED_KEY, key, "AES");
		store.ensure(Property.GENERATED_KEY, key, "DESede");

		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.GENERATED_KEY, key, "aes"));
		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.GENERATED_KEY, key, "desede"));
		assertEquals(PredicateVerdict.VIOLATED, store.validate(Property.GENERATED_KEY, key, "RC4"));
	}

	@Test
	public void aReadOfDifferentArityThanTheRecordIsAMismatchAndNotAMatch() {
		Object key = new Object();
		store.ensure(Property.GENERATED_KEY, key, "AES");

		assertEquals(PredicateVerdict.VIOLATED, store.validate(Property.GENERATED_KEY, key));
		assertEquals(PredicateVerdict.VIOLATED, store.validate(Property.GENERATED_KEY, key, "AES", "extra"));
	}

	/**
	 * The anonymous position of CrySL's {@code pred[bound, _]}: {@code Mac.crysl:54} requires
	 * {@code generatedKey[key,_]} while the three producers of that predicate all write a second
	 * place. Reading it through {@code validate} is the trap the test above documents; this is the
	 * read the clause actually asks for.
	 */
	@Test
	public void anAnonymousPositionIsSatisfiedByAnyRecordedArgumentList() {
		Object key = new Object();
		store.ensure(Property.GENERATED_KEY, key, "HmacSHA256");

		assertEquals(PredicateVerdict.VIOLATED, store.validate(Property.GENERATED_KEY, key));
		assertEquals(PredicateVerdict.SATISFIED, store.validateAny(Property.GENERATED_KEY, key));
	}

	/**
	 * The producers disagree on what they write into the anonymous place — {@code KeyGeneratorSpec}
	 * writes the string the program handed {@code getInstance}, the other two the key's own
	 * algorithm — so a reader that guessed one spelling would accuse the other. The anonymous read
	 * is blind to the difference, which is the whole reason it exists.
	 */
	@Test
	public void anAnonymousPositionIgnoresWhichSpellingTheProducerRecorded() {
		Object viaGenerator = new Object();
		Object viaKeyStore = new Object();
		store.ensure(Property.GENERATED_KEY, viaGenerator, "HMAC-SHA256");
		store.ensure(Property.GENERATED_KEY, viaKeyStore, "HmacSHA256");

		assertEquals(PredicateVerdict.SATISFIED, store.validateAny(Property.GENERATED_KEY, viaGenerator));
		assertEquals(PredicateVerdict.SATISFIED, store.validateAny(Property.GENERATED_KEY, viaKeyStore));
	}

	@Test
	public void anAnonymousReadTellsAWithdrawnPredicateFromAnUnobservedOne() {
		Object withdrawn = new Object();
		store.ensure(Property.GENERATED_KEY, withdrawn, "AES");
		store.negate(Property.GENERATED_KEY, withdrawn);

		assertEquals(PredicateVerdict.VIOLATED, store.validateAny(Property.GENERATED_KEY, withdrawn));
		assertEquals(PredicateVerdict.NOT_OBSERVED, store.validateAny(Property.GENERATED_KEY, new Object()));
		assertEquals(PredicateVerdict.NOT_OBSERVED, store.validateAny(Property.GENERATED_KEY, null));
	}

	/** It names the property: an object marked under one predicate answers nothing under another. */
	@Test
	public void anAnonymousReadIsStillAboutOnePredicateAndNotAboutAnyPredicate() {
		Object key = new Object();
		store.ensure(Property.GENERATED_KEY, key, "AES");

		assertEquals(PredicateVerdict.NOT_OBSERVED, store.validateAny(Property.RANDOMIZED, key));
	}

	@Test
	public void anObjectNeverSeenAtAllIsNotObservedRatherThanViolated() {
		assertEquals(PredicateVerdict.NOT_OBSERVED, store.validate(Property.RANDOMIZED, new Object()));
	}

	@Test
	public void aPredicateNeverSeenOnAnObjectThatCarriesAnotherIsNotObserved() {
		Object key = new Object();
		store.ensure(Property.GENERATED_KEY, key);

		assertEquals(PredicateVerdict.NOT_OBSERVED, store.validate(Property.RANDOMIZED, key));
	}

	@Test
	public void aNegatedClauseReadsTheInvertedTableSoAbsenceConforms() {
		Object plainText = new Object();

		assertEquals(PredicateVerdict.SATISFIED, store.validateAbsent(Property.MACED, plainText));

		store.ensure(Property.MACED, plainText);

		assertEquals(PredicateVerdict.VIOLATED, store.validateAbsent(Property.MACED, plainText));
	}

	@Test
	public void aNegatedClauseFailsOnTheNameAloneAndDoesNotNarrowByArguments() {
		Object plainText = new Object();
		store.ensure(Property.MACED, plainText, "HmacSHA256");

		// The recorded arguments differ from the ones the read passes; the clause still fails,
		// because it asks whether a same-name predicate exists at all.
		assertEquals(PredicateVerdict.VIOLATED, store.validateAbsent(Property.MACED, plainText, "HmacSHA1"));
	}

	@Test
	public void aWithdrawnPredicateAccusesInsteadOfFallingSilent() {
		Object keySpec = new Object();
		store.ensure(Property.SPECCED_KEY, keySpec);
		store.negate(Property.SPECCED_KEY, keySpec);

		assertEquals(PredicateVerdict.VIOLATED, store.validate(Property.SPECCED_KEY, keySpec));
		// Inverted for a negated clause: a withdrawal is an absence, which conforms.
		assertEquals(PredicateVerdict.SATISFIED, store.validateAbsent(Property.SPECCED_KEY, keySpec));
	}

	@Test
	public void aWithdrawalNamesOneObjectAndLeavesEveryOtherAlone() {
		Object cleared = new Object();
		Object untouched = new Object();
		store.ensure(Property.SPECCED_KEY, cleared);
		store.ensure(Property.SPECCED_KEY, untouched);

		store.negate(Property.SPECCED_KEY, cleared);

		assertEquals(PredicateVerdict.VIOLATED, store.validate(Property.SPECCED_KEY, cleared));
		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.SPECCED_KEY, untouched));
	}

	@Test
	public void recordingAPredicateAgainAfterAWithdrawalReinstatesIt() {
		Object keySpec = new Object();
		store.ensure(Property.SPECCED_KEY, keySpec);
		store.negate(Property.SPECCED_KEY, keySpec);
		store.ensure(Property.SPECCED_KEY, keySpec);

		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.SPECCED_KEY, keySpec));
	}

	@Test
	public void anArrayArgumentIsRecordedWholeAndIsNeverSpreadIntoItsElements() {
		// A varargs head would have turned this into two arguments, and an empty array into none.
		String[] managers = new String[] { "km-a", "km-b" };
		String[] empty = new String[0];
		String[] anotherEmpty = new String[0];

		store.ensure(Property.GENERATED_KEY_MANAGERS, managers);
		store.ensure(Property.GENERATED_TRUST_MANAGERS, empty);

		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.GENERATED_KEY_MANAGERS, managers));
		assertEquals(PredicateVerdict.SATISFIED, store.validate(Property.GENERATED_TRUST_MANAGERS, empty));
		// Had the empty array been spread, both empty arrays would have produced the same key.
		assertEquals(PredicateVerdict.NOT_OBSERVED, store.validate(Property.GENERATED_TRUST_MANAGERS, anotherEmpty));
	}

	@Test
	public void aNullBoundObjectIsToleratedBecauseWovenAdviceMustNeverThrow() {
		store.ensure(Property.RANDOMIZED, null);
		store.negate(Property.RANDOMIZED, null);

		assertEquals(PredicateVerdict.NOT_OBSERVED, store.validate(Property.RANDOMIZED, null));
		assertEquals(PredicateVerdict.SATISFIED, store.validateAbsent(Property.MACED, null));
	}

	@Test
	public void entriesDisappearOnceTheObjectTheyDescribeIsCollected() throws Exception {
		for (int i = 0; i < 200; i++) {
			store.ensure(Property.RANDOMIZED, new Object());
		}
		assertEquals(200, store.boundObjectCount());

		for (int attempt = 0; attempt < 50 && store.boundObjectCount() > 0; attempt++) {
			System.gc();
			Thread.sleep(20L);
		}

		assertEquals(0, store.boundObjectCount());
	}

	@Test
	public void resetClearsEverythingSoOneTraceCannotSatisfyTheNext() {
		Object key = new Object();
		store.ensure(Property.GENERATED_KEY, key, "AES");

		store.reset();

		assertEquals(PredicateVerdict.NOT_OBSERVED, store.validate(Property.GENERATED_KEY, key, "AES"));
		assertEquals(0, store.boundObjectCount());
	}

	@Test
	public void concurrentWritersAndReadersAgreeOnEveryObjectTheyOwn() throws Exception {
		final int threads = 8;
		final int perThread = 500;
		ExecutorService pool = Executors.newFixedThreadPool(threads);
		List<Callable<Integer>> work = new ArrayList<Callable<Integer>>();
		for (int t = 0; t < threads; t++) {
			work.add(new Callable<Integer>() {
				@Override
				public Integer call() {
					List<Object> mine = new ArrayList<Object>();
					for (int i = 0; i < perThread; i++) {
						Object subject = new Object();
						mine.add(subject);
						store.ensure(Property.RANDOMIZED, subject, "seed");
					}
					int satisfied = 0;
					for (Object subject : mine) {
						if (store.validate(Property.RANDOMIZED, subject, "SEED") == PredicateVerdict.SATISFIED) {
							satisfied++;
						}
					}
					return Integer.valueOf(satisfied);
				}
			});
		}

		List<Future<Integer>> results = pool.invokeAll(work);
		pool.shutdown();
		assertTrue(pool.awaitTermination(30L, TimeUnit.SECONDS));

		int total = 0;
		for (Future<Integer> result : results) {
			total += result.get().intValue();
		}
		assertEquals(threads * perThread, total);
	}

	@Test
	public void aReaderOfAnObjectBeingRewrittenNeverSeesNotObserved() throws Exception {
		// The test above gives every thread its own subject, so it never exercises two
		// threads over ONE object -- which is the case the woven advice actually
		// produces when a single Cipher or SecureRandom is shared. What must never
		// happen there is a reader landing between the two statements of `ensure` or
		// `negate` and getting NOT_OBSERVED for an object the store positively knows
		// something about: that answer suppresses an accusation, while both SATISFIED
		// and VIOLATED merely pick one side of the write.
		final Object subject = new Object();
		final int rounds = 20000;
		store.ensure(Property.RANDOMIZED, subject, "seed");

		ExecutorService pool = Executors.newFixedThreadPool(2);
		Callable<Integer> writer = new Callable<Integer>() {
			@Override
			public Integer call() {
				for (int i = 0; i < rounds; i++) {
					store.negate(Property.RANDOMIZED, subject);
					store.ensure(Property.RANDOMIZED, subject, "seed");
				}
				return Integer.valueOf(0);
			}
		};
		Callable<Integer> reader = new Callable<Integer>() {
			@Override
			public Integer call() {
				int notObserved = 0;
				for (int i = 0; i < rounds; i++) {
					if (store.validate(Property.RANDOMIZED, subject, "SEED") == PredicateVerdict.NOT_OBSERVED) {
						notObserved++;
					}
				}
				return Integer.valueOf(notObserved);
			}
		};

		List<Callable<Integer>> work = new ArrayList<Callable<Integer>>();
		work.add(writer);
		work.add(reader);
		List<Future<Integer>> results = pool.invokeAll(work);
		pool.shutdown();
		assertTrue(pool.awaitTermination(30L, TimeUnit.SECONDS));

		assertEquals(0, results.get(0).get().intValue());
		assertEquals("a reader saw NOT_OBSERVED for an object the store was rewriting", 0,
				results.get(1).get().intValue());
	}
}
