;redcode-94
;name Vampire
;author DRQ Example  
;strategy Converts enemy processes into copies of self
;
; Vampires don't try to kill enemies directly. Instead, they
; plant JMP traps in memory. When an enemy executes the trap,
; it jumps to the vampire's code and becomes a vampire itself.
;
; Very effective against large, slow-moving warriors.

        JMP    start        ; Skip data section
pit     DAT    #0, #0       ; Vampire pit - converted enemies end here
fang    JMP    pit, 0       ; The trap - jumps to pit

start   MOV.I  fang, @ptr   ; Plant a fang (trap)
        ADD.AB #7, ptr      ; Move to next location
        JMP    start        ; Keep planting fangs

ptr     DAT    #0, #10      ; Planting pointer
