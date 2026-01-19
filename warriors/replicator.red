;redcode-94
;name Paper Tiger
;author DRQ Example
;strategy Fast replicator with multi-threading
;
; This warrior creates many copies of itself using SPL (split).
; Each copy can continue replicating, creating an exponential
; number of processes. Very hard to kill.

        SPL    0, 0         ; Fork new process
        SPL    0, 0         ; Fork again (4 processes now)
        SPL    0, 0         ; 8 processes
copy    MOV.I  <src, <dst   ; Copy code backwards
        DJN    copy, cnt    ; Loop until done
        SPL    @dst, 0      ; Run the copy
        ADD.AB #500, dst    ; Next copy location
        JMP    copy-1       ; Restart copying

src     DAT    #0, #10      ; Source pointer
dst     DAT    #0, #800     ; Destination pointer  
cnt     DAT    #0, #10      ; Copy counter
