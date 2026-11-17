# TLA+ patterns

Start from the smallest shape that can produce the bug. Each pattern below
names the state, the actions, the properties, and the usual failure.

## Work queue with visibility timeout

Use when a worker claims a job, processes it, and only then acknowledges it.
The dangerous window is between claim and ack.

```tla
CONSTANTS Jobs, Workers, MaxToken

VARIABLES visible, claims, processing, processed, nextToken

vars == <<visible, claims, processing, processed, nextToken>>

Init ==
    /\ visible = Jobs
    /\ claims = {}
    /\ processing = {}
    /\ processed = {}
    /\ nextToken = 1

Claim(w) ==
    /\ nextToken <= MaxToken
    /\ \E j \in visible:
        /\ visible' = visible \ {j}
        /\ claims' = claims \cup
             {[job |-> j, worker |-> w, token |-> nextToken]}
        /\ processing' = processing \cup
             {[job |-> j, worker |-> w, token |-> nextToken]}
        /\ nextToken' = nextToken + 1
        /\ UNCHANGED processed

Timeout(j) ==
    /\ \E c \in claims:
        /\ c.job = j
        /\ visible' = visible \cup {j}
        /\ claims' = claims \ {c}
        /\ UNCHANGED <<processing, processed, nextToken>>

Complete(w, j) ==
    /\ \E c \in processing:
        /\ c.job = j
        /\ c.worker = w
        /\ processing' = processing \ {c}
        /\ processed' = processed \cup {<<w, j>>}
        /\ UNCHANGED <<visible, claims, nextToken>>
```

`claims` is the server's view; `processing` is the worker's local view. Keep
them separate. If `Complete` reads `claims`, a stale worker cannot complete and
the bug disappears from the model. That is a modeling error, not a proof.

Properties:

```tla
NoDoubleProcessing ==
    \A j \in Jobs:
        Cardinality({w \in Workers : <<w, j>> \in processed}) <= 1

EventuallyProcessed ==
    \A j \in Jobs: <>(j \in {p[2] : p \in processed})
```

Add narrow fairness on the claim and complete actions before checking
liveness. Without fairness, TLC reports a stuttering trace.

The bug: `Complete` checks only the worker's local `processing` set and does
not check the current claim token. After `Timeout`, a second worker claims the
job; the first worker can still complete it. TLC finds the trace
`Claim(w1) -> Timeout -> Claim(w2) -> Complete(w1) -> Complete(w2)`.

Bound `nextToken` with `MaxToken`. Without the bound, repeated timeout and
claim makes the state space infinite. Use the smallest bound that still
produces the trace (3 tokens is enough for two claims).

Fix: pass the token to `Complete` and require that the server-side `claims`
still contains the same `[job, worker, token]` record. A stale worker cannot
complete. In code, this is a fencing token or a compare-and-set on the job
version.

## Retry with an idempotency key

Use when a client retries a request and the server may process it more than
once.

```tla
CONSTANTS Messages, Devices

VARIABLES pending, delivered

Init ==
    /\ pending = {}
    /\ delivered = [d \in Devices |-> {}]

Send(m, d) ==
    /\ pending' = pending \cup {<<m, d>>}
    /\ UNCHANGED delivered

Deliver(m, d) ==
    /\ <<m, d>> \in pending
    /\ pending' = pending \ {<<m, d>>}
    /\ delivered' = [delivered EXCEPT ![d] = @ \cup {m}]
```

`delivered[d]` is a set, so a duplicate delivery is idempotent by construction.
The property is simple:

```tla
\* BAD: tautology. Do not write this.
NoDuplicate ==
    \A d \in Devices: Cardinality(delivered[d]) = Cardinality(delivered[d])
```

That property is tautological; do not write it. The useful check is whether the
code's data structure is a set. If the code appends to a list or increments a
counter, model that structure and the duplicate becomes visible:

```tla
VARIABLES deliveries
deliveries' = Append(deliveries, <<m, d>>)
NoDuplicate ==
    \A m \in Messages: Cardinality({i \in DOMAIN deliveries :
        deliveries[i] = m}) <= 1
```

The modeling lesson: the invariant is only as strong as the state you keep.

## Notification fan-out across devices

Use when one event must reach every device, and devices go offline and
reconnect.

```tla
CONSTANTS Devices, Messages

VARIABLES online, outbox, inbox, acked

Init ==
    /\ online = Devices
    /\ outbox = [d \in Devices |-> {}]
    /\ inbox = [d \in Devices |-> {}]
    /\ acked = [d \in Devices |-> {}]

Offline(d) ==
    /\ online' = online \ {d}
    /\ UNCHANGED <<outbox, inbox, acked>>

Online(d) ==
    /\ online' = online \cup {d}
    /\ UNCHANGED <<outbox, inbox, acked>>

Enqueue(d, m) ==
    /\ d \in online
    /\ outbox' = [outbox EXCEPT ![d] = @ \cup {m}]
    /\ UNCHANGED <<online, inbox, acked>>

Deliver(d, m) ==
    /\ d \in online
    /\ m \in outbox[d]
    /\ outbox' = [outbox EXCEPT ![d] = @ \ {m}]
    /\ inbox' = [inbox EXCEPT ![d] = @ \cup {m}]
    /\ UNCHANGED <<online, acked>>

Ack(d, m) ==
    /\ m \in inbox[d]
    /\ acked' = [acked EXCEPT ![d] = @ \cup {m}]
    /\ UNCHANGED <<online, outbox, inbox>>
```

Properties:

```tla
NoAckWithoutDelivery ==
    \A d \in Devices: acked[d] \subseteq inbox[d]

InboxWellFormed ==
    \A d \in Devices: inbox[d] \subseteq Messages

\* With weak fairness on Deliver for online devices:
EventuallyDelivered ==
    \A d \in Devices: \A m \in Messages:
        (d \in online /\ m \in outbox[d]) ~> (m \in inbox[d])
```

Common bugs: `Enqueue` drops a message while the device is offline; `Online`
clears the outbox; the server resends everything on reconnect and the client
does not dedupe. Model the drop explicitly if the code drops.

## Lease-based leader election

Use when a leader holds a time-bounded lease and renews it. The dangerous case
is a process pause longer than the lease.

```tla
CONSTANTS Nodes, MaxTime, LeaseDuration

VARIABLES now, leaseOwner, leaseExpiry, believesLeader, paused

vars == <<now, leaseOwner, leaseExpiry, believesLeader, paused>>

Init ==
    /\ now = 0
    /\ leaseOwner = "none"
    /\ leaseExpiry = 0
    /\ believesLeader = [n \in Nodes |-> FALSE]
    /\ paused = {}

Tick ==
    /\ now < MaxTime
    /\ now' = now + 1
    /\ believesLeader' = [n \in Nodes |->
         IF n \in paused \/ leaseExpiry > now + 1
         THEN believesLeader[n] ELSE FALSE]
    /\ UNCHANGED <<leaseOwner, leaseExpiry, paused>>

Acquire(n) ==
    /\ n \notin paused
    /\ leaseOwner = "none" \/ leaseExpiry <= now
    /\ leaseOwner' = n
    /\ leaseExpiry' = now + LeaseDuration
    /\ believesLeader' = [believesLeader EXCEPT ![n] = TRUE]
    /\ UNCHANGED <<now, paused>>

Renew(n) ==
    /\ n \notin paused
    /\ leaseOwner = n
    /\ believesLeader[n]
    /\ leaseExpiry > now
    /\ leaseExpiry' = now + LeaseDuration
    /\ UNCHANGED <<now, leaseOwner, believesLeader, paused>>

Pause(n) ==
    /\ n \notin paused
    /\ paused' = paused \cup {n}
    /\ UNCHANGED <<now, leaseOwner, leaseExpiry, believesLeader>>

Resume(n) ==
    /\ n \in paused
    /\ paused' = paused \ {n}
    /\ UNCHANGED <<now, leaseOwner, leaseExpiry, believesLeader>>

Next ==
    \/ Tick
    \/ \E n \in Nodes: Acquire(n) \/ Renew(n) \/ Pause(n) \/ Resume(n)

Spec == Init /\ [][Next]_vars
\* Safety only. Add narrow fairness on Acquire/Renew for liveness.
```

`leaseOwner` and `leaseExpiry` are the server's view. `believesLeader` is each
node's local view. The gap between them is the bug.

Property:

```tla
AtMostOneLeader ==
    Cardinality({n \in Nodes : believesLeader[n]}) <= 1
```

The bug: a paused node keeps `believesLeader[n] = TRUE`. Its lease expires,
another node acquires, and now two nodes believe they are leader. TLC finds the
trace `Acquire(n1) -> Pause(n1) -> Tick ... -> Acquire(n2)`. If n1 resumes, it
may still act as leader.

Fix: a fencing token or a lease check at every write. On resume, the old
leader must renew before acting; if the lease is gone, it steps down. In code,
put the token in the write path, not only in the election loop.

## Cache coherence and read-your-writes

Use when a client reads from a local cache and writes go through a different
path.

Shape:

- `store`: the source of truth, with a version.
- `cache`: a per-node value plus the version it was filled from.
- `Write(v)`: increments the store version and updates the store.
- `Fill(n)`: copies the store value and version into the cache.
- `Invalidate(n)`: clears the cache entry.
- `Read(n)`: reads the cache if present, otherwise fills from the store.

Properties:

- A cached value's version is not newer than the store version.
- After a client's write returns, that client's next read sees the write
  (read-your-writes).
- No stale read after invalidation is acknowledged.

Common bug: `Write` updates the store but does not invalidate other caches.
The model shows a stale read. The fix is an invalidation protocol or a
version check on read; the spec tells you which one closes the window.

## Saga with compensation

Use when a multi-step workflow can fail after some steps have committed.

Shape:

- `step`: a function from transaction to a bounded step number.
- `committed`: the set of steps that have committed.
- `compensated`: the set of steps that have been compensated.
- `Do(t)`: advance a transaction if its precondition holds.
- `Fail(t)`: mark a transaction failed.
- `Compensate(t)`: run the compensating action for a committed step.

Properties:

- No transaction is marked done while a committed step lacks compensation.
- A failed transaction eventually compensates every committed step
  (liveness, with fairness).
- A compensation is idempotent.

Common bug: failure between a commit and its compensation leaves a partial
state. Model the crash window explicitly; do not make commit and compensation
one atomic action if the code has a window between them.

## Pattern selection

| Symptom | Pattern |
| --- | --- |
| Two workers process the same job | Visibility timeout plus fencing token |
| Duplicate side effect after retry | Idempotency key |
| Missing or duplicate notification after reconnect | Fan-out with outbox and dedupe |
| Two leaders after a pause | Lease plus fencing token |
| Stale read after a write | Cache coherence |
| Partial state after a mid-workflow failure | Saga with compensation |
