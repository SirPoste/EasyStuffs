package main

import (
	"os"
	"syscall"
)

// hideOwnConsole closes the console window Windows opens on a double click.
// The executable stays a normal console program, like the other tools, so the
// antivirus on a network share does not delete it.
func hideOwnConsole() {
	kernel32 := syscall.NewLazyDLL("kernel32.dll")
	getConsoleWindow := kernel32.NewProc("GetConsoleWindow")
	hwnd, _, _ := getConsoleWindow.Call()
	if hwnd != 0 {
		user32 := syscall.NewLazyDLL("user32.dll")
		showWindow := user32.NewProc("ShowWindow")
		showWindow.Call(hwnd, 0) // SW_HIDE
	}
	freeConsole := kernel32.NewProc("FreeConsole")
	freeConsole.Call()
}

// attachParentConsole connects output to the console that launched the program.
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
