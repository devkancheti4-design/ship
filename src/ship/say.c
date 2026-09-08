/* say.c - THE SAY LAW. GENERATED; every expression authored by search.
 *
 * For ONE working-tree change, what KIND of claim may its subject line make?
 * Replaces the language model as the eyes of the SHIP law: the model wrote
 * prose, this rules the claim, and the body fills the nouns from measurement.
 *
 *   0 revert  the change undoes a recorded commit
 *   1 style   alters no token, only whitespace
 *   2 test    every changed path is a test
 *   3 docs    every changed path is documentation
 *   4 build   every changed path is manifest, lockfile, build or CI
 *   5 feat    a focused change introduces a new definition
 *   6 fix     a focused change adds a guard to an existing definition
 *   7 plain   no claim: describe the change, never diagnose it
 *
 *   bit 0 INVERSE   bit 1 BLANK    bit 2 TESTSONLY  bit 3 DOCSONLY
 *   bit 4 DEPSONLY  bit 5 NEWDEF   bit 6 GUARD      bit 7 FOCUSED
 *
 * WHY R1-R4 HOLD STRUCTURALLY
 *
 * The ladder rungs already sit at the observation bit positions, so no
 * encoding step exists to get wrong.  R1: every shape bit occupies mask bit
 * 0..4 and every content bit 5..6, so ctz reads a shape first whenever one
 * exists - content cannot outrank shape because it lives above it, and the
 * order INVERSE < BLANK < TESTSONLY < DOCSONLY < DEPSONLY is that same fact
 * among the shapes themselves.  R2: CONTENT is ANDed with gf = 0 - FOCUSED,
 * identically zero until FOCUSED is set, so a diffuse change carries no feat
 * or fix bit in its word at all - "feat: add helper" over 40 files is not
 * merely discouraged, it is unrepresentable.  R3: NEWDEF owns bit 5 and GUARD
 * bit 6, so a new definition containing a guard reads as feat by position.
 * R4: the floor at bit 7 is the only bit always present, so an empty word
 * yields plain - the law cannot invent a claim because it has nothing else to
 * return.  R5 follows: every observation only ADDS a bit, and adding a bit can
 * only lower ctz.
 *
 * No word, path, extension or language appears below.  What counts as a test
 * path, a definition shape or a guard shape lives in the MEASUREMENT.  The law
 * reads the SITUATION of the change, never its content.
 */
#include <stdio.h>
#include <stdint.h>

/* ---- the three authored lanes ---- */
static inline int32_t SHAPE  (int32_t x) { return (x & 31); }  /* -> mask bits 0..4 */
static inline int32_t CONTENT(int32_t x) { return ((x & 32) + (x & 64)); }  /* -> mask bits 5..6 */
static inline int32_t FOCUS  (int32_t x) { return (x >> 7); }  /* the gate          */

/* authored for "which token do I write next", unchanged since */
static inline int32_t EMIT(int32_t m) { return m & (-m); }

#define FLOOR 128                    /* no claim survives -> plain */

int32_t say(int32_t obs)
{
    int32_t gf   = 0 - FOCUS(obs);          /* all-ones only when FOCUSED */
    int32_t mask = SHAPE(obs) + (gf & CONTENT(obs)) + FLOOR;
    return __builtin_ctz(EMIT(mask));       /* rung order IS kind order */
}

/* ========== independent oracle: branchy, shares no expression ========== */
static int oracle(int x)
{
    int inverse = (x>>0)&1, blank = (x>>1)&1, tests = (x>>2)&1;
    int docs = (x>>3)&1, deps = (x>>4)&1, newdef = (x>>5)&1;
    int guard = (x>>6)&1, focused = (x>>7)&1;
    if (inverse) return 0;
    if (blank)   return 1;
    if (tests)   return 2;
    if (docs)    return 3;
    if (deps)    return 4;
    if (focused && newdef) return 5;
    if (focused && guard)  return 6;
    return 7;
}

int main(void)
{
    long vaguer=0, bolder=0, r1=0, r2=0, r3=0, r4=0, r5=0;
    long n[8] = {0,0,0,0,0,0,0,0};
    const int SHAPE_BITS = 0x1F;
    for (int x = 0; x < 256; x++) {
        int k = say(x), o = oracle(x);
        if (k > o) vaguer++;
        if (k < o) bolder++;
        n[k]++;
        if ((x & SHAPE_BITS) && k > 4) r1++;
        if (!((x>>7)&1) && (k == 5 || k == 6)) r2++;
        if (!(x & SHAPE_BITS) && ((x>>7)&1) && ((x>>5)&1) && k != 5) r3++;
        if (!(x & SHAPE_BITS)
            && !(((x>>7)&1) && (((x>>5)&1) || ((x>>6)&1))) && k != 7) r4++;
    }
    for (int x = 0; x < 256; x++)
        for (int b = 0; b < 8; b++)
            if (!((x>>b)&1) && say(x | (1<<b)) > say(x)) r5++;
    printf("  said something vaguer than allowed   %ld\n", vaguer);
    printf("  claimed more than the evidence       %ld\n", bolder);
    printf("  R1 shape outranks content           %ld\n", r1);
    printf("  R2 no diagnosis without focus       %ld\n", r2);
    printf("  R3 feat outranks fix                %ld\n", r3);
    printf("  R4 silence is the floor             %ld\n", r4);
    printf("  R5 monotone                         %ld\n", r5);
    printf("  partition %ld/%ld/%ld/%ld/%ld/%ld/%ld/%ld\n",
           n[0],n[1],n[2],n[3],n[4],n[5],n[6],n[7]);
    long cnt = (n[0]!=128)+(n[1]!=64)+(n[2]!=32)+(n[3]!=16)
             + (n[4]!=8)+(n[5]!=2)+(n[6]!=1)+(n[7]!=5);
    printf("  counts 128/64/32/16/8/2/1/5         %s\n", cnt ? "MISMATCH":"exact");
    const int S[11] = {0xE0,0xA4,0x02,0x82,0x81,0x10,0xC0,0x60,0x80,0x00,0x0C};
    const int E[11] = {5,   2,   1,   1,   0,   4,   6,   7,   7,   7,   2};
    long inc = 0;
    for (int i = 0; i < 11; i++) if (say(S[i]) != E[i]) inc++;
    printf("  the nine situations                 %ld violations\n", inc);
    long t = vaguer+bolder+r1+r2+r3+r4+r5+cnt+inc;
    printf("\n  TOTAL  256 inputs  %ld violations\n", t);
    return t != 0;
}
