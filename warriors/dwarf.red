;redcode-94
;name Dwarf
;author A.K. Dewdney
;strategy Classic bomber - drops DAT bombs at regular intervals
;
; The Dwarf is a "stone" type warrior that bombs memory at regular
; intervals with DAT instructions. When an enemy process tries to
; execute a DAT, it dies.
;
; Bombs every 4th address, eventually covering 25% of the core.

        ADD.AB #4, 3        ; Increment bomb pointer by 4
        MOV.I  2, @2        ; Copy bomb to target address
        JMP    -2           ; Loop back to ADD
bomb    DAT    #0, #0       ; The bomb (kills if executed)
