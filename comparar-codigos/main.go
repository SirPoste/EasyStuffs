package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
)

func main() {
	if len(os.Args) > 1 {
		attachParentConsole()
	}
	os.Exit(run(os.Args[0], os.Args[1:], os.Stdout, os.Stderr))
}

func run(prog string, args []string, stdout, stderr io.Writer) int {
	name := filepath.Base(prog)
	switch len(args) {
	case 0:
		return serveWeb(stdout, stderr)
	case 2:
		return compareOnce(args[0], args[1], stdout, stderr)
	default:
		fmt.Fprintf(stderr, "Uso: %s\n", name)
		fmt.Fprintf(stderr, "Sem argumentos, abre a pagina para comparar o Serial Number.\n")
		fmt.Fprintf(stderr, "%s <codigo1> <codigo2> compara os dois codigos na consola.\n", name)
		fmt.Fprintf(stderr, "Formato: %s, depois %d digitos (Serial Number) e %d digitos (P). So o Serial Number e comparado.\n", codePrefix, sDigits, pDigits)
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
