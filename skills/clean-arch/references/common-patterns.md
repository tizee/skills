# Common Patterns & Solutions

## Pattern: Dependency Rule Violation

**Problem**:
```typescript
// ❌ Domain layer imports from Infrastructure
import { UserRepository } from '../infrastructure/UserRepository';

export class CreateUserUseCase {
  constructor(private repo: UserRepository) {} // Concrete dependency
}
```

**Solution**:
```typescript
// ✅ Domain layer defines interface
export interface IUserRepository {
  save(user: User): Promise<void>;
  findById(id: string): Promise<User | null>;
}

export class CreateUserUseCase {
  constructor(private repo: IUserRepository) {} // Abstract dependency
}

// Infrastructure implements interface
export class UserRepository implements IUserRepository {
  // Implementation details here
}
```

---

## Pattern: God Class

**Problem**:
```typescript
// ❌ Class does too much
export class OrderManager {
  createOrder() {}
  cancelOrder() {}
  processPayment() {}    // Should be in PaymentService
  sendEmail() {}         // Should be in EmailService
  updateInventory() {}   // Should be in InventoryService
  generateReport() {}  // Should be in ReportService
}
```

**Solution**:
```typescript
// ✅ Each class has single responsibility
export class OrderService {
  constructor(
    private paymentService: PaymentService,
    private emailService: EmailService,
    private inventoryService: InventoryService
  ) {}
  
  async createOrder(orderData: OrderData) {
    // Orchestrate, don't implement
    await this.inventoryService.reserve(orderData.items);
    const payment = await this.paymentService.charge(orderData.payment);
    await this.emailService.sendConfirmation(orderData.customer);
    // ...
  }
}
```

---

## Pattern: Feature Envy

**Problem**:
```typescript
// ❌ Order uses Customer's data extensively
export class Order {
  calculateDiscount(customer: Customer): number {
    if (customer.isVIP() && customer.getYearsAsCustomer() > 5) {
      return this.total * 0.2;
    }
    return 0;
  }
}
```

**Solution**:
```typescript
// ✅ Move method to the class it envies
export class Customer {
  calculateDiscount(orderTotal: number): number {
    if (this.isVIP() && this.yearsAsCustomer > 5) {
      return orderTotal * 0.2;
    }
    return 0;
  }
}

export class Order {
  calculateDiscount(customer: Customer): number {
    return customer.calculateDiscount(this.total);
  }
}
```

---

## Pattern: Control-Plane / Data-Plane Isolation via Typed Command Channel

**Problem**: A control interface (HTTP API, CLI, admin RPC) reaches directly into core engine state, sharing mutable structures across threads. Transport concerns (parsing, status codes) leak into the engine, and every new control operation risks a data race.

```rust
// ❌ API thread mutates engine state directly under a shared lock.
struct ApiHandler { engine: Arc<Mutex<Engine>> }
impl ApiHandler {
    fn handle(&self, req: HttpRequest) {
        let mut e = self.engine.lock().unwrap();
        e.vcpus[0].pause();          // transport thread now drives core internals
        e.status = parse_status(req); // HTTP parsing tangled into engine state
    }
}
```

**Solution**: Make the boundary a *typed message enum* over a channel. The control plane only constructs commands; the core owns all state and processes commands in its own event loop. No shared mutable state crosses the boundary.

```rust
// ✅ The only thing that crosses the boundary is a typed, transport-agnostic command.
enum EngineAction { Pause, Resume, Start, Snapshot(SnapshotParams) }
enum EngineResponse { Ok, Paused, Error(EngineError) }

// Control plane: parse transport -> command, send, await response.
struct ApiServer { to_core: Sender<EngineAction>, from_core: Receiver<EngineResponse> }

// Core: single owner of state, drains the command channel in its event loop.
struct Core { /* owns all engine state */ }
impl Core { fn handle(&mut self, action: EngineAction) -> EngineResponse { /* ... */ } }
```

**Why it matters**: The command enum is an auditable contract; adding a transport (gRPC, CLI) means adding a translator, not touching the core. The core is testable without booting the transport, and the "no shared mutable state" rule is enforced by construction, not discipline.

> Source: adapted from firecracker — HTTP API server and VMM core communicate
> only through a typed `VmmAction` / `VmmResponse` enum over an MPSC channel plus
> an eventfd; the API thread never touches VMM state directly.

---

## Pattern: Persistence Seam — Serializable State vs Runtime Reconstruction Args

**Problem**: The snapshot/save type is the live runtime object, so persisted blobs capture file descriptors, threads, or raw pointers — values that are meaningless (or dangerous) when restored in another process.

```rust
// ❌ Serializing the live object drags non-portable, untrusted handles into the blob.
#[derive(Serialize, Deserialize)]
struct Device { fd: RawFd, thread: JoinHandle<()>, config: Config } // fd/thread can't survive
```

**Solution**: Split a `Persist`-style trait into a plain serializable `State` and separate `ConstructorArgs` supplied at restore time. The blob holds only portable data; live handles are rebuilt from the current environment and re-validated, never trusted from disk.

```rust
// ✅ State is pure data; the runtime provides fresh handles at restore.
trait Persist {
    type State;            // Serde-serializable POD only
    type ConstructorArgs;  // fresh fds / memory / callbacks from the live process
    type Error;
    fn save(&self) -> Self::State;
    fn restore(args: Self::ConstructorArgs, state: &Self::State) -> Result<Self, Self::Error>;
}
```

**Why it matters**: This is dependency inversion applied to persistence — the stored format depends on nothing runtime-specific, so it stays portable and forward-compatible. Restore becomes a validation boundary (a trust boundary: re-check the blob), not a blind rehydrate.

> Source: adapted from firecracker — the `Persist` trait separates a serializable
> `State` from `ConstructorArgs`, so snapshots never persist fds or threads.

---

## Pattern: Explicit State-Transition Table

**Problem**: A protocol or lifecycle state machine is enforced by scattered `if` checks, so illegal transitions slip through and conformance to the spec is unverifiable.

```rust
// ❌ Transition rules smeared across the codebase; easy to miss a case.
fn set_status(&mut self, new: u32) {
    if new == DRIVER_OK { self.status = new; } // which prior states are legal? unclear
    else { self.status = new; }
}
```

**Solution**: Encode legal transitions as one explicit table (or exhaustive `match` on an enum) and reject anything not in it. The closed set of states lives in one auditable place.

```rust
// ✅ The whole state machine is one table; illegal transitions are rejected uniformly.
const VALID_TRANSITIONS: &[(Status, Status)] = &[
    (Init, Acknowledge),
    (Acknowledge, Driver),
    (Driver, FeaturesOk),
    (FeaturesOk, DriverOk),
];
fn set_status(&mut self, new: Status) -> Result<(), Error> {
    if VALID_TRANSITIONS.contains(&(self.status, new)) { self.status = new; Ok(()) }
    else { Err(Error::IllegalTransition(self.status, new)) }
}
```

**Why it matters**: Model closed sets of states with an enum and closed sets of transitions with a table — invalid states become unrepresentable or uniformly rejectable, and the table doubles as executable documentation of the spec. It is the concrete form of "are state transitions explicit and validated?" in the production-robustness checks.

> Source: adapted from firecracker — the virtio MMIO transport validates driver
> status changes against an explicit `VALID_TRANSITIONS` table.

---

# Decision Tables

## When to Extract Method vs Extract Class

| Scenario | Action | Example |
|----------|--------|---------|
| Method > 20 lines, but uses only local data | Extract Method | Complex calculation in service |
| Method > 20 lines, uses different data groups | Extract Class | Order processing with payment + shipping logic |
| Class > 200 lines, multiple responsibilities | Extract Class | UserManager with auth + profile + preferences |
| Related methods share subset of fields | Extract Class | Reporting methods using date range |

## When to Use Inheritance vs Composition

| Use Inheritance When | Use Composition When |
|---------------------|---------------------|
| True "is-a" relationship | "has-a" or "uses-a" relationship |
| Subclass is always a valid substitute | Behavior varies at runtime |
| Code reuse of interface + implementation | Only need to reuse implementation |
| Small, stable base class | Multiple sources of behavior |

## Repository vs Service vs Use Case

| Component | Responsibility | Example |
|-----------|---------------|---------|
| **Repository** | Data access, persistence | `userRepo.findById()`, `orderRepo.save()` |
| **Domain Service** | Business logic spanning aggregates | `pricingService.calculateTotal()` |
| **Application Service** | Orchestrate use case flow | `createOrderUseCase.execute()` |
| **Controller** | HTTP handling, input validation | `orderController.create()` |
