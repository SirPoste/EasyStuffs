package main

import (
	"bufio"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

func main() {
	rootFlag := flag.String("root", "", "pasta raiz (por omissao: pasta do executavel)")
	modeFlag := flag.String("mode", "", "all = copiar/atualizar em todas as pastas; existing = so substituir as que ja existem")
	yesFlag := flag.Bool("yes", false, "nao pedir confirmacao")
	flag.Parse()

	noPause = *yesFlag
	enableWindowsUTF8()

	root := strings.TrimSpace(*rootFlag)
	if root == "" {
		var err error
		root, err = executableDir()
		if err != nil {
			fatal("nao foi possivel determinar a pasta do executavel: %v", err)
		}
	}

	fmt.Println("============================================")
	fmt.Println("  Atualizador de Imagens")
	fmt.Println("============================================")
	fmt.Println()
	fmt.Printf("Pasta raiz : %s\n", root)
	fmt.Printf("Origem     : %s\n", filepath.Join(root, updateDirName))
	fmt.Println()

	mode := Mode(*modeFlag)
	if mode == "" {
		mode = chooseMode(*yesFlag)
	}

	label := "copiar e atualizar em TODAS as pastas e subpastas"
	if mode == ModeExisting {
		label = "atualizar apenas imagens com o mesmo nome"
	}
	fmt.Printf("Modo       : %s\n\n", label)

	if !*yesFlag && !confirm("Continuar?") {
		fmt.Println("Operacao cancelada.")
		pause()
		return
	}

	res, err := SyncImages(Options{Root: root, Mode: mode})
	if err != nil {
		fatal("%v", err)
	}

	printResult(res)
	writeLog(root, res)

	if len(res.Errors) > 0 {
		pause()
		os.Exit(1)
	}
	pause()
}

func chooseMode(autoYes bool) Mode {
	if autoYes {
		return ModeAll
	}
	fmt.Println("O que pretende fazer?")
	fmt.Println("  1) Copiar/atualizar as imagens da pasta \"update\"")
	fmt.Println("     em TODAS as outras pastas e subpastas")
	fmt.Println("  2) Atualizar apenas ficheiros que ja existem com o mesmo nome")
	fmt.Println("  0) Sair")
	fmt.Println()

	for {
		fmt.Print("Escolha [1]: ")
		line := readLine()
		if line == "" || line == "1" {
			return ModeAll
		}
		if line == "2" {
			return ModeExisting
		}
		if line == "0" {
			fmt.Println("Operacao cancelada.")
			pause()
			os.Exit(0)
		}
		fmt.Println("Opcao invalida.")
	}
}

func printResult(res Result) {
	fmt.Println()
	fmt.Println("--------------------------------------------")
	fmt.Printf("Imagens na pasta update : %d\n", res.SourceImages)
	fmt.Printf("Pastas de destino       : %d\n", res.TargetDirs)
	fmt.Printf("Copiadas (novas)        : %d\n", res.Copied)
	fmt.Printf("Atualizadas             : %d\n", res.Updated)
	fmt.Printf("Ja estavam iguais       : %d\n", res.Skipped)
	fmt.Printf("Erros                   : %d\n", len(res.Errors))
	fmt.Println("--------------------------------------------")

	for _, w := range res.Warnings {
		fmt.Printf("Aviso: %s\n", w)
	}
	for _, e := range res.Errors {
		fmt.Printf("Erro : %s\n", e)
	}
	if len(res.Errors) == 0 {
		fmt.Println("Concluido.")
	}
}

func writeLog(root string, res Result) {
	path := filepath.Join(root, "atualizacao-imagens.log")
	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		fmt.Printf("Nao foi possivel gravar o log: %v\n", err)
		return
	}
	defer f.Close()

	fmt.Fprintf(f, "\n===== %s =====\n", time.Now().Format("2006-01-02 15:04:05"))
	fmt.Fprintf(f, "imagens=%d pastas=%d copiadas=%d atualizadas=%d iguais=%d erros=%d\n",
		res.SourceImages, res.TargetDirs, res.Copied, res.Updated, res.Skipped, len(res.Errors))
	for _, w := range res.Warnings {
		fmt.Fprintf(f, "aviso: %s\n", w)
	}
	for _, op := range res.Ops {
		if op.Action == "skipped" {
			continue
		}
		fmt.Fprintf(f, "%s: %s -> %s\n", op.Action, op.Source, op.Destination)
	}
	for _, e := range res.Errors {
		fmt.Fprintf(f, "erro: %s\n", e)
	}
	fmt.Printf("\nLog gravado em: %s\n", path)
}

func executableDir() (string, error) {
	exe, err := os.Executable()
	if err != nil {
		return "", err
	}
	exe, err = filepath.EvalSymlinks(exe)
	if err != nil {
		return "", err
	}
	return filepath.Dir(exe), nil
}

func confirm(question string) bool {
	fmt.Printf("%s [s/N]: ", question)
	line := strings.ToLower(readLine())
	return line == "s" || line == "sim" || line == "y" || line == "yes"
}

func readLine() string {
	scanner := bufio.NewScanner(os.Stdin)
	if !scanner.Scan() {
		return ""
	}
	return strings.TrimSpace(scanner.Text())
}

var noPause bool

func pause() {
	if noPause || !isInteractive() {
		return
	}
	fmt.Println()
	fmt.Print("Prima Enter para sair...")
	bufio.NewReader(os.Stdin).ReadBytes('\n')
}

func isInteractive() bool {
	st, err := os.Stdin.Stat()
	if err != nil {
		return false
	}
	return st.Mode()&os.ModeCharDevice != 0
}

func fatal(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "Erro: "+format+"\n", args...)
	pause()
	os.Exit(1)
}

func enableWindowsUTF8() {
	if runtime.GOOS != "windows" {
		return
	}
	// Best-effort; older consoles may still show garbled accents.
	os.Setenv("PYTHONIOENCODING", "utf-8")
}
