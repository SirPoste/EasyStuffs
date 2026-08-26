package main

import (
	"bufio"
	"fmt"
	"os"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "Uso: %s <ficheiro> [ficheiro2 ...]\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "Esvazia o conteudo do(s) ficheiro(s) indicado(s), sem os apagar.\n")
		fmt.Fprintf(os.Stderr, "Pode arrastar um ficheiro para este programa ou indica-lo na linha de comandos.\n")
		fmt.Fprint(os.Stderr, "Prima Enter para sair...")
		_, _ = bufio.NewReader(os.Stdin).ReadBytes('\n')
		os.Exit(1)
	}

	failed := false
	for _, path := range os.Args[1:] {
		if err := emptyFile(path); err != nil {
			fmt.Fprintf(os.Stderr, "Erro: %s: %v\n", path, err)
			failed = true
			continue
		}
		fmt.Printf("Ficheiro esvaziado: %s\n", path)
	}
	if failed {
		os.Exit(1)
	}
}

func emptyFile(path string) error {
	info, err := os.Lstat(path)
	if err != nil {
		return err
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return fmt.Errorf("recusado: e um atalho/symlink")
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("nao e um ficheiro regular")
	}

	f, err := os.OpenFile(path, os.O_WRONLY|os.O_TRUNC, 0)
	if err != nil {
		return err
	}
	return f.Close()
}
