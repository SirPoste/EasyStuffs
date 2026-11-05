package main

import (
	"os"
	"syscall"
)

// attachParentConsole connects output to the console that launched the program.
// The Windows executable has no console of its own, so a double click goes
// straight to the browser. A comparison started from cmd still prints there.
func attachParentConsole() {
	kernel32 := syscall.NewLazyDLL("kernel32.dll")
	attach := kernel32.NewProc("AttachConsole")
	// ATTACH_PARENT_PROCESS is DWORD(-1).
	r, _, _ := attach.Call(uintptr(0xFFFFFFFF))
	if r == 0 {
		return
	}
	if hout, err := syscall.GetStdHandle(syscall.STD_OUTPUT_HANDLE); err == nil {
		os.Stdout = os.NewFile(uintptr(hout), "stdout")
	}
	if herr, err := syscall.GetStdHandle(syscall.STD_ERROR_HANDLE); err == nil {
		os.Stderr = os.NewFile(uintptr(herr), "stderr")
	}
}
