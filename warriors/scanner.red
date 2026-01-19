;redcode-94
;name Simple Scanner
;author DRQ Example
;strategy Scans for enemies, then bombs their location
;
; Scanners look for non-zero memory addresses (enemy code)
; and then attack that location with bombs. More sophisticated
; than blind bombing but slower to start attacking.

scan    ADD.AB #15, ptr     ; Move scan pointer
        MOV.I  @ptr, temp   ; Read target address
        SNE.I  temp, empty  ; Skip if not empty (found enemy!)
        JMP    scan         ; Keep scanning
        
        ; Found something! Attack it
attack  MOV.I  bomb, @ptr   ; Drop bomb
        ADD.AB #1, ptr      ; Move to next address
        DJN    attack, count ; Repeat 5 times
        JMP    scan         ; Resume scanning

bomb    DAT    #0, #0       ; Bomb
ptr     DAT    #0, #100     ; Scan pointer
temp    DAT    #0, #0       ; Temporary storage
empty   DAT    #0, #0       ; Empty pattern to match
count   DAT    #0, #5       ; Bomb count
