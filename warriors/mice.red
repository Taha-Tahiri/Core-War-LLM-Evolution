;redcode-94
;name Mice
;author Chip Wendell
;strategy Self-replicating bomber - creates copies of itself
;
; Mice is a "paper" type warrior that creates multiple copies
; of itself across memory. By having many copies, it becomes
; very hard to kill - you'd need to find and destroy all copies.
;
; Combines replication with bombing for a hybrid strategy.

start   SPL    0, 0         ; Fork a new process
        MOV.I  -1, 1        ; Copy the SPL instruction forward
        JMP    start        ; Keep replicating
