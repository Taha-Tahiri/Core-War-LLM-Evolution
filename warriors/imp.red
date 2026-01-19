;redcode-94
;name Imp
;author A.K. Dewdney
;strategy The simplest warrior - copies itself forward endlessly
;
; The Imp is the most basic Core War warrior. It consists of a single
; instruction that copies itself one address forward, creating an
; endless chain of MOV instructions marching through memory.
;
; While simple, it's surprisingly hard to kill as it spreads everywhere.

MOV.I 0, 1
