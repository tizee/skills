---
urls:
  - https://spinroot.com/gerard/pdf/P10.pdf
---

# Worked Example: Good but Not Good Enough

Most C fails subtly, not grossly. The function below passes generic review -- short, flat, guarded, no magic numbers -- and still fails this standard. Learning to see *this* class of miss is the point of the exercise.

## Stage 0: the near miss

```c
uint16_t map_eat(map_t *map, map_pos_t pos)
{
    map_cell_t cell;
    if (map == NULL)
        return 0;
    if (!map_is_inside(pos))
        return 0;
    cell = map->cells[pos.row][pos.col];
    if (cell == MAP_CELL_PELLET) {
        map->cells[pos.row][pos.col] = MAP_CELL_EMPTY;
        map->pellet_count--;
        return MAP_SCORE_PELLET;
    }
    if (cell == MAP_CELL_POWER) {
        map->cells[pos.row][pos.col] = MAP_CELL_EMPTY;
        map->pellet_count--;
        return MAP_SCORE_POWER;
    }
    return 0;
}
```

The tells, in order of weight:

1. **The consume block is pasted twice.** Clearing the cell and decrementing the count is one concept written in two places. The moment the second branch was written, `map_consume_cell` should have been born. An editor adding a side effect to consumption -- a sound cue, a dirty flag -- will patch one copy and miss the other, because nothing links them.
2. **The branches encode data as control flow.** Cell type to score is a *mapping*, not logic. A mapping belongs in one lookup leaf, where the next cell type costs one line instead of one pasted block.
3. **Three concepts interleave in one body**: deciding edibility, awarding score, mutating the map. No single question about this function has a single home.
4. **`map_cell_t cell;` sits uninitialized above the guards.** Declare at first valid value.

## The near-miss test

Run this on any existing function that "looks fine":

- Is any mutation sequence written more than once?
- Is any `if` chain really a table?
- Does the body answer more than one question?
- Is any declaration above its first valid value?
- Does any return value serve double duty as data and as failure?

Judge the refactor by the cost of the next change, not by the line count of the diff.

## Stage 1: behavior-preserving decomposition

Signature preserved, so this stage is safe to land under any scope constraint:

```c
/* True when the cell can be eaten. Pure. */
static bool map_cell_is_edible(map_cell_t cell);

/* Score for consuming a cell. Zero for inedible cells. Pure. */
static uint16_t map_cell_score(map_cell_t cell);

/* Empties the cell and updates pellet accounting. */
static void map_consume_cell(map_t *map, map_pos_t pos);

uint16_t map_eat(map_t *map, map_pos_t pos)
{
    if (map == NULL)
        return 0;
    if (!map_is_inside(pos))
        return 0;

    map_cell_t cell = map->cells[pos.row][pos.col];
    if (!map_cell_is_edible(cell))
        return 0;

    map_consume_cell(map, pos);
    return map_cell_score(cell);
}

static bool map_cell_is_edible(map_cell_t cell)
{
    return cell == MAP_CELL_PELLET || cell == MAP_CELL_POWER;
}

static uint16_t map_cell_score(map_cell_t cell)
{
    switch (cell) {
    case MAP_CELL_PELLET:
        return MAP_SCORE_PELLET;
    case MAP_CELL_POWER:
        return MAP_SCORE_POWER;
    default:
        return 0;
    }
}

static void map_consume_cell(map_t *map, map_pos_t pos)
{
    map->cells[pos.row][pos.col] = MAP_CELL_EMPTY;
    map->pellet_count--;
}
```

**The proof is change cost.** Add a fruit cell: the original grows a third pasted block, and the next editor patches two of three copies. The refactor grows one line in `map_cell_is_edible` and one in `map_cell_score`. Grep improves the same way -- "what mutates cells" now has exactly one answer.

If edibility is exactly "scores nonzero", both pure leaves collapse into one `static const` score table indexed by cell type, with zero branches. State that invariant in a comment above the table if you take that step.

## Stage 2: full conformance

Stage 1 kept one violation on purpose: **the signature fuses failure with score**, returning `0` for a NULL map, an out-of-bounds position, and an ordinary empty cell alike. Pushed to full conformance, the module becomes two files.

```c
/* map.h */
#ifndef MAP_H
#define MAP_H

#include <stddef.h>
#include <stdint.h>

enum {
    MAP_ROWS = 31,
    MAP_COLS = 28
};

typedef enum {
    MAP_CELL_EMPTY  = 0,
    MAP_CELL_WALL   = 1,
    MAP_CELL_PELLET = 2,
    MAP_CELL_POWER  = 3
} map_cell_t;

typedef enum {
    MAP_OK         =  0,
    MAP_ERR_ARG    = -1,
    MAP_ERR_BOUNDS = -2
} map_status_t;

enum {
    MAP_SCORE_PELLET = 10,
    MAP_SCORE_POWER  = 50
};

typedef struct {
    size_t row;
    size_t col;
} map_pos_t;

typedef struct {
    map_cell_t cells[MAP_ROWS][MAP_COLS];
    size_t     pellet_count;
} map_t;

/* Consumes the cell at pos if edible. Writes the score awarded, zero when
 * nothing edible is there. Fails with MAP_ERR_ARG on a NULL pointer and
 * MAP_ERR_BOUNDS on an out-of-range position. */
map_status_t map_eat(map_t *map, uint16_t *out_score, map_pos_t pos);

#endif /* MAP_H */
```

```c
/* map.c: owns the play grid, cell consumption, and pellet accounting. */

#include <assert.h>
#include <stdbool.h>

#include "map.h"

/* Propagates any non-OK status to the caller. Permitted only in
 * functions that acquire nothing. Sole macro allowed to return. */
#define MAP_TRY(expr)                       \
    do {                                    \
        map_status_t map_try_s_ = (expr);   \
        if (map_try_s_ != MAP_OK)           \
            return map_try_s_;              \
    } while (0)

/* Rejects NULL map or output pointers. Fails with MAP_ERR_ARG. */
static map_status_t map_validate_eat_args(const map_t *map,
                                          const uint16_t *out_score);

/* Rejects positions outside the grid. Fails with MAP_ERR_BOUNDS. */
static map_status_t map_validate_pos(map_pos_t pos);

/* Consumes the cell at pos if edible. Returns the score awarded, zero
 * otherwise. */
static uint16_t map_consume_at(map_t *map, map_pos_t pos);

/* True when the cell can be eaten. Pure. */
static bool map_cell_is_edible(map_cell_t cell);

/* Score for consuming a cell. Zero for inedible cells. Pure. */
static uint16_t map_cell_score(map_cell_t cell);

/* Empties the cell and updates pellet accounting. */
static void map_consume_cell(map_t *map, map_pos_t pos);

/* The only two functions that touch cell storage. */
static map_cell_t map_cell_at(const map_t *map, map_pos_t pos);
static void map_set_cell(map_t *map, map_pos_t pos, map_cell_t cell);

map_status_t map_eat(map_t *map, uint16_t *out_score, map_pos_t pos)
{
    MAP_TRY(map_validate_eat_args(map, out_score));
    MAP_TRY(map_validate_pos(pos));

    *out_score = map_consume_at(map, pos);
    return MAP_OK;
}

static map_status_t map_validate_eat_args(const map_t *map,
                                          const uint16_t *out_score)
{
    if (map == NULL)
        return MAP_ERR_ARG;
    if (out_score == NULL)
        return MAP_ERR_ARG;
    return MAP_OK;
}

static map_status_t map_validate_pos(map_pos_t pos)
{
    if (pos.row >= (size_t)MAP_ROWS)
        return MAP_ERR_BOUNDS;
    if (pos.col >= (size_t)MAP_COLS)
        return MAP_ERR_BOUNDS;
    return MAP_OK;
}

static uint16_t map_consume_at(map_t *map, map_pos_t pos)
{
    map_cell_t cell = map_cell_at(map, pos);
    if (!map_cell_is_edible(cell))
        return 0;

    map_consume_cell(map, pos);
    return map_cell_score(cell);
}

static bool map_cell_is_edible(map_cell_t cell)
{
    return cell == MAP_CELL_PELLET || cell == MAP_CELL_POWER;
}

static uint16_t map_cell_score(map_cell_t cell)
{
    switch (cell) {
    case MAP_CELL_PELLET:
        return MAP_SCORE_PELLET;
    case MAP_CELL_POWER:
        return MAP_SCORE_POWER;
    default:
        return 0;
    }
}

static void map_consume_cell(map_t *map, map_pos_t pos)
{
    assert(map->pellet_count > 0);
    map_set_cell(map, pos, MAP_CELL_EMPTY);
    map->pellet_count--;
}

static map_cell_t map_cell_at(const map_t *map, map_pos_t pos)
{
    return map->cells[pos.row][pos.col];
}

static void map_set_cell(map_t *map, map_pos_t pos, map_cell_t cell)
{
    map->cells[pos.row][pos.col] = cell;
}
```

## What stage 2 bought

- **Every failure has a name and exactly one producing validator.** Normal gameplay never wears an error's clothes: an empty cell is `MAP_OK` with score zero.
- **`MAP_TRY` collapses the propagation**, safe because `map_eat` acquires nothing.
- **`map_cell_at` and `map_set_cell` own every touch of cell storage**, so the row-major indexing convention lives in two adjacent lines and "what mutates cells" greps to one.
- **`map_consume_cell` asserts the accounting invariant instead of re-validating** -- the public boundary already proved the arguments.
- Parameter order follows context, outputs, inputs throughout.

## Choosing a stage

Stage 1 is the default for an edit inside an existing codebase: it preserves the signature, so it cannot break a caller. Stage 2 requires the task's scope to permit an API change; do not silently widen a bug fix into a header change.

## The meta-lesson

Stage 2 forced two amendments to the function-altitude rules: **orchestrators may branch on named predicates**, and **leaves may call the module's own accessors**. That is how a standard stays useful -- it is grown by feeding it code that breaks it, and each break becomes a rule or an amendment. Apply the same process to any codebase adopting these rules.
