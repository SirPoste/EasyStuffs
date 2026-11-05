package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

func main() {
	os.Exit(run(os.Args[0], os.Args[1:], os.Stdin, os.Stdout, os.Stderr))
}

func run(prog string, args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	name := filepath.Base(prog)
	switch len(args) {
	case 0:
		return interactive(stdin, stdout, stderr)
	case 2:
		return compareOnce(args[0], args[1], stdout, stderr)
	default:
		fmt.Fprintf(stderr, "Uso: %s <codigo1> <codigo2>\n", name)
		fmt.Fprintf(stderr, "Sem argumentos, pede os dois codigos no ecra.\n")
		fmt.Fprintf(stderr, "Formato: %s e depois %d digitos (S) e %d digitos (P).\n", codePrefix, sDigits, pDigits)
		return 1
	}
}

func compareOnce(leftRaw, rightRaw string, stdout, stderr io.Writer) int {
	left, err := Parse(leftRaw)
	if err != nil {
		fmt.Fprintf(stderr, "Erro: codigo 1: %v\n", err)
		return 1
	}
	right, err := Parse(rightRaw)
	if err != nil {
		fmt.Fprintf(stderr, "Erro: codigo 2: %v\n", err)
		return 1
	}
	result := Compare(left, right)
	fmt.Fprint(stdout, Report(result))
	if result.Equal() {
		return 0
	}
	return 2
}

func interactive(stdin io.Reader, stdout, stderr io.Writer) int {
	in := bufio.NewReader(stdin)
	fmt.Fprintln(stdout, "Comparar dois codigos de barras")
	fmt.Fprintf(stdout, "Formato: %s + %d digitos (S) + %d digitos (P)\n", codePrefix, sDigits, pDigits)
	fmt.Fprintln(stdout, "Enter vazio para sair.")
	for {
		fmt.Fprint(stdout, "Primeiro codigo: ")
		first, ok := readLine(in)
		if !ok || first == "" {
			fmt.Fprintln(stdout)
			return 0
		}
		fmt.Fprint(stdout, "Segundo codigo: ")
		second, ok := readLine(in)
		if !ok || second == "" {
			fmt.Fprintln(stdout)
			return 0
		}
		fmt.Fprintln(stdout)
		compareOnce(first, second, stdout, stderr)
		fmt.Fprintln(stdout)
	}
}

func readLine(in *bufio.Reader) (string, bool) {
	line, err := in.ReadString('\n')
	if line == "" && err != nil {
		return "", false
	}
	return strings.TrimSpace(line), true
}
