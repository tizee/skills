---- MODULE Spec ----
\* Change the module name to match the file name when you copy this file.
\* Starting point for a work-queue model. Replace Items, Workers, and the
\* actions with the protocol you are checking. Keep the model smaller than the
\* code: model the commit points and the failure modes, not the payloads.
EXTENDS Naturals, FiniteSets

CONSTANTS Items, Workers

VARIABLE queue, inFlight, done

vars == <<queue, inFlight, done>>

Init ==
    /\ queue = Items
    /\ inFlight = {}
    /\ done = {}

\* Map: Claim(job) -> worker.claim(job)
\* Claim and removal are one atomic step. If the real system leaves the job
\* visible until an ack, split this action and add a visibility timeout.
Claim(w) ==
    /\ \E j \in queue:
        /\ queue' = queue \ {j}
        /\ inFlight' = inFlight \cup {<<w, j>>}
        /\ UNCHANGED done

\* Map: Complete(job) -> worker.complete(job)
Complete(w, j) ==
    /\ <<w, j>> \in inFlight
    /\ inFlight' = inFlight \ {<<w, j>>}
    /\ done' = done \cup {j}
    /\ UNCHANGED queue

Next ==
    \/ \E w \in Workers: Claim(w)
    \/ \E w \in Workers: \E j \in Items: Complete(w, j)

Fairness ==
    \A w \in Workers:
        WF_vars(Claim(w) \/ \E j \in Items: Complete(w, j))

Spec == Init /\ [][Next]_vars /\ Fairness

TypeOK ==
    /\ queue \subseteq Items
    /\ inFlight \subseteq Workers \X Items
    /\ done \subseteq Items

\* Safety: a job is never in flight for two workers at once.
NoDoubleClaim ==
    \A j \in Items:
        Cardinality({w \in Workers : <<w, j>> \in inFlight}) <= 1

\* Liveness: every job is eventually done.
EventuallyDone ==
    \A j \in Items: <>(j \in done)

====
