---
urls:
  - https://www.gnu.org/prep/standards/html_node/Writing-C.html
  - https://wiki.sei.cmu.edu/confluence/display/c/PRE06-C.+Enclose+header+files+in+an+include+guard
---

# File Layout

The first screen of a file teaches its complete vocabulary. A reader who starts at line 1 should meet every constant, type, and function contract before meeting any logic.

## `.c` file order

1. **File comment** -- one or two lines stating what this module *owns* and does.
2. **Includes** -- system headers, blank line, project headers. Alphabetical within each group.
3. **Constants** -- `enum` first, then `#define`.
4. **Types** -- structs, unions, typedefs.
5. **Prototypes for every `static` function**, each with its contract comment.
6. **Public function definitions**, in the same order as the header declares them.
7. **`static` function definitions**, in call order.

Static prototypes at the top are not redundancy: they are the module's table of contents, and they let definitions appear in call order without forward-reference errors.

## `.h` file order

Include guard, includes, constants, types, prototypes. Nothing else -- no function bodies, no variable definitions.

```c
#ifndef SENSOR_H
#define SENSOR_H

#include <stdint.h>

typedef enum {
    SENSOR_OK        = 0,
    SENSOR_ERR_ARG   = -1,
    SENSOR_ERR_BUS   = -2,
    SENSOR_ERR_RANGE = -3
} sensor_status_t;

typedef struct sensor sensor_t;

/* Reads one sample. Writes millidegrees on success. s and out_millideg
 * must be non-NULL. Fails with SENSOR_ERR_BUS when the bus read fails. */
sensor_status_t sensor_poll(sensor_t *s, int32_t *out_millideg);

#endif /* SENSOR_H */
```

- The header is the contract. Everything a caller needs, nothing more.
- Include guards use the module name, never `#pragma once` in portable code unless the project already standardized on it.
- Headers include what they use, and nothing they do not. If a header needs only a pointer to a type, forward-declare (`typedef struct sensor sensor_t;`) instead of including the defining header.
- Never `#include` a `.c` file. Never define a non-`static` variable in a header.

## Include hygiene

- A `.c` file includes its own header first in the project group, so the header is proven self-sufficient.
- No transitive-include reliance: if you call `memcpy`, include `<string.h>` yourself.
- System headers in `<>`, project headers in `""`.

## Anti-Pattern

```c
#include "util.h"          /* what does this give me? */

static int helper(int x);  /* no contract comment */

int mod_run(int x)
{
    return helper(x) * 3;  /* 3 = ? */
}

#define MOD_SCALE 3        /* constant defined below its use */

static int helper(int x) { return x + MOD_SCALE; }
```

A reader hits `helper` and `3` before knowing what either means, and `MOD_SCALE` is defined after the code that conceptually depends on it.

## Positive Pattern

```c
/* sensor.c: owns polling and conversion for the temperature sensor. */

#include <assert.h>
#include <stdint.h>

#include "bus.h"
#include "sensor.h"

enum {
    SENSOR_POLL_INTERVAL_MS = 250,
    SENSOR_RAW_MAX          = 4095,
    SENSOR_SCALE_MILLIDEG   = 62
};

struct sensor {
    bus_t   *bus;            /* borrowed, never owned */
    int32_t  last_millideg;
};

/* Rejects a NULL sensor or output pointer. Fails with SENSOR_ERR_ARG. */
static sensor_status_t sensor_validate_poll_args(const sensor_t *s,
                                                 const int32_t *out_millideg);

/* Adapter over bus_read_u16. Fails with SENSOR_ERR_BUS. */
static sensor_status_t sensor_read_raw(sensor_t *s, uint16_t *out_raw);

/* Rejects raw samples above hardware range. Fails with SENSOR_ERR_RANGE. */
static sensor_status_t sensor_validate_raw(uint16_t raw);

/* Caches the converted sample on the sensor. Returns it in millidegrees. */
static int32_t sensor_record(sensor_t *s, uint16_t raw);

/* Converts a raw sample to millidegrees. Pure. */
static int32_t sensor_convert(uint16_t raw);

sensor_status_t sensor_poll(sensor_t *s, int32_t *out_millideg)
{
    SENSOR_TRY(sensor_validate_poll_args(s, out_millideg));

    uint16_t raw = 0;
    SENSOR_TRY(sensor_read_raw(s, &raw));
    SENSOR_TRY(sensor_validate_raw(raw));

    *out_millideg = sensor_record(s, raw);
    return SENSOR_OK;
}

/* ... static definitions follow, in call order ... */
```

`sensor_poll` is a plan, not a procedure: five lines that name every step. The vocabulary above it answers every question the plan raises.

## Formatting mechanics

- 4-space indent, no tabs. 100-column limit.
- One statement per line. One declaration per line.
- Function opening brace on its own line; control-flow braces on the same line.
- A single-statement guard clause may omit braces with the statement on the next line. Everything else is braced.
- Let `clang-format` own this. Check in a `.clang-format` and stop discussing it.

## Comments

- Above every prototype: one contract comment stating what the function does, ownership and nullability of every pointer, and the failure modes. Never restate the signature.
- If the contract comment needs the word "and", the function does two things -- split it.
- Inside bodies: comment *why*, never *what*. The code already says what.
- No commented-out code, ever. Version control remembers.
