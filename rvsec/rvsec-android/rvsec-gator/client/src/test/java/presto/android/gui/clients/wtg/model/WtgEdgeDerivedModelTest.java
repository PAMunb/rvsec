package presto.android.gui.clients.wtg.model;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotSame;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.util.Collections;
import java.util.List;
import java.util.Set;

import org.junit.Test;

import com.google.common.collect.Lists;
import com.google.common.collect.Sets;

import presto.android.gui.graph.NIdNode;
import presto.android.gui.graph.NObjectNode;
import presto.android.gui.listener.EventType;
import presto.android.gui.wtg.EventHandler;
import presto.android.gui.wtg.RootTag;
import presto.android.gui.wtg.StackOperation;
import presto.android.gui.wtg.ds.WTGEdge;
import presto.android.gui.wtg.ds.WTGNode;
import soot.SootClass;

/**
 * Behaviour locks for the two WTG model nodes that are DERIVED from GATOR's
 * static-analysis graph: {@link Event} (built from a GATOR
 * {@code EventHandler}) and {@link Transition} (built from a GATOR
 * {@code WTGEdge}). Together they finish the {@link Result} container by
 * supplying the non-null {@link Transition} that
 * {@link Result#addTransition(Transition)} needs as a positive control (the
 * residual left open by {@code WtgModelValueSemanticsTest}).
 *
 * <p><b>Why hand-rolled stubs, not mocks.</b> The module's test classpath is
 * JUnit 4 only — no Mockito. GATOR's graph types, however, are constructible
 * WITHOUT a Soot {@code Scene}: {@link NObjectNode}'s only abstract method is
 * {@code getClassType()}, its {@code NNode} base ctor merely assigns an id, and
 * {@code EventHandler}/{@code WTGNode}/{@code WTGEdge} ctors just store fields.
 * So a tiny {@link StubObjectNode} (returns a caller-supplied {@link SootClass})
 * and a {@link StubIdNode} (returns a literal id name, sidestepping
 * {@code IDNameExtractor.v()}) are enough to exercise the real production
 * field-mapping, {@code toEvents} stream, and equals/hashCode/toString of both
 * model classes.</p>
 *
 * <p><b>Scope boundary (REPORT-ONLY).</b> The non-null-handler arm of the
 * {@code Event} ctor — {@code (getEventHandler()==null) ? "" : getSignature()} —
 * needs a real {@code SootMethod} with a resolved signature, i.e. a bootstrapped
 * Soot {@code Scene}. Every handler here is built with a {@code null}
 * {@code SootMethod}, so {@code handler} stays on the {@code ""} arm and the
 * signature branch is left to the integration tests. Consequently the
 * {@code handler}-differs conjunct of {@code Event.equals} is also not lit here
 * (both operands are {@code ""}); the other four conjuncts are.</p>
 *
 * <p>Every negative assertion is paired with a same-shape positive control so a
 * regression that inverts a guard (a widened {@code equals}, a dropped
 * null-check) fails loudly instead of passing silently.</p>
 */
public class WtgEdgeDerivedModelTest {

	// ── Scene-free stubs ─────────────────────────────────────────────────

	/**
	 * Minimal concrete {@link NObjectNode}: carries an explicit node id and a
	 * class type, nothing else. The {@code id} field is public on {@code NNode}
	 * and is overwritten here so the derived {@link Event}/{@link Transition}
	 * pick up a deterministic value instead of the auto-incremented one.
	 */
	static final class StubObjectNode extends NObjectNode {
		private final SootClass cls;

		StubObjectNode(int idVal, SootClass cls) {
			this.id = idVal;
			this.cls = cls;
		}

		@Override
		public SootClass getClassType() {
			return cls;
		}
	}

	/**
	 * Minimal concrete {@link NIdNode} whose {@code getIdName()} returns a
	 * literal, avoiding {@code IDNameExtractor.v()} (a Soot-bound singleton).
	 * {@code getIdValue()} is inherited and returns the ctor's {@code Integer}.
	 */
	static final class StubIdNode extends NIdNode {
		private final String idName;

		StubIdNode(Integer idValue, String idName) {
			super(idValue, "stub");
			this.idName = idName;
		}

		@Override
		public String getIdName() {
			return idName;
		}
	}

	// ── fixture factories ────────────────────────────────────────────────

	private static SootClass sootClass(String name) {
		return new SootClass(name);
	}

	private static StubObjectNode widget(int id, String className) {
		return new StubObjectNode(id, sootClass(className));
	}

	/** An {@link Event} built directly from a handler with a null SootMethod. */
	private static Event eventFrom(NObjectNode widgetNode, EventType type) {
		return new Event(new EventHandler(null, widgetNode, type, null));
	}

	/**
	 * A trigger handler suitable for a {@link WTGEdge}'s handler <b>Set</b>:
	 * both window and widget are non-null because {@code EventHandler}'s inner
	 * sig hashes them, and the Set insertion inside the edge ctor would NPE on a
	 * null window.
	 */
	private static EventHandler triggerHandler(EventType type, int widgetId, String widgetClass) {
		NObjectNode window = widget(900, "com.example.Window");
		NObjectNode widgetNode = widget(widgetId, widgetClass);
		return new EventHandler(window, widgetNode, type, null);
	}

	private static WTGEdge edge(int srcId, int tgtId, Set<EventHandler> handlers, List<EventHandler> callbacks) {
		WTGNode src = new WTGNode(widget(srcId, "com.example.SrcWindow"));
		WTGNode tgt = new WTGNode(widget(tgtId, "com.example.TgtWindow"));
		List<StackOperation> noStackOps = Collections.emptyList();
		return new WTGEdge(src, tgt, handlers, RootTag.start_activity, noStackOps, callbacks);
	}

	// ── Event: ctor field mapping ────────────────────────────────────────

	/**
	 * A handler with NO widget (window-level / implicit lifecycle event) takes
	 * the {@code getWidget() == null} FALSE arm: the widget block is skipped, so
	 * widgetClass/widgetName stay null and widgetId stays 0. The null SootMethod
	 * takes the handler-ternary's {@code ""} arm. Concrete values:
	 * EventHandler(null, null, click, null) → type="click", handler="".
	 */
	@Test
	public void eventFromWidgetlessHandlerHasTypeButNoWidgetFields() {
		Event e = new Event(new EventHandler(null, null, EventType.click, null));

		assertEquals("event type comes from EventType.toString()", "click", e.getType());
		assertEquals("null SootMethod maps to the empty handler string", "", e.getHandler());
		assertEquals("no widget means widgetId stays at its 0 default", 0, e.getWidgetId());
		assertNull("no widget means widgetClass is never set", e.getWidgetClass());
		assertNull("no widget means widgetName is never set", e.getWidgetName());
	}

	/**
	 * A widget WITHOUT an idNode takes the {@code getWidget() != null} TRUE arm
	 * but the {@code idNode != null} FALSE arm: widgetId and widgetClass come
	 * straight from the object node, and widgetName stays null (only an idNode
	 * supplies a name). Concrete values: node id=7, class="com.example.Button"
	 * → widgetId=7, widgetClass="com.example.Button", widgetName=null.
	 */
	@Test
	public void eventFromWidgetWithoutIdNodeUsesNodeIdAndClass() {
		Event e = eventFrom(widget(7, "com.example.Button"), EventType.long_click);

		assertEquals("long_click", e.getType());
		assertEquals("widgetId is taken from the object node id", 7, e.getWidgetId());
		assertEquals("com.example.Button", e.getWidgetClass());
		assertNull("without an idNode there is no widget name", e.getWidgetName());
	}

	/**
	 * A widget WITH an idNode takes the {@code idNode != null} TRUE arm: the
	 * resource name and the numeric id are read from the idNode, OVERRIDING the
	 * raw object-node id. Concrete values: node id=7 but idNode id=4242,
	 * name="login_button" → widgetId becomes 4242 (not 7), widgetName set.
	 * This is the branch that distinguishes a resource-identified widget from a
	 * bare view, so the override is asserted explicitly against the node id.
	 */
	@Test
	public void eventFromWidgetWithIdNodeOverridesIdAndSetsName() {
		StubObjectNode node = widget(7, "com.example.Button");
		node.idNode = new StubIdNode(4242, "login_button");

		Event e = eventFrom(node, EventType.click);

		assertEquals("idNode's id value overrides the raw node id", 4242, e.getWidgetId());
		assertEquals("idNode supplies the widget name", "login_button", e.getWidgetName());
		assertEquals("widgetClass still comes from the node", "com.example.Button", e.getWidgetClass());
	}

	// ── Event: equals / hashCode / toString ──────────────────────────────

	/**
	 * The reflexive fast-path ({@code this == obj}) short-circuits equals to
	 * true for any Event.
	 */
	@Test
	public void eventIsReflexivelyEqual() {
		Event e = eventFrom(widget(1, "com.example.W"), EventType.click);
		assertTrue("an Event must equal itself", e.equals(e));
	}

	/**
	 * Two DISTINCT Events built from structurally identical handlers (same
	 * type, same widget id + class, both idNode-less) are equal and share a
	 * hash — the value-equality that lets Events dedup inside the
	 * {@link Transition} event Set. Exercises the full happy path of equals:
	 * this!=obj, obj!=null, same class, and all four lit conjuncts true.
	 */
	@Test
	public void eventsWithSameFieldsAreEqualAndShareHashCode() {
		Event a = eventFrom(widget(3, "com.example.W"), EventType.click);
		Event b = eventFrom(widget(3, "com.example.W"), EventType.click);

		assertNotSame(a, b);
		assertTrue("Events with identical fields must be equal", a.equals(b));
		assertEquals("equal Events must share a hash code", a.hashCode(), b.hashCode());
	}

	/**
	 * equals(null) takes the {@code obj == null} arm and returns false. Positive
	 * control: the same Event equals an equal-valued sibling.
	 */
	@Test
	public void eventIsNotEqualToNull() {
		Event e = eventFrom(widget(1, "com.example.W"), EventType.click);

		assertFalse("an Event must never equal null", e.equals(null));
		assertTrue("positive control: still equal to an equal-valued Event",
				e.equals(eventFrom(widget(1, "com.example.W"), EventType.click)));
	}

	/**
	 * equals against a foreign type takes the {@code getClass() != obj.getClass()}
	 * arm and returns false. Positive control: equal to a real Event.
	 */
	@Test
	public void eventIsNotEqualToForeignType() {
		Event e = eventFrom(widget(1, "com.example.W"), EventType.click);

		assertFalse("an Event must not equal a non-Event object", e.equals("click"));
		assertTrue("positive control: equal to a same-valued Event",
				e.equals(eventFrom(widget(1, "com.example.W"), EventType.click)));
	}

	/**
	 * A differing event TYPE breaks equality via the {@code Objects.equals(type, ..)}
	 * conjunct — even when the widget matches. click vs long_click on the same
	 * widget are not equal. Positive control: same type is equal.
	 */
	@Test
	public void eventWithDifferentTypeIsNotEqual() {
		Event base = eventFrom(widget(1, "com.example.W"), EventType.click);

		assertFalse("a different event type must break equality",
				base.equals(eventFrom(widget(1, "com.example.W"), EventType.long_click)));
		assertTrue("positive control: matching type is equal",
				base.equals(eventFrom(widget(1, "com.example.W"), EventType.click)));
	}

	/**
	 * A differing widget ID breaks equality via the {@code widgetId == other.widgetId}
	 * conjunct — even when type and class match. Positive control: same id equal.
	 */
	@Test
	public void eventWithDifferentWidgetIdIsNotEqual() {
		Event base = eventFrom(widget(1, "com.example.W"), EventType.click);

		assertFalse("a different widget id must break equality",
				base.equals(eventFrom(widget(2, "com.example.W"), EventType.click)));
		assertTrue("positive control: matching widget id is equal",
				base.equals(eventFrom(widget(1, "com.example.W"), EventType.click)));
	}

	/**
	 * A differing widget CLASS breaks equality via the
	 * {@code Objects.equals(widgetClass, ..)} conjunct — even when type and id
	 * match. Positive control: same class equal.
	 */
	@Test
	public void eventWithDifferentWidgetClassIsNotEqual() {
		Event base = eventFrom(widget(1, "com.example.Button"), EventType.click);

		assertFalse("a different widget class must break equality",
				base.equals(eventFrom(widget(1, "com.example.TextView"), EventType.click)));
		assertTrue("positive control: matching widget class is equal",
				base.equals(eventFrom(widget(1, "com.example.Button"), EventType.click)));
	}

	/**
	 * A differing widget NAME breaks equality via the
	 * {@code Objects.equals(widgetName, ..)} conjunct. Both Events carry an
	 * idNode (so widgetName is set) with the same numeric id but different
	 * names → not equal. Positive control: same name equal.
	 */
	@Test
	public void eventWithDifferentWidgetNameIsNotEqual() {
		StubObjectNode nodeA = widget(1, "com.example.W");
		nodeA.idNode = new StubIdNode(50, "name_a");
		StubObjectNode nodeB = widget(1, "com.example.W");
		nodeB.idNode = new StubIdNode(50, "name_b");
		StubObjectNode nodeAgain = widget(1, "com.example.W");
		nodeAgain.idNode = new StubIdNode(50, "name_a");

		Event base = eventFrom(nodeA, EventType.click);

		assertFalse("a different widget name must break equality",
				base.equals(eventFrom(nodeB, EventType.click)));
		assertTrue("positive control: matching widget name is equal",
				base.equals(eventFrom(nodeAgain, EventType.click)));
	}

	/**
	 * toString renders the documented {@code Event [type=.., handler=.., widgetId=..,
	 * widgetClass=.., widgetName=..]} shape used in GATOR/WTG debug logs.
	 */
	@Test
	public void eventToStringContainsTypeAndWidgetFields() {
		String s = eventFrom(widget(7, "com.example.Button"), EventType.click).toString();

		assertTrue("toString must include the type, got: " + s, s.contains("click"));
		assertTrue("toString must include the widget id, got: " + s, s.contains("7"));
		assertTrue("toString must include the widget class, got: " + s,
				s.contains("com.example.Button"));
	}

	// ── Transition: ctor field mapping from a WTGEdge ────────────────────

	/**
	 * A Transition built from a WTGEdge maps source/target window ids from the
	 * edge's endpoint nodes and converts the handler Set into an Event set.
	 * Concrete values: src node id=1, tgt node id=2, one click handler on a
	 * widget id=55 → sourceId=1, targetId=2, exactly one Event, no callbacks.
	 */
	@Test
	public void transitionFromEdgeExposesWindowIdsAndEvents() {
		Set<EventHandler> handlers = Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button"));
		WTGEdge e = edge(1, 2, handlers, Collections.<EventHandler>emptyList());

		Transition t = new Transition(e);

		assertEquals("sourceId comes from the edge source window id", 1, t.getSourceId());
		assertEquals("targetId comes from the edge target window id", 2, t.getTargetId());
		assertEquals("one handler yields one triggering Event", 1, t.getEvents().size());
		assertTrue("no callback handlers means an empty callback set", t.getCallbacks().isEmpty());

		Event only = t.getEvents().iterator().next();
		assertEquals("the derived Event carries the handler's type", "click", only.getType());
		assertEquals("the derived Event carries the widget id", 55, only.getWidgetId());
	}

	/**
	 * The {@code callbacks} field is populated from the edge's callback list via
	 * the same {@code toEvents} conversion — proving both conversion sites (not
	 * just the trigger handlers) are wired. Concrete values: one trigger handler
	 * plus one callback handler → events size 1 AND callbacks size 1.
	 */
	@Test
	public void transitionConvertsCallbackHandlersToEvents() {
		Set<EventHandler> handlers = Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button"));
		List<EventHandler> callbacks = Lists.newArrayList(triggerHandler(EventType.enter_text, 66, "com.example.EditText"));
		WTGEdge e = edge(1, 2, handlers, callbacks);

		Transition t = new Transition(e);

		assertEquals("trigger events still map", 1, t.getEvents().size());
		assertEquals("callback handlers map into the callbacks set", 1, t.getCallbacks().size());
		assertEquals("the callback Event carries the callback handler's type",
				"enter_text", t.getCallbacks().iterator().next().getType());
	}

	// ── Transition: equals / hashCode / toString ─────────────────────────

	/** The reflexive fast-path short-circuits equals to true. */
	@Test
	public void transitionIsReflexivelyEqual() {
		Transition t = new Transition(edge(1, 2,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList()));
		assertTrue("a Transition must equal itself", t.equals(t));
	}

	/**
	 * Two DISTINCT Transitions from structurally identical edges (same source /
	 * target ids, same single click handler, no callbacks) are equal and share a
	 * hash. Exercises equals' full happy path plus all four conjuncts true.
	 */
	@Test
	public void transitionsWithSameFieldsAreEqualAndShareHashCode() {
		Transition a = new Transition(edge(1, 2,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList()));
		Transition b = new Transition(edge(1, 2,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList()));

		assertNotSame(a, b);
		assertTrue("Transitions with identical fields must be equal", a.equals(b));
		assertEquals("equal Transitions must share a hash code", a.hashCode(), b.hashCode());
	}

	/** equals(null) returns false; positive control equals an equal sibling. */
	@Test
	public void transitionIsNotEqualToNull() {
		Transition t = new Transition(edge(1, 2,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList()));

		assertFalse("a Transition must never equal null", t.equals(null));
		assertTrue("positive control: equal to an equal-valued Transition",
				t.equals(new Transition(edge(1, 2,
						Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
						Collections.<EventHandler>emptyList()))));
	}

	/** equals against a foreign type returns false; positive control equals a real Transition. */
	@Test
	public void transitionIsNotEqualToForeignType() {
		Transition t = new Transition(edge(1, 2,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList()));

		assertFalse("a Transition must not equal a non-Transition object", t.equals("1->2"));
		assertTrue("positive control: equal to a same-valued Transition",
				t.equals(new Transition(edge(1, 2,
						Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
						Collections.<EventHandler>emptyList()))));
	}

	/**
	 * A differing SOURCE id breaks equality via the {@code sourceId == other.sourceId}
	 * conjunct — even when target and events match. Positive control: same source equal.
	 */
	@Test
	public void transitionWithDifferentSourceIdIsNotEqual() {
		Transition base = new Transition(edge(1, 2,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList()));

		assertFalse("a different source id must break equality",
				base.equals(new Transition(edge(9, 2,
						Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
						Collections.<EventHandler>emptyList()))));
		assertTrue("positive control: matching source id is equal",
				base.equals(new Transition(edge(1, 2,
						Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
						Collections.<EventHandler>emptyList()))));
	}

	/**
	 * A differing TARGET id breaks equality via the {@code targetId == other.targetId}
	 * conjunct. Positive control: same target equal.
	 */
	@Test
	public void transitionWithDifferentTargetIdIsNotEqual() {
		Transition base = new Transition(edge(1, 2,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList()));

		assertFalse("a different target id must break equality",
				base.equals(new Transition(edge(1, 9,
						Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
						Collections.<EventHandler>emptyList()))));
		assertTrue("positive control: matching target id is equal",
				base.equals(new Transition(edge(1, 2,
						Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
						Collections.<EventHandler>emptyList()))));
	}

	/**
	 * A differing EVENT set breaks equality via the {@code Objects.equals(events, ..)}
	 * conjunct — same endpoints, but one edge's handler is a click and the
	 * other's a long_click, so the derived Event sets differ. Positive control:
	 * same event set equal.
	 */
	@Test
	public void transitionWithDifferentEventsIsNotEqual() {
		Transition base = new Transition(edge(1, 2,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList()));

		assertFalse("a different triggering event must break equality",
				base.equals(new Transition(edge(1, 2,
						Sets.newHashSet(triggerHandler(EventType.long_click, 55, "com.example.Button")),
						Collections.<EventHandler>emptyList()))));
		assertTrue("positive control: matching events is equal",
				base.equals(new Transition(edge(1, 2,
						Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
						Collections.<EventHandler>emptyList()))));
	}

	/**
	 * A differing CALLBACK set breaks equality via the {@code Objects.equals(callbacks, ..)}
	 * conjunct — same endpoints and trigger event, but one edge carries a
	 * callback handler and the other does not. Positive control: same (empty)
	 * callbacks equal.
	 */
	@Test
	public void transitionWithDifferentCallbacksIsNotEqual() {
		Transition base = new Transition(edge(1, 2,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList()));

		assertFalse("a differing callback set must break equality",
				base.equals(new Transition(edge(1, 2,
						Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
						Lists.newArrayList(triggerHandler(EventType.enter_text, 66, "com.example.EditText"))))));
		assertTrue("positive control: matching empty callbacks is equal",
				base.equals(new Transition(edge(1, 2,
						Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
						Collections.<EventHandler>emptyList()))));
	}

	/**
	 * toString renders the documented {@code Transition [sourceId=.., getTargetId=..,
	 * events=.., callbacks=..]} shape with both endpoint ids.
	 */
	@Test
	public void transitionToStringContainsEndpointIds() {
		String s = new Transition(edge(3, 8,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList())).toString();

		assertTrue("toString must include the source id, got: " + s, s.contains("3"));
		assertTrue("toString must include the target id, got: " + s, s.contains("8"));
	}

	// ── Result.addTransition: the residual null-guard from Batch 1 ───────

	/**
	 * Completes {@link Result} coverage left open by the value-semantics batch:
	 * {@code addTransition} accumulates a real (non-null) Transition and takes
	 * the {@code transition != null} guard's TRUE arm, while {@code addTransition(null)}
	 * takes the FALSE arm as a silent no-op. The real Transition — built from a
	 * WTGEdge fixture — is the positive control the guard needs, which is why it
	 * lives in this batch rather than the pure-POJO one.
	 */
	@Test
	public void addTransitionAccumulatesRealTransitionAndIgnoresNull() {
		Result r = new Result();

		r.addTransition(null);
		assertTrue("a null transition must be ignored", r.getTransitions().isEmpty());

		Transition t = new Transition(edge(1, 2,
				Sets.newHashSet(triggerHandler(EventType.click, 55, "com.example.Button")),
				Collections.<EventHandler>emptyList()));
		r.addTransition(t); // positive control: a real transition DOES land
		assertEquals("a non-null transition must be added", 1, r.getTransitions().size());

		r.addTransition(null); // no-op again, alongside an existing entry
		assertEquals("a trailing null must not disturb existing entries",
				1, r.getTransitions().size());
	}
}
