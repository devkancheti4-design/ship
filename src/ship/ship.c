/* ship.c - THE SHIP LAW. GENERATED; every expression authored by search.
 *
 * For ONE working-tree change, how far may it travel?
 *   3 PUSH    stage, commit, push
 *   2 COMMIT  stage, commit; stop before the network
 *   1 STAGE   stage and write the message file; stop before history
 *   0 NONE    write nothing, not even the index
 *
 *   bit 0 DIRTY      GATE   the tree differs from HEAD
 *   bit 1 SECRET     VETO   added line or staged path has credential shape
 *   bit 2 CONFLICT   VETO   markers present, or mid-merge/rebase/cherry-pick
 *   bit 3 BULK       VETO   >50 files, >5MB, or an untracked binary blob
 *   bit 4 BLIND      EYES   no well-formed summary exists
 *   bit 5 RED        NET    the repository check exited non-zero
 *   bit 6 PROTECTED  NET    protected branch, or detached HEAD
 *   bit 7 FORWARD    GATE   a push would be a fast-forward
 *
 * WHY R1-R4 HOLD STRUCTURALLY
 *
 * The three tiers nest, so they are three bits of one mask in tier order and
 * ctz returns the act with no encoding step.  R1 and R2 need no case: both a
 * veto and a clear DIRTY contribute to mask bit 0, the lowest bit there is, so
 * ctz returns 0 whatever else is set - nothing can outrank them because there
 * is nothing below bit 0.  R3 needs no cap: BLIND owns bit 1 and every network
 * hazard owns bit 2, so an eyes failure is always read first and history is
 * unreachable while it stands.  R4 is the same fact one level up: the network
 * bit sits strictly below the floor at bit 3, and the floor is the only route
 * to PUSH, so PUSH is reachable only when bits 0, 1 and 2 are all silent.  R5
 * follows: a hazard only ADDS a lower bit, which can only lower ctz; a gate
 * only REMOVES one, which can only raise it.
 *
 * No path, branch name, remote name or model name appears below.  What counts
 * as a secret shape, a protected branch or a bulk change lives entirely in the
 * MEASUREMENT.  The law reads the SITUATION of the change, never its content.
 */
#include <stdio.h>
#include <stdint.h>

/* ---- the three authored tier lanes ---- */
static inline int32_t STOP(int32_t x) { return (((x + 14) >> 4) - ((x - 1) >> 4)); }  /* -> mask bit 0 */
static inline int32_t EYES(int32_t x) { return ((1 & (x >> 4)) + (1 & (x >> 4))); }  /* -> mask bit 1 */
static inline int32_t NET (int32_t x) { return ((1 - (4 & (x >> 5))) + (3 | ((x + 96) >> 6))); }  /* -> mask bit 2 */

/* authored for "which token do I write next", unchanged since */
static inline int32_t EMIT(int32_t m) { return m & (-m); }

#define FLOOR 8                       /* nothing objected -> PUSH */

int32_t ship(int32_t obs)
{
    int32_t mask = STOP(obs) + EYES(obs) + NET(obs) + FLOOR;
    return __builtin_ctz(EMIT(mask));      /* tier order IS act order */
}

/* ============ independent oracle: branchy, shares no expression ============ */
static int oracle(int x)
{
    int dirty     = (x >>  0) & 1;
    int secret    = (x >>  1) & 1;
    int conflict  = (x >>  2) & 1;
    int bulk      = (x >>  3) & 1;
    int blind     = (x >>  4) & 1;
    int red       = (x >>  5) & 1;
    int protectd  = (x >>  6) & 1;
    int forward   = (x >>  7) & 1;
    if (!dirty) return 0;
    if (secret) return 0;
    if (conflict) return 0;
    if (bulk) return 0;
    if (blind) return 1;
    if (red) return 2;
    if (protectd) return 2;
    if (!forward) return 2;
    return 3;
}

int main(void)
{
    long further = 0, refused = 0;
    long r1 = 0, r2 = 0, r3 = 0, r4 = 0, r5 = 0;
    long n[4] = {0,0,0,0};
    const int VETO = 2|4|8;
    for (int x = 0; x < 256; x++) {
        int k = ship(x), o = oracle(x);
        if (k > o) further++;
        if (k < o) refused++;
        n[k]++;
        if ((x & VETO) && k != 0) r1++;
        if (!(x & 1) && k != 0) r2++;
        if ((x & 16) && !(x & VETO) && (x & 1) && k > 1) r3++;
        if ((((x & 32) || (x & 64) || !(x & 128)))
            && !(x & VETO) && (x & 1) && !(x & 16) && k > 2) r4++;
    }
    /* R5: hazards never move a change further; gates never move it back */
    const int HAZ[6] = {2,4,8,16,32,64}, GATE[2] = {1,128};
    for (int x = 0; x < 256; x++) {
        for (int i = 0; i < 6; i++)
            if (!(x & HAZ[i]) && ship(x | HAZ[i]) > ship(x)) r5++;
        for (int i = 0; i < 2; i++)
            if (!(x & GATE[i]) && ship(x | GATE[i]) < ship(x)) r5++;
    }
    printf("  travelled further than allowed   %ld\n", further);
    printf("  refused when it must not         %ld\n", refused);
    printf("  R1 veto absolute                 %ld\n", r1);
    printf("  R2 DIRTY gates everything        %ld\n", r2);
    printf("  R3 no history without eyes       %ld\n", r3);
    printf("  R4 no network without ff/green   %ld\n", r4);
    printf("  R5 monotone                      %ld\n", r5);
    printf("  partition  PUSH %ld  COMMIT %ld  STAGE %ld  NONE %ld\n",
           n[3], n[2], n[1], n[0]);
    long cnt = (n[3]!=1) + (n[2]!=7) + (n[1]!=8) + (n[0]!=240);
    printf("  counts 1/7/8/240                 %s\n", cnt ? "MISMATCH" : "exact");

    const int S[12] = {0x83,0x85,0x89,0x91,0xD1,0xB1,0xC1,0x01,0xA1,0x00,0x80,0x81};
    const int W[12] = {0,   0,   0,   1,   1,   1,   2,   2,   2,   0,   0,   3};
    long inc = 0;
    for (int i = 0; i < 12; i++) if (ship(S[i]) != W[i]) inc++;
    printf("  the eight situations             %ld violations\n", inc);
    long total = further+refused+r1+r2+r3+r4+r5+cnt+inc;
    printf("\n  TOTAL  256 inputs  %ld violations\n", total);
    return total != 0;
}
