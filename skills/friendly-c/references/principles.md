---
urls:
  - https://spinroot.com/gerard/pdf/P10.pdf
  - https://www.sonarsource.com/docs/CognitiveComplexity.pdf
  - https://wiki.sei.cmu.edu/confluence/display/c/SEI+CERT+C+Coding+Standard
---

# Core Principles

## Goals

- Any 40-line region should be understandable without reading the rest of the program.
- Every symbol should grep to a small, complete set of sites: one definition, few producers, obvious consumers.
- Every invariant the compiler cannot check should be visible as a name, a type, or an `assert`.

## Decision Order

1. Correctness and defined behavior
2. Legibility and locality
3. Change cost
4. Performance

## Principles

- **Locality beats cleverness.** The cost of C code is not the time to write it, it is the working memory needed to change it two years later. Prefer the version where a reader carries less state per line.
- **Teach the vocabulary before the logic.** A file's first screen states what the module owns, its constants, its types, and its function contracts. A reader should never meet an unexplained symbol and have to search downward.
- **Names are the only documentation that cannot go stale in the wrong direction.** A magic number is a fact with no grep anchor; a named constant is self-documenting at every use site and editable in one place.
- **One concept, one home.** Logic never appears twice. The second occurrence becomes a named function the moment it is written, because a later editor patching one copy has nothing telling them the other copy exists.
- **Make illegal states hard to build.** Tag every union, name every status, initialize at declaration, `const` every pointer you do not write through. C will not stop you, so shape the code so the mistake looks wrong.
- **Assertions are machine-checked comments.** They state what must stay true, at zero release cost, exactly where an editor is about to change something.
- **Fail loudly at the boundary, assume internally.** One validation site per public entry point; internal helpers assert instead of re-validating. Validation duplicated at every level is noise that hides logic.
- **Bound everything.** Every loop has a statically evident upper bound, every buffer write has a length, every allocation has a matching release next to it.
- **Measure before optimizing.** Modern compilers defeat most hand-optimization. Profile, then change the algorithm or the memory access pattern -- not the brace style.

## Anti-Pattern

Logic and plan interleaved, state accumulating, nothing greppable:

```c
int process(cfg_t *cfg, char *in, int n, char *out)
{
    if (cfg && in && out && n > 0) {
        for (int i = 0; i < n; i++) {
            if (in[i] != 0) {
                if (in[i] >= 'a' && in[i] <= 'z') {
                    out[i] = in[i] - 32;   /* magic 32, depth 3 */
                    cfg->count++;
                } else {
                    out[i] = in[i];
                }
            }
        }
        return 0;
    }
    return -1;
}
```

Four problems, all locality problems: `-1`/`0` carry no name, `32` carries no meaning, the loop body mixes classification with mutation, and the happy path is indented three levels behind a success-shaped `if`.

## Positive Pattern

```c
/* Uppercases ASCII letters into out, counting conversions on cfg.
 * out must hold at least len bytes. Fails with TEXT_ERR_ARG. */
text_status_t text_upper(text_cfg_t *cfg, char *out, const char *in, size_t len)
{
    if (cfg == NULL || in == NULL || out == NULL)
        return TEXT_ERR_ARG;

    for (size_t i = 0; i < len; i++) {
        out[i] = text_upper_char(in[i]);
        if (out[i] != in[i])
            cfg->converted_count++;
    }
    return TEXT_OK;
}

/* Maps one ASCII byte to its uppercase form. Pure. */
static char text_upper_char(char c)
{
    if (c < 'a' || c > 'z')
        return c;
    return (char)(c - TEXT_CASE_DELTA);
}
```

Guards discharge preconditions first, the happy path sits at the left margin, the classification rule has exactly one home, and `TEXT_CASE_DELTA` greps to one definition.

## Provenance

These rules are not aesthetic preferences; each was earned:

- **Power of 10** (Holzmann, NASA/JPL): bounded loops, no recursion, smallest scope, check every return value, two assertions per function. Its ban on allocation after init is flight-software law and is *not* adopted here.
- **Cognitive Complexity** (Campbell, SonarSource): the formal basis for the nesting cap -- the metric charges each break in linear flow and charges nesting progressively.
- **CERT C / MISRA C**: adopted in spirit -- no reliance on undefined behavior, every warning an error. Explicitly rejected: the single-exit-point rule, because early returns are what keep nesting flat.
- **Kernighan & Pike**: simplicity, clarity, generality, in that order.
- **Hanson, *C Interfaces and Implementations***: the module-as-interface discipline, and ownership stated at the interface.
